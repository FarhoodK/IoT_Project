import json
from tqdm import tqdm
import time
from datetime import datetime


class Pump:
    """Represents a pump that handles dispensing of cocktail ingredients."""

    def __init__(self, id, ingredient, temperature, maintenance, cocktails, temperature_sensor, float_switch,
                 last_refill_time,mqtt_client):
        self.id = id
        self.ingredient = ingredient
        self.temperature = temperature
        self.maintenance = maintenance
        self.cocktails = cocktails
        self.temperature_sensor = temperature_sensor
        self.float_switch = float_switch
        self.last_refill_time = last_refill_time
        self.mqtt_client = mqtt_client  #Add MQTT client instance

    def display_status(self):
        """Display the current status of the pump."""
        temp = self.temperature_sensor.read_temperature(self.last_refill_time)
        quantity = self.float_switch.left_quantity
        status_msg = {"Pump_Number": self.id,
                      "Ingredient": self.ingredient,
                      "Current_Temperature": {temp},
                      "Remaining_Quantity": round(quantity, 2),
                      "Maintenance_Needed": self.float_switch.maintenance,
                      "Configured_for": self.cocktails}
        
        #print(f"Pump Number: {self.id},\nIngredient: {self.ingredient},\nCurrent Temperature: {temp}°C,\nRemaining Quantity: {round(quantity, 2)}%,\nMaintenance Needed: {self.float_switch.maintenance},\nConfigured for: {self.cocktails}\n")

        #pubish status to MQTT
        self.mqtt_client.publish(json.dumps(status_msg))

    def refill(self):
        """Refill the pump and reset its quantity.Publish status vis MQTT"""
        print(f"Refilling {self.ingredient}...")
        self.float_switch.left_quantity = 0  # Start from empty to show refill progress
        refill_duration = 10  # seconds
        steps = 100
        step_time = refill_duration / steps

        # Simulate the refilling process with a progress bar
        for _ in tqdm(range(steps), desc=f"Refilling {self.ingredient}", unit="step"):
            time.sleep(step_time)

        self.float_switch.left_quantity = 100
        self.last_refill_time = datetime.now()
        self.temperature_sensor.read_temperature(self.last_refill_time)
        print(
            f"{self.ingredient} refilled. Current quantity: {self.float_switch.left_quantity}%. Current temperature: {self.temperature_sensor.read_temperature(self.last_refill_time)}°C\n")

        #Publish status to MQTT
        status_msg= {'Pump_Number': self.id,
                     "Ingredient": self.ingredient,
                     "Action": "Refill",
                     "New_Quantity": self.float_switch.left_quantity,
                     "Current_Temperature": self.temperature_sensor.read_temperature(self.last_refill_time)}

        self.mqtt_client.publish(json.dumps(status_msg))

    def wait_for_optimal_temperature(self, optimal_temp):
        """
        Check if the ingredient has reached the optimal temperature.
        Return False if the temperature is still above the optimal value.
        """
        current_temp = self.temperature_sensor.read_temperature(self.last_refill_time)
        if current_temp > optimal_temp:
            print(
                f"The {self.ingredient} is still above its optimal temperature. Please wait a few minutes or choose another cocktail.")
            return False
        return True

    def erogate(self, ingredient, ml, optimal_temp, required_qty_percent):
        """
        Dispense the specified amount of ingredient if the temperature is optimal and the quantity is enough. Publish status via MQTT
        """
        if not self.wait_for_optimal_temperature(optimal_temp):
            return

        if self.float_switch.left_quantity < required_qty_percent:
            self.refill()
            if not self.wait_for_optimal_temperature(optimal_temp):
                return

        print(f"Erogating {ml}ml of {ingredient}...")
        flow_rate = 600  # ml per minute
        total_time_seconds = (ml / flow_rate) * 60
        steps = 100
        step_time = total_time_seconds / steps

        for _ in tqdm(range(steps), desc=f"Erogating {ingredient}", unit="step"):
            time.sleep(step_time)

        print(f"Remaining quantity of {ingredient}: {self.float_switch.read_quantity(ml)}%\n")

        #Publish status to MQTT

        status_msg = {'Pump_Number': self.id,
                      "Ingredient": self.ingredient,
                      "Action": "Erogate",
                      "Dispensed_Quantity": ml,
                      "Remaining_Quantity": self.float_switch.read_quantity(ml)}
        
        self.mqtt_client.publish(json.dumps(status_msg))
        