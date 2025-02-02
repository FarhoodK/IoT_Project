from publisher import MqttClient
import json

broker = "mqtt.eclipseprojects.io"
topic = "smartender/status"

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received update: {payload}")
    except json.JSONDecodeError:
        print("Received invalid JSON message")

mqtt_client = MqttClient(broker, topic)
mqtt_client.subscribe(on_message)
mqtt_client.connect()

print(f"Subscribed to {topic}")
try:
    while True: pass
except KeyboardInterrupt:
    mqtt_client.client.disconnect()