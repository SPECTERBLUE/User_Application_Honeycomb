import pytest
from unittest.mock import MagicMock, patch
import grpc
from chirpstack_api import api
from tenant_fetcher import TenantFetcher
import config

@pytest.fixture
def tenant_service_stub():
    return MagicMock()

@pytest.fixture
def fetcher(tenant_service_stub):
    with patch("config.LIMIT", 10), patch("config.OFFSET", 0), patch("config.MAX_TENANTS", 30), patch("config.AUTH_METADATA", [("authorization", "Bearer test-token")]):
        return TenantFetcher(tenant_service_stub)

def test_fetch_tenants_success(fetcher, tenant_service_stub):
    """Test successful tenant fetching with multiple pages."""
    response_page_1 = api.ListTenantsResponse(
        result=[api.TenantListItem(id=f"tenant_{i}") for i in range(10)],
    )
    response_page_2 = api.ListTenantsResponse(
        result=[api.TenantListItem(id=f"tenant_{i}") for i in range(10, 20)],
    )
    response_page_3 = api.ListTenantsResponse(
        result=[api.TenantListItem(id=f"tenant_{i}") for i in range(20, 25)],
    )

    tenant_service_stub.List.side_effect = [response_page_1, response_page_2, response_page_3]

    tenants = fetcher.fetch_tenants()

    expected_tenants = [f"tenant_{i}" for i in range(25)]
    assert tenants == expected_tenants
    assert tenant_service_stub.List.call_count == 3

def test_fetch_tenants_empty(fetcher, tenant_service_stub):
    """Test fetching tenants when no tenants exist."""
    tenant_service_stub.List.return_value = api.ListTenantsResponse(result=[])
    
    tenants = fetcher.fetch_tenants()
    
    assert tenants == []
    tenant_service_stub.List.assert_called_once()

def test_fetch_tenants_grpc_error(fetcher, tenant_service_stub):
    """Test gRPC error handling."""
    tenant_service_stub.List.side_effect = grpc.RpcError("gRPC error")
    
    tenants = fetcher.fetch_tenants()
    
    assert tenants == []
    tenant_service_stub.List.assert_called_once()

def test_fetch_tenants_unexpected_error(fetcher, tenant_service_stub):
    """Test unexpected error handling."""
    tenant_service_stub.List.side_effect = Exception("Unexpected error")
    
    tenants = fetcher.fetch_tenants()
    
    assert tenants == []
    tenant_service_stub.List.assert_called_once()
