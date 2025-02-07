from scheduler import start_scheduler
from event_fetcher_parse import start_mqtt_client
import threading

if __name__ == "__main__":
    # Run scheduler (device fetching) in a separate thread
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    # Start MQTT client to listen for device events
    start_mqtt_client()
