from tqdm import tqdm
import time
from datetime import datetime


class Pump:
    def __init__(self, id, ingredient, temperature, maintenance, cocktails,
                 temperature_sensor, float_switch, last_refill_time):
        self.id = id
        self.ingredient = ingredient
        self.temperature = temperature
        self.maintenance = maintenance
        self.cocktails = cocktails
        self.temperature_sensor = temperature_sensor
        self.float_switch = float_switch
        self.last_refill_time = last_refill_time

    def wait_for_optimal_temperature(self, optimal_temp):
        current_temp = self.temperature_sensor.read_temperature(self.last_refill_time)
        return current_temp <= optimal_temp

    def display_status(self):
        status_msg = {
            "Pump_Number": self.id,
            "Ingredient": self.ingredient,
            "Current_Temperature": self.temperature_sensor.read_temperature(self.last_refill_time),
            "Remaining_Quantity": round(self.float_switch.left_quantity, 2),
            "Maintenance_Needed": self.float_switch.maintenance,
            "Configured_for": self.cocktails,
            "timestamp": datetime.now().isoformat()
        }
        return status_msg
        

    def refill(self):
        self.float_switch.left_quantity = 0
        refill_duration = 10
        steps = 100
        step_time = refill_duration / steps

        for _ in tqdm(range(steps), desc=f"Refilling {self.ingredient}", unit="step", ncols=80, leave=False):
            time.sleep(step_time)

        self.float_switch.left_quantity = 100
        self.last_refill_time = datetime.now()

        status_msg = {
            "Pump_Number": self.id,
            "Ingredient": self.ingredient,
            "Action": "Refill",
            "New_Quantity": self.float_switch.left_quantity,
            "Current_Temperature": self.temperature_sensor.read_temperature(self.last_refill_time),
            "timestamp": datetime.now().isoformat(),
            "type": "refill"
        }
        return status_msg

    def erogate(self, ingredient, ml, optimal_temp, required_qty_percent):
        if not self.wait_for_optimal_temperature(optimal_temp):
            return

        if self.float_switch.left_quantity < required_qty_percent:
            self.refill()
            if not self.wait_for_optimal_temperature(optimal_temp):
                return

        flow_rate = 600  # ml per minute
        total_time_seconds = (ml / flow_rate) * 60
        steps = 100
        step_time = total_time_seconds / steps

        tqdm.write(f"\nStarting dispensing process for {ingredient} ({ml} ml)...")

        # Create the progress bar and keep it in place after it finishes
        with tqdm(total=steps, desc=f"Dispensing {ingredient}", unit="step", ncols=80, dynamic_ncols=True,
                  leave=True) as pbar:
            for _ in range(steps):
                time.sleep(step_time)
                pbar.update(1)

        # Once it's finished, the progress bar will stay at 100%
        tqdm.write(f"Finished dispensing {ml} ml of {ingredient}. Remaining: {self.float_switch.read_quantity(ml)} ml")

        # Optional: Add space after the progress bar to prevent it from being overwritten too quickly
        print("\n" * 1)  # Adds one blank line to separate the next progress bar

        # Update status via MQTT
        current_temp = self.temperature_sensor.read_temperature(self.last_refill_time)
        status_msg = {
            "Pump_Number": self.id,
            "Ingredient": self.ingredient,
            "Action": "Dispense",
            "Dispensed_ml": ml,
            "Remaining_Quantity": self.float_switch.read_quantity(ml),
            "Current_Temperature": current_temp,
            "timestamp": datetime.now().isoformat(),
            "type": "dispense"
        }
        return status_msg


