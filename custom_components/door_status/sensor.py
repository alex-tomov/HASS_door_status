"""Sensor platform for Door Status."""
from __future__ import annotations

import logging
import numpy as np
from PIL import Image
import io
import asyncio
from datetime import timedelta
from typing import Any, Tuple

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.camera import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_DOOR_STATUS_UPDATED,
    CONF_CAMERA_ENTITY,
    CONF_POINT_A,
    CONF_POINT_B,
    CONF_MIN_COLOR,
    CONF_MAX_COLOR,
    CONF_IDLE_INTERVAL,
    CONF_ACTIVE_INTERVAL,
    CONF_CHANGE_THRESHOLD,
    CONF_CLOSED_POSITION,
    CONF_OPEN_POSITION,
    CONF_TRANSITION_THRESHOLD,
    CONF_STATE_TIMEOUT,
    STATE_OPEN,
    STATE_CLOSED,
    STATE_OPENING,
    STATE_CLOSING,
    STATE_PARTIALLY_OPEN,
    STATE_UNKNOWN,
    NEXT_ACTION_OPEN,
    NEXT_ACTION_CLOSE,
    NEXT_ACTION_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    async_add_entities([DoorStatusSensor(hass, config_entry)])

class DoorStatusSensor(SensorEntity, RestoreEntity):
    """Representation of a Door Status Sensor."""

    _attr_should_poll = False  # We'll handle updates manually
    _attr_icon = "mdi:door"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the sensor."""
        self._hass = hass
        self._config_entry = config_entry
        self._percent_value: float | None = None
        self._door_state: str = STATE_UNKNOWN
        self._next_action: str = NEXT_ACTION_UNKNOWN
        self._last_percent: float | None = None
        self._last_update_time = dt_util.utcnow()
        self._state_stable_since = dt_util.utcnow()
        self._unsub_update = None
        self._active_mode = False
        self._camera_entity = config_entry.data[CONF_CAMERA_ENTITY]
        self._state_history = []
        self._max_history_length = 20
        
        # Parse configuration
        self._point_a = self._parse_coordinates(config_entry.data[CONF_POINT_A])
        self._point_b = self._parse_coordinates(config_entry.data[CONF_POINT_B])
        self._min_color = self._parse_color(config_entry.data[CONF_MIN_COLOR])
        self._max_color = self._parse_color(config_entry.data[CONF_MAX_COLOR])
        self._idle_interval = config_entry.data[CONF_IDLE_INTERVAL]
        self._active_interval = config_entry.data[CONF_ACTIVE_INTERVAL]
        self._change_threshold = config_entry.data[CONF_CHANGE_THRESHOLD]
        self._closed_position = config_entry.data[CONF_CLOSED_POSITION]
        self._open_position = config_entry.data[CONF_OPEN_POSITION]
        self._transition_threshold = config_entry.data[CONF_TRANSITION_THRESHOLD]
        self._state_timeout = config_entry.data[CONF_STATE_TIMEOUT]
        
        self._attr_name = f"Door Status {self._camera_entity}"
        self._attr_unique_id = config_entry.entry_id
        self._available = False

    def _parse_coordinates(self, coord_str: str) -> tuple[int, int]:
        """Parse coordinates from string 'x,y' to tuple (x,y)."""
        try:
            x, y = map(int, coord_str.split(','))
            return (x, y)
        except ValueError as e:
            _LOGGER.error("Invalid coordinates format: %s", coord_str)
            raise ValueError(f"Invalid coordinates format: {coord_str}") from e

    def _parse_color(self, color_str: str) -> tuple[int, int, int]:
        """Parse color from string 'R,G,B' to tuple (R,G,B)."""
        try:
            r, g, b = map(int, color_str.split(','))
            return (r, g, b)
        except ValueError as e:
            _LOGGER.error("Invalid color format: %s", color_str)
            raise ValueError(f"Invalid color format: {color_str}") from e

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        # Restore previous state if available
        if (state := await self.async_get_last_state()):
            try:
                self._door_state = state.state
                self._percent_value = float(state.attributes.get('percent'))
                self._next_action = state.attributes.get('next_action', NEXT_ACTION_UNKNOWN)
                self._last_percent = float(state.attributes.get('last_percent', self._percent_value))
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid stored state: %s", state.state)
                self._percent_value = None
                self._door_state = STATE_UNKNOWN
                self._next_action = NEXT_ACTION_UNKNOWN
                self._last_percent = None
        
        # Start the update loop
        self._schedule_update()

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed."""
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None

    def _schedule_update(self):
        """Schedule the next update."""
        if self._unsub_update:
            self._unsub_update()
        
        interval = self._active_interval if self._active_mode else self._idle_interval
        self._unsub_update = async_track_time_interval(
            self._hass,
            self._async_update,
            timedelta(seconds=interval)
        )

    async def _async_update(self, now=None):
        """Fetch new state data for the sensor."""
        try:
            self._available = False
            
            # Verify camera exists and is available
            camera_state = self._hass.states.get(self._camera_entity)
            if not camera_state or camera_state.state == "unavailable":
                _LOGGER.warning("Camera entity %s is unavailable", self._camera_entity)
                return

            # Get camera image with timeout
            image = await asyncio.wait_for(
                async_get_image(self._hass, self._camera_entity),
                timeout=10.0
            )
            
            if not image or not image.content:
                _LOGGER.warning("No image data received from camera %s", self._camera_entity)
                return

            # Convert to PIL Image
            img_data = io.BytesIO(image.content)
            try:
                with Image.open(img_data) as img:
                    img_array = np.array(img.convert('RGB'))  # Ensure RGB format
            except Exception as e:
                _LOGGER.error("Error converting image: %s", str(e))
                return

            # Validate image array
            if not isinstance(img_array, np.ndarray) or len(img_array.shape) != 3:
                _LOGGER.error("Invalid image array format")
                return

            # Get pixels along the line
            try:
                pixels = self._get_line_pixels(img_array, self._point_a, self._point_b)
                if len(pixels) == 0:
                    _LOGGER.warning("No pixels found along the specified line")
                    return
            except Exception as e:
                _LOGGER.error("Error getting line pixels: %s", str(e))
                return

            # Calculate match percentage with the color range
            try:
                # Check if pixels are within the min/max color range
                in_range = np.all(
                    (pixels >= self._min_color) & (pixels <= self._max_color),
                    axis=1
                )
                match_percent = (np.sum(in_range) / len(pixels)) * 100
                current_percent = round(float(match_percent), 1)
                
                # Store in history (limited length)
                self._state_history.append(current_percent)
                if len(self._state_history) > self._max_history_length:
                    self._state_history.pop(0)
                
                # Determine if we should switch to active mode
                if self._last_percent is not None:
                    change = abs(current_percent - self._last_percent)
                    if change >= self._change_threshold:
                        if not self._active_mode:
                            self._active_mode = True
                            self._schedule_update()
                            _LOGGER.debug("Switched to active mode due to change: %.1f%%", change)
                    elif self._active_mode:
                        self._active_mode = False
                        self._schedule_update()
                        _LOGGER.debug("Switched back to idle mode")
                
                # Update internal state
                self._last_percent = self._percent_value
                self._percent_value = current_percent
                self._last_update_time = dt_util.utcnow()
                self._available = True
                
                # Determine if we should update HA state
                state_changed = False
                if self._door_state == STATE_UNKNOWN:  # First update
                    state_changed = True
                else:
                    change = abs(current_percent - (self._last_percent or current_percent))
                    time_since_last_change = (dt_util.utcnow() - self._state_stable_since).total_seconds()
                    
                    # Significant change or timeout
                    if change >= self._transition_threshold or time_since_last_change > self._state_timeout:
                        state_changed = True
                
                if state_changed:
                    old_state = self._door_state
                    self._update_door_state()
                    self._state_stable_since = dt_util.utcnow()
                    
                    # Only write to HA if state changed
                    if self._door_state != old_state:
                        self.async_write_ha_state()
                        
                        # Fire event for significant state changes
                        self._hass.bus.fire(
                            EVENT_DOOR_STATUS_UPDATED,
                            {
                                "percent": self._percent_value,
                                "state": self._door_state,
                                "next_action": self._next_action,
                                "entity_id": self.entity_id,
                                "camera_entity": self._camera_entity
                            }
                        )
                    
                    _LOGGER.debug("State changed: %.1f%%, Door state: %s, Next action: %s", 
                                 current_percent, self._door_state, self._next_action)
                else:
                    _LOGGER.debug("State unchanged: %.1f%% (last: %.1f%%)", 
                                 current_percent, self._last_percent or current_percent)
                
            except Exception as e:
                _LOGGER.error("Error calculating match percentage: %s", str(e))
                return

        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout getting image from camera %s", self._camera_entity)
        except Exception as e:
            _LOGGER.error("Error in async_update: %s", str(e), exc_info=True)

    def _update_door_state(self):
        """Update the door state and next action based on current and previous values."""
        if self._percent_value is None or self._last_percent is None:
            self._door_state = STATE_UNKNOWN
            self._next_action = NEXT_ACTION_UNKNOWN
            return
        
        change = self._percent_value - (self._last_percent or self._percent_value)
        moving = abs(change) >= self._transition_threshold
        
        # Check if door is fully open or closed
        if self._percent_value <= self._open_position + self._transition_threshold:
            self._door_state = STATE_OPEN
            self._next_action = NEXT_ACTION_CLOSE
        elif self._percent_value >= self._closed_position - self._transition_threshold:
            self._door_state = STATE_CLOSED
            self._next_action = NEXT_ACTION_OPEN
        # Check if door is moving
        elif moving:
            if change > 0:
                self._door_state = STATE_CLOSING
                self._next_action = NEXT_ACTION_OPEN
            else:
                self._door_state = STATE_OPENING
                self._next_action = NEXT_ACTION_CLOSE
        # Door is partially open and not moving
        elif self._percent_value > self._open_position + self._transition_threshold:
            self._door_state = STATE_PARTIALLY_OPEN
            # Determine next action based on last movement direction
            if self._door_state == STATE_OPENING:
                self._next_action = NEXT_ACTION_CLOSE
            elif self._door_state == STATE_CLOSING:
                self._next_action = NEXT_ACTION_OPEN
            else:
                # If we don't know last direction, guess based on position
                if self._percent_value > (self._closed_position + self._open_position) / 2:
                    self._next_action = NEXT_ACTION_OPEN
                else:
                    self._next_action = NEXT_ACTION_CLOSE
        # No significant change
        else:
            # Keep previous state if it was opening/closing/partially open
            if self._door_state not in [STATE_OPENING, STATE_CLOSING, STATE_PARTIALLY_OPEN]:
                # If near open/closed threshold, maintain that state
                if self._percent_value <= self._open_position + (2 * self._transition_threshold):
                    self._door_state = STATE_OPEN
                    self._next_action = NEXT_ACTION_CLOSE
                elif self._percent_value >= self._closed_position - (2 * self._transition_threshold):
                    self._door_state = STATE_CLOSED
                    self._next_action = NEXT_ACTION_OPEN
                else:
                    self._door_state = STATE_UNKNOWN
                    self._next_action = NEXT_ACTION_UNKNOWN

    @property
    def state(self) -> str:
        """Return the door state as the primary state value."""
        return self._door_state if self._door_state is not None else STATE_UNKNOWN

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "percent": self._percent_value,
            "next_action": self._next_action,
            "last_percent": self._last_percent,
            "last_update": self._state_stable_since.isoformat(),
            "active_mode": self._active_mode,
            "history_size": len(self._state_history),
            "min_color": self._min_color,
            "max_color": self._max_color,
            "point_a": self._point_a,
            "point_b": self._point_b,
            "closed_position": self._closed_position,
            "open_position": self._open_position,
            "transition_threshold": self._transition_threshold,
            "state_timeout": self._state_timeout,
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    async def async_update_config(self, new_config: dict) -> None:
        """Update the sensor configuration."""
        # Update all configurable parameters
        if CONF_POINT_A in new_config:
            self._point_a = self._parse_coordinates(new_config[CONF_POINT_A])
        if CONF_POINT_B in new_config:
            self._point_b = self._parse_coordinates(new_config[CONF_POINT_B])
        if CONF_MIN_COLOR in new_config:
            self._min_color = self._parse_color(new_config[CONF_MIN_COLOR])
        if CONF_MAX_COLOR in new_config:
            self._max_color = self._parse_color(new_config[CONF_MAX_COLOR])
        if CONF_IDLE_INTERVAL in new_config:
            self._idle_interval = new_config[CONF_IDLE_INTERVAL]
        if CONF_ACTIVE_INTERVAL in new_config:
            self._active_interval = new_config[CONF_ACTIVE_INTERVAL]
        if CONF_CHANGE_THRESHOLD in new_config:
            self._change_threshold = new_config[CONF_CHANGE_THRESHOLD]
        if CONF_CLOSED_POSITION in new_config:
            self._closed_position = new_config[CONF_CLOSED_POSITION]
        if CONF_OPEN_POSITION in new_config:
            self._open_position = new_config[CONF_OPEN_POSITION]
        if CONF_TRANSITION_THRESHOLD in new_config:
            self._transition_threshold = new_config[CONF_TRANSITION_THRESHOLD]
        if CONF_STATE_TIMEOUT in new_config:
            self._state_timeout = new_config[CONF_STATE_TIMEOUT]
        
        # Reschedule updates if interval changed
        self._schedule_update()
        
        # Force immediate update with new settings
        await self._async_update()

    def _get_line_pixels(self, img_array: np.ndarray, point_a: tuple[int, int], point_b: tuple[int, int]) -> np.ndarray:
        """Get pixels along a line using Bresenham's algorithm with bounds checking."""
        height, width = img_array.shape[:2]
        x0, y0 = point_a
        x1, y1 = point_b
        pixels = []

        # Clip coordinates to image bounds
        x0 = max(0, min(x0, width - 1))
        y0 = max(0, min(y0, height - 1))
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = -1 if x0 > x1 else 1
        sy = -1 if y0 > y1 else 1

        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if 0 <= y < height and 0 <= x < width:
                    pixels.append(img_array[y, x])
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if 0 <= y < height and 0 <= x < width:
                    pixels.append(img_array[y, x])
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy

        if 0 <= y < height and 0 <= x < width:
            pixels.append(img_array[y, x])

        return np.array(pixels)