from bleson import get_provider, Peripheral
from bleson.core.hci.type_codes import GATT_SUCCESS

# Characteristic UUIDs
TX_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"  # writable from client
RX_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"  # notify to client

class FakeOBDPeripheral(Peripheral):
    def __init__(self, provider):
        super().__init__(provider)

        # Writable characteristic where client sends commands
        self.add_writable_characteristic(uuid=TX_UUID, on_write=self.on_write)

        # Notifying characteristic where simulator sends back responses
        self.add_notifying_characteristic(uuid=RX_UUID)

        print("Fake OBD-II BLE Simulator Ready.")

    def on_write(self, characteristic, value, offset):
        # Decode command sent by client
        cmd = value.decode(errors='ignore').strip()
        print(f"[SIM] Received: {cmd}")

        # Respond like a real OBD-II adapter
        if cmd == "ATZ":
            self.notify(RX_UUID, b"ELM327 v2.1\r>")
        elif cmd == "0105":
            # Example coolant temp response: 83°C -> 0x7B
            self.notify(RX_UUID, b"41 05 7B\r>")
        else:
            self.notify(RX_UUID, b"OK\r>")

        return GATT_SUCCESS

def run():
    provider = get_provider()              # Get Linux BLE backend
    sim = FakeOBDPeripheral(provider)      # Create simulator object
    sim.start()                             # Start BLE advertising
    print("[SIM] Running. Press Ctrl+C to stop.")

    try:
        while True:
            pass  # Keep simulator alive
    except KeyboardInterrupt:
        sim.stop()
        print("[SIM] Stopped.")

if __name__ == "__main__":
    run()
