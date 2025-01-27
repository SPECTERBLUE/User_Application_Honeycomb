import json
import time
import random

class DeviceData:
    def __init__(self):
        # Basic sensor data
        self.distance = 0.0
        self.vibration = 0.0
        self.temperature = 0.0
        self.humidity = 0.0
        
        # IMU arrays (accel = [ax, ay, az], gyro = [gx, gy, gz])
        self.accel = [0.0, 0.0, 0.0]
        self.gyro = [0.0, 0.0, 0.0]
        
        # Crane movement array: forward, backward, upward
        self.crane = [0.0, 0.0, 0.0]

        # Device info
        self.mac_address = "00:00:00:00:00:00"
        self.dev_eui = "2CF7F12052608E69"
        self.app_eui = "526973696e674846"
        self.app_key = "9912F15CFA594117755B457CB55A1796"
        self.model_number = "LoRaSense-1000"
        self.hardware = "Rev 1.2"
        self.frequency_band = "868 MHz"
        self.mode = "OTAA"

    def update_randomly(self):
        """
        Simulate reading from sensors by assigning random data.
        In your real code, replace this with actual sensor reads.
        """
        self.distance = random.uniform(1.0, 100.0)
        self.vibration = random.uniform(0.0, 10.0)
        self.temperature = random.uniform(20.0, 35.0)
        self.humidity = random.uniform(30.0, 90.0)
        
        # Fill IMU arrays
        self.accel = [
            random.uniform(-1.0, 1.0),  # ax
            random.uniform(-1.0, 1.0),  # ay
            random.uniform(-1.0, 1.0)   # az
        ]
        self.gyro = [
            random.uniform(-100.0, 100.0),  # gx
            random.uniform(-100.0, 100.0),  # gy
            random.uniform(-100.0, 100.0)   # gz
        ]
        self.crane = [
            random.uniform(0, 50),  # forward
            random.uniform(0, 50),  # backward
            random.uniform(0, 20)   # upward
        ]

    def to_json(self):
        """
        Return a JSON string of the entire data payload.
        Mirrors the structure you had in C++ (handleSensorData).
        """
        # Build a Python dict for the top-level data
        data = {}
        # Sensor readings
        data["distance"] = self.distance
        data["vibration"] = self.vibration
        data["temperature"] = self.temperature
        data["humidity"] = self.humidity
        data["crane"] = self.crane  # array of crane movements
        data["imu"] = {
            "accel": self.accel,
            "gyro": self.gyro
        }
        
        # Nested device info
        device_info = {}
        device_info["uptime"] = time.time()  # current time as "uptime"
        device_info["battery_level"] = random.randint(70, 100)  # fake
        device_info["signal_strength"] = random.randint(-100, -50)  # fake
        device_info["firmware_version"] = "1.0.0"
        device_info["last_sync_time"] = "2024-12-01T12:00:00Z"
        device_info["mac_address"] = self.mac_address
        device_info["dev_eui"] = self.dev_eui
        device_info["app_eui"] = self.app_eui
        device_info["app_key"] = self.app_key
        device_info["net_eui"] = "N/A"
        device_info["model_number"] = self.model_number
        device_info["hardware"] = self.hardware
        device_info["frequency_band"] = self.frequency_band
        device_info["mode"] = self.mode
        
        # Add `device_info` to the main dict
        data["device"] = device_info
        
        # Convert the entire dict to a JSON string
        return json.dumps(data)

# Example usage
if __name__ == "__main__":
    device_data = DeviceData()
    device_data.update_randomly()  # Simulate reading new sensor data
    json_output = device_data.to_json()
    print(json_output)
