
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
        Example: average values per time window per sensor
        """
        
        buckets = defaultdict(list)

        for msg in self.telemetry_data:
            window = msg["time"] // window_size_sec
            key = (msg["name"], window)
            buckets[key].append(msg["value"])

        return [
            {
                "sensor": k[0],
                "window": k[1],
                "avg": sum(v) / len(v)
            }
            for k, v in buckets.items()
        ]
