import json
import time
import random

class DeviceData:
    def __init__(self):
        #
        # SENSOR ARRAYS (each with 1 element or multiple for multi-axis)
        #
        # Single-value sensors stored as 1-element arrays
        self.distance = [0.0]
        self.vibration = [0.0]
        self.temperature = [0.0]
        self.humidity = [0.0]

        # IMU arrays
        self.accel = [0.0, 0.0, 0.0]  # [ax, ay, az]
        self.gyro  = [0.0, 0.0, 0.0]  # [gx, gy, gz]

        # Crane movement array: [forward, backward, upward]
        self.crane = [0.0, 0.0, 0.0]

        #
        # DEVICE INFO ARRAYS
        #
        # Even if they are strings, we store them as arrays of length 1
        self.mac_address     = ["00:00:00:00:00:00"]
        self.dev_eui         = ["2CF7F12052608E69"]
        self.app_eui         = ["526973696e674846"]
        self.app_key         = ["9912F15CFA594117755B457CB55A1796"]
        self.net_eui         = ["N/A"]
        self.model_number    = ["LoRaSense-1000"]
        self.hardware        = ["Rev 1.2"]
        self.frequency_band  = ["868 MHz"]
        self.mode            = ["OTAA"]

        # Other device info also stored as single-element arrays
        self.uptime          = [0]        # Will update to time-based in update_randomly()
        self.battery_level   = [100]      # (example)
        self.signal_strength = [-50]      # (example)
        self.firmware_version= ["1.0.0"]
        self.last_sync_time  = ["2024-12-01T12:00:00Z"]

    def update_randomly(self):
        """
        Simulate reading from sensors by assigning random data.
        In your real code, replace these lines with actual sensor reads.
        """
        self.distance[0]     = random.uniform(1.0, 100.0)
        self.vibration[0]    = random.uniform(0.0, 10.0)
        self.temperature[0]  = random.uniform(20.0, 35.0)
        self.humidity[0]     = random.uniform(30.0, 90.0)

        # IMU arrays
        self.accel = [
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0)
        ]
        self.gyro = [
            random.uniform(-100.0, 100.0),
            random.uniform(-100.0, 100.0),
            random.uniform(-100.0, 100.0)
        ]

        # Crane movement
        self.crane = [
            random.uniform(0, 50),  # forward
            random.uniform(0, 50),  # backward
            random.uniform(0, 20)   # upward
        ]

        # Device info updates (single-element arrays)
        self.uptime[0]          = int(time.time())    # integer seconds
        self.battery_level[0]   = random.randint(70, 100)   # fake battery
        self.signal_strength[0] = random.randint(-100, -50) # fake RSSI

    def to_json(self):
        """
        Return a JSON string of the entire data payload.
        """
        data = {}

        # SENSOR DATA
        data["distance"]    = self.distance
        data["vibration"]   = self.vibration
        data["temperature"] = self.temperature
        data["humidity"]    = self.humidity
        data["crane"]       = self.crane  # [forward, backward, upward]
        data["imu"] = {
            "accel": self.accel,
            "gyro":  self.gyro
        }

        # DEVICE INFO
        device_info = {
            "uptime":           self.uptime,
            "battery_level":    self.battery_level,
            "signal_strength":  self.signal_strength,
            "firmware_version": self.firmware_version,
            "last_sync_time":   self.last_sync_time,
            "mac_address":      self.mac_address,
            "dev_eui":          self.dev_eui,
            "app_eui":          self.app_eui,
            "app_key":          self.app_key,
            "net_eui":          self.net_eui,
            "model_number":     self.model_number,
            "hardware":         self.hardware,
            "frequency_band":   self.frequency_band,
            "mode":             self.mode
        }

        data["device"] = device_info

        return json.dumps(data)

# Example usage
if __name__ == "__main__":
    device_data = DeviceData()
    device_data.update_randomly()    # Simulate reading from sensors
    json_output = device_data.to_json()
    print(json_output)
