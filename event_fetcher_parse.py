import paho.mqtt.client as mqtt
import base64
import json

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

        # Print the result
        print(f"DR: {dr}")
        print(f"Data: {data_hex}")
        print(f"FCnt: {f_cnt}")
        print(f"FPort: {f_port}")
        print(f"devEui: {dev_eui}")
    except Exception as e:
        print(f"Error processing message: {e}")

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