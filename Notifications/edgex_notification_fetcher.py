from User_token import admin_JWT_token_generator
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

notification_url = "https://rapid.meridiandatalabs.com/support-notifications/api/v3/notification/status/PROCESSED"

def fetch_notifications():
    '''
    fetches notifications from edgex-processed
    '''
    try:
        token = admin_JWT_token_generator()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        parameters = {
            'limit': 1000,
            'offset': 1000
        }
        
        requests_response = requests.get(notification_url, headers=headers, params=parameters)
        requests_response.raise_for_status()
        notifications = requests_response.json()
        
        logger.info(f"Fetched {len(notifications.get('data', []))} notifications.")
        return notifications.get('data', [])
        
    except Exception as e:
        logger.error(f"Error generating JWT token: {e}", exc_info=True)
        return None

