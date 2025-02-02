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


class Smartender:
    """Main class to handle the Smartender operations."""

    def __init__(self, filename1):
        """
        Initialize Smartender with a JSON file containing cocktail data.
        """
        self.filename1 = filename1
        self.available_cocktails = []
        self.selected_cocktails = []
        self.selected_ingredients = []
        self.active_pumps = []
        self.cooling_thread = None
        self.cooling_event = threading.Event()
        self.telegram_bot = None
        self.data = {"selected_cocktails": []}
        self.status = "Idle"
        self.current_task = None

        # Initialize MQTT client
        self.mqtt_client = MqttClient(
            broker="mqtt.eclipseprojects.io",
            topic="smartender/status"
        )
        self.mqtt_client.connect()

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
        print("Welcome to your SmarTender!\n")
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
                print(f"{cocktail.name} added to your Smartender\n")

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

    def cooling_progress_bar(self, total_time):
        """Show a progress bar to simulate ingredients cooling waiting time."""
        self.cooling_event.clear()
        with tqdm(total=total_time, desc="Cooling Ingredients",
                  bar_format="{l_bar}{bar} [time left: {remaining}]") as pbar:
            while not self.cooling_event.is_set() and pbar.n < total_time:
                time.sleep(1)
                pbar.update(1)

    def wait_for_ingredients(self, pumps, optimal_temps):
        """Wait until all ingredients are at their optimal temperature."""
        total_cooling_time = 10 * 60  # 10 minutes cooling time
        while True:
            all_optimal = all(
                pump.temperature_sensor.read_temperature(pump.last_refill_time) <= optimal_temp
                for pump, optimal_temp in zip(pumps, optimal_temps)
            )

            if all_optimal:
                print("All ingredients have reached their optimal temperatures.")
                return

            print("Some ingredients are still above optimal temperatures. Please wait or choose another cocktail.")
            if not self.cooling_thread or not self.cooling_thread.is_alive():
                self.cooling_thread = threading.Thread(
                    target=self.cooling_progress_bar,
                    args=(total_cooling_time,)
                )
                self.cooling_thread.start()

            user_input = self.get_user_input("Press 'b' to choose another cocktail: ")
            if user_input.lower() == 'b':
                self.cooling_event.set()
                self.cooling_thread.join()
                return

    def make_cocktail(self, cocktail_name=None, user="UNKNOWN"):
        """Prepare the selected cocktail."""
        self.status = f"Making cocktail for {user}"
        self.current_task = "Cocktail"
        for cocktail in self.selected_cocktails:
            if cocktail_name.lower() == cocktail.name.lower():
                print(f"\nPreparing {cocktail.name}!\n")
                ingredients_to_cool = []
                optimal_temps = []

                # First pass: Check quantities and temperatures
                for ingredient, details in cocktail.ingredients.items():
                    for pump in self.active_pumps:
                        if pump.ingredient == ingredient:
                            required_ml = details['quantity']
                            required_qty_percent = ((required_ml / 10) / pump.float_switch.quantity) * 100
                            optimal_temp = details['optimal_temp_C']

                            # Check and refill if needed
                            if pump.float_switch.left_quantity < required_qty_percent:
                                print(f"Refilling {ingredient}...")
                                pump.refill()

                            # Check temperature
                            current_temp = pump.temperature_sensor.read_temperature(pump.last_refill_time)
                            if current_temp > optimal_temp:
                                ingredients_to_cool.append(pump)
                                optimal_temps.append(optimal_temp)

                # Handle temperature requirements
                if ingredients_to_cool:
                    self.wait_for_ingredients(ingredients_to_cool, optimal_temps)
                    return

                # Second pass: Actual dispensing
                for ingredient, details in cocktail.ingredients.items():
                    for pump in self.active_pumps:
                        if pump.ingredient == ingredient:
                            required_ml = details['quantity']
                            optimal_temp = details['optimal_temp_C']
                            required_qty_percent = ((required_ml / 10) / pump.float_switch.quantity) * 100
                            pump.erogate(ingredient, required_ml, optimal_temp, required_qty_percent)

                print("Your cocktail is ready. Enjoy!\n")
                self.status = "Idle"
                self.current_task = None
                return
