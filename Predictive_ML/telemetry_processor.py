from collections import defaultdict
import logging
from collections import defaultdict
import pandas as pd


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TelemetryProcessor:
    def __init__(self, telemetry_data):
        self.telemetry_data = telemetry_data

    def filter_by_time(self, start_ts=None, end_ts=None):
        if start_ts is None and end_ts is None:
            return self.telemetry_data

        return [
            m for m in self.telemetry_data
            if (start_ts is None or m["time"] >= start_ts)
            and (end_ts is None or m["time"] <= end_ts)
        ]

    def group_by_sensor(self):
        grouped = {}
        for msg in self.telemetry_data:
            name = msg.get("name")
            grouped.setdefault(name, []).append(msg)
        return grouped

    def aggregate_window(self, window_size_sec):
        """
        Aggregates telemetry into fixed time windows per sensor.
        Output is ML- and CSV-friendly.
        """

        buckets = defaultdict(list)

        for msg in self.telemetry_data:
            try:
                window_start = (msg["time"] // window_size_sec) * window_size_sec
                key = (msg["name"], window_start)
                buckets[key].append(msg["value"])
            except KeyError:
                logging.warning(f"Skipping malformed message: {msg}")

        aggregated = []

        for (sensor, window_start), values in buckets.items():
            aggregated.append({
                "sensor": sensor,
                "window_start": window_start,
                "count": len(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            })

        return aggregated

MAX_FORWARD_FILL_WINDOWS = 3

def handle_missing_windows(processed_data: list):
    """
    Applies forward fill for <= 3 missing windows.
    Marks sensor as NOT_WORKING if missing > 3 windows.
    """

    by_sensor = defaultdict(list)

    # Group by sensor
    for row in processed_data:
        by_sensor[row["sensor"]].append(row)

    final_data = []

    for sensor, rows in by_sensor.items():
        rows = sorted(rows, key=lambda x: x["window_start"])

        last_valid = None
        missing_count = 0
        sensor_failed = False

        for row in rows:
            if row["avg"] is not None and not sensor_failed:
                last_valid = row["avg"]
                missing_count = 0
                row["status"] = "OK"

            else:
                missing_count += 1

                if missing_count <= MAX_FORWARD_FILL_WINDOWS and last_valid is not None:
                    row["avg"] = last_valid
                    row["status"] = "FILLED"
                else:
                    row["avg"] = None
                    row["status"] = "NOT_WORKING"
                    sensor_failed = True

            final_data.append(row)

    return final_data

def label_data(aggregated_data, threshold_map):
    labeled = []

    for row in aggregated_data:
        sensor = row["sensor"]
        value = row["avg"]

        label = 0 # Default: normal

        if sensor in threshold_map:
            pf = threshold_map[sensor]["prefailure"]
            fl = threshold_map[sensor]["failure"]

            if value >= fl:
                label = 2 # Failure
            elif value >= pf:
                label = 1 # Pre-failure

        labeled.append({
            **row,
            "label": label
        })

    return labeled

# label data specic to 60kW 3-phase Slipring Induction Motor 
'''
Based on your motor specifications (400V, 50Hz, 120A stator, 317V/121A rotor), we will simulate the following sensors:

* **Stator Current & Voltage:** To detect electrical imbalances or overload.
* **Rotor Current & Voltage:** Crucial for slipring motors to detect brush wear, slip ring degradation, or rotor winding issues.
* **Vibration (mm/s):** To detect mechanical faults like bearing wear or misalignment.
* **Temperature (°C):** Winding and bearing temperatures.

We will tag five distinct states:

* `0`: Healthy Operation
* `1`: Overload (High currents, rising temperatures)
* `2`: Rotor/Slipring Fault (Fluctuating rotor voltage/current, increased slip)
* `3`: Stator Fault (Unbalanced or spiking stator current)
* `4`: Mechanical Fault (High vibration and bearing temperature)
'''

# Mechanical > Stator > Rotor > Overload > Healthy

def label_motor_faults(window_df, thresholds):
    """
    Multi-class labeling for 60kW Slipring Induction Motor
    Works on WINDOWED (pivoted) dataframe rows.
    """

    labeled_rows = []

    for _, row in window_df.iterrows():

        label = 0  # Healthy default

        stator_i = row.get("Stator_Current_avg")
        stator_v = row.get("Stator_Voltage_avg")

        rotor_i = row.get("Rotor_Current_avg")
        rotor_v = row.get("Rotor_Voltage_avg")

        vib = row.get("Vibration_avg")
        temp = row.get("Temperature_avg")

        # -------------------------------
        # 1️ MECHANICAL FAULT (highest priority)
        # -------------------------------
        if (
            vib is not None and temp is not None and
            vib >= thresholds["vibration"]["mechanical"] and
            temp >= thresholds["temperature"]["mechanical"]
        ):
            label = 4

        # -------------------------------
        # 2️ STATOR FAULT
        # Current spike / electrical imbalance
        # -------------------------------
        elif (
            stator_i is not None and
            stator_i >= thresholds["stator_current"]["fault_spike"]
        ):
            label = 3

        # -------------------------------
        # 3️ ROTOR / SLIPRING FAULT
        # Rotor current abnormal OR voltage drop
        # -------------------------------
        elif (
            rotor_i is not None and
            rotor_i >= thresholds["rotor_current"]["fault"]
        ):
            label = 2

        # -------------------------------
        # 4️ OVERLOAD
        # High stator current + rising temperature
        # -------------------------------
        elif (
            stator_i is not None and temp is not None and
            stator_i >= thresholds["stator_current"]["overload"] and
            temp >= thresholds["temperature"]["overload"]
        ):
            label = 1

        labeled_rows.append({
            **row.to_dict(),
            "label": label
        })

    return pd.DataFrame(labeled_rows)

