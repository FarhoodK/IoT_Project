import json
import threading
import time
from pump import Pump
from cocktail import Cocktail
from floatswitch import FloatSwitch
from temperaturesensor import TemperatureSensor
from datetime import datetime
from tqdm import tqdm
from smartender_bot import SmartenderBot
from orders import Orders
from logger import Logger

class Smartender:
    # Main class to handle the Smartender operations.

    def __init__(self, filename, bot_token):
        self.filename = filename
        self.available_cocktails = []
        self.selected_cocktails = []
        self.selected_ingredients = []
        self.active_pumps = []
        self.cooling_thread = None
        self.cooling_event = threading.Event()
        self.data = {"selected_cocktails": []}
        self.status = "Idle"
        self.current_task = None
        self.orders = Orders(self)
        self.bot_token = bot_token
        self.logger = Logger("SMARTENDER")

    def start_telegram_bot(self):
        self.telegram_bot = SmartenderBot(self.bot_token, self)
        self.telegram_bot.start()
        

    def load_cocktails(self):
        self.logger.info("Cocktails loaded from JSON")
        # Load cocktails from a JSON file.
        try:
            with open(self.filename, 'r') as file:
                data = json.load(file)
                for name, details in data.items():
                    self.available_cocktails.append(
                        Cocktail(name, details['ingredients'], details['steps'])
                    )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error loading cocktails: {e}")

    def save_selected_cocktails(self, cocktail_name):
        self.logger.info("Save Selected Cocktails")
        # Save selected cocktails.
        for cocktail in self.available_cocktails:
            if cocktail.name == cocktail_name:
                self.data["selected_cocktails"].append(cocktail.to_dict())
                self.logger.info(f"{cocktail_name} added to selected cocktails")
                break

    def selected_to_json(self):
        # Write selected cocktails to JSON for the Telegram Bot to read.
        with open('selected_cocktails.json', 'w') as file:
            json.dump(self.data, file, indent=4)

    def configure(self, selected_cocktails=None):
        # Configure Smartender pumps based on selected cocktails.
        self.logger.info("Configuring Smartender...")
        if selected_cocktails:
            for cocktail_name in selected_cocktails:
                self.add_cocktail(cocktail_name)
                self.save_selected_cocktails(cocktail_name)
                self.logger.info(f"Configured {cocktail_name} in Smartender")
            self.selected_to_json()
            self.setup_pumps()
            return

    def add_cocktail(self, cocktail_name):
        # Add a selected cocktail to the Smartender menu.
        for cocktail in self.available_cocktails:
            if cocktail_name.lower() == str(cocktail.name).lower():
                self.selected_cocktails.append(cocktail)
                for ingredient in cocktail.ingredients:
                    if ingredient not in self.selected_ingredients:
                        self.selected_ingredients.append(ingredient)
                self.logger.info(f"{cocktail.name} added to Smartender")
        return  # Break after adding the cocktail to avoid duplicate additions
        #print(f"Error: Cocktail {cocktail_name} not found in available cocktails.")

    def display_pump_status(self):
        # Display status of all active pumps.
        for pump in self.active_pumps:
            pump.display_status()

    def show_cocktails(self, cocktails):
        # Display list of available cocktails.
        print("\nAvailable Cocktails:\n")
        for cocktail in cocktails:
            cocktail.show()

    def setup_pumps(self):
        # Set up pumps for selected ingredients and cocktails.
        pump_id = 0
        for cocktail in self.selected_cocktails:
            for ingredient, details in cocktail.ingredients.items():
                if not self.pump_exists(ingredient):
                    # If pump for ingredient doesn't exist, create a new one
                    new_pump = Pump(
                        id=pump_id,
                        ingredient=ingredient,
                        temperature=details['temperature'],
                        maintenance=None,
                        cocktails=[cocktail.name],
                        temperature_sensor=TemperatureSensor(),
                        float_switch=FloatSwitch(),
                        last_refill_time=datetime.now(),
                    )
                    self.active_pumps.append(new_pump)
                    pump_id += 1
                else:
                    self.update_pump_cocktails(ingredient, cocktail.name)
        self.logger.info("Pumps successfully configured!\n")

    def pump_exists(self, ingredient):
        # Check if a pump for the ingredient already exists.
        return any(pump.ingredient == ingredient for pump in self.active_pumps)

    def update_pump_cocktails(self, ingredient, cocktail_name):
        # Update the list of cocktails for an existing pump.
        for pump in self.active_pumps:
            if pump.ingredient == ingredient:
                if cocktail_name not in pump.cocktails:
                    pump.cocktails.append(cocktail_name)

    def cooling_progress_bar(self, total_time, cooling_percentage=100):
        # Show a progress bar to simulate ingredients cooling waiting time.
        self.cooling_event.clear()
        with tqdm(total=total_time, desc="Cooling Ingredients", bar_format="{l_bar}{bar} [time left: {remaining}]") as pbar:
            # Update progress every second based on cooling steps
            while not self.cooling_event.is_set() and pbar.n < total_time:
                time.sleep(total_time / cooling_percentage)  # Control update speed (based on cooling percentage)
                pbar.update(1)  # Move progress bar step by step

    def wait_for_ingredients(self, pumps, optimal_temps):
        # Wait until all ingredients are at their optimal temperature asynchronously.

        # Identify which ingredients actually need cooling
        ingredients_to_cool = [
            (pump, optimal_temp) for pump, optimal_temp in zip(pumps, optimal_temps)
            if pump.temperature_sensor.read_temperature(pump.last_refill_time) > optimal_temp
        ]

        # If no ingredients require cooling, return immediately
        if not ingredients_to_cool:
            self.logger.info("All ingredients are already at optimal temperature.")
            return

        total_cooling_time = 10  # Simulated cooling time in seconds
        cooling_percentage = 20  # Assuming cooling is divided into 5 phases

        # Start the cooling progress bar in a separate thread if it's not already running
        if not self.cooling_thread or not self.cooling_thread.is_alive():
            self.cooling_thread = threading.Thread(
                target=self.cooling_progress_bar, args=(total_cooling_time, cooling_percentage)
            )
            self.cooling_thread.start()

        # Continuously check ingredient temperatures and update progress bar
        while True:
            # Check whether all ingredients have cooled down to optimal temperature
            all_optimal = all(
                pump.temperature_sensor.read_temperature(pump.last_refill_time) <= optimal_temp
                for pump, optimal_temp in ingredients_to_cool
            )

            if all_optimal:
                self.logger.info("All ingredients have reached their optimal temperatures.")
                self.cooling_event.set()  # Stop progress bar
                break  # Exit the loop

            time.sleep(1)  # Avoid high CPU usage

    def make_cocktail(self, order_id):
        # Process the cocktail order based on the order ID.
        # Find the order in the queue using the unique order ID
        self.logger.info("Order queue:" + str(self.orders.order_queue))
        order = next((o for o in self.orders.order_queue if o['id'] == order_id), None)

        if not order:
            self.logger.error(f"Order {order_id} not found in the queue.")
            return  # Order not found, exit

        cocktail_name = order['cocktail_name']
        chat_id = order['chat_id']
        user = f"User-{chat_id}"  # You can modify this based on your user system

        self.logger.info(f"Attempting to make {cocktail_name} for {user}")

        self.status = f"Making cocktail for {user}"
        self.current_task = "Cocktail"

        if len(self.selected_cocktails) > 0:
            for cocktail in self.selected_cocktails:
                if cocktail_name.lower() == cocktail.name.lower():
                    self.logger.info(f"Preparing {cocktail.name}!")

                    ingredients_to_cool = []
                    optimal_temps = []

                    # First pass: Check quantities and temperatures
                    for ingredient, details in cocktail.ingredients.items():
                        for pump in self.active_pumps:
                            if pump.ingredient == ingredient:
                                required_ml = details['quantity']
                                required_qty_percent = ((required_ml / 10) / pump.float_switch.quantity) * 100
                                optimal_temp = details['optimal_temp_C']

                                # Debugging: Print pump details
                                self.logger.info(f"Checking pump {pump.id} ({pump.ingredient})")
                                self.logger.info(f"Required: {required_ml} ml, Available: {pump.float_switch.left_quantity} ml")

                                # Check and refill if needed
                                if pump.float_switch.left_quantity < required_qty_percent:
                                    self.logger.info(f"Refilling {ingredient}...")
                                    pump.refill()

                                # Check temperature
                                current_temp = pump.temperature_sensor.read_temperature(pump.last_refill_time)
                                self.logger.info(f"{ingredient} current temp: {current_temp}, optimal: {optimal_temp}")

                                if current_temp > optimal_temp:
                                    ingredients_to_cool.append(pump)
                                    optimal_temps.append(optimal_temp)

                    # Handle temperature requirements
                    if ingredients_to_cool:
                        self.logger.info(f"Cooling required for {[p.ingredient for p in ingredients_to_cool]}")
                        self.wait_for_ingredients(ingredients_to_cool, optimal_temps)

                    # Second pass: Actual dispensing
                    self.logger.info("Starting dispensing process...\n")
                    for ingredient, details in cocktail.ingredients.items():
                        for pump in self.active_pumps:
                            if pump.ingredient == ingredient:
                                required_ml = details['quantity']
                                optimal_temp = details['optimal_temp_C']
                                required_qty_percent = ((required_ml / 10) / pump.float_switch.quantity) * 100

                                self.logger.info(f"Dispensing {ingredient} - {required_ml} ml")

                                pump.erogate(ingredient, required_ml, optimal_temp, required_qty_percent)

                    # Cocktail complete
                    self.telegram_bot.send_completion(chat_id, cocktail_name)
                    self.logger.info(f"{cocktail_name} complete!")
                    self.status = "Idle"
                    self.current_task = None
                    return

            # If cocktail not found in selected cocktails
            self.telegram_bot.bot.sendMessage(chat_id, f"{cocktail_name} not in menu. Pick another cocktail.")
            self.logger.error(f"{cocktail_name} not found in selected cocktails.")

        else:
            self.telegram_bot.bot.sendMessage(chat_id, f"{cocktail_name} not in menu. Pick another cocktail.")
            self.logger.error(f"Empty cocktail list. Configure Smartender")
