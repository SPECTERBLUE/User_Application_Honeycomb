import paho.mqtt.client as mqtt
import base64
import json
import logging
import time
from downlink import process_downlink_packet
from key_rotation import KeyRotationManager
import config

from device_manager import device_manager
import grpc
from config import AUTH_METADATA, CHIRPSTACK_HOST
from chirpstack_api import api
from binascii import unhexlify

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MQTT broker details
broker = config.mqtt  # Replace with your ChirpStack MQTT broker address
port = 1883  # Default MQTT port (use 8883 for TLS)
event_up_topic = "application/+/device/+/event/up"  # Topic for uplink events
event_join_topic = "application/+/device/+/event/join"  # Topic for join events

# Global State
last_rotation_time = 0  # Timestamp of the last key rotation
key_manager = None  # KeyRotationManager instance (initialized later)

def initialize_key_rotation(channel_input, auth_token_input):
    """Initialize KeyRotationManager before use."""
    global key_manager, channel, auth_token, last_rotation_time
    
    channel = channel_input
    auth_token = auth_token_input
    
    key_manager = KeyRotationManager(channel, auth_token)
    logger.info("Key Rotation Manager initialized successfully.")

def on_connect(client, userdata, flags, rc):
    """Callback when the client connects to the MQTT broker."""
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {broker}:{port} with result code {rc}")
        try:
            client.subscribe(event_up_topic)
            client.subscribe(event_join_topic)
            logger.info(f"Subscribed to topics: {event_up_topic}, {event_join_topic}")
        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    """Callback when a message is received."""
    global last_rotation_time, key_manager
    try:
        logger.info(f"Message received on topic {msg.topic}")
        payload = json.loads(msg.payload.decode("utf-8"))
        logger.info(f"Decoded JSON payload: {payload}")
        
        # Handle join event
        if "join" in msg.topic:
            handle_join_event(payload)
            return
        
        # Extract fields for uplink event
        dr = payload.get("dr")
        f_cnt = payload.get("fCnt")
        f_port = payload.get("fPort")
        data_base64 = payload.get("data")
        dev_eui = payload["deviceInfo"].get("devEui")
        
        if not all([dr, f_cnt, f_port, data_base64, dev_eui]):
            logger.warning("Missing fields in payload")
            return
        
        # Decode Base64 data
        data_bytes = base64.b64decode(data_base64)
        data_hex = data_bytes.hex()
        
        # Process downlink packet
        packet = f"PORT:{f_port} RX:{data_hex} DevEUI:{dev_eui}"
        logger.info(f"Packet: {packet}")
        process_downlink_packet(packet)
        
        # Log extracted information
        logger.info(f"DR: {dr}, FCnt: {f_cnt}, FPort: {f_port}, Data (Hex): {data_hex}")
        logger.info(f"Device EUI: {dev_eui}")
        
        # Check if 2 months have passed and trigger key rotation
        current_time = time.time()
        if current_time - last_rotation_time >= 30 * 24 * 60 * 60:  # 2 months in seconds
            logger.info("🔄 2 months passed. Initiating key rotation...")
            if key_manager:
                key_manager.rotate_keys()
                last_rotation_time = current_time  # Update timestamp
            else:
                logger.warning("KeyRotationManager not initialized!")
    except Exception as e:
        logger.exception(f"Unexpected error processing message: {e}")

def handle_join_event(payload):
    """Handle join event and trigger key rotation."""
    global last_rotation_time, key_manager
    try:
        
        # flush
        for _, device_info in device_manager.all_devices.items():
            dev_eui = device_info.get("euid")
            channel = grpc.insecure_channel(CHIRPSTACK_HOST)
            client = api.DeviceServiceStub(channel)
            req = api.FlushDeviceQueueRequest(dev_eui=dev_eui)
            resp = client.FlushQueue(req, metadata=AUTH_METADATA)
            logger.info(f"Device Queue Flush Enqueued {dev_eui}")
        #
        
        dev_eui = payload["deviceInfo"].get("devEui")
        if not dev_eui:
            logger.warning("Missing DevEUI in join event")
            return
        
        logger.info(f"Device {dev_eui} joined.")

        if key_manager:
            logger.info(f"🔑 Rotating keys for device {dev_eui}...")
            time.sleep(0.5 * 60)  # Simulate delay
            key_manager.rotate_keys()
            last_rotation_time = time.time()
        else:
            logger.warning("KeyRotationManager not initialized!")
    except Exception as e:
        logger.exception(f"Unexpected error handling join event: {e}")

def start_mqtt_client():
    """Initialize and start the MQTT client."""
    try:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        
        logger.info("Connecting to MQTT broker...")
        client.connect(broker, port, 60)
        
        logger.info("Listening for device events...")
        client.loop_forever()
    except Exception as e:
        logger.exception(f"MQTT Client error: {e}")
