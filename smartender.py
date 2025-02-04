import json
import threading
import time
from pump import Pump
from cocktail import Cocktail
from floatswitch import FloatSwitch
from temperaturesensor import TemperatureSensor
from publisher import MqttClient
from datetime import datetime
from tqdm import tqdm
from smartender_bot import SmartenderBot


class Smartender:
    """Main class to handle the Smartender operations."""

    def __init__(self, filename, bot_token):
        """
        Initialize Smartender with a JSON file containing cocktail data.
        """
        self.filename1 = filename
        self.available_cocktails = []
        self.selected_cocktails = []
        self.selected_ingredients = []
        self.active_pumps = []
        self.cooling_thread = None
        self.cooling_event = threading.Event()
        self.data = {"selected_cocktails": []}
        self.status = "Idle"
        self.current_task = None
        self.bot_token = bot_token

        # Initialize MQTT client
        self.mqtt_client = MqttClient(
            broker="mqtt.eclipseprojects.io",
            topic="smartender/"
        )
        self.mqtt_client.connect()

        # Initialize Telegram Bot
        self.telegram_bot = SmartenderBot(self.bot_token, self)
        self.telegram_bot.start()
        self.load_cocktails()

    def load_cocktails(self):
        """Load cocktails from a JSON file."""
        try:
            with open(self.filename1, 'r') as file:
                data = json.load(file)
                for name, details in data.items():
                    self.available_cocktails.append(
                        Cocktail(name, details['ingredients'], details['steps'])
                    )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading cocktails: {e}")

    def save_selected_cocktails(self, cocktail_name):
        """Save selected cocktails."""
        for cocktail in self.available_cocktails:
            if cocktail.name == cocktail_name:
                self.data["selected_cocktails"].append(cocktail.to_dict())
                print(self.selected_cocktails)
                break

    def selected_to_json(self):
        """Write selected cocktails to JSON for the Telegram Bot to read."""
        print(self.data)
        with open('selected_cocktails.json', 'w') as file:
            json.dump(self.data, file, indent=4)

    def display_pump_status(self):
        """Display status of all active pumps."""
        for pump in self.active_pumps:
            pump.display_status()

    def show_cocktails(self, cocktails):
        """Display list of available cocktails."""
        print("\nAvailable Cocktails:\n")
        for cocktail in cocktails:
            cocktail.show()

    def get_user_input(self, prompt, quit_option='q'):
        """Get user input and handle quitting."""
        user_input = input(prompt).strip()
        if user_input.lower() == quit_option:
            return None
        return user_input

    def configure(self):
        """Handles Smartender configuration."""
        print("Welcome to your Smartender!\n")
        while len(self.selected_ingredients) < 20:
            user_input = self.get_user_input(
                "What cocktails do you want to make? Choose one or more from the available options: q to quit\t")
            if user_input is None:
                break
            self.add_cocktail(user_input)

        self.setup_pumps()

    def add_cocktail(self, user_input):
        """Add a selected cocktail to the Smartender menu."""
        for cocktail in self.available_cocktails:
            if user_input.lower() == cocktail.name.lower():
                self.selected_cocktails.append(cocktail)
                for ingredient in cocktail.ingredients:
                    if ingredient not in self.selected_ingredients:
                        self.selected_ingredients.append(ingredient)
                print(f"{cocktail.name} added to Smartender\n")

    def setup_pumps(self):
        """Set up pumps for selected ingredients and cocktails."""
        pump_id = 0
        for cocktail in self.selected_cocktails:
            for ingredient, details in cocktail.ingredients.items():
                if not self.pump_exists(ingredient):
                    new_pump = Pump(
                        id=pump_id,
                        ingredient=ingredient,
                        temperature=details['temperature'],
                        maintenance=None,
                        cocktails=[cocktail.name],
                        temperature_sensor=TemperatureSensor(),
                        float_switch=FloatSwitch(),
                        last_refill_time=datetime.now(),
                        mqtt_client=self.mqtt_client
                    )
                    self.active_pumps.append(new_pump)
                    pump_id += 1
                else:
                    self.update_pump_cocktails(ingredient, cocktail.name)
        print("Pumps successfully configured!\n")

    def pump_exists(self, ingredient):
        """Check if a pump for the ingredient already exists."""
        return any(pump.ingredient == ingredient for pump in self.active_pumps)

    def update_pump_cocktails(self, ingredient, cocktail_name):
        """Update the list of cocktails for an existing pump."""
        for pump in self.active_pumps:
            if pump.ingredient == ingredient:
                if cocktail_name not in pump.cocktails:
                    pump.cocktails.append(cocktail_name)

    def cooling_progress_bar(self, total_time, cooling_percentage=100):
        """Show a progress bar to simulate ingredients cooling waiting time."""
        self.cooling_event.clear()
        with tqdm(total=total_time, desc="Cooling Ingredients", bar_format="{l_bar}{bar} [time left: {remaining}]") as pbar:
            # Update progress every second based on cooling steps
            while not self.cooling_event.is_set() and pbar.n < total_time:
                time.sleep(total_time / cooling_percentage)  # Control update speed (based on cooling percentage)
                pbar.update(1)  # Move progress bar step by step

    def wait_for_ingredients(self, pumps, optimal_temps):
        """Wait until all ingredients are at their optimal temperature asynchronously."""

        # Identify which ingredients actually need cooling
        ingredients_to_cool = [
            (pump, optimal_temp) for pump, optimal_temp in zip(pumps, optimal_temps)
            if pump.temperature_sensor.read_temperature(pump.last_refill_time) > optimal_temp
        ]

        # If no ingredients require cooling, return immediately
        if not ingredients_to_cool:
            print("All ingredients are already at optimal temperature.")
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
                print("All ingredients have reached their optimal temperatures.")
                self.cooling_event.set()  # Stop progress bar
                break  # Exit the loop

            time.sleep(1)  # Avoid high CPU usage

    def make_cocktail(self, cocktail_name=None, user="UNKNOWN", chat_id=None):
        """Prepare the selected cocktail with MQTT status updates."""

        print(f"\nDEBUG: Attempting to make {cocktail_name} for {user}")
        print(f"DEBUG: Selected Cocktails: {[c.name for c in self.selected_cocktails]}")

        # Publish cocktail order start
        self.mqtt_client.publish('cocktail_order', {
            'cocktail_name': cocktail_name,
            'user': user,
            'status': 'started'
        })

        self.status = f"Making cocktail for {user}"
        self.current_task = "Cocktail"

        if len(self.selected_cocktails) > 0:
            for cocktail in self.selected_cocktails:
                if cocktail_name.lower() == cocktail.name.lower():
                    print(f"\nPreparing {cocktail.name}!\n")

                    # Publish initial status
                    self.mqtt_client.publish('cocktail_status', {
                        'cocktail_name': cocktail_name,
                        'user': user,
                        'status': 'preparing',
                    })

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
                                print(f"DEBUG: Checking pump {pump.id} ({pump.ingredient})")
                                print(f"DEBUG: Required: {required_ml} ml, Available: {pump.float_switch.left_quantity} ml")

                                # Publish pump status
                                self.mqtt_client.publish('pump_status', {
                                    'pump_id': pump.id,
                                    'ingredient': pump.ingredient,
                                    'temperature': pump.temperature_sensor.read_temperature(pump.last_refill_time),
                                    'remaining_quantity': pump.float_switch.left_quantity
                                })

                                # Check and refill if needed
                                if pump.float_switch.left_quantity < required_qty_percent:
                                    print(f"Refilling {ingredient}...")
                                    pump.refill()

                                    # Publish refill status
                                    self.mqtt_client.publish('cocktail_status', {
                                        'cocktail_name': cocktail_name,
                                        'user': user,
                                        'status': 'refilling',
                                        'ingredient': ingredient,
                                    })

                                # Check temperature
                                current_temp = pump.temperature_sensor.read_temperature(pump.last_refill_time)
                                print(f"DEBUG: {ingredient} current temp: {current_temp}, optimal: {optimal_temp}")

                                if current_temp > optimal_temp:
                                    ingredients_to_cool.append(pump)
                                    optimal_temps.append(optimal_temp)

                    # Handle temperature requirements
                    if ingredients_to_cool:
                        print(f"DEBUG: Cooling required for {[p.ingredient for p in ingredients_to_cool]}")
                        self.mqtt_client.publish('cocktail_status', {
                            'cocktail_name': cocktail_name,
                            'user': user,
                            'status': 'cooling',
                        })
                        self.wait_for_ingredients(ingredients_to_cool, optimal_temps)

                # Second pass: Actual dispensing
                    print("\nDEBUG: Starting dispensing process...\n")
                    for ingredient, details in cocktail.ingredients.items():
                        for pump in self.active_pumps:
                            if pump.ingredient == ingredient:
                                required_ml = details['quantity']
                                optimal_temp = details['optimal_temp_C']
                                required_qty_percent = ((required_ml / 10) / pump.float_switch.quantity) * 100

                                print(f"DEBUG: Dispensing {ingredient} - {required_ml} ml")

                                # Publish dispensing status
                                self.mqtt_client.publish('cocktail_status', {
                                    'cocktail_name': cocktail_name,
                                    'user': user,
                                    'status': f'dispensing {ingredient}',
                                })

                                pump.erogate(ingredient, required_ml, optimal_temp, required_qty_percent)

                    # Cocktail complete
                    self.mqtt_client.publish('cocktail_status', {
                        'cocktail_name': cocktail_name,
                        'user': user,
                        'status': 'completed'
                    })

                    self.telegram_bot.bot.sendMessage(chat_id, f"🍸 Your {cocktail_name} is ready. Enjoy!")
                    self.status = "Idle"
                    self.current_task = None
                    return

            self.telegram_bot.bot.sendMessage(chat_id, f"{cocktail_name} not in menu. Pick another cocktail.")
            print(f"ERROR: {cocktail_name} not found in selected cocktails.")

        else:
            self.telegram_bot.bot.sendMessage(chat_id, f"{cocktail_name} not in menu. Pick another cocktail.")
            print(f"ERROR: Empty cocktail list. Configure Smartender")
