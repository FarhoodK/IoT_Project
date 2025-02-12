from publisher import MqttClient

broker = "mqtt.eclipseprojects.io"
topic = "smartender/status"

mqtt_client = MqttClient(broker, topic)
mqtt_client.connect()
mqtt_client.subscribe(mqtt_client.on_message)

print(f"Subscribed to {topic} on broker {broker}")

try:
    while True:
        pass

except KeyboardInterrupt:
    print("Disconnecting from broker due to keyboard interrupt")
    mqtt_client.client.loop_stop()
    mqtt_client.client.disconnect()
