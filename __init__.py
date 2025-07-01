"""Prepaid Energy Meter integration setup."""

from .const import DOMAIN

async def async_setup_entry(hass, config_entry):
    """Set up Prepaid Energy Meter from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await hass.async_forward_entry_setup(config_entry, "sensor")
    return True

async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    return await hass.async_forward_entry_unload(config_entry, "sensor")