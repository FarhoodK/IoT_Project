# publisher.py
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time
import threading


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
            message['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.message_queue.append(message)
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def publish(self, msg_type, details=None):
        """
        Publish standardized message with type and details
        :param msg_type: Type of message (e.g., 'cocktail_order', 'cocktail_status', 'pump_status')
        :param details: Dictionary of additional details
        """
        message = {
            'type': msg_type,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if details:
            message.update(details)
        print(f"Published message {message} on {self.topic}")
        self.client.publish(self.topic, json.dumps(message))

    def get_messages(self):
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages

    def start_listening(self, callback):
        def listen():
            while True:
                new_messages = self.get_messages()
                if new_messages:
                    callback(new_messages)
                time.sleep(1)

        listener_thread = threading.Thread(target=listen)
        listener_thread.daemon = True
        listener_thread.start()
