import re

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
    "11": {
        "name": "Throttle Position",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: (a / 255) * 100,
    },
    "2F": {
        "name": "Fuel Tank Level",
        "unit": "%",
        "bytes": 1,
        "decode": lambda a: (a / 255) * 100,
    },
    "46": {
        "name": "Ambient Air Temperature",
        "unit": "°C",
        "bytes": 1,
        "decode": lambda a: a - 40,
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

    return {
        "pid": pid,
        "name": defn["name"],
        "value": round(value, 2),
        "unit": defn["unit"],
    }
