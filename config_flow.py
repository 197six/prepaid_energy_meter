"""Config flow for Prepaid Energy Meter."""

from homeassistant import config_entries
import voluptuous as vol
from homeassistant.const import CONF_NAME
from .const import DOMAIN, CONF_METER_SENSOR, CONF_INITIAL_BALANCE

class PrepaidEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prepaid Energy Meter."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title="Prepaid Energy Meter",
                data=user_input,
            )

        # Get all sensors for selection
        sensor_entities = [
            entity_id for entity_id in self.hass.states.async_entity_ids("sensor")
        ]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_METER_SENSOR): vol.In(sensor_entities),
                vol.Required(CONF_INITIAL_BALANCE, default=0.0): vol.Coerce(float),
            }),
            errors=errors,
        )
