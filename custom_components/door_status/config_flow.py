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
    DEFAULT_MIN_COLOR,
    DEFAULT_MAX_COLOR,
    DEFAULT_IDLE_INTERVAL,
    DEFAULT_ACTIVE_INTERVAL,
    DEFAULT_CHANGE_THRESHOLD,
    DEFAULT_CLOSED_POSITION,
    DEFAULT_OPEN_POSITION,
    DEFAULT_TRANSITION_THRESHOLD,
    DEFAULT_STATE_TIMEOUT,
)

def color_tuple(value: str) -> tuple[int, int, int]:
    """Convert color string to tuple."""
    try:
        r, g, b = map(int, value.split(','))
        return (r, g, b)
    except ValueError:
        raise vol.Invalid("Color must be in format 'R,G,B'")

class DoorStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Door Status."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Validate camera exists
            camera_state = self.hass.states.get(user_input[CONF_CAMERA_ENTITY])
            if not camera_state or not camera_state.domain == "camera":
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
                return self.async_create_entry(
                    title=f"Door Status {user_input[CONF_CAMERA_ENTITY]}",
                    data=user_input,
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
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DoorStatusOptionsFlow(config_entry)

class DoorStatusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Door Status."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Required(
                CONF_POINT_A,
                default=self.config_entry.options.get(
                    CONF_POINT_A,
                    self.config_entry.data.get(CONF_POINT_A, "0,0")
                )
            ): str,
            vol.Required(
                CONF_POINT_B,
                default=self.config_entry.options.get(
                    CONF_POINT_B,
                    self.config_entry.data.get(CONF_POINT_B, "100,100")
                )
            ): str,
            vol.Required(
                CONF_MIN_COLOR,
                default=self.config_entry.options.get(
                    CONF_MIN_COLOR,
                    self.config_entry.data.get(CONF_MIN_COLOR, "0,0,0")
                )
            ): str,
            vol.Required(
                CONF_MAX_COLOR,
                default=self.config_entry.options.get(
                    CONF_MAX_COLOR,
                    self.config_entry.data.get(CONF_MAX_COLOR, "255,255,255")
                )
            ): str,
            vol.Required(
                CONF_IDLE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_IDLE_INTERVAL,
                    self.config_entry.data.get(CONF_IDLE_INTERVAL, DEFAULT_IDLE_INTERVAL)
                )
            ): int,
            vol.Required(
                CONF_ACTIVE_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_ACTIVE_INTERVAL,
                    self.config_entry.data.get(CONF_ACTIVE_INTERVAL, DEFAULT_ACTIVE_INTERVAL)
                )
            ): int,
            vol.Required(
                CONF_CHANGE_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_CHANGE_THRESHOLD,
                    self.config_entry.data.get(CONF_CHANGE_THRESHOLD, DEFAULT_CHANGE_THRESHOLD)
                )
            ): int,
            vol.Required(
                CONF_CLOSED_POSITION,
                default=self.config_entry.options.get(
                    CONF_CLOSED_POSITION,
                    self.config_entry.data.get(CONF_CLOSED_POSITION, DEFAULT_CLOSED_POSITION)
                )
            ): int,
            vol.Required(
                CONF_OPEN_POSITION,
                default=self.config_entry.options.get(
                    CONF_OPEN_POSITION,
                    self.config_entry.data.get(CONF_OPEN_POSITION, DEFAULT_OPEN_POSITION)
                )
            ): int,
            vol.Required(
                CONF_TRANSITION_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_TRANSITION_THRESHOLD,
                    self.config_entry.data.get(CONF_TRANSITION_THRESHOLD, DEFAULT_TRANSITION_THRESHOLD)
                )
            ): int,
            vol.Required(
                CONF_STATE_TIMEOUT,
                default=self.config_entry.options.get(
                    CONF_STATE_TIMEOUT,
                    self.config_entry.data.get(CONF_STATE_TIMEOUT, DEFAULT_STATE_TIMEOUT)
                )
            ): int,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )