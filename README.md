# Prepaid Energy Meter

A Home Assistant custom integration to track prepaid electricity balance.

## Features

- Tracks remaining prepaid units (kWh) for a pay-as-you-go meter.
- Subtracts daily usage (difference in total meter reading) at 23:59:55.
- Allows manual top-up and reset via Home Assistant services.

## Setup

1. Install this integration in your `custom_components` directory.
2. Add via Home Assistant UI, select your total meter sensor, and set your initial balance.

## Services

- `prepaid_energy_meter.top_up` — Add units to the balance.
- `prepaid_energy_meter.reset` — Reset the balance to a specific value.

See `services.yaml` for details.
