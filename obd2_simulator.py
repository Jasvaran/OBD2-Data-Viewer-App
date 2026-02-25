"""
ELM327 / OBD2 BLE Simulator
─────────────────────────────
Drop-in mock for BleakClient so you can test PID requests
without a car or Bluetooth adapter.

Responds to:
  • AT commands  (ATZ, ATE0, ATL0, ATH0, ATSP0, …)
  • Mode 01 PIDs (engine RPM, speed, coolant temp, throttle, …)
  • Mode 09 PIDs (VIN)

Values are randomised within realistic ranges and update each call.
"""

import asyncio
import random
import time

# ── Simulated UUIDs (match the ones main.py already uses) ──────────────
SIM_TX_UUID = "12345678-1234-1234-1234-1234567890ac"
SIM_RX_UUID = "12345678-1234-1234-1234-1234567890ad"

# ── PID response generators ───────────────────────────────────────────
# Each returns a hex payload string (the data bytes only, no header).

def _pid_04_engine_load():
    """Calculated engine load (0-100 %)"""
    val = random.randint(0, 255)
    return f"41 04 {val:02X}"

def _pid_05_coolant_temp():
    """Coolant temperature (-40 … 215 °C)"""
    temp_c = random.randint(70, 105)          # realistic warm range
    val = temp_c + 40
    return f"41 05 {val:02X}"

def _pid_0B_intake_pressure():
    """Intake manifold absolute pressure (kPa)"""
    val = random.randint(20, 101)
    return f"41 0B {val:02X}"

def _pid_0C_rpm():
    """Engine RPM  (0-16 383.75)"""
    rpm = random.randint(700, 6500)
    a = (rpm * 4) >> 8
    b = (rpm * 4) & 0xFF
    return f"41 0C {a:02X} {b:02X}"

def _pid_0D_speed():
    """Vehicle speed km/h"""
    spd = random.randint(0, 180)
    return f"41 0D {spd:02X}"

def _pid_0F_intake_temp():
    """Intake air temperature"""
    temp_c = random.randint(15, 50)
    val = temp_c + 40
    return f"41 0F {val:02X}"

def _pid_10_maf():
    """MAF air-flow rate (g/s)"""
    maf_100 = random.randint(0, 650)
    a = maf_100 >> 8
    b = maf_100 & 0xFF
    return f"41 10 {a:02X} {b:02X}"

def _pid_11_throttle():
    """Throttle position (0-100 %)"""
    val = random.randint(0, 255)
    return f"41 11 {val:02X}"

def _pid_1C_obd_standard():
    """OBD standards this vehicle conforms to"""
    return "41 1C 06"                         # EOBD (Europe)

def _pid_1F_runtime():
    """Run time since engine start (seconds)"""
    secs = int(time.monotonic()) % 65535
    a = secs >> 8
    b = secs & 0xFF
    return f"41 1F {a:02X} {b:02X}"

def _pid_2F_fuel_level():
    """Fuel tank level input (0-100 %)"""
    val = random.randint(50, 230)
    return f"41 2F {val:02X}"

def _pid_46_ambient_temp():
    """Ambient air temperature"""
    temp_c = random.randint(10, 35)
    val = temp_c + 40
    return f"41 46 {val:02X}"

def _pid_51_fuel_type():
    """Fuel type — Gasoline"""
    return "41 51 01"

def _pid_00_supported_pids_01_20():
    """Supported PIDs [01-20] — bitmask"""
    return "41 00 BE 3E B8 13"

def _pid_20_supported_pids_21_40():
    """Supported PIDs [21-40]"""
    return "41 20 80 05 A0 11"

def _pid_40_supported_pids_41_60():
    """Supported PIDs [41-60]"""
    return "41 40 6C 10 00 00"

def _mode_09_02_vin():
    """Vehicle Identification Number"""
    vin = "WVWZZZ3CZWE123456"
    hex_vin = " ".join(f"{ord(c):02X}" for c in vin)
    return f"49 02 01 {hex_vin}"


