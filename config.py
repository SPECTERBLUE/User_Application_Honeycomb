# ChirpStack gRPC Configuration
CHIRPSTACK_HOST = "192.168.0.71:8088"  # Ensure this is the correct ChirpStack gRPC server address
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjEzYWFkNjExLWQwNGQtNDZmMC05NTVjLTEzZmJkNDJmOWRiMCIsInR5cCI6ImtleSJ9.6HEmWED6JC52WiK_KjGHcC3Leazti9HINqyQAKfxmk0"  # Replace with your ChirpStack API token

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
mqtt = "192.168.0.71"

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