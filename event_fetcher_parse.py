import paho.mqtt.client as mqtt
import base64
import json
from device_manager import device_manager

# MQTT broker details
broker = "localhost"  # Replace with your ChirpStack MQTT broker address
port = 1883           # Default MQTT port (use 8883 for TLS)
topic = "application/+/device/+/event/+"  # Topic for all events

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # Subscribe to the topic
    client.subscribe(topic)
    print(f"Subscribed to topic: {topic}")
    
# Function to find the device codec by matching dev_eui
def get_device_codec(dev_eui):
    """Match dev_eui with euid in all_devices and return codec."""
    for device_name, device_info in device_manager.all_devices.items():
        if device_info.get("euid") == dev_eui:
            return device_info.get("codec")
    return None  # Return None if no matching device is found

# Callback when a message is received
def on_message(client, userdata, msg):
    try:
        # Decode the message payload (JSON format)
        payload = json.loads(msg.payload.decode("utf-8"))
        # Extract fields
        dr = payload["dr"]
        f_cnt = payload["fCnt"]
        f_port = payload["fPort"]
        data_base64 = payload["data"]
        dev_eui = payload["deviceInfo"]["devEui"]  # Extract devEui

        # Decode the Base64 data
        data_bytes = base64.b64decode(data_base64)

        # Convert bytes to hexadecimal string
        data_hex = data_bytes.hex()
        
         # Find the codec based on dev_eui
        codec = get_device_codec(dev_eui)

        if codec:
            print(f"Device {dev_eui} found. Using codec: {codec}")
            # Here, use the codec to decode `data_hex` (implement actual decoding logic)
            #decoded_data = codec.decode(data_hex)  # Assuming codec has a `.decode()` method
            #print(f"Decoded Data: {decoded_data}")
        else:
            print(f"No codec found for device {dev_eui}. Raw data: {data_hex}")

        # Print extracted information
        print(f"DR: {dr}, FCnt: {f_cnt}, FPort: {f_port}, Data (Hex): {data_hex}")

        # Print the result
        print(f"DR: {dr}")
        print(f"Data: {data_hex}")
        print(f"FCnt: {f_cnt}")
        print(f"FPort: {f_port}")
        print(f"devEui: {dev_eui}")
    except Exception as e:
        print(f"Error processing message: {e}")

def start_mqtt_client():
    """Start the MQTT client and listen for events."""
    # Create an MQTT client
    client = mqtt.Client()

    # Assign callback functions
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to the MQTT broker
    client.connect(broker, port, 60)

    # Start the loop to process incoming messages
    print("Listening for all device events...")
    client.loop_forever()