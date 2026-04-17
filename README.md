# OBD-II Data Viewer Application

A Python terminal app for connecting to a Bluetooth ELM327-style OBD-II adapter, polling live vehicle PIDs, decoding the responses, and showing them in a continuously updating dashboard.

The project also includes a built-in simulator so you can work on the polling, parsing, and dashboard experience without needing a car or BLE adapter connected.

## Features

- Scan for nearby BLE devices and choose one interactively
- Connect to a real ELM327-compatible Bluetooth OBD-II adapter with `bleak`
- Send initialization commands such as `ATZ` and `ATE0`
- Poll a set of Mode 01 OBD-II PIDs in a loop
- Decode raw hex responses into human-readable values
- Display live results in a Rich-powered terminal dashboard
- Run in simulation mode with a mock `BleakClient`
- Buffer and clean noisy adapter output such as `OK`, `SEARCHING...`, and echoed commands

## Current PIDs Displayed

The default dashboard polls and displays:

- Coolant Temperature
- Engine RPM
- Vehicle Speed
- Engine Load
- Intake Manifold Pressure
- Intake Air Temperature
- Throttle Position
- Fuel Tank Level
- Ambient Air Temperature

These are configured in [PID_Resources/pid_list.py](PID_Resources/pid_list.py) and decoded in [PID_Resources/pid_decoder.py](PID_Resources/pid_decoder.py).

## Project Structure

- [main.py](main.py): app entry point, BLE discovery, connection, polling loop, and live dashboard updates
- [obd2_simulator.py](obd2_simulator.py): mock ELM327/BLE client for offline development
- [intialization_commands.py](intialization_commands.py): startup commands sent to the adapter
- [PID_Resources/pid_list.py](PID_Resources/pid_list.py): list of requested PIDs
- [PID_Resources/pid_decoder.py](PID_Resources/pid_decoder.py): response parsing and PID-specific decode formulas
- [dashboard/dashboardData.py](dashboard/dashboardData.py): dashboard data store and Rich table builder
- [Bluetooth_testing.py](Bluetooth_testing.py): older BLE experimentation file kept for reference
- [docs/LIVE_DASHBOARD_PLAN.md](docs/LIVE_DASHBOARD_PLAN.md): notes on the live dashboard implementation
- [docs/CONVERSATION_STUDY_NOTES.md](docs/CONVERSATION_STUDY_NOTES.md): debugging notes about parsing noisy real adapter output
- [docs/project-improvement-directions.md](docs/project-improvement-directions.md): practical directions for expanding the project

## How It Works

1. `main.py` scans for nearby named BLE devices.
2. You choose a device from the terminal prompt.
3. The app discovers GATT characteristics and picks:
   - the first writable characteristic as TX
   - the first notify/indicate characteristic as RX
4. Initialization commands are sent to the adapter.
5. The app continuously requests each PID in `PID_LIST`.
6. Incoming BLE notifications are buffered and split into lines.
7. Valid `41 xx ...` Mode 01 responses are decoded into values.
8. The dashboard updates in place using `rich.live.Live`.

## Requirements

- Python 3.11 or newer recommended
- A terminal that supports Rich output
- For real hardware mode:
  - a BLE-capable machine
  - an ELM327-compatible Bluetooth OBD-II adapter
  - Bluetooth permissions enabled for your OS and terminal/Python runtime

Python packages used by the app:

- `bleak`
- `rich`

This project now includes `uv` project metadata in [pyproject.toml](pyproject.toml) and a lockfile in [uv.lock](uv.lock).

If you are using `uv`, install the project dependencies with:

```bash
uv sync
```

Then run the app with:

```bash
uv run python main.py
```

Install them with:

```bash
pip install bleak rich
```

## Running The Project

Start the app with:

```bash
python3 -m uv run python main.py
```

By default, the app runs in normal BLE mode and scans for nearby named devices.

## CLI Options

The app supports common runtime configuration through command-line flags:

