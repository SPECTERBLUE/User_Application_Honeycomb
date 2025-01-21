from chirpstack_api import api
import grpc

# ChirpStack gRPC Configuration
CHIRPSTACK_HOST = "localhost:8088"  # Ensure this is the correct ChirpStack gRPC server address
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjM5NWE4ZWFjLTc5N2YtNDIzYy04ODM2LTgwMGU0MjI1NjNlZiIsInR5cCI6ImtleSJ9.19X5iDaI6PgQKuBRq12ytyF-iqezGlSovirKAz78x-o"  # Replace with your ChirpStack API token
APPLICATION_ID = "41a744f9-7e86-4d71-9d5a-bcb5da6ded0d"  # Replace with your ChirpStack Application ID


def get_devices_as_dict():
    """
    Fetches all devices from ChirpStack using the chirpstack_api library with pagination.

    Returns:
        dict: A dictionary with device names as keys and metadata (e.g., EUID, description, profile ID) as values.
    """
    # Establish gRPC connection
    try:
        channel = grpc.insecure_channel(CHIRPSTACK_HOST)
        auth_token = [("authorization", "Bearer %s" % API_TOKEN)]
        
        # Create service stub for DeviceService
        device_service = api.DeviceServiceStub(channel=channel)
        print("gRPC connection established.")
    except grpc.RpcError as e:
        print(f"Error establishing gRPC connection: {e.details()}")
        return {}

    # Dictionary to store devices
    devices_dict = {}
    offset = 0
    limit = 100  # Number of devices to fetch per request

    try:
        while True:
            # Request device list with pagination and the application_id
            request = api.ListDevicesRequest(application_id=APPLICATION_ID, limit=limit, offset=offset)
            print(f"Fetching devices with offset {offset} and limit {limit}")
            
            # Make gRPC call
            response = device_service.List(request, metadata=auth_token)

            # Log the response length
            print(f"Response received: {len(response.result)} devices found.")

            # Process each device in the response
            for device in response.result:
                print(f"Processing device: {device.name}")
                devices_dict[device.name] = {
                    "euid": device.dev_eui,
                    "description": device.description,
                    "device_profile_id": device.device_profile_id,
                    "device_profile_name": device.device_profile_name,
                    "created_at": device.created_at.ToDatetime().isoformat() if device.created_at else None,
                    "updated_at": device.updated_at.ToDatetime().isoformat() if device.updated_at else None,
                    "last_seen_at": device.last_seen_at.ToDatetime().isoformat() if device.last_seen_at else None,
                }

            # Break if fewer devices than limit are returned (end of list)
            if len(response.result) < limit:
                break

            # Increment offset for the next page
            offset += limit

        print(f"Fetched {len(devices_dict)} devices from ChirpStack.")
        return devices_dict

    except grpc.RpcError as e:
        print(f"Error fetching devices: {e.details()}")
        return {}

# Example usage
if __name__ == "__main__":
    devices = get_devices_as_dict()
    print("Devices:", devices)
