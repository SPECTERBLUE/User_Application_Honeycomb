import schedule
import time
from device_manager import device_manager

if __name__ == "__main__":
    # Initial fetch at startup
    device_manager.fetch_all_devices()
    
     # Show devices after fetching
    device_manager.show_device_names()

    # Run the scheduler in a loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Wait 60 seconds before checking again
