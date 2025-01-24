import logging
import config
import grpc
from chirpstack_api import api

logger = logging.getLogger(__name__)

class TenantFetcher:
    def __init__(self, tenant_service_stub):
        """
        Initializes the TenantFetcher class.

        Args:
            tenant_service_stub (api.TenantServiceStub): gRPC service stub for tenant operations.
        """
        # Validate OFFSET, LIMIT, and MAX_APPLICATIONS
        if config.LIMIT is None or config.OFFSET is None:
            raise ValueError("Offset and limit should be configured in the config.")
        if config.LIMIT <=0 or config.OFFSET<0 or config.MAX_TENANTS<=0:
            raise ValueError("LIMIT must be a positive integer,OFFSET must be a non-negative integer,MAX_APPLICATIONS must be a positive integer.")
        
        self.tenant_service_stub = tenant_service_stub
        self.offset = config.OFFSET
        self.limit = config.LIMIT
        self.max_tenants = config.MAX_TENANTS

    def fetch_tenants(self):
        """
        Fetches all tenants from ChirpStack using the gRPC API with pagination.

        Returns:
            list: A list of tenant IDs.
        """
        tenant_ids = []

        try:
            while True:
                # Request tenant list with pagination
                request = api.ListTenantsRequest(
                    limit=self.limit,
                    offset=self.offset
                    )
                
                logger.info(f"Fetching tenants with offset {self.offset} and limit {self.limit}")

                # Make gRPC call
                response = self.tenant_service_stub.List(request, metadata=config.AUTH_METADATA)
                logger.info(f"Response received: {len(response.result)} tenants found.")

                # Add tenant IDs to the list
                for tenant in response.result:
                    tenant_ids.append(tenant.id)

                # Break the loop if no more tenants are found or max limit is reached
                if len(response.result) < self.limit or self.offset >= self.max_tenants:
                    if self.offset >= self.max_tenants:
                        logger.warning("Reached maximum pagination limit for tenants.")
                    break

                # Increment offset for the next page
                self.offset += self.limit

            if not tenant_ids:
                logger.warning("No tenants found.")

            return tenant_ids

        except grpc.RpcError as e:
            logger.error(f"gRPC error occurred while fetching tenants: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching tenants: {str(e)}")
            return []


