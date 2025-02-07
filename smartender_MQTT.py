import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, broker, port, topic):
        self.client = mqtt.Client()
        self.client.connect(broker, port)
        self.client.loop_start()
        self.topic = topic

    def publish(self, topic, message):
        self.client.publish(topic, message)

    def subscribe(self, on_message):
        self.client.subscribe(self.topic)

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()