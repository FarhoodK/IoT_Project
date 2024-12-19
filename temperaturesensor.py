import random
from datetime import datetime, timedelta

class TemperatureSensor:
    """Simulates a temperature sensor."""
    
    def __init__(self, initial_temperature=None):
        self.temperature = initial_temperature

    def read_temperature(self, last_refill_time):
        """
        Simulate temperature reading.
        If the last refill was within the last minute, the sensed temperature will be higher.
        """
        if last_refill_time and datetime.now() < last_refill_time + timedelta(seconds=10):
            self.temperature = round(random.uniform(4.1, 25.0), 2)
        else:
            self.temperature = round(random.uniform(0.0, 4.0), 2)
        return self.temperature