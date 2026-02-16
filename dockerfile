FROM ubuntu:22.04

# Install Python, pip, and BlueZ tools
RUN apt update && apt install -y python3 python3-pip bluez dbus dbus-user-session

# Install Python BLE peripheral library
RUN pip3 install bluez-peripheral dbus-next

WORKDIR /app

# Run the simulator script when container starts
CMD ["python3", "-u", "/app/ble-simulator/simulator.py"]