- `--simulate`: run with the built-in mock OBD/BLE simulator
- `--debug`: enable verbose logging for discovery, characteristics, PID requests, and ignored adapter chatter
- `--poll-delay <seconds>`: control the delay between PID requests
- `--device-name "<name>"`: connect to the first BLE device whose advertised local name exactly matches the given value
- `--device-address <address>`: connect directly to a BLE adapter by address
- `--scan-timeout <seconds>`: control how long BLE discovery runs in real mode

See the built-in help with:

```bash
python3 -m uv run python main.py --help
```

### Real Adapter Mode

Run in normal BLE mode with interactive device selection:

```bash
python3 -m uv run python main.py
```

Or target a specific adapter by name:

```bash
python3 -m uv run python main.py --device-name "OBDII"
```

Or connect directly by address:

```bash
python3 -m uv run python main.py --device-address "AA:BB:CC:DD:EE:FF"
```

In real adapter mode, the app:

- the app scans for nearby BLE devices
- shows named devices it finds
- prompts you to choose one if you did not provide `--device-name` or `--device-address`
- connects using `BleakClient`

### Simulation Mode

To run without hardware:

```bash
python3 -m uv run python main.py --simulate
```

In simulation mode, the app:

- skips BLE scanning
- uses `MockBleakClient`
- returns randomized but realistic-looking OBD-II values
- lets you test the dashboard and decoder loop locally

## Example Workflow

1. Run `python3 -m uv run python main.py --simulate` to test without hardware.
2. Run `python3 -m uv run python main.py` to use interactive BLE discovery.
3. Optionally target an adapter with `python3 -m uv run python main.py --device-name "OBDII"`.
4. Optionally slow polling with `python3 -m uv run python main.py --poll-delay 0.25`.
5. Press `Ctrl+C` to stop the loop.

## Example Commands

```bash
python3 -m uv run python main.py --simulate
python3 -m uv run python main.py --debug
python3 -m uv run python main.py --poll-delay 0.25
python3 -m uv run python main.py --device-name "OBDII"
python3 -m uv run python main.py --device-address "AA:BB:CC:DD:EE:FF"
python3 -m uv run python main.py --scan-timeout 8
```

## Adding Or Changing PIDs

To add a new PID:

1. Add the command to [PID_Resources/pid_list.py](PID_Resources/pid_list.py).
2. Add a matching entry to `PID_DEFINITIONS` in [PID_Resources/pid_decoder.py](PID_Resources/pid_decoder.py).
3. Include:
   - `name`
   - `unit`
   - number of data `bytes`
   - a `decode` lambda or function

Example shape:

```python
"XX": {
    "name": "Example PID",
    "unit": "units",
    "bytes": 1,
    "decode": lambda a: a,
}
```

If a PID is in the polling list but not in the decoder, it will not be displayed as decoded dashboard data.

## Notes And Limitations

- There is no `requirements.txt` yet for non-`uv` installs.
- The app currently chooses the first writable and first notify characteristic it sees. Some adapters may require more specific UUID selection logic.
- Only a subset of Mode 01 PIDs is implemented.
- The main interface is terminal-only; there is no GUI or web frontend yet.
- File naming includes `intialization_commands.py`, which is intentionally referenced as-is in the code even though the word is misspelled.

## Troubleshooting

### No named BLE devices were found

- Make sure the adapter is powered on and advertising
- Move closer to the adapter
- Confirm Bluetooth permissions are granted
- Try scanning again

### You see control text like `OK` or `SEARCHING...`

That is normal for real ELM327 traffic. The app already filters common non-PID chatter before decoding.

### The dashboard shows `N/A`

- The PID may not have returned a valid response yet
- The adapter may not support that PID
- The response may not match a decoder entry yet

### The wrong BLE characteristic is selected

Some adapters expose several characteristics. The current implementation uses a generic first-match strategy, so adapter-specific UUID handling may be needed.

## Future Improvement Ideas

- Add a `requirements.txt` for non-`uv` users
- Add preferred UUID matching for known OBD-II adapters
- Expand decoder support for more PIDs and Mode 09 data
- Add logging and debug verbosity levels
- Export captured data to CSV or JSON
- Build a graphical dashboard

## Status

This project is a solid working prototype for live OBD-II polling over BLE with a terminal dashboard and simulator-backed development flow.
