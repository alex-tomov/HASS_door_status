"""Config flow for Door Status."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
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
    CONF_SNAPSHOT,
    CONF_CROP,
    CONF_ROTATE_ANGLE,
    DEFAULT_MIN_COLOR,
    DEFAULT_MAX_COLOR,
    DEFAULT_IDLE_INTERVAL,
    DEFAULT_ACTIVE_INTERVAL,
    DEFAULT_CHANGE_THRESHOLD,
    DEFAULT_CLOSED_POSITION,
    DEFAULT_OPEN_POSITION,
    DEFAULT_TRANSITION_THRESHOLD,
    DEFAULT_STATE_TIMEOUT,
    DEFAULT_CROP,
    DEFAULT_ROTATE_ANGLE
)

def color_tuple(value: str) -> tuple[int, int, int]:
    """Convert color string to tuple."""
    try:
        r, g, b = map(int, value.split(','))
        return (r, g, b)
    except ValueError:
        raise vol.Invalid("Color must be in format 'R,G,B'")

def crop_list(value: str) -> list[int]:
    """Convert crop string to list."""
    try:
        return list(map(int, value.split(',')))
    except ValueError:
        raise vol.Invalid("Crop must be in format 'left,top,right,bottom'")

class DoorStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Door Status."""

    VERSION = 2
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Validate camera exists
            camera_state = self.hass.states.get(user_input[CONF_CAMERA_ENTITY])
            if not camera_state or camera_state.domain != "camera":
                errors[CONF_CAMERA_ENTITY] = "invalid_camera"
            
            # Validate coordinates
            try:
                point_a = tuple(map(int, user_input[CONF_POINT_A].split(',')))
                point_b = tuple(map(int, user_input[CONF_POINT_B].split(',')))
                if len(point_a) != 2 or len(point_b) != 2:
                    errors["base"] = "invalid_coordinates"
            except ValueError:
                errors["base"] = "invalid_coordinates"
                
            if not errors:
                # Prepare snapshot config
                snapshot_config = {}
                if user_input.get(CONF_CROP):
                    snapshot_config[CONF_CROP] = user_input[CONF_CROP]
                if user_input.get(CONF_ROTATE_ANGLE, DEFAULT_ROTATE_ANGLE) != DEFAULT_ROTATE_ANGLE:
                    snapshot_config[CONF_ROTATE_ANGLE] = user_input[CONF_ROTATE_ANGLE]
                
                return self.async_create_entry(
                    title=f"Door Status {user_input[CONF_CAMERA_ENTITY]}",
                    data={
                        CONF_CAMERA_ENTITY: user_input[CONF_CAMERA_ENTITY],
                        CONF_POINT_A: user_input[CONF_POINT_A],
                        CONF_POINT_B: user_input[CONF_POINT_B],
                        CONF_MIN_COLOR: user_input[CONF_MIN_COLOR],
                        CONF_MAX_COLOR: user_input[CONF_MAX_COLOR],
                        CONF_IDLE_INTERVAL: user_input[CONF_IDLE_INTERVAL],
                        CONF_ACTIVE_INTERVAL: user_input[CONF_ACTIVE_INTERVAL],
                        CONF_CHANGE_THRESHOLD: user_input[CONF_CHANGE_THRESHOLD],
                        CONF_CLOSED_POSITION: user_input[CONF_CLOSED_POSITION],
                        CONF_OPEN_POSITION: user_input[CONF_OPEN_POSITION],
                        CONF_TRANSITION_THRESHOLD: user_input[CONF_TRANSITION_THRESHOLD],
                        CONF_STATE_TIMEOUT: user_input[CONF_STATE_TIMEOUT],
                        CONF_SNAPSHOT: snapshot_config,
                    },
                )

        data_schema = vol.Schema({
            vol.Required(CONF_CAMERA_ENTITY): str,
            vol.Required(CONF_POINT_A, default="0,0"): str,
            vol.Required(CONF_POINT_B, default="100,100"): str,
            vol.Required(CONF_MIN_COLOR, default="0,0,0"): str,
            vol.Required(CONF_MAX_COLOR, default="255,255,255"): str,
            vol.Required(CONF_IDLE_INTERVAL, default=DEFAULT_IDLE_INTERVAL): int,
            vol.Required(CONF_ACTIVE_INTERVAL, default=DEFAULT_ACTIVE_INTERVAL): int,
            vol.Required(CONF_CHANGE_THRESHOLD, default=DEFAULT_CHANGE_THRESHOLD): int,
            vol.Required(CONF_CLOSED_POSITION, default=DEFAULT_CLOSED_POSITION): int,
            vol.Required(CONF_OPEN_POSITION, default=DEFAULT_OPEN_POSITION): int,
            vol.Required(CONF_TRANSITION_THRESHOLD, default=DEFAULT_TRANSITION_THRESHOLD): int,
            vol.Required(CONF_STATE_TIMEOUT, default=DEFAULT_STATE_TIMEOUT): int,
            vol.Optional(CONF_CROP): str,
            vol.Optional(CONF_ROTATE_ANGLE, default=DEFAULT_ROTATE_ANGLE): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return DoorStatusOptionsFlowHandler(config_entry)

class DoorStatusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Door Status."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # Update both options and data to ensure immediate effect
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
                options=user_input
            )
            return self.async_create_entry(title="", data=user_input)

        # Get current options or use defaults from config entry data
        options = self.config_entry.options or {}
        data = {**self.config_entry.data, **options}
        snapshot_config = data.get(CONF_SNAPSHOT, {})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_POINT_A,
                    default=data.get(CONF_POINT_A, "0,0")
                ): str,
                vol.Required(
                    CONF_POINT_B,
                    default=data.get(CONF_POINT_B, "100,100")
                ): str,
                vol.Required(
                    CONF_MIN_COLOR,
                    default=data.get(CONF_MIN_COLOR, "0,0,0")
                ): str,
                vol.Required(
                    CONF_MAX_COLOR,
                    default=data.get(CONF_MAX_COLOR, "255,255,255")
                ): str,
                vol.Required(
                    CONF_IDLE_INTERVAL,
                    default=data.get(CONF_IDLE_INTERVAL, DEFAULT_IDLE_INTERVAL)
                ): int,
                vol.Required(
                    CONF_ACTIVE_INTERVAL,
                    default=data.get(CONF_ACTIVE_INTERVAL, DEFAULT_ACTIVE_INTERVAL)
                ): int,
                vol.Required(
                    CONF_CHANGE_THRESHOLD,
                    default=data.get(CONF_CHANGE_THRESHOLD, DEFAULT_CHANGE_THRESHOLD)
                ): int,
                vol.Required(
                    CONF_CLOSED_POSITION,
                    default=data.get(CONF_CLOSED_POSITION, DEFAULT_CLOSED_POSITION)
                ): int,
                vol.Required(
                    CONF_OPEN_POSITION,
                    default=data.get(CONF_OPEN_POSITION, DEFAULT_OPEN_POSITION)
                ): int,
                vol.Required(
                    CONF_TRANSITION_THRESHOLD,
                    default=data.get(CONF_TRANSITION_THRESHOLD, DEFAULT_TRANSITION_THRESHOLD)
                ): int,
                vol.Required(
                    CONF_STATE_TIMEOUT,
                    default=data.get(CONF_STATE_TIMEOUT, DEFAULT_STATE_TIMEOUT)
                ): int,
                vol.Optional(
                    CONF_CROP,
                    default=snapshot_config.get(CONF_CROP, "")
                ): str,
                vol.Optional(
                    CONF_ROTATE_ANGLE,
                    default=snapshot_config.get(CONF_ROTATE_ANGLE, DEFAULT_ROTATE_ANGLE)
                ): int,
            }),
        )