import pytest
from unittest.mock import Mock, patch
from chirpstack_api import api
import grpc
import logging
import config
from application_fetcher import ApplicationFetcher  

# Setup logging for tests
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_application_stub():
    return Mock()

@pytest.fixture
def config_fixture():
    # Create a mock config that matches your actual config.py
    class Config:
        CHIRPSTACK_HOST = "localhost:8088"
        API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjFlMGQzMTAzLTY3ZGMtNGYxMi1iZjRlLTdkY2IyNjI2NDBhZiIsInR5cCI6ImtleSJ9.HxodGM0g8I9Ws8yTYNw8KFa5iP9NEUNvqV1HJVJ60No"
        APPLICATION_ID = None
        TENANT_ID = None
        USER_ID = None
        MAX_DEVICES = 1000
        MAX_APPLICATIONS = 1000
        MAX_TENANTS = 100
        LIMIT = 100
        OFFSET = 0
        mqtt = "localhost"
        AUTH_METADATA = [("authorization", f"Bearer {API_TOKEN}")]
        AUTO_KEY_ROTATION_TIME = 30 * 24 * 60 * 60
        JOIN_SIMULATED_TIME_DELAY = 0.5 * 60
        UL_ED_PUBLIC_KEY = 26
        DL_UA_PUBLIC_KEY = 76
        DL_KEYROTATION_SUCCESS = 10
        DL_REBOOT = 52
        DL_UPDATE_FREQUENCY = 51
        DL_DEVICE_STATUS = 55
        DL_LOG_LEVEL = 62
        DL_TIME_SYNC = 60
        DL_RESET_FACTORY = 61
    return Config

def test_initialization_with_actual_config(mock_application_stub):
    # Test that the fetcher initializes correctly with the actual config values
    fetcher = ApplicationFetcher(mock_application_stub)
    
    assert fetcher.limit == config.LIMIT
    assert fetcher.offset == config.OFFSET
    assert fetcher.max_applications == config.MAX_APPLICATIONS

def test_fetch_applications_with_actual_config_values(mock_application_stub, caplog):
    # Setup mock response matching the actual LIMIT from config
    mock_response = Mock()
    mock_response.result = [Mock(id=f"app_{i}") for i in range(config.LIMIT)]
    mock_application_stub.List.return_value = mock_response
    
    fetcher = ApplicationFetcher(mock_application_stub)
    tenant_id = "test_tenant"
    result = fetcher.fetch_applications(tenant_id)
    
    # Verify the call used the actual config values
    args, kwargs = mock_application_stub.List.call_args_list[0]
    assert args[0].limit == config.LIMIT
    assert args[0].offset == config.OFFSET
    assert kwargs['metadata'] == config.AUTH_METADATA



def test_auth_metadata_usage(mock_application_stub):
    # Verify the actual AUTH_METADATA is used in gRPC calls
    mock_response = Mock()
    mock_response.result = []
    mock_application_stub.List.return_value = mock_response
    
    fetcher = ApplicationFetcher(mock_application_stub)
    tenant_id = "test_tenant"
    fetcher.fetch_applications(tenant_id)
    
    args, kwargs = mock_application_stub.List.call_args_list[0]
    assert kwargs['metadata'] == config.AUTH_METADATA
    assert kwargs['metadata'][0][0] == "authorization"
    assert kwargs['metadata'][0][1].startswith("Bearer ")

def test_config_values_are_used_correctly(mock_application_stub):
    # Verify all relevant config values are properly used
    fetcher = ApplicationFetcher(mock_application_stub)
    
    assert fetcher.limit == 100  # From config.LIMIT
    assert fetcher.offset == 0  # From config.OFFSET
    assert fetcher.max_applications == 1000  # From config.MAX_APPLICATIONS
    
    # Verify the class enforces these values in its operations
    mock_response = Mock()
    mock_response.result = [Mock(id=f"app_{i}") for i in range(50)]
    mock_application_stub.List.return_value = mock_response
    
    tenant_id = "test_tenant"
    fetcher.fetch_applications(tenant_id)
    
    args, kwargs = mock_application_stub.List.call_args_list[0]
    assert args[0].limit == 100  # Using config.LIMIT
    assert args[0].offset == 0  # Using config.OFFSET