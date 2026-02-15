# Use a lightweight Ubuntu Linux
FROM ubuntu:22.04

# Install Python and Bluetooth stack
RUN apt update && apt install -y python3 python3-pip bluez bluetooth

# Install bleson inside Linux
RUN pip3 install bleson

# Set working directory
WORKDIR /app

# Run the simulator script when container starts
CMD ["python3", "-u", "/app/simulator.py"]