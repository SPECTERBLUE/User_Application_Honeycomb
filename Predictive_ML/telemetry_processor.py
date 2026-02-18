from collections import defaultdict
import logging
from collections import defaultdict


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
        rows = sorted(rows, key=lambda x: x["window"])

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

        label = "NORMAL"

        if sensor in threshold_map:
            pf = threshold_map[sensor]["prefailure"]
            fl = threshold_map[sensor]["failure"]

            if value >= fl:
                label = "POSTFAILURE"
            elif value >= pf:
                label = "PREFAILURE"

        labeled.append({
            **row,
            "label": label
        })

    return labeled

