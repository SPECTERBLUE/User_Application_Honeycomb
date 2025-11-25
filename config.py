
# ChirpStack gRPC Configuration
CHIRPSTACK_HOST = "localhost:8088"  # Ensure this is the correct ChirpStack gRPC server address
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjY4N2JkYjA2LTFmNTgtNGQ5ZS05MmMzLTNlZGNlMDQ2YzZjMCIsInR5cCI6ImtleSJ9.g5aP9FJrT-3ImHC1I1U0HiItxgD8JBp8mzm-wsrTgQI"  # Replace with your API token

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
LOGIN_AESGCM_KEY = b"bR7xZ1qP8eWn4vFVS23KY92MuXqGdEL0"

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "mihir.rayadurgam2002@gmail.com"
SMTP_PASSWORD = "flng qger blhv pnph"

# reset password link
FRONTEND_URL = "http://localhost:5173/auth"