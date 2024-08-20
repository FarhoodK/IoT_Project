import paho.mqtt.client as mqtt

class MqttClient:
    def __init__(self, broker, topic):
        self.client = mqtt.Client()
        self.broker = broker
        self.topic = topic

    def connect(self):
        self.client.connect(self.broker)
        self.client.loop_start()

    def publish(self, msg):
        self.client.publish(self.topic, msg)

    def subscribe(self, callback=None):
        self.client.subscribe(self.topic)
        self.client.on_message = callback

    def on_message(self, client, userdata,msg):
        print(f"Received message: {msg.payload.decode()} on topic {msg.topic}")
