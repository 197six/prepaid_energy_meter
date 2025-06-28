from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Prepaid Energy Meter from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Prepaid Energy Meter from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
