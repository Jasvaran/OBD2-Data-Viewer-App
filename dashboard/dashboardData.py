from PID_Resources import PID_LIST
from rich.table import Table

PID_ORDER = [pid_cmd[2:] for pid_cmd in PID_LIST]
dashboard_dataDict = dict.fromkeys(PID_ORDER, None)

def build_table(dashboard_dataDict):
    """
    Build a Rich table from dashboard_data.

    Expected dashboard_data shape:
    {
        "0C": {"pid": "0C", "name": "Engine RPM", "value": 2450, "unit": "rpm"},
        "0D": {"pid": "0D", "name": "Vehicle Speed", "value": 52, "unit": "km/h"},
    }
    """
    table = Table(title="OBD-II Dashboard Data")
    table.add_column("PID", justify="center", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Value", justify="right", style="green")

    for pid in PID_ORDER:
        data = dashboard_dataDict.get(pid)
        if data is not None:
            value_text = f"{data['value']} {data['unit']}".strip()
            table.add_row(data["pid"], data["name"], value_text)
        else:
            table.add_row(pid, "N/A", "N/A")

    return table