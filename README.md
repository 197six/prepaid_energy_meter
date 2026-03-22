# Prepaid Energy Meter

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration to track your prepaid electricity balance, estimate days remaining, and alert you before you run out of power.

Works with **any prepaid meter** -- no specific inverter or hardware required. All you need is a Home Assistant sensor that tracks your total grid kWh consumption.

---

## Features

- Tracks remaining prepaid kWh balance
- Decrements balance nightly based on actual meter delta (not estimates)
- Handles meter rollover and resets gracefully
- Calculates a 7-day rolling average daily consumption
- Estimates days remaining based on that average
- Fires HA push notifications at three configurable thresholds (warning / low / critical)
- Each alert fires once per threshold crossing -- no spam
- Alerts reset automatically when you top up
- Manual top-up and balance reset via HA services
- Full state restore across HA restarts
- HACS compatible

---

## Requirements

- Home Assistant 2023.6 or later
- A sensor entity that tracks cumulative grid kWh consumption (e.g. from a smart meter, energy monitor, or inverter integration)
- At least one HA notification service configured (e.g. the HA mobile app)

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three-dot menu and select **Custom repositories**
4. Add `https://github.com/197six/prepaid_energy_meter` with category **Integration**
5. Search for "Prepaid Energy Meter" and install
6. Restart Home Assistant

### Manual

1. Copy the `custom_components/prepaid_energy_meter` folder into your HA `custom_components` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Prepaid Energy Meter**
3. Fill in the setup form:

| Field | Description |
|---|---|
| Grid kWh Meter Sensor | The HA sensor entity tracking your total grid consumption |
| Current Balance (kWh) | Your actual current prepaid balance |
| Warning Threshold | Balance at which a warning notification fires (default: 50 kWh) |
| Low Threshold | Balance at which a low alert fires (default: 25 kWh) |
| Critical Threshold | Balance at which a critical alert fires (default: 10 kWh) |
| Notification Service | Your HA notify service (e.g. `notify.mobile_app_simons_phone`) |

---

## Sensors Created

| Entity | Description |
|---|---|
| `sensor.prepaid_energy_balance` | Current remaining balance in kWh |

### Attributes

| Attribute | Description |
|---|---|
| `last_updated` | Timestamp of last balance update |
| `last_meter_reading` | Last recorded grid meter value |
| `last_topup_amount_kwh` | Units added in the last top-up |
| `last_topup_date` | Timestamp of last top-up |
| `daily_average_kwh` | Rolling 7-day average daily consumption |
| `estimated_days_remaining` | Estimated days until balance reaches zero |
| `alert_level` | Current alert level: none / warning / low / critical |
| `daily_consumption_log` | Last 7 days of daily usage records |

---

## Services

### `prepaid_energy_meter.top_up`

Add units when you purchase more electricity.

```yaml
service: prepaid_energy_meter.top_up
data:
  units: 50.0
```

### `prepaid_energy_meter.reset`

Set the balance to a specific value (useful for reconciling against your utility statement).

```yaml
service: prepaid_energy_meter.reset
data:
  balance: 100.0
```

---

## Dashboard Card Example

```yaml
type: entities
title: Prepaid Electricity
entities:
  - entity: sensor.prepaid_energy_balance
    name: Balance Remaining
  - type: attribute
    entity: sensor.prepaid_energy_balance
    attribute: estimated_days_remaining
    name: Days Remaining
    suffix: days
  - type: attribute
    entity: sensor.prepaid_energy_balance
    attribute: daily_average_kwh
    name: Daily Average
    suffix: kWh
  - type: attribute
    entity: sensor.prepaid_energy_balance
    attribute: last_topup_date
    name: Last Top-Up
```

---

## Updating Thresholds

After setup, you can update alert thresholds without reinstalling. Go to **Settings > Devices & Services**, find the integration, and click **Configure**.

---

## Notes

- The integration reads your meter once at 23:59:55 each night. If HA is down at that time, that day's update will be skipped.
- If your meter reading ever drops (rollover, replacement, or reset), the integration treats that day's consumption as zero and logs a warning. No balance is deducted.
- The 7-day rolling average excludes days where HA was offline.

---

## Licence

GPL-3.0
