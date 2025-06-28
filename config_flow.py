from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers.selector import (
    TextSelector,
    NumberSelector,
    EntitySelector,
)

from .const import DOMAIN


class PrepaidEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prepaid Energy Meter."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        schema = vol.Schema({
            vol.Required("name"): TextSelector(),
            vol.Required("energy_sensor"): EntitySelector(),
            vol.Optional("starting_units", default=0.0): NumberSelector(
                {
                    "min": 0,
                    "max": 10000,
                    "step": 0.1,
                    "unit_of_measurement": "kWh",
                    "mode": "box"
                }
            )
        })

        return self.async_show_form(step_id="user", data_schema=schema)
