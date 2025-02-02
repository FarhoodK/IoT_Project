import paho.mqtt.client as mqtt
import json

class MqttClient:
    def __init__(self, broker, topic):
        self.client = mqtt.Client()
        self.broker = broker
        self.topic = topic
        self.message_queue = []

    def connect(self):
        try:
            self.client.connect(self.broker)
            self.client.subscribe(self.topic)
            self.client.on_message = self._on_message
            self.client.loop_start()
        except Exception as e:
            print(f"MQTT Connection Error: {e}")

    def _on_message(self, client, userdata, msg):
        try:
            message = json.loads(msg.payload.decode())
            self.message_queue.append(message)
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def publish(self, msg):
        self.client.publish(self.topic, json.dumps(msg))

    def get_messages(self):
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages