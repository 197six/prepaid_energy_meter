from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([PrepaidEnergySensor(hass, config_entry)])

class PrepaidEnergySensor(SensorEntity):
    def __init__(self, hass, config_entry):
        self._hass = hass
        self._config_entry = config_entry
        self._attr_name = "PrePaid"
        self._energy_sensor_id = config_entry.data["energy_sensor"]
        self._attr_state = round(config_entry.data["starting_units"], 2)
        self._attr_unit_of_measurement = "kWh"

    async def async_added_to_hass(self):
        async_track_time_change(
            self._hass,
            self._daily_update,
            hour=23,
            minute=59,
            second=55,
        )

    async def _daily_update(self, time):
        state = self._hass.states.get(self._energy_sensor_id)
        if state and state.state not in ("unknown", "unavailable", None, ""):
            try:
                used = float(state.state)
                self._attr_state = round(max(0.0, self._attr_state - used), 2)
                self.async_write_ha_state()
            except ValueError:
                pass

    @property
    def state(self):
        return self._attr_state

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        async_track_time_change(
            self._hass,
            self._daily_update,
            hour=23,
            minute=59,
            second=55,
        )

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

    async def _handle_update_units(self, call):
        add = call.data.get("additional_units", 0.0)
        self._attr_state = round(self._attr_state + add, 2)
        self.async_write_ha_state()

    async def _handle_reset_units(self, call):
        reset_value = call.data.get("starting_units", 0.0)
        self._attr_state = round(reset_value, 2)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {
            "last_updated": self._last_update.strftime('%Y-%m-%d %H:%M:%S') if hasattr(self, '_last_update') else None
        }

    async def async_will_remove_from_hass(self):
        await self._store_state()

    async def _store_state(self):
        self._hass.states.async_set(self.entity_id, self._attr_state)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = self._hass.states.get(self.entity_id)
        if last_state and last_state.state not in ("unknown", "unavailable"):
            self._attr_state = float(last_state.state)

        async_track_time_change(
            self._hass,
            self._daily_update,
            hour=23,
            minute=59,
            second=55,
        )

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
