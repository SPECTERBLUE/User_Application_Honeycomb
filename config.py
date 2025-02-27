# ChirpStack gRPC Configuration
CHIRPSTACK_HOST = "192.168.0.71:8088"  # Ensure this is the correct ChirpStack gRPC server address
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjcxZjZiYjBjLTc0OGMtNDI5MC1hODkyLTJmNDk3MjRhNTYxYSIsInR5cCI6ImtleSJ9.Ol6qv3NZ6CEI3x3-6Kqhs7q-ePVRTWs-CnnYabmhncc"  # Replace with your ChirpStack API token

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
