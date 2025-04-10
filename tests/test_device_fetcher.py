import pytest
from unittest.mock import Mock, patch
from chirpstack_api import api
import grpc
import logging
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
import config
from device_fetcher import DeviceFetcher  

# Setup logging for tests
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_device_stub():
    return Mock()

@pytest.fixture
def auth_token():
    return config.AUTH_METADATA

@pytest.fixture
def sample_device():
    ts = Timestamp()
    ts.FromDatetime(datetime(2023, 1, 1))
    device = Mock()
    device.name = "test_device"
    device.dev_eui = "1122334455667788"
    device.description = "Test device"
    device.device_profile_id = "profile_123"
    device.device_profile_name = "Test Profile"
    device.created_at = ts
    device.updated_at = ts
    device.last_seen_at = ts
    return device

def test_initialization_validation(mock_device_stub, auth_token):
    # Test invalid LIMIT
    original_limit = config.LIMIT
    try:
        config.LIMIT = 0
        with pytest.raises(ValueError, match="LIMIT must be a positive integer"):
            DeviceFetcher(mock_device_stub, auth_token)
    finally:
        config.LIMIT = original_limit

    # Test invalid OFFSET
    original_offset = config.OFFSET
    try:
        config.OFFSET = -1
        with pytest.raises(ValueError, match="OFFSET must be a non-negative integer"):
            DeviceFetcher(mock_device_stub, auth_token)
    finally:
        config.OFFSET = original_offset

    # Test invalid MAX_DEVICES
    original_max = config.MAX_DEVICES
    try:
        config.MAX_DEVICES = 0
        with pytest.raises(ValueError, match="MAX_DEVICES must be a positive integer"):
            DeviceFetcher(mock_device_stub, auth_token)
    finally:
        config.MAX_DEVICES = original_max


def test_get_devices_as_dict_empty_response(mock_device_stub, auth_token, caplog):
    mock_response = Mock()
    mock_response.result = []
    mock_device_stub.List.return_value = mock_response
    
    fetcher = DeviceFetcher(mock_device_stub, auth_token)
    result = fetcher.get_devices_as_dict("test_app_123")
    
    assert result == {}
    assert "No devices found for the given Application ID." in caplog.text

def test_get_devices_as_dict_max_limit_reached(mock_device_stub, auth_token, caplog):
    original_max = config.MAX_DEVICES
    try:
        config.MAX_DEVICES = 150  # Set lower limit for test
        
        # Create mock devices
        devices = []
        for i in range(150):
            device = Mock()
            device.name = f"device_{i}"
            device.dev_eui = f"eui_{i}"
            device.description = f"Description {i}"
            device.device_profile_id = f"profile_{i}"
            device.device_profile_name = f"Profile {i}"
            device.created_at = None
            device.updated_at = None
            device.last_seen_at = None
            devices.append(device)
        
        # Setup mock to return pages
        mock_device_stub.List.side_effect = [
            Mock(result=devices[:100]),  # First page
            Mock(result=devices[100:150])  # Second page
        ]
        
        fetcher = DeviceFetcher(mock_device_stub, auth_token)
        result = fetcher.get_devices_as_dict("test_app_123")
        
        # Should get exactly 150 devices
        assert len(result) == 150
        assert mock_device_stub.List.call_count == 2
    finally:
        config.MAX_DEVICES = original_max
def test_get_devices_as_dict_grpc_error(mock_device_stub, auth_token, caplog):
    mock_device_stub.List.side_effect = grpc.RpcError("Test gRPC error")
    
    fetcher = DeviceFetcher(mock_device_stub, auth_token)
    result = fetcher.get_devices_as_dict("test_app_123")
    
    assert "error" in result
    assert "Error fetching devices" in result["error"]
    assert "gRPC error occurred" in caplog.text

def test_get_devices_as_dict_unexpected_error(mock_device_stub, auth_token, caplog):
    mock_device_stub.List.side_effect = Exception("Test unexpected error")
    
    fetcher = DeviceFetcher(mock_device_stub, auth_token)
    result = fetcher.get_devices_as_dict("test_app_123")
    
    assert "error" in result
    assert "An unexpected error occurred" in result["error"]
    assert "An unexpected error occurred" in caplog.text

def test_device_metadata_structure(mock_device_stub, auth_token, sample_device):
    mock_response = Mock()
    mock_response.result = [sample_device]
    mock_device_stub.List.return_value = mock_response
    
    fetcher = DeviceFetcher(mock_device_stub, auth_token)
    result = fetcher.get_devices_as_dict("test_app_123")
    
    device_info = result["test_device"]
    assert device_info["euid"] == "1122334455667788"
    assert device_info["description"] == "Test device"
    assert device_info["device_profile_id"] == "profile_123"
    assert device_info["device_profile_name"] == "Test Profile"
    assert device_info["created_at"] == "2023-01-01T00:00:00"
    assert device_info["updated_at"] == "2023-01-01T00:00:00"
    assert device_info["last_seen_at"] == "2023-01-01T00:00:00"

def test_null_timestamp_handling(mock_device_stub, auth_token):
    device = Mock()
    device.name = "test_device"
    device.dev_eui = "1122334455667788"
    device.description = "Test device"
    device.device_profile_id = "profile_123"
    device.device_profile_name = "Test Profile"
    device.created_at = None
    device.updated_at = None
    device.last_seen_at = None
    
    mock_response = Mock()
    mock_response.result = [device]
    mock_device_stub.List.return_value = mock_response
    
    fetcher = DeviceFetcher(mock_device_stub, auth_token)
    result = fetcher.get_devices_as_dict("test_app_123")
    
    device_info = result["test_device"]
    assert device_info["created_at"] is None
    assert device_info["updated_at"] is None
    assert device_info["last_seen_at"] is None