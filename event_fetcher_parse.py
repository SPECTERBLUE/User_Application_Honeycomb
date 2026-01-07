import paho.mqtt.client as mqtt
import base64
import json
import logging
import time
from downlink import is_valid_hex, process_downlink_packet, get_device_codec, get_application_id
from key_rotation import KeyRotationManager
import config
import js2py
from device_manager import device_manager
from send_http_request import HttpSender
import grpc
from config import AUTH_METADATA, CHIRPSTACK_HOST ,AUTO_KEY_ROTATION_TIME
from chirpstack_api import api
from binascii import unhexlify
import js2py

def js_to_py(obj):
    # js2py object
    if isinstance(obj, js2py.base.JsObjectWrapper):

        # Detect JS Array (numeric keys)
        try:
            keys = obj.to_dict().keys()
            if all(str(k).isdigit() for k in keys):
                return [js_to_py(obj[k]) for k in sorted(keys, key=int)]
            else:
                return {k: js_to_py(v) for k, v in obj.to_dict().items()}
        except Exception:
            pass

        # Fallback
        try:
            return obj.to_list()
        except Exception:
            return obj

    # Native Python types
    elif isinstance(obj, list):
        return [js_to_py(i) for i in obj]

    elif isinstance(obj, dict):
        return {k: js_to_py(v) for k, v in obj.items()}

    return obj


# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

channel = grpc.insecure_channel(config.CHIRPSTACK_HOST)
sender = HttpSender(channel, config.AUTH_METADATA)

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
    
    if config.SYMETRIC_CYPHERING==False:
        logger.debug("Asymmetric cyphering is enabled.")
        
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
            if current_time - last_rotation_time >= AUTO_KEY_ROTATION_TIME:  # 2 months in seconds
                logger.info("🔄 2 months passed. Initiating key rotation...")
                if key_manager:
                    key_manager.rotate_keys()
                    last_rotation_time = current_time  # Update timestamp
                else:
                    logger.warning("KeyRotationManager not initialized!")
        except Exception as e:
            logger.exception(f"Unexpected error processing message: {e}")
            
    else:
        logger.debug("Symetric cyphering is enabled. Skipping asymmetric key rotation handling.")
        try:
            logger.info("entered loop symetric cyphering")
            logger.info(f"Message received on topic {msg.topic}")
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"Decoded JSON payload: {payload}") 
            
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
            
            # Log extracted information
            logger.info(f"DR: {dr}, FCnt: {f_cnt}, FPort: {f_port}, Data (Hex): {data_hex}")
            logger.info(f"Device EUI: {dev_eui}")

            if not is_valid_hex(data_hex):
                logging.error(f"Invalid hex data received for device {dev_eui}: {data_hex}")
                return  # Exit if invalid hex data
            
            # Find codec for the device
            codec = get_device_codec(dev_eui)

            if codec:
                logging.debug(f"Device {dev_eui} found. Using codec: {codec}")
                # decoded_data = codec.decode(data_hex)  # Implement decoding logic
                # logger.info(f"Decoded Data: {decoded_data}")
            else:
                logging.warning(f"No codec found for device {dev_eui}.")
        
            # ===============================
            #  JavaScript codec execution
            # ===============================
            js_decoder = js2py.EvalJs()
            js_decoder.execute(codec)   # codec must define decodeUplink()

            # Prepare ChirpStack-style input
            js_input = {
                "bytes": list(data_bytes),   # IMPORTANT: raw bytes, NOT UTF-8
                "fPort": f_port
            }

            decoded_result = js_decoder.decodeUplink(js_input)
            logger.info(f"Decoded result for {dev_eui}: {decoded_result}")
            
            decoded_result = js_to_py(decoded_result)


            # Extract SenML / decoded payload
            payload = decoded_result.get("Payload", {})
            senml_records = payload.get("data", [])
            logger.info(f"SenML records for {dev_eui}: {senml_records}")

            # Get application ID dynamically
            application_id = get_application_id(dev_eui)
            if not application_id:
                logging.error(f"Application ID not found for device {dev_eui}, skipping processing.")
                return None
 
            sender.send_payload(application_id, senml_records)
            
            logging.info(f"Payload sent successfully to application {application_id}: {senml_records}")
            
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
            time.sleep(config.JOIN_SIMULATED_TIME_DELAY)  # Simulate delay
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
