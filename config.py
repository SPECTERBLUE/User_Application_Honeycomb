# ChirpStack gRPC Configuration
CHIRPSTACK_HOST = "localhost:8088"  # Ensure this is the correct ChirpStack gRPC server address
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjM5NWE4ZWFjLTc5N2YtNDIzYy04ODM2LTgwMGU0MjI1NjNlZiIsInR5cCI6ImtleSJ9.19X5iDaI6PgQKuBRq12ytyF-iqezGlSovirKAz78x-o"  # Replace with your ChirpStack API token
APPLICATION_ID = None  # Remove hardcoded Application ID
TENANT_ID = "52f14cd4-c6f1-4fbd-8f87-4025e1d49242"  # Replace with your tenant ID

# Pagination Configuration
MAX_DEVICES = 1000
MAX_APPLICATIONS = 1000
LIMIT = 100
OFFSET = 0

# Add authorization metadata
AUTH_METADATA = [("authorization", f"Bearer {API_TOKEN}")]
