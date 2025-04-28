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
   
    # Log the contents of edgex_users.json



EDGEX_USERS_FILE = "edgex_users.json"
ADMIN_TOKEN_URL = "http://183.82.1.171:8200/v1/identity/oidc/token/admin"
RULES_LIST_URL = "https://edge.meridiandatalabs.com/rules-engine/rules"
RULE_DETAIL_URL_TEMPLATE = "https://edge.meridiandatalabs.com/rules-engine/rules/{rule_name}"
RULE_UPDATE_URL_TEMPLATE = "https://edge.meridiandatalabs.com/rules-engine/rules/{rule_name}"

def JWT_token_generator():
    """Generates and uses JWT token for the admin user to fetch rules, modify Authorization, and update them."""

    # Step 1: Read admin token from edgex_users.json
    try:
        with open(EDGEX_USERS_FILE, "r") as f:
            data = json.load(f)
        admin_entry = next((entry for entry in data if entry.get("username") == "admin"), None)

        if not admin_entry or not admin_entry.get("token"):
            logger.warning("Admin user not found or missing token in edgex_users.json.")
            return

        admin_token = admin_entry["token"]
    except Exception as e:
        logger.error(f"Error reading {EDGEX_USERS_FILE}: {e}")
        return

    # Step 2: Use admin token to get fresh JWT
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {admin_token}'
    }

    try:
        response = requests.get(ADMIN_TOKEN_URL, headers=headers)
        response.raise_for_status()

        jwt_token = response.json().get("data", {}).get("token")
        if not jwt_token:
            logger.warning("No JWT token found for admin.")
            return

        logger.info("JWT token fetched for admin.")

    except requests.RequestException as req_err:
        logger.error(f"Failed to fetch admin JWT token: {req_err}")
        return

    # Step 3: Fetch list of all rules
    headers = {
        'Authorization': f'Bearer {jwt_token}'
    }

    try:
        response = requests.get(RULES_LIST_URL, headers=headers)
        response.raise_for_status()

        rules_list = response.json()
        if not isinstance(rules_list, list):
            logger.error(f"Unexpected rules list format: {rules_list}")
            return

        logger.info(f"Fetched {len(rules_list)} rules successfully.")

    except requests.RequestException as req_err:
        logger.error(f"Failed to fetch rules list: {req_err}")
        return

    # Step 4: Fetch each rule's details, modify Authorization, and update
    for rule in rules_list:
        rule_id = rule.get("id")
        if not rule_id:
            logger.warning(f"Rule entry without ID found: {rule}")
            continue

        rule_detail_url = RULE_DETAIL_URL_TEMPLATE.format(rule_name=rule_id)
        rule_update_url = RULE_UPDATE_URL_TEMPLATE.format(rule_name=rule_id)

        try:
            # Fetch rule details
            response = requests.get(rule_detail_url, headers=headers)
            response.raise_for_status()
            rule_detail = response.json()
            logger.info(f"Fetched rule detail for '{rule_id}'.")

            # 🔥 Update the Authorization inside actions.rest.headers
            if "actions" in rule_detail:
                for action in rule_detail["actions"]:
                    rest_action = action.get("rest")
                    if rest_action and "headers" in rest_action:
                        if "Authorization" in rest_action["headers"]:
                            rest_action["headers"]["Authorization"] = f"Bearer {jwt_token}"
                            logger.info(f"Authorization header updated for rule '{rule_id}'.")

            # Update the rule by sending PUT request
            update_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {jwt_token}'
            }

            update_response = requests.put(
                rule_update_url,
                headers=update_headers,
                json=rule_detail  # Use modified rule_detail as body
            )

            if update_response.status_code == 200:
                logger.info(f"Rule '{rule_id}' updated successfully.")
            else:
                logger.error(f"Failed to update rule '{rule_id}': {update_response.status_code} {update_response.text}")

        except requests.RequestException as req_err:
            logger.error(f"Failed to fetch or update rule '{rule_id}': {req_err}")





if __name__ == "__main__":
    
    # Run the user updater
    update_user_list()
    
    JWT_token_generator()
