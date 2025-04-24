import logging
from User_fetcher import UserFetcher
import json
import os
import requests

#  Set this to True to remove users not in current API response
REMOVE_OLD_USERS = True

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_user_list():
    """Main logic for user fetching and edgex_users.json maintenance."""
    list_of_users = UserFetcher().fetch_all_users()

    users = list_of_users.get("users")
    if users and isinstance(users, list):
        logger.info(f"Number of users fetched: {len(users)}")

        credentials_list = [user.get("credentials") for user in users if "credentials" in user]
        logger.info(f"Credentials extracted: {credentials_list}")
    else:
        logger.error("No users found or invalid response format.")
        credentials_list = []

    usernames_list = [cred["identity"] for cred in credentials_list if "identity" in cred]
    logger.info(f"Usernames_list extracted: {usernames_list}")

    current_usernames = {email.split("@", 1)[0] for email in usernames_list if "@" in email}
    current_usernames.add("admin")  # Always include admin

    existing_data = {}
    if os.path.exists("edgex_users.json"):
        try:
            with open("edgex_users.json", "r") as f:
                existing_users = json.load(f)
                existing_data = {entry["username"]: entry["token"] for entry in existing_users}
                logger.info("Existing edgex_users.json loaded.")
        except Exception as e:
            logger.error(f"Error reading existing JSON: {e}")

    edgex_user_data = []
    for username in current_usernames:
        token = existing_data.get(username, "")
        edgex_user_data.append({
            "username": username,
            "token": token
        })

    if not REMOVE_OLD_USERS:
        for username, token in existing_data.items():
            if username not in current_usernames:
                edgex_user_data.append({
                    "username": username,
                    "token": token
                })
        logger.info("Old users retained.")

    try:
        with open("edgex_users.json", "w") as f:
            json.dump(edgex_user_data, f, indent=4)
        logger.info("edgex_users.json updated successfully.")
    except Exception as e:
        logger.error(f"Error writing to JSON file: {e}")
        
import requests
import json
import logging

logger = logging.getLogger(__name__)

def JWT_token_generator():
    """Generates and logs JWT tokens for all users in edgex_users.json."""
    try:
        with open("edgex_users.json", "r") as f:
            data = json.load(f)

        for entry in data:
            username = entry.get("username")
            token = entry.get("token")

            if not username or not token:
                logger.warning(f"Missing username or token for entry: {entry}")
                continue

            logger.info(f"Using token for {username}")
            url = f"http://183.82.1.171:8200/v1/identity/oidc/token/{username}"

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }

            try:
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    jwt_token = response.json().get("data", {}).get("token")
                    if jwt_token:
                        logger.info(f"JWT token for {username}: {jwt_token}")
                    else:
                        logger.warning(f"No token found in response for {username}")
                else:
                    logger.error(f"Failed to fetch token for {username}: {response.status_code} {response.text}")

            except requests.RequestException as req_err:
                logger.error(f"Request error for {username}: {req_err}")

    except Exception as e:
        logger.error(f"Error reading edgex_users.json: {e}")




if __name__ == "__main__":
    
    # Run the user updater
    update_user_list()
    
    JWT_token_generator()
