"""Sensor platform for Prepaid Energy Meter."""
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.restore_state import RestoreEntity

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
    ALERT_WARNING,
    ALERT_LOW,
    ALERT_CRITICAL,
    ALERT_NONE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Prepaid Energy Meter sensor from a config entry."""
    sensor = PrepaidEnergySensor(hass, config_entry)
    async_add_entities([sensor])
    hass.data[DOMAIN][config_entry.entry_id]["sensor"] = sensor


class PrepaidEnergySensor(RestoreEntity, SensorEntity):
    """
    Tracks a prepaid electricity balance.

    Reads a grid kWh meter sensor at 23:59:55 each night.
    Subtracts the day's usage from the running balance.
    Fires HA notifications when balance crosses configurable thresholds.
    """

    _attr_icon = "mdi:lightning-bolt-circle"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_should_poll = False

    def __init__(self, hass, config_entry):
        self._hass = hass
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_balance"
        self._attr_name = "Prepaid Energy Balance"

        cfg = config_entry.data
        self._meter_sensor = cfg[CONF_METER_SENSOR]
        self._balance = float(cfg[CONF_INITIAL_BALANCE])
        self._threshold_warning = float(cfg.get(CONF_THRESHOLD_WARNING, DEFAULT_THRESHOLD_WARNING))
        self._threshold_low = float(cfg.get(CONF_THRESHOLD_LOW, DEFAULT_THRESHOLD_LOW))
        self._threshold_critical = float(cfg.get(CONF_THRESHOLD_CRITICAL, DEFAULT_THRESHOLD_CRITICAL))
        self._notification_service = cfg.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)

        self._last_meter_value = None
        self._last_updated = None
        self._last_topup_amount = None
        self._last_topup_date = None
        self._last_alert_level = ALERT_NONE

    # --- Properties ---

    @property
    def native_value(self):
        return round(self._balance, 2)

    @property
    def extra_state_attributes(self):
        return {
            "last_updated": self._last_updated.strftime("%Y-%m-%d %H:%M:%S") if self._last_updated else None,
            "last_meter_reading": self._last_meter_value,
            "last_topup_amount_kwh": self._last_topup_amount,
            "last_topup_date": self._last_topup_date,
            "alert_level": self._last_alert_level,
        }

    # --- Lifecycle ---

    async def async_added_to_hass(self):
        """Restore previous state and start nightly update timer."""
        await super().async_added_to_hass()
        await self._restore_state()

        async_track_time_change(
            self._hass,
            self._daily_update,
            hour=23,
            minute=59,
            second=55,
        )
        _LOGGER.info("Prepaid Energy Meter initialised. Balance: %.2f kWh", self._balance)

    async def _restore_state(self):
        """Restore balance and meter reading from last known state."""
        last_state = await self.async_get_last_state()
        if not last_state or last_state.state in ("unknown", "unavailable"):
            _LOGGER.debug("No previous state to restore.")
            self._seed_meter_baseline()
            return

        try:
            self._balance = float(last_state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Could not restore balance from state '%s'.", last_state.state)

        attrs = last_state.attributes

        try:
            if attrs.get("last_meter_reading") is not None:
                self._last_meter_value = float(attrs["last_meter_reading"])
        except (ValueError, TypeError):
            _LOGGER.warning("Could not restore last meter reading.")

        self._last_topup_amount = attrs.get("last_topup_amount_kwh")
        self._last_topup_date = attrs.get("last_topup_date")
        self._last_alert_level = attrs.get("alert_level", ALERT_NONE)

        if self._last_meter_value is None:
            self._seed_meter_baseline()

        _LOGGER.debug("State restored. Balance: %.2f kWh, last meter: %s", self._balance, self._last_meter_value)

    def _seed_meter_baseline(self):
        """Read current meter value as baseline on first run."""
        meter_state = self._hass.states.get(self._meter_sensor)
        if meter_state and meter_state.state not in ("unknown", "unavailable", None, ""):
            try:
                self._last_meter_value = float(meter_state.state)
                _LOGGER.debug("Seeded meter baseline: %.2f", self._last_meter_value)
            except (ValueError, TypeError):
                _LOGGER.warning("Meter sensor '%s' returned non-numeric state: %s", self._meter_sensor, meter_state.state)

    # --- Daily update ---

    async def _daily_update(self, now):
        """
        Called at 23:59:55 each night (or manually via force_update).
        Reads today's meter value, calculates usage since last reading,
        and deducts from balance.
        """
        meter_state = self._hass.states.get(self._meter_sensor)
        if not meter_state or meter_state.state in ("unknown", "unavailable", None, ""):
            _LOGGER.warning("Meter sensor '%s' unavailable. Skipping update.", self._meter_sensor)
            return

        try:
            current_meter = float(meter_state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Meter sensor returned non-numeric value: %s. Skipping.", meter_state.state)
            return

        if self._last_meter_value is None:
            # First ever run -- seed baseline, no deduction
            self._last_meter_value = current_meter
            self._last_updated = datetime.now()
            self.async_write_ha_state()
            _LOGGER.info("First run -- seeded meter baseline at %.2f kWh.", current_meter)
            return

        # Calculate usage. If meter has reset to a new day (daily counter),
        # use current reading directly as today's usage.
        if current_meter < self._last_meter_value:
            used = round(current_meter, 2)
            _LOGGER.info("Daily counter reset detected. Today's usage: %.2f kWh.", used)
        else:
            used = round(current_meter - self._last_meter_value, 2)

        self._balance = round(max(0.0, self._balance - used), 2)
        self._last_meter_value = current_meter
        self._last_updated = datetime.now()

        _LOGGER.info("Update complete. Used: %.2f kWh. Balance: %.2f kWh.", used, self._balance)

        self.async_write_ha_state()
        await self._check_alerts()

    # --- Services ---

    async def async_top_up(self, units: float):
        """Add units to balance."""
        if units <= 0:
            _LOGGER.warning("Top-up called with non-positive value: %.2f. Ignoring.", units)
            return

        self._balance = round(self._balance + units, 2)
        self._last_topup_amount = units
        self._last_topup_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._last_updated = datetime.now()
        self._last_alert_level = ALERT_NONE
        self.async_write_ha_state()
        _LOGGER.info("Topped up %.2f kWh. New balance: %.2f kWh.", units, self._balance)

    async def async_reset(self, balance: float):
        """Set balance to a specific value."""
        self._balance = round(max(0.0, balance), 2)
        self._last_updated = datetime.now()
        self._last_alert_level = ALERT_NONE
        self.async_write_ha_state()
        _LOGGER.info("Balance reset to %.2f kWh.", self._balance)

    async def async_force_update(self):
        """Manually trigger a daily update calculation immediately."""
        _LOGGER.info("Force update triggered manually.")
        await self._daily_update(None)

    # --- Alerts ---

    async def _check_alerts(self):
        """Fire a notification if balance has crossed a threshold downward."""
        balance = self._balance
        current_level = self._current_alert_level(balance)

        level_order = [ALERT_NONE, ALERT_WARNING, ALERT_LOW, ALERT_CRITICAL]
        current_rank = level_order.index(current_level)
        last_rank = level_order.index(self._last_alert_level)

        if current_rank <= last_rank:
            return

        self._last_alert_level = current_level

        messages = {
            ALERT_WARNING: (
                "Prepaid Electricity Warning",
                f"Your prepaid electricity balance is getting low: {balance:.1f} kWh remaining."
            ),
            ALERT_LOW: (
                "Prepaid Electricity Low",
                f"Balance is low: {balance:.1f} kWh remaining. Consider topping up soon."
            ),
            ALERT_CRITICAL: (
                "Prepaid Electricity Critical",
                f"URGENT: Only {balance:.1f} kWh remaining. Top up now to avoid power interruption."
            ),
        }

        title, message = messages[current_level]

        try:
            await self._hass.services.async_call(
                "notify",
                self._notification_service.replace("notify.", ""),
                {"title": title, "message": message},
                blocking=False,
            )
            _LOGGER.info("Alert fired: %s", current_level)
        except Exception as err:
            _LOGGER.error("Failed to send notification via '%s': %s", self._notification_service, err)

    def _current_alert_level(self, balance: float) -> str:
        """Return the appropriate alert level for a given balance."""
        if balance <= self._threshold_critical:
            return ALERT_CRITICAL
        if balance <= self._threshold_low:
            return ALERT_LOW
        if balance <= self._threshold_warning:
            return ALERT_WARNING
        return ALERT_NONE
