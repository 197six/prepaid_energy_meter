"""Config flow for Prepaid Energy Meter."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_METER_SENSOR,
    CONF_INITIAL_BALANCE,
    CONF_THRESHOLD_WARNING,
    CONF_THRESHOLD_LOW,
    CONF_THRESHOLD_CRITICAL,
    CONF_NOTIFICATION_SERVICE,
    DEFAULT_THRESHOLD_WARNING,
    DEFAULT_THRESHOLD_LOW,
    DEFAULT_THRESHOLD_CRITICAL,
    DEFAULT_NOTIFICATION_SERVICE,
)

_LOGGER = logging.getLogger(__name__)


class PrepaidEnergyMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1: Basic setup -- meter sensor and initial balance."""
        errors = {}

        if user_input is not None:
            # Validate the meter sensor exists
            meter_state = self.hass.states.get(user_input[CONF_METER_SENSOR])
            if meter_state is None:
                errors[CONF_METER_SENSOR] = "sensor_not_found"
            else:
                try:
                    float(meter_state.state)
                except (ValueError, TypeError):
                    errors[CONF_METER_SENSOR] = "sensor_not_numeric"

            if not errors:
                return self.async_create_entry(
                    title="Prepaid Energy Meter",
                    data=user_input,
                )

        schema = vol.Schema({
            vol.Required(CONF_METER_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_INITIAL_BALANCE, default=0.0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=0.1, unit_of_measurement="kWh")
            ),
            vol.Required(CONF_THRESHOLD_WARNING, default=DEFAULT_THRESHOLD_WARNING): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="kWh")
            ),
            vol.Required(CONF_THRESHOLD_LOW, default=DEFAULT_THRESHOLD_LOW): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="kWh")
            ),
            vol.Required(CONF_THRESHOLD_CRITICAL, default=DEFAULT_THRESHOLD_CRITICAL): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="kWh")
            ),
            vol.Required(CONF_NOTIFICATION_SERVICE, default=DEFAULT_NOTIFICATION_SERVICE): selector.TextSelector(),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/197six/prepaid_energy_meter"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return options flow for reconfiguring thresholds."""
        return PrepaidEnergyMeterOptionsFlow(config_entry)


class PrepaidEnergyMeterOptionsFlow(config_entries.OptionsFlow):
    """Handle options -- lets user update thresholds without reinstalling."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Show options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.data

        schema = vol.Schema({
            vol.Required(
                CONF_THRESHOLD_WARNING,
                default=current.get(CONF_THRESHOLD_WARNING, DEFAULT_THRESHOLD_WARNING)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="kWh")
            ),
            vol.Required(
                CONF_THRESHOLD_LOW,
                default=current.get(CONF_THRESHOLD_LOW, DEFAULT_THRESHOLD_LOW)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="kWh")
            ),
            vol.Required(
                CONF_THRESHOLD_CRITICAL,
                default=current.get(CONF_THRESHOLD_CRITICAL, DEFAULT_THRESHOLD_CRITICAL)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="kWh")
            ),
            vol.Required(
                CONF_NOTIFICATION_SERVICE,
                default=current.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
            ): selector.TextSelector(),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
