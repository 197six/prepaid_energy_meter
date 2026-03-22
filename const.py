"""Constants for Prepaid Energy Meter."""

DOMAIN = "prepaid_energy_meter"

# Config entry keys
CONF_METER_SENSOR = "meter_sensor"
CONF_INITIAL_BALANCE = "initial_balance"
CONF_THRESHOLD_WARNING = "threshold_warning"
CONF_THRESHOLD_LOW = "threshold_low"
CONF_THRESHOLD_CRITICAL = "threshold_critical"
CONF_NOTIFICATION_SERVICE = "notification_service"

# Defaults
DEFAULT_THRESHOLD_WARNING = 50.0
DEFAULT_THRESHOLD_LOW = 25.0
DEFAULT_THRESHOLD_CRITICAL = 10.0
DEFAULT_NOTIFICATION_SERVICE = "notify.mobile_app"

# Storage keys
STORAGE_KEY = "prepaid_energy_meter_data"
STORAGE_VERSION = 1

# Alert levels
ALERT_WARNING = "warning"
ALERT_LOW = "low"
ALERT_CRITICAL = "critical"
ALERT_NONE = "none"

# How many days of history to use for average consumption estimate
ROLLING_AVERAGE_DAYS = 7
