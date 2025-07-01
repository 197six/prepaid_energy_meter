"""Config flow for Prepaid Energy Meter."""

from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class PrepaidEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prepaid Energy Meter."""

    VERSION = 1
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        return self.async_create_entry(title="Prepaid Energy Meter", data={})
