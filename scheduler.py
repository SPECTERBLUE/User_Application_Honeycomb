import schedule
import time
from device_manager import device_manager
import User_token

def scheduled_update():
    """Fetch and display updated device list."""
    device_manager.fetch_all_devices()
    device_manager.show_device_names()

def start_scheduler():
    """Start the scheduler loop."""
    schedule.every(1).minutes.do(scheduled_update)
    
    scheduled_update()
    
    schedule.every().day.at("00:00").do(User_token.Jwt_rotaion_all)
    
    while True:
        schedule.run_pending()
        time.sleep(10)  # Avoid excessive CPU usage