# ── Lookup tables ──────────────────────────────────────────────────────
MODE_01 = {
    "0100": _pid_00_supported_pids_01_20,
    "0104": _pid_04_engine_load,
    "0105": _pid_05_coolant_temp,
    "010B": _pid_0B_intake_pressure,
    "010C": _pid_0C_rpm,
    "010D": _pid_0D_speed,
    "010F": _pid_0F_intake_temp,
    "0110": _pid_10_maf,
    "0111": _pid_11_throttle,
    "011C": _pid_1C_obd_standard,
    "011F": _pid_1F_runtime,
    "0120": _pid_20_supported_pids_21_40,
    "012F": _pid_2F_fuel_level,
    "0140": _pid_40_supported_pids_41_60,
    "0146": _pid_46_ambient_temp,
    "0151": _pid_51_fuel_type,
}

MODE_09 = {
    "0902": _mode_09_02_vin,
}

AT_RESPONSES = {
    "ATZ":   "ELM327 v1.5 (SIMULATED)",
    "ATE0":  "OK",
    "ATE1":  "OK",
    "ATL0":  "OK",
    "ATL1":  "OK",
    "ATH0":  "OK",
    "ATH1":  "OK",
    "ATSP0": "OK",
    "ATSP6": "OK",
    "ATRV":  "14.2V",
    "ATI":   "ELM327 v1.5",
    "AT@1":  "SIMULATED OBD2",
    "ATDP":  "AUTO, ISO 15765-4 (CAN 11/500)",
    "ATDPN": "A6",
}


def _build_response(cmd: str) -> str:
    """Return an ELM327-style response string for *cmd*."""
    cmd = cmd.strip().upper().replace(" ", "")

    # AT commands
    if cmd.startswith("AT"):
        return AT_RESPONSES.get(cmd, "OK")

    # Mode 01
    if cmd in MODE_01:
        return MODE_01[cmd]()

    # Mode 09
    if cmd in MODE_09:
        return MODE_09[cmd]()

    return "NO DATA"


# ── Fake GATT characteristic ──────────────────────────────────────────

class _FakeChar:
    """Mimics a BLE GATT characteristic."""

    def __init__(self, uuid: str, properties: list[str], description: str = ""):
        self.uuid = uuid
        self.properties = properties
        self.description = description


class _FakeService:
    """Mimics a BLE GATT service containing characteristics."""

    def __init__(self):
        self.characteristics = [
            _FakeChar(SIM_TX_UUID, ["write-without-response", "write"], "ELM327 TX"),
            _FakeChar(SIM_RX_UUID, ["notify"], "ELM327 RX"),
        ]


# ── Mock BleakClient ──────────────────────────────────────────────────

class MockBleakClient:
    """
    Stand-in for bleak.BleakClient.
    Use as an async context manager exactly like the real one:

        async with MockBleakClient("SIMULATED") as client:
            ...
    """

    def __init__(self, address: str, **kwargs):
        self.address = address
        self._notify_callback = None
        self._connected = False
        self.services = [_FakeService()]

    # ── context manager ────────────────────────────────────────────────
    async def __aenter__(self):
        self._connected = True
        return self

    async def __aexit__(self, *exc):
        self._connected = False

    # ── GATT operations ────────────────────────────────────────────────
    async def start_notify(self, uuid: str, callback):
        self._notify_callback = callback

    async def stop_notify(self, uuid: str):
        self._notify_callback = None

    async def write_gatt_char(self, uuid: str, data: bytes, response=False):
        """Process the command and fire the notify callback with a response."""
        cmd = data.decode(errors="ignore").strip()
        reply = _build_response(cmd)

        # Small delay to feel more realistic
        await asyncio.sleep(random.uniform(0.02, 0.12))

        if self._notify_callback:
            # Send the actual data first
            self._notify_callback(SIM_RX_UUID, (reply + "\r").encode())
            # Then send the prompt separately (like real ELM327)
            await asyncio.sleep(0.01)
            self._notify_callback(SIM_RX_UUID, b">")
