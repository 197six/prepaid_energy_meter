from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Prepaid Energy Sensor from a config entry."""
    async_add_entities([PrepaidEnergySensor(hass, config_entry)])


class PrepaidEnergySensor(SensorEntity):
    def __init__(self, hass, config_entry):
        self.hass = hass
        self._config_entry = config_entry

        self._attr_name = config_entry.data["name"]
        self._energy_sensor_id = config_entry.data["energy_sensor"]
        self._starting_units = config_entry.data["starting_units"]
        self._start_reading = None
        self._attr_state = self._starting_units
        self._attr_unit_of_measurement = "kWh"
        self._attr_unique_id = f"{config_entry.entry_id}_prepaid_energy_remaining"

    async def async_added_to_hass(self):
        """Initialise start reading and set up listener for usage updates."""
        source = self.hass.states.get(self._energy_sensor_id)
        if source and source.state not in ("unavailable", "unknown", None, ""):
            self._start_reading = float(source.state)
        else:
            self._start_reading = 0.0

        async_track_state_change_event(
            self.hass,
            [self._energy_sensor_id],
            self._handle_energy_update
        )

    @callback
    def _handle_energy_update(self, event):
        """Update remaining units when energy sensor changes."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state not in ("unavailable", "unknown", None, ""):
            current_reading = float(new_state.state)
            if self._start_reading is None:
                self._start_reading = current_reading
            used = max(0.0, current_reading - self._start_reading)
            self._attr_state = round(max(0.0, self._starting_units - used), 2)
            self.async_write_ha_state()

    @property
    def state(self):
        return self._attr_state
