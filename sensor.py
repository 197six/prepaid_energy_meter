"""Sensor platform for Prepaid Energy Meter."""

from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Prepaid Energy Meter sensor(s) from a config entry."""
    # Placeholder: Add your sensor entity/entities here
    async_add_entities([])

class PrepaidEnergySensor(SensorEntity):
    def __init__(self, hass, config_entry):
        self._hass = hass
        self._config_entry = config_entry
        self._attr_name = "PrePaid"
        self._energy_sensor_id = config_entry.data["energy_sensor"]
        self._attr_state = round(config_entry.data["starting_units"], 2)
        self._attr_unit_of_measurement = "kWh"
        self._last_update = None
        self._last_energy_value = None  # Track last energy sensor value

    @property
    def state(self):
        return self._attr_state

    @property
    def extra_state_attributes(self):
        return {
            "last_updated": self._last_update.strftime('%Y-%m-%d %H:%M:%S') if self._last_update else None
        }

    async def async_added_to_hass(self):
        # Restore previous state if available
        await super().async_added_to_hass()
        last_state = self._hass.states.get(self.entity_id)
        if last_state and last_state.state not in ("unknown", "unavailable"):
            try:
                self._attr_state = float(last_state.state)
            except ValueError:
                pass

        # Restore last energy sensor value if available
        last_energy = self._hass.states.get(self._energy_sensor_id)
        if last_energy and last_energy.state not in ("unknown", "unavailable", None, ""):
            try:
                self._last_energy_value = float(last_energy.state)
            except ValueError:
                self._last_energy_value = None

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
            DOMAIN,
            "update_units",
            self._handle_update_units,
        )
        self._hass.services.async_register(
            DOMAIN,
            "reset_units",
            self._handle_reset_units,
        )

    async def _daily_update(self, time):
        state = self._hass.states.get(self._energy_sensor_id)
        if state and state.state not in ("unknown", "unavailable", None, ""):
            try:
                current_value = float(state.state)
                if self._last_energy_value is not None:
                    used = current_value - self._last_energy_value
                    if used < 0:
                        used = 0  # Prevent negative usage
                else:
                    used = 0  # No previous value, can't compute usage

                self._attr_state = round(max(0.0, self._attr_state - used), 2)
                self._last_update = datetime.now()
                self._last_energy_value = current_value
                self.async_write_ha_state()
            except ValueError:
                pass

    async def _handle_update_units(self, call):
        add = call.data.get("additional_units", 0.0)
        self._attr_state = round(self._attr_state + add, 2)
        self._last_update = datetime.now()
        self.async_write_ha_state()

    async def _handle_reset_units(self, call):
        reset_value = call.data.get("starting_units", 0.0)
        self._attr_state = round(reset_value, 2)
        self._last_update = datetime.now()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        await self._store_state()

    async def _store_state(self):
        self._hass.states.async_set(self.entity_id, self._attr_state)
