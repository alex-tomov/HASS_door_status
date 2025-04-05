"""Migrations for the Door Status integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    if config_entry.version == 1:
        # Migration from version 1 to 2
        new_data = {**config_entry.data}
        
        # Add default values for new fields if missing
        new_data.setdefault(CONF_MIN_COLOR, "0,0,0")
        new_data.setdefault(CONF_MAX_COLOR, "255,255,255")
        new_data.setdefault(CONF_IDLE_INTERVAL, 10)
        new_data.setdefault(CONF_ACTIVE_INTERVAL, 1)
        new_data.setdefault(CONF_CHANGE_THRESHOLD, 10)
        new_data.setdefault(CONF_CLOSED_POSITION, 90)
        new_data.setdefault(CONF_OPEN_POSITION, 10)
        new_data.setdefault(CONF_TRANSITION_THRESHOLD, 5)
        new_data.setdefault(CONF_STATE_TIMEOUT, 5)
        
        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data)
        
    return True