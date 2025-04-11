import pytest
from unittest.mock import Mock, patch, MagicMock
import grpc
import logging
from chirpstack_api import api
from device_manager import DeviceManager  

@pytest.fixture
def mock_device_manager():
    # Patch the gRPC channel and stubs
    with patch('grpc.insecure_channel'), \
         patch('device_manager.api.TenantServiceStub'), \
         patch('device_manager.api.ApplicationServiceStub'), \
         patch('device_manager.api.DeviceServiceStub'), \
         patch('device_manager.api.DeviceProfileServiceStub'):
        
        # Create a DeviceManager instance with mocked dependencies
        manager = DeviceManager()
        
        # Mock the fetcher classes
        manager.tenant_fetcher = Mock()
        manager.application_fetcher = Mock()
        manager.device_fetcher = Mock()
        manager.codec_fetcher = Mock()
        
        yield manager

def test_initialization(mock_device_manager):
    """Test that DeviceManager initializes correctly."""
    assert isinstance(mock_device_manager, DeviceManager)
    assert mock_device_manager.all_devices == {}

def test_fetch_all_devices_no_tenants(mock_device_manager, caplog):
    """Test behavior when no tenants are found."""
    mock_device_manager.tenant_fetcher.fetch_tenants.return_value = []
    
    mock_device_manager.fetch_all_devices()
    
    assert "No tenants found." in caplog.text
    assert mock_device_manager.all_devices == {}

def test_fetch_all_devices_no_applications(mock_device_manager, caplog):
    """Test behavior when tenants exist but have no applications."""
    mock_device_manager.tenant_fetcher.fetch_tenants.return_value = ["tenant1"]
    mock_device_manager.application_fetcher.fetch_applications.return_value = []
    
    mock_device_manager.fetch_all_devices()
    
    assert "No applications found for tenant ID: tenant1" in caplog.text
    assert mock_device_manager.all_devices == {}

def test_fetch_all_devices_success(mock_device_manager, caplog):
    """Test successful device fetching with all components."""
    # Ensure we capture INFO level logs
    caplog.set_level(logging.INFO)
    
    # Setup mock data
    mock_device_manager.tenant_fetcher.fetch_tenants.return_value = ["tenant1"]
    mock_device_manager.application_fetcher.fetch_applications.return_value = ["app1", "app2"]

    # Mock device data - return different devices for each app
    mock_devices_app1 = {
        "device1": {
            "device_profile_id": "profile1",
            "other_data": "value1"
        }
    }
    mock_devices_app2 = {
        "device2": {
            "device_profile_id": "profile2",
            "other_data": "value2"
        }
    }
    # Return different devices for different app calls
    mock_device_manager.device_fetcher.get_devices_as_dict.side_effect = [
        mock_devices_app1,
        mock_devices_app2
    ]

    # Mock codec data
    mock_codec_info = {
        "codec_type": "CUSTOM",
        "payload_encoder": "encoder_script"
    }
    mock_device_manager.codec_fetcher.fetch_codec.return_value = mock_codec_info

    mock_device_manager.fetch_all_devices()

    # Verify calls
    mock_device_manager.tenant_fetcher.fetch_tenants.assert_called_once()
    mock_device_manager.application_fetcher.fetch_applications.assert_called_with("tenant1")
    assert mock_device_manager.device_fetcher.get_devices_as_dict.call_count == 2
    assert mock_device_manager.codec_fetcher.fetch_codec.call_count == 2  # One for each device

    # Verify the final device data
    assert len(mock_device_manager.all_devices) == 2
    assert "device1" in mock_device_manager.all_devices
    assert "device2" in mock_device_manager.all_devices
    
    # Verify logging
    log_messages = [record.message for record in caplog.records]
    assert "Fetching all devices..." in log_messages
    assert "Fetched tenant IDs: ['tenant1']" in log_messages
    assert "Fetching applications for tenant ID: tenant1" in log_messages
    assert "Applications for tenant ID tenant1: ['app1', 'app2']" in log_messages
    assert "Updated codec information for device: device1" in log_messages
    assert "Updated codec information for device: device2" in log_messages
    assert "Updated device list: 2 devices." in log_messages

def test_fetch_all_devices_with_error(mock_device_manager, caplog):
    """Test error handling during device fetching."""
    mock_device_manager.tenant_fetcher.fetch_tenants.return_value = ["tenant1"]
    mock_device_manager.application_fetcher.fetch_applications.side_effect = Exception("Test error")
    
    mock_device_manager.fetch_all_devices()
    
    assert "Error fetching applications for tenant tenant1" in caplog.text
    assert mock_device_manager.all_devices == {}

def test_get_device_list(mock_device_manager):
    """Test get_device_list method."""
    test_devices = {"device1": {"data": "value1"}, "device2": {"data": "value2"}}
    mock_device_manager.all_devices = test_devices
    
    assert mock_device_manager.get_device_list() == test_devices

@patch('device_manager.Console')
def test_show_device_names_empty(mock_console, mock_device_manager):
    """Test show_device_names with empty device list."""
    mock_device_manager.all_devices = {}
    mock_device_manager.show_device_names()
    
    # Verify the "No devices found!" message was printed
    mock_console.return_value.print.assert_called_with("[bold red]No devices found![/bold red]")

@patch('device_manager.Table')
@patch('device_manager.Console')
def test_show_device_names_with_devices(mock_console, mock_table, mock_device_manager):
    """Test show_device_names with devices."""
    mock_device_manager.all_devices = {
        "device1": {"device_profile_id": "profile1"},
        "device2": {"device_profile_id": "profile2"}
    }
    
    # Setup table mock
    mock_table_instance = MagicMock()
    mock_table.return_value = mock_table_instance
    
    mock_device_manager.show_device_names()
    
    # Verify table was created with correct columns
    mock_table.assert_called_with(title="Device List")
    mock_table_instance.add_column.assert_any_call("Device Name", justify="left", style="cyan", no_wrap=True)
    mock_table_instance.add_column.assert_any_call("Device Profile ID", justify="left", style="green")
    
    # Verify devices were added to table
    assert mock_table_instance.add_row.call_count == 2
    mock_console.return_value.print.assert_called_with(mock_table_instance)