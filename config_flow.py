from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class PrepaidEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="PrePaid", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("starting_units", default=0.0): vol.Coerce(float),
                vol.Required("energy_sensor"): str,
            }),
            errors=errors,
        )
