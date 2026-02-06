import User_fetcher
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class FetchAssetsTelemetry:
    def __init__(self):
        self.user_fetcher = User_fetcher.UserFetcher()

    def get_auth_tokens(self):
        try:
            response = self.user_fetcher.fetch_auth_token_with_domain_id()
            if response:
                logging.info("Successfully fetched auth tokens.")
                return response
            else:
                logging.error("Auth tokens not found in the response.")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP Request failed: {e}")
            return None
        
    def get_telemetry_data_asset(self, asset_id, limit=1000, max_messages=100000):
        try:
            tokens = self.get_auth_tokens()
            if not tokens:
                logging.error("Cannot fetch telemetry data without auth tokens.")
                return None

            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Accept": "application/json"
            }

            all_messages = []
            offset = 0
            total = None

            while True:
                # Safety stop: hard cap
                if len(all_messages) >= max_messages:
                    logging.warning(
                        f"Max telemetry limit ({max_messages}) reached for asset {asset_id}. "
                        "Stopping further fetch."
                    )
                    break

                url = (
                    f"{self.user_fetcher.base_url}/channels/{asset_id}/messages"
                    f"?limit={limit}&offset={offset}"
                )

                response = requests.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()

                messages = data.get("messages", [])

                # Trim batch if it exceeds max_messages
                remaining = max_messages - len(all_messages)
                if len(messages) > remaining:
                    messages = messages[:remaining]

                all_messages.extend(messages)

                if total is None:
                    total = data.get("total", 0)

                logging.info(
                    f"Fetched {len(messages)} messages "
                    f"(offset={offset}, total_fetched={len(all_messages)}/{min(total, max_messages)})"
                )

                # Stop conditions
                if not messages:
                    break

                offset += limit
                if offset >= total:
                    break

            logging.info(
                f"Completed fetching telemetry for asset {asset_id}. "
                f"Total messages fetched: {len(all_messages)}"
            )

            return all_messages

        except requests.RequestException as e:
            logging.error(f"Error fetching telemetry data for asset {asset_id}: {e}")
            return None


    def get_telemetry_data_things(self, thing_id, asset_id, limit=1000, max_messages=100000):
        try:
            tokens = self.get_auth_tokens()
            if not tokens:
                logging.error("Cannot fetch telemetry data without auth tokens.")
                return None

            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Accept": "application/json"
            }

            all_thing_messages = []
            offset = 0
            total = None

            while True:
                # Hard safety cap
                if len(all_thing_messages) >= max_messages:
                    logging.warning(
                        f"Max telemetry limit ({max_messages}) reached for thing {thing_id}, asset {asset_id}. "
                        "Stopping further fetch."
                    )
                    break

                url = (
                    f"{self.user_fetcher.base_url}/channels/{asset_id}/messages"
                    f"?limit={limit}&offset={offset}&publisher={thing_id}"
                )

                response = requests.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                messages = data.get("messages", [])

                if not messages:
                    break

                # Set total once
                if total is None:
                    total = data.get("total", 0)

                # Trim batch BEFORE extending
                remaining = max_messages - len(all_thing_messages)
                if len(messages) > remaining:
                    messages = messages[:remaining]

                all_thing_messages.extend(messages)

                logging.info(
                    f"Fetched {len(messages)} messages "
                    f"(offset={offset}, total_fetched={len(all_thing_messages)}/{min(total, max_messages)})"
                )

                # Move offset by actual batch size
                offset += len(messages)

                if offset >= total:
                    break

            logging.info(
                f"Completed fetching telemetry for thing {thing_id}, asset {asset_id}. "
                f"Total messages fetched: {len(all_thing_messages)}"
            )

            return all_thing_messages

        except requests.RequestException as e:
            logging.error(
                f"Error fetching telemetry data for thing {thing_id}, asset {asset_id}: {e}"
            )
            return None

            