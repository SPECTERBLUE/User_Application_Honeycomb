import logging
import grpc
from chirpstack_api import api  

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HttpIntegration:
    def __init__(self, channel, auth_token):
        """
        Initialize HTTP Integration handler using gRPC.

        :param channel: gRPC channel for ChirpStack.
        :param auth_token: Authentication metadata for API calls.
        """
        self.channel = channel
        self.auth_token = auth_token
        self.integration_service = api.ApplicationServiceStub(channel)

    def get_http_integrations(self, application_id):
        """
        Fetch all HTTP integrations from ChirpStack for a given application.

        :param application_id: ID of the application in ChirpStack
        :return: List of tuples containing (endpoint, headers)
        """
        request = api.GetHttpIntegrationRequest(application_id=application_id)

        try:
            response = self.integration_service.GetHttpIntegration(request, metadata=self.auth_token)
            logging.info(f"Received response: {response}")

            # Extract endpoint(s)
            endpoints = response.integration.event_endpoint_url.split(',') if hasattr(response, "integration") and response.integration else []

            # Extract headers directly since it's already a dictionary
            headers = dict(response.integration.headers) if hasattr(response.integration, "headers") else {}

            logging.info(f"Retrieved HTTP endpoints: {endpoints}")
            logging.info(f"Retrieved Headers: {headers}")

            return [(endpoint.strip(), headers) for endpoint in endpoints]

        except grpc.RpcError as e:
            logging.error(f"Failed to fetch HTTP integrations: {e.details()}")
            return "No endpoint available", []
        
    def update_http_integration(self, application_id, endpoint, headers):
        """
        Update the HTTP integration for a given application.

        :param application_id: ID of the application in ChirpStack
        :param endpoint: New endpoint URL
        :param headers: New headers for the integration
        """
        request = api.UpdateHttpIntegrationRequest(
            application_id=application_id,
            integration=api.HttpIntegration(
                event_endpoint_url=endpoint,
                headers=headers
            )
        )

        try:
            self.integration_service.UpdateHttpIntegration(request, metadata=self.auth_token)
            logging.info(f"Updated HTTP integration for application {application_id} successfully.")
        except grpc.RpcError as e:
            logging.error(f"Failed to update HTTP integration: {e.details()}")