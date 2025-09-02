"""The Door Status integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Door Status component."""
    # Register recorder exclusion filter
    if not hass.data.get(DOMAIN):
        hass.data[DOMAIN] = {}
        
        @callback
        def _exclude_door_status_entities(event: Event) -> None:
            """Exclude door status entities from recorder."""
            if event.data.get("action") == "entity_registry_updated":
                entity_id = event.data["entity_id"]
                if entity_id.startswith(f"sensor.{DOMAIN}_"):
                    hass.data[DOMAIN][entity_id] = True
                    async_dispatcher_send(
                        hass,
                        "exclude_entity_from_recorder",
                        entity_id,
                        True
                    )

        hass.bus.async_listen("entity_registry_updated", _exclude_door_status_entities)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Door Status from a config entry."""
    async def _check_camera_available(_event=None):
        camera_entity = entry.data.get("camera_entity")
        if hass.states.get(camera_entity) is None or \
           hass.states.get(camera_entity).state == "unavailable":
            _LOGGER.warning("Camera still unavailable during startup")
        else:
            _LOGGER.info("Camera became available, updating Door Status sensor")
            await hass.config_entries.async_reload(entry.entry_id)

    hass.bus.async_listen_once("homeassistant_started", _check_camera_available)

    # ✅ Forward the setup to the sensor platform using the new API
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # Setup reload service
    async def async_reload_config_entry(call):
        """Reload Door Status config entry."""
        await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(
        DOMAIN,
        f"reload_{entry.entry_id}",
        async_reload_config_entry
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)