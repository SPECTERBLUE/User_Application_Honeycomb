from chirpstack_api import api
import config
import grpc
import logging

logger = logging.getLogger(__name__)

class ApplicationFetcher:
    def __init__(self, application_service_stub):
        """
        Initializes the ApplicationFetcher class.

        Args:
            application_service_stub (api.ApplicationServiceStub): gRPC service stub for application operations.
        """
        # Validate OFFSET, LIMIT, and MAX_APPLICATIONS
        if config.LIMIT is None or config.OFFSET is None:
            raise ValueError("Offset and limit should be configured in the config.")
        if config.LIMIT <=0 or config.OFFSET<0 or config.MAX_APPLICATIONS<=0:
            raise ValueError("LIMIT must be a positive integer,OFFSET must be a non-negative integer,MAX_APPLICATIONS must be a positive integer.")
        
        self.application_service_stub = application_service_stub
        self.offset = config.OFFSET
        self.limit = config.LIMIT
        self.max_applications = config.MAX_APPLICATIONS

    def fetch_applications(self):
        """
        Fetches all applications from ChirpStack using the gRPC API with pagination.

        Returns:
            list: A list of application IDs.
        """
        application_ids = []

        try:
            while True:
                # Request application list with pagination
                request = api.ListApplicationsRequest(
                    limit=config.LIMIT,
                    offset=config.OFFSET,
                    tenant_id=config.TENANT_ID
                )
                logger.info(f"Fetching applications with offset {self.offset} and limit {self.limit}")

                # Make gRPC call
                response = self.application_service_stub.List(request, metadata=config.AUTH_METADATA)
                logger.info(f"Response received: {len(response.result)} applications found.")

                # Add application IDs to the list
                for application in response.result:
                    application_ids.append(application.id)

                # Break the loop if no more applications are found or max limit is reached
                if len(response.result) < self.limit or self.offset >= self.max_applications:
                    if self.offset >= self.max_applications:
                        logger.warning("Reached maximum pagination limit for applications.")
                    break

                # Increment offset for the next page
                self.offset += self.limit

            if not application_ids:
                logger.warning("No applications found.")

            return application_ids

        except grpc.RpcError as e:
            logger.error(f"gRPC error occurred while fetching applications: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching applications: {str(e)}")
            return []
