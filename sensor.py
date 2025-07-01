"""Sensor platform for Prepaid Energy Meter."""

from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, CONF_METER_SENSOR, CONF_INITIAL_BALANCE

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Prepaid Energy Meter sensor from a config entry."""
    async_add_entities([PrepaidEnergySensor(hass, config_entry)])
    await hass.async_forward_entry_setup(config_entry, "sensor")

class PrepaidEnergySensor(RestoreEntity, SensorEntity):
    """Sensor to track prepaid energy balance."""

    def __init__(self, hass, config_entry):
        self._hass = hass
        self._config_entry = config_entry
        self._attr_name = "Prepaid Energy Balance"
        self._meter_sensor = config_entry.data[CONF_METER_SENSOR]
        self._attr_unit_of_measurement = "kWh"
        self._attr_state = config_entry.data[CONF_INITIAL_BALANCE]
        self._last_meter_value = None
        self._last_update = None

    @property
    def state(self):
        return self._attr_state

    @property
    def extra_state_attributes(self):
        return {
            "last_updated": self._last_update.strftime('%Y-%m-%d %H:%M:%S') if self._last_update else None,
            "last_meter_value": self._last_meter_value,
        }

    async def async_added_to_hass(self):
        """Restore state and set up daily update and services."""
        await super().async_added_to_hass()
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            try:
                self._attr_state = float(last_state.state)
            except Exception:
                pass
            self._last_meter_value = last_state.attributes.get("last_meter_value", None)
            if self._last_meter_value is not None:
                try:
                    self._last_meter_value = float(self._last_meter_value)
                except Exception:
                    self._last_meter_value = None

        # Get current meter value if not set
        if self._last_meter_value is None:
            meter_state = self._hass.states.get(self._meter_sensor)
            if meter_state and meter_state.state not in ("unknown", "unavailable", None, ""):
                try:
                    self._last_meter_value = float(meter_state.state)
                except Exception:
                    self._last_meter_value = None

        # Schedule daily update
        async_track_time_change(
            self._hass,
            self._daily_update,
            hour=23,
            minute=59,
            second=55,
        )

        # Register services
        self._hass.services.async_register(
            DOMAIN, "top_up", self._handle_top_up
        )
        self._hass.services.async_register(
            DOMAIN, "reset", self._handle_reset
        )

    async def _daily_update(self, now):
        """Subtract daily usage from prepaid balance."""
        meter_state = self._hass.states.get(self._meter_sensor)
        if meter_state and meter_state.state not in ("unknown", "unavailable", None, ""):
            try:
                current_meter = float(meter_state.state)
                if self._last_meter_value is not None:
                    used = current_meter - self._last_meter_value
                    if used < 0:
                        used = 0  # Prevent negative usage
                else:
                    used = 0
                self._attr_state = round(max(0.0, self._attr_state - used), 2)
                self._last_update = datetime.now()
                self._last_meter_value = current_meter
                self.async_write_ha_state()
            except Exception:
                pass

    async def _handle_top_up(self, call):
        """Add units to the prepaid balance."""
        add = call.data.get("units", 0.0)
        try:
            add = float(add)
        except Exception:
            add = 0.0
        self._attr_state = round(self._attr_state + add, 2)
        self._last_update = datetime.now()
        self.async_write_ha_state()

    async def _handle_reset(self, call):
        """Reset the prepaid balance to a specific value."""
        value = call.data.get("value", 0.0)
        try:
            value = float(value)
        except Exception:
            value = 0.0
        self._attr_state = round(value, 2)
        self._last_update = datetime.now()
        self.async_write_ha_state()
