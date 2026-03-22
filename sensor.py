"""Sensor platform for Prepaid Energy Meter."""
import logging
from collections import deque
from datetime import datetime, date

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
    ROLLING_AVERAGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Prepaid Energy Meter sensor from a config entry."""
    sensor = PrepaidEnergySensor(hass, config_entry)
    async_add_entities([sensor])

    # Register sensor reference so __init__ services can reach it
    hass.data[DOMAIN][config_entry.entry_id]["sensor"] = sensor


class PrepaidEnergySensor(RestoreEntity, SensorEntity):
    """
    Tracks a prepaid electricity balance.

    Balance decrements nightly based on the delta of a grid kWh meter sensor.
    Supports manual top-up via service call.
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
        self._last_update = None
        self._last_topup_amount = None
        self._last_topup_date = None
        self._last_alert_level = ALERT_NONE

        # Rolling daily consumption log: list of (date_str, kWh_used) tuples
        self._daily_log: deque = deque(maxlen=ROLLING_AVERAGE_DAYS)

    # --- Properties ---

    @property
    def native_value(self):
        return round(self._balance, 2)

    @property
    def extra_state_attributes(self):
        avg = self._rolling_average()
        days_remaining = None
        if avg and avg > 0:
            days_remaining = round(self._balance / avg, 1)

        return {
            "last_updated": self._last_update.strftime("%Y-%m-%d %H:%M:%S") if self._last_update else None,
            "last_meter_reading": self._last_meter_value,
            "last_topup_amount_kwh": self._last_topup_amount,
            "last_topup_date": self._last_topup_date,
            "daily_average_kwh": round(avg, 2) if avg else None,
            "estimated_days_remaining": days_remaining,
            "alert_level": self._last_alert_level,
            "daily_consumption_log": list(self._daily_log),
        }

    # --- Lifecycle ---

    async def async_added_to_hass(self):
        """Restore previous state and start daily update timer."""
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
        """Restore balance and history from last known state."""
        last_state = await self.async_get_last_state()
        if not last_state or last_state.state in ("unknown", "unavailable"):
            _LOGGER.debug("No previous state to restore.")
            self._seed_meter_baseline()
            return

        try:
            self._balance = float(last_state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Could not restore balance from state '%s', keeping initial value.", last_state.state)

        attrs = last_state.attributes

        try:
            if attrs.get("last_meter_reading") is not None:
                self._last_meter_value = float(attrs["last_meter_reading"])
        except (ValueError, TypeError):
            _LOGGER.warning("Could not restore last meter reading.")

        self._last_topup_amount = attrs.get("last_topup_amount_kwh")
        self._last_topup_date = attrs.get("last_topup_date")
        self._last_alert_level = attrs.get("alert_level", ALERT_NONE)

        log = attrs.get("daily_consumption_log", [])
        if isinstance(log, list):
            self._daily_log = deque(log, maxlen=ROLLING_AVERAGE_DAYS)

        if self._last_meter_value is None:
            self._seed_meter_baseline()

        _LOGGER.debug("State restored. Balance: %.2f kWh, last meter: %s", self._balance, self._last_meter_value)

    def _seed_meter_baseline(self):
        """Read current meter value as baseline if we have nothing restored."""
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
        Called at 23:59:55 each night.
        Reads today's meter value, calculates usage, decrements balance.
        """
        meter_state = self._hass.states.get(self._meter_sensor)
        if not meter_state or meter_state.state in ("unknown", "unavailable", None, ""):
            _LOGGER.warning("Meter sensor '%s' unavailable at daily update time. Skipping.", self._meter_sensor)
            return

        try:
            current_meter = float(meter_state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Meter sensor returned non-numeric value: %s. Skipping daily update.", meter_state.state)
            return

        if self._last_meter_value is None:
            # First run -- just seed the baseline, don't deduct anything
            self._last_meter_value = current_meter
            self._last_update = datetime.now()
            self.async_write_ha_state()
            _LOGGER.info("First daily run -- seeded meter baseline at %.2f kWh.", current_meter)
            return

        # Handle meter rollover or reset (e.g. meter replaced, counter reset)
        if current_meter < self._last_meter_value:
            _LOGGER.warning(
                "Meter reading dropped from %.2f to %.2f. Possible rollover or reset. Treating usage as 0 today.",
                self._last_meter_value, current_meter
            )
            used = 0.0
        else:
            used = round(current_meter - self._last_meter_value, 2)

        self._balance = round(max(0.0, self._balance - used), 2)
        self._last_meter_value = current_meter
        self._last_update = datetime.now()

        # Log daily consumption
        today = date.today().isoformat()
        self._daily_log.append({"date": today, "used_kwh": used})
        _LOGGER.info("Daily update: used %.2f kWh. Remaining balance: %.2f kWh.", used, self._balance)

        self.async_write_ha_state()

        # Check and fire alerts
        await self._check_alerts()

    # --- Top-up and reset ---

    async def async_top_up(self, units: float):
        """Add units to balance. Called by service handler in __init__."""
        if units <= 0:
            _LOGGER.warning("Top-up called with non-positive value: %.2f. Ignoring.", units)
            return

        self._balance = round(self._balance + units, 2)
        self._last_topup_amount = units
        self._last_topup_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._last_update = datetime.now()

        # Reset alert level so notifications fire again if balance drops again
        self._last_alert_level = ALERT_NONE

        self.async_write_ha_state()
        _LOGGER.info("Topped up %.2f kWh. New balance: %.2f kWh.", units, self._balance)

    async def async_reset(self, balance: float):
        """Set balance to a specific value. Called by service handler in __init__."""
        self._balance = round(max(0.0, balance), 2)
        self._last_update = datetime.now()
        self._last_alert_level = ALERT_NONE
        self.async_write_ha_state()
        _LOGGER.info("Balance reset to %.2f kWh.", self._balance)

    # --- Alerts ---

    async def _check_alerts(self):
        """
        Fire a notification if balance has crossed a threshold downward.
        Each level fires only once -- resets on top-up.
        """
        balance = self._balance
        current_level = self._current_alert_level(balance)

        # Only notify if we've crossed into a new (worse) level
        level_order = [ALERT_NONE, ALERT_WARNING, ALERT_LOW, ALERT_CRITICAL]
        current_rank = level_order.index(current_level)
        last_rank = level_order.index(self._last_alert_level)

        if current_rank <= last_rank:
            return  # No change or already notified at this level

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

    def _rolling_average(self):
        """Calculate average daily consumption over logged days."""
        if not self._daily_log:
            return None
        total = sum(entry["used_kwh"] for entry in self._daily_log)
        return total / len(self._daily_log)
