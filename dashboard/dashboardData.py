from PID_Resources import PID_LIST
from rich.table import Table

dashboard_dataDict = {}

dashboard_dataDict.fromkeys(PID_LIST)

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
    table.add_column("Unit", justify="left", style="yellow")

    for pid, data in dashboard_dataDict.items():
        if data is not None:
            table.add_row(data["pid"], data["name"], str(data["value"]), data["unit"])
        else:
            table.add_row(pid, "N/A", "N/A", "N/A")

    return table