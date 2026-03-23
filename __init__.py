"""Prepaid Energy Meter - Home Assistant Custom Integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

SERVICE_TOP_UP_SCHEMA = vol.Schema({
    vol.Required("units"): vol.Coerce(float),
})

SERVICE_RESET_SCHEMA = vol.Schema({
    vol.Required("balance"): vol.Coerce(float),
})

SERVICE_FORCE_UPDATE_SCHEMA = vol.Schema({})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Prepaid Energy Meter from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services at the integration level (not per-entity)
    async def handle_top_up(call: ServiceCall) -> None:
        """Handle top_up service call."""
        units = call.data["units"]
        for entry_id, entry_data in hass.data[DOMAIN].items():
            sensor = entry_data.get("sensor")
            if sensor:
                await sensor.async_top_up(units)

    async def handle_reset(call: ServiceCall) -> None:
        """Handle reset service call."""
        balance = call.data["balance"]
        for entry_id, entry_data in hass.data[DOMAIN].items():
            sensor = entry_data.get("sensor")
            if sensor:
                await sensor.async_reset(balance)

    async def handle_force_update(call: ServiceCall) -> None:
        """Trigger an immediate daily update calculation outside of the scheduled 23:59:55 run."""
        for entry_id, entry_data in hass.data[DOMAIN].items():
            sensor = entry_data.get("sensor")
            if sensor:
                await sensor.async_force_update()

    hass.services.async_register(
        DOMAIN, "top_up", handle_top_up, schema=SERVICE_TOP_UP_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "reset", handle_reset, schema=SERVICE_RESET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "force_update", handle_force_update, schema=SERVICE_FORCE_UPDATE_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    # Remove services if no more entries
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, "top_up")
        hass.services.async_remove(DOMAIN, "reset")
        hass.services.async_remove(DOMAIN, "force_update")

    return unload_ok
