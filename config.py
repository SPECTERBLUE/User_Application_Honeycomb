CHIRPSTACK_HOST = "localhost:8088"  # Ensure this is the correct ChirpStack gRPC server address
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjYwZWUzOTc5LWU2ODItNGFhMi05MzMzLTMzOWE0ODZhMzMwNSIsInR5cCI6ImtleSJ9.dKk_vtIw-EbUmrbW--cIrBDG_h_gitR3LWRqzfJi3TI"  # Replace with your API token
# Not needed
APPLICATION_ID = None  # Remove hardcoded Application ID
TENANT_ID = None  # Replace with your tenant ID
USER_ID = None # Replace with your user ID 

# Pagination Configuration
MAX_DEVICES = 1000
MAX_APPLICATIONS = 1000
MAX_TENANTS = 100
LIMIT = 100
OFFSET = 0

# mqtt
mqtt = "localhost"
keepalive = 60

# Add authorization metadata
AUTH_METADATA = [("authorization", f"Bearer {API_TOKEN}")]

#Automatic Key Rotation Configuration
AUTO_KEY_ROTATION_TIME = 30 * 24 * 60 * 60  # Time in seconds for automatic key rotation

# Join based key rotation
JOIN_SIMULATED_TIME_DELAY = 0.5 * 60  # Time in seconds to simulate join delay

#Uplink Configuration fports
UL_ED_PUBLIC_KEY = 26

# Downlink Configuration fports
DL_UA_PUBLIC_KEY = 76
DL_KEYROTATION_SUCCESS = 10
DL_REBOOT = 52
DL_UPDATE_FREQUENCY = 51
DL_DEVICE_STATUS = 55
DL_LOG_LEVEL = 62
DL_TIME_SYNC = 60
DL_RESET_FACTORY = 61

#API
CONTAINER_EDGEX_SECURITY_PROXY = "edgex-security-proxy-setup"
CONTAINER_CHIRPSTACK = "chirpstack-chirpstack-1"
CONTAINER_VAULT = "edgex-security-secretstore-setup"

VAULT_ROOT_PATH = "/vault/config/assets/resp-init.json"

# base url for user fetcher from honeycomb
BASE_URL = "http://localhost:80"

# user credentials for honeycomb
# Username = "admin@mdl.com"
# Password = "grse2024"

encrypted_user = {
    "iv": "9HCBQdwicgPlsWr+",
    "ciphertext": "wDWyk5/v6U+enmu8wQ==",
    "tag": "fqRo3CMAQbuh0JPisFRvPw=="
}

# Store secret as a dict
encrypted_pass = {
    "iv": "wJ5DJZP4RVcFjn+u",
    "ciphertext": "NcvLKS4zmnE=",
    "tag": "3t7ihXeewTFSjYYBEkRvWw=="
}

# Domain name  for honeycomb
Domain = "GRSE"

AES_KEY = b"n2342dwwendwejnwedwjkdnwedne2dxn"




# ---------------------------
# Mainflux Channel Configs
# ---------------------------

WS_TEMP_OUT_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_TEMP_OUT_AUTH="Thing 4a1e1728-13da-479f-b276-7e55e6c80a38"

WS_HUM_OUT_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_HUM_OUT_AUTH="Thing 96b9a8b6-f8f0-40f6-9d4f-7c294480ab71"

WS_TEMP_IN_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_TEMP_IN_AUTH="Thing 70f50939-efcc-4de6-894b-c7ce6c4ef886"

WS_HUM_IN_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_HUM_IN_AUTH="Thing 31a026b6-b4aa-4a67-b359-7977cdf6215c"

WS_WIND_SPEED_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_WIND_SPEED_AUTH="Thing f70c3f4b-9552-4acc-bf22-4b4e748724cf"

WS_WIND_DIR_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_WIND_DIR_AUTH="Thing 4513faac-be7e-4675-ab39-4a1715fab27d"

WS_SOLAR_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_SOLAR_AUTH="Thing 1be7af8d-4e24-4821-9b27-493362a708bc"

WS_RAINFALL_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_RAINFALL_AUTH="Thing b770e0f0-128a-40ec-b56c-d471650339f1"

WS_PRESSURE_REL_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_PRESSURE_REL_AUTH="Thing 040d965e-d8cc-4e18-a4cd-6d8e83fea244"

WS_PRESSURE_ABS_URL="http://localhost:80/http/channels/b6cf5fdc-ac3d-4bd1-aabe-755d7a85f4a5/messages/"
WS_PRESSURE_ABS_AUTH="Thing 9a66c0df-d068-4094-929d-16d35601787f"




# ---------------------------
# EdgeX Configs
# ---------------------------

EDGEX_URL="http://localhost:59880/api/v3/event/device-rest/ws_ambient/_WS_Temperature_Indoor_Sensor/all"
EDGEX_TOKEN="Bearer eyJhbGciOiJFUzM4NCIsImtpZCI6Ijk1NGNkZDIyLTRjZDItOGQ0Mi02YTU0LTAzYWIwODgzYTA3MiJ9.eyJhdWQiOiJlZGdleCIsImV4cCI6MTc1NzU3ODgwMiwiaWF0IjoxNzU3NDkyNDAyLCJpc3MiOiIvdjEvaWRlbnRpdHkvb2lkYyIsIm5hbWUiOiJhZG1pbiIsIm5hbWVzcGFjZSI6InJvb3QiLCJzdWIiOiJkNzhiNmVmYy1iYTlmLWZiZmEtZWZjOC0wMWQyODJjMTc2NWUifQ.enS9YxhxF8mwmTWmTSizJv4GeK2GS3E8Az_PpuvkbEGqOPqdzHhFM8hcnPLgmtlk3rOCObHVuhz7Me07toUwRy2_ZuJ-CZjRf2bAORaf7L3c-AZ8RM0qhMcevKOzn5_6"