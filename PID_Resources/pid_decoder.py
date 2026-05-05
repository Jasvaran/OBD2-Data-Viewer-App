import re

OBD_STANDARDS = {
    1: "OBD-II (CARB)",
    2: "OBD (EPA)",
    3: "OBD and OBD-II",
    4: "OBD-I",
    5: "Not OBD compliant",
    6: "EOBD",
    7: "EOBD and OBD-II",
    8: "EOBD and OBD",
    9: "EOBD, OBD and OBD-II",
    10: "JOBD",
    11: "JOBD and OBD-II",
    12: "JOBD and EOBD",
    13: "JOBD, EOBD and OBD-II",
    14: "Reserved",
    15: "Reserved",
    16: "Reserved",
    17: "Engine Manufacturer Diagnostics",
    18: "Engine Manufacturer Diagnostics Enhanced",
    19: "Heavy Duty OBD",
    20: "World Wide Harmonized OBD",
    21: "Reserved",
    22: "Heavy Duty EOBD Stage I",
    23: "Heavy Duty EOBD Stage I N",
    24: "Heavy Duty EOBD Stage II",
    25: "Heavy Duty EOBD Stage II N",
    26: "OBDBr-1",
    27: "OBDBr-2",
    28: "KOBD",
    29: "IOBD I",
    30: "IOBD II",
    31: "Heavy Duty Euro OBD Stage VI",
}

FUEL_TYPES = {
    0: "Not available",
    1: "Gasoline",
    2: "Methanol",
    3: "Ethanol",
    4: "Diesel",
    5: "LPG",
    6: "CNG",
    7: "Propane",
    8: "Electric",
    9: "Bifuel gasoline",
    10: "Bifuel methanol",
    11: "Bifuel ethanol",
    12: "Bifuel LPG",
    13: "Bifuel CNG",
    14: "Bifuel propane",
    15: "Bifuel electric",
    16: "Bifuel mixed electric/combustion",
    17: "Hybrid gasoline",
    18: "Hybrid ethanol",
    19: "Hybrid diesel",
    20: "Hybrid electric",
    21: "Hybrid mixed electric/combustion",
    22: "Hybrid regenerative",
    23: "Bifuel diesel",
}

PID_DEFINITIONS = {
    "05": {
        "name": "Coolant Temperature",
        "unit": "°C",
        "bytes": 1,
        "decode": lambda a: a - 40,
    },
    "0C": {
        "name": "Engine RPM",
        "unit": "rpm",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) / 4,
    },
    "0D": {
        "name": "Vehicle Speed",
        "unit": "km/h",
        "bytes": 1,
        "decode": lambda a: a,
    },
    "04": {
        "name": "Engine Load",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: (a / 255) * 100,
    },
    "0B": {
        "name": "Intake Manifold Pressure",
        "unit": "kPa",
        "bytes": 1,
        "decode": lambda a: a,
    },
    "0F": {
        "name": "Intake Air Temperature",
        "unit": "°C",
        "bytes": 1,
        "decode": lambda a: a - 40,
    },
    "10": {
        "name": "MAF Air Flow Rate",
        "unit": "g/s",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) / 100,
    },
    "11": {
        "name": "Throttle Position",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: (a / 255) * 100,
    },
    "1C": {
        "name": "OBD Standard",
        "unit": "",
        "bytes": 1,
        "decode": lambda a: OBD_STANDARDS.get(a, f"Unknown ({a})"),
    },
    "1F": {
        "name": "Run Time Since Engine Start",
        "unit": "s",
        "bytes": 2,
        "decode": lambda a, b: (a * 256) + b,
    },
    "23": {
        "name": "Fuel Rail Gauge Pressure",
        "unit": "kPa",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) * 10,
    },
    "2F": {
        "name": "Fuel Tank Level",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: (a / 255) * 100,
    },
    "42": {
        "name": "Control Module Voltage",
        "unit": "V",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) / 1000,
    },
    "43": {
        "name": "Absolute Load",
        "unit": "%",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) * 100 / 255,
    },
    "44": {
        "name": "Commanded Equivalence Ratio",
        "unit": "",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) * 2 / 65536,
    },
    "46": {
        "name": "Ambient Air Temperature",
        "unit": "°C",
        "bytes": 1,
        "decode": lambda a: a - 40,
    },
    "49": {
        "name": "Accelerator Pedal Position D",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: (a / 255) * 100,
    },
    "51": {
        "name": "Fuel Type",
        "unit": "",
        "bytes": 1,
        "decode": lambda a: FUEL_TYPES.get(a, f"Unknown ({a})"),
    },
    "5C": {
        "name": "Engine Oil Temperature",
        "unit": "°C",
        "bytes": 1,
        "decode": lambda a: a - 40,
    },
    "5D": {
        "name": "Fuel Injection Timing",
        "unit": "°",
        "bytes": 2,
        "decode": lambda a, b: ((a * 256) + b) / 128 - 210,
    },
    "61": {
        "name": "Driver Demand Engine Torque",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: a - 125,
    },
}

def decode_response(response:str) -> dict | None:
    """
    Parse an ELM327 response like "41 05 6E" into a readable result.
    Returns a dict like: {"pid": "05", "name": "Coolant Temperature", "value": 70, "unit": "°C"}
    Returns None if the response can't be parsed.
    """

    cleaned = response.strip().upper()
    match = re.search(r"\b41\s+[0-9A-F]{2}(?:\s+[0-9A-F]{2}){1,4}\b", cleaned)
    if match:
        cleaned = match.group(0)

    # Must start with "41" (Mode 1 response)
    parts = cleaned.split()

    if not parts or parts[0] != "41":
        return None

    if len(parts) < 2:
        return None

    pid = parts[1]

    if pid not in PID_DEFINITIONS:
        return None
    defn = PID_DEFINITIONS[pid]

    if len(parts) < 2 + defn["bytes"]:
        return None

    # Convert the data bytes from hex strings to integers
    data_bytes = [int(b, 16) for b in parts[2:2 + defn["bytes"]]]

    value = defn["decode"](*data_bytes)
    if isinstance(value, float):
        value = round(value, 2)

    return {
        "pid": pid,
        "name": defn["name"],
        "value": value,
        "unit": defn["unit"],
    }
