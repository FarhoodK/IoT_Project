import json
from tqdm import tqdm
import time
from datetime import datetime

class Pump:
    def __init__(self, id, ingredient, temperature, maintenance, cocktails, 
                temperature_sensor, float_switch, last_refill_time, mqtt_client):
        self.id = id
        self.ingredient = ingredient
        self.temperature = temperature
        self.maintenance = maintenance
        self.cocktails = cocktails
        self.temperature_sensor = temperature_sensor
        self.float_switch = float_switch
        self.last_refill_time = last_refill_time
        self.mqtt_client = mqtt_client

    def wait_for_optimal_temperature(self, optimal_temp):
        current_temp = self.temperature_sensor.read_temperature(self.last_refill_time)
        if current_temp > optimal_temp:
            return False
        return True

    def display_status(self):
        temp = self.temperature_sensor.read_temperature(self.last_refill_time)
        quantity = self.float_switch.left_quantity
        status_msg = {
            "Pump_Number": self.id,
            "Ingredient": self.ingredient,
            "Current_Temperature": temp,
            "Remaining_Quantity": round(quantity, 2),
            "Maintenance_Needed": self.float_switch.maintenance,
            "Configured_for": self.cocktails,
            "timestamp": datetime.now().isoformat(),
            "type": "status"
        }
        self.mqtt_client.publish(status_msg)

    def refill(self):
        self.float_switch.left_quantity = 0
        refill_duration = 10
        steps = 100
        step_time = refill_duration / steps

        for _ in tqdm(range(steps), desc=f"Refilling {self.ingredient}", unit="step"):
            time.sleep(step_time)

        self.float_switch.left_quantity = 100
        self.last_refill_time = datetime.now()
        
        status_msg = {
            'Pump_Number': self.id,
            "Ingredient": self.ingredient,
            "Action": "Refill",
            "New_Quantity": self.float_switch.left_quantity,
            "Current_Temperature": self.temperature_sensor.read_temperature(self.last_refill_time),
            "timestamp": datetime.now().isoformat(),
            "type": "refill"
        }
        self.mqtt_client.publish(status_msg)

    def erogate(self, ingredient, ml, optimal_temp, required_qty_percent):
        if not self.wait_for_optimal_temperature(optimal_temp):
            return

        if self.float_switch.left_quantity < required_qty_percent:
            self.refill()
            if not self.wait_for_optimal_temperature(optimal_temp):
                return

        flow_rate = 600
        total_time_seconds = (ml / flow_rate) * 60
        steps = 100
        step_time = total_time_seconds / steps

        for _ in tqdm(range(steps), desc=f"Dispensing {ingredient}", unit="step"):
            time.sleep(step_time)

        remaining = self.float_switch.read_quantity(ml)
        status_msg = {
            'Pump_Number': self.id,
            "Ingredient": self.ingredient,
            "Action": "Dispense",
            "Dispensed_ml": ml,
            "Remaining_Quantity": remaining,
            "Current_Temperature": self.temperature_sensor.read_temperature(self.last_refill_time),
            "timestamp": datetime.now().isoformat(),
            "type": "dispense"
        }
        self.mqtt_client.publish(status_msg)