
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

