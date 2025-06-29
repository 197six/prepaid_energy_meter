import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Prepaid Energy Sensor."""
    async_add_entities([PrepaidEnergySensor(hass, config_entry)], update_before_add=True)

class PrepaidEnergySensor(SensorEntity):
    def __init__(self, hass, config_entry):
        self.hass = hass
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id

        self._attr_name = config_entry.data["name"]
        self._energy_sensor_id = config_entry.data["energy_sensor"]
        self._starting_units = config_entry.data["starting_units"]
        self._attr_unit_of_measurement = "kWh"
        self._attr_unique_id = f"{self._entry_id}_prepaid_energy_remaining"
        self._attr_state = self._starting_units

        self._start_reading = None

    async def async_added_to_hass(self):
        """Set up state tracking and persistent start value."""
        self.hass.data.setdefault(DOMAIN, {})
        domain_data = self.hass.data[DOMAIN].setdefault(self._entry_id, {})

        # Restore start reading or capture from sensor
        if "start_reading" in domain_data:
            self._start_reading = domain_data["start_reading"]
            _LOGGER.debug("Restored start reading: %s", self._start_reading)
        else:
            current_state = self.hass.states.get(self._energy_sensor_id)
            if current_state and current_state.state not in ("unknown", "unavailable", "", None):
                self._start_reading = float(current_state.state)
                domain_data["start_reading"] = self._start_reading
                _LOGGER.debug("Captured new start reading: %s", self._start_reading)
            else:
                self._start_reading = 0.0
                domain_data["start_reading"] = 0.0
                _LOGGER.warning("Energy sensor unavailable on init; defaulting start to 0.0")

        # Start listening for changes
        async_track_state_change_event(
            self.hass,
            [self._energy_sensor_id],
            self._handle_energy_update
        )

    @callback
    def _handle_energy_update(self, event):
        """Update balance on energy sensor state change."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state not in ("unknown", "unavailable", "", None):
            try:
                current_reading = float(new_state.state)
                if self._start_reading is None:
                    self._start_reading = current_reading
                    self.hass.data[DOMAIN][self._entry_id]["start_reading"] = current_reading
                    _LOGGER.debug("Captured start reading on first update: %s", current_reading)

                used = max(0.0, current_reading - self._start_reading)
                self._attr_state = round(max(0.0, self._starting_units - used), 2)
                self.async_write_ha_state()
                _LOGGER.debug("Updated balance: %.2f (used: %.2f)", self._attr_state, used)
            except ValueError:
                _LOGGER.warning("Could not parse reading from %s", new_state.state)

    @property
    def state(self):
        return self._attr_state
