import time
import json
import telepot
from logger import Logger
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import os


class SmartenderBot:
    def __init__(self, token, smartender):
        # Initialize the Telegram bot for Smartender.
        self.token = token
        self.smartender = smartender
        self.bot = None
        self.message_loop_thread = None
        self.stop_event = threading.Event()
        self._bot_lock = threading.Lock()
        self.logger = Logger("BOT")

    def start(self):
        try:
            with self._bot_lock:
                if self.bot:
                    self.stop()

                self.bot = telepot.Bot(self.token)
                self.stop_event.clear()

            # Start message loop in a separate thread
            self.message_loop_thread = threading.Thread(
                target=self._run_message_loop, 
                daemon=True
            )
            self.message_loop_thread.start()

            self.logger.info("Telegram bot initialized successfully!")
            self.logger.info(f"Bot username: {self.bot.getMe()['username']}")

        except Exception as e:
            self.logger.error(f"Error initializing Telegram bot: {e}")
            self.bot = None
            self.stop_event.set()

    def _run_message_loop(self):
        while not self.stop_event.is_set():
            try:
                # Use a small offset to avoid processing old messages
                offset = 0
                
                # Continuously poll for updates
                while not self.stop_event.is_set():
                    try:
                        # Get updates with a timeout and small polling interval
                        updates = self.bot.getUpdates(
                            offset=offset, 
                            timeout=30,  # Long polling timeout
                            allowed_updates=['message', 'callback_query']
                        )
                        
                        # Process each update
                        for update in updates:
                            # Update offset to avoid reprocessing
                            offset = update['update_id'] + 1
                            
                            # Handle different update types
                            if 'message' in update:
                                self.handle_message(update['message'])
                            elif 'callback_query' in update:
                                self.handle_callback_query(update['callback_query'])
                    
                    except telepot.exception.TelegramError as te:
                        # Handle Telegram-specific errors
                        if 'Conflict' in str(te):
                            self.logger.error("Bot conflict detected. Waiting and retrying...")
                            time.sleep(5)
                        else:
                            self.logger.error(f"Telegram error: {te}")
                            time.sleep(3)
                    
                    except Exception as e:
                        self.logger.error(f"Unexpected error in message loop: {e}")
                        time.sleep(3)
            
            except Exception as e:
                self.logger.error(f"Critical error in bot loop: {e}")
                time.sleep(5)

    def handle_message(self, msg):
        # Handle incoming Telegram messages.
        content_type, chat_type, chat_id = telepot.glance(msg)

        # Get the username, if available, otherwise use chat_id
        user_username = msg['from'].get('username', None)
        if not user_username:
            user_username = f"User-{chat_id}"  # Fallback name

        if content_type == 'text':
            command = msg['text'].lower()
            if command == '/start':
                self.send_welcome_message(chat_id, user_username)
                self.send_cocktail_menu(chat_id)
                self.logger.info(f"{user_username} ({chat_id}) - {command}")
            elif command == '/help':
                self.send_help_message(chat_id, user_username)
                self.logger.info(f"{user_username} ({chat_id}) - {command}")
            elif command == '/menu':
                self.send_cocktail_menu(chat_id)
                self.logger.info(f"{user_username} ({chat_id}) - {command}")

    def handle_callback_query(self, msg):
            # Handle inline keyboard selections for cocktails.
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        user_username = msg['from'].get('username', None) or f"User-{chat_id}"

        self.logger.info(f"Received order from {user_username}: {query_data}")
        try:
            # Notify the user that their order is in the queue
            self.bot.sendMessage(chat_id, f"🔄 Your cocktail has been added to the queue! Please wait...")
            # Add order to Orders instead of calling make_cocktail() immediately
            self.smartender.orders.add_order(query_data, user_username, chat_id)
                       
        except Exception as e:
            error_message = f"Sorry, there was an error processing your cocktail."
            self.logger.error(f"Error processing cocktail order: {e}")
            self.bot.sendMessage(chat_id, error_message)

    def send_welcome_message(self, chat_id, username):
        # Send welcome message to new users.
        welcome_text = (
            f"🍸 Welcome to Smartender, {username}! 🤖\n\n"
            "I'm your personal bartender bot. I can help you prepare "
            "delicious cocktails with precision and style.\n\n"
            "Use /menu to see available cocktails or /help for more commands."
        )
        self.bot.sendMessage(chat_id, welcome_text)

    def send_help_message(self, chat_id, username):
        # Send help message with available commands.
        help_text = (
            "🤖 Smartender Bot Commands:\n\n"
            "/start - Start the bot and see welcome message\n"
            "/menu - Show available cocktails\n"
            "/help - Show this help message"
        )
        self.bot.sendMessage(chat_id, help_text)

    def send_cocktail_menu(self, chat_id):
        # Send the cocktail selection menu with inline buttons, including ingredients.
        try:
            # Check if the file exists before attempting to open
            if not os.path.exists('selected_cocktails.json'):
                raise FileNotFoundError("Cocktail menu file not found.")

            with open('selected_cocktails.json', 'r') as file:
                data = json.load(file)

            cocktails = data.get('selected_cocktails', [])

            # Handle case where no cocktails are available
            if not cocktails:
                raise ValueError("No cocktails available in the menu.")

            # Initialize a message to hold all the cocktail names and ingredients
            message_text = "🍹 Available cocktails:\n\n"
            keyboard = []

            for idx, cocktail in enumerate(cocktails, 1):
                cocktail_name = cocktail.get('name', 'Unknown Cocktail')
                ingredients = cocktail.get('ingredients', [])

                # Format the ingredients list
                ingredients_text = ' ▾ '.join(ingredients) if ingredients else 'No ingredients listed.'

                # Create a button for the cocktail
                cocktail_button = InlineKeyboardButton(
                    text=cocktail_name,
                    callback_data=cocktail_name
                )

                # Append cocktail details to the message
                message_text += f"🔸 {cocktail_name}:\n{ingredients_text}\n\n"

                # Add the button to the keyboard
                keyboard.append([cocktail_button])

            # Send the message with all cocktail names and ingredients
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            self.bot.sendMessage(chat_id, message_text, reply_markup=markup)

        except FileNotFoundError:
            self.bot.sendMessage(
                chat_id,
                "❌ The cocktail menu is not available. Please add some cocktails first!"
            )
            self.logger.error("Cocktail menu file not found.")
        except json.JSONDecodeError:
            self.bot.sendMessage(
                chat_id,
                "⚠️ There was an error reading the menu file. It might be corrupted."
            )
            self.logger.error("Error reading the cocktail menu file: JSON decode error.")
        except ValueError as e:
            self.bot.sendMessage(
                chat_id,
                f"⚠️ {str(e)}"
            )
            self.logger.error(f"ValueError: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.bot.sendMessage(
                chat_id,
                "⚠️ An unexpected error occurred while loading the cocktail menu."
            )

    def send_queue_position(self, chat_id, position):
        if position > 3:
            self.bot.sendMessage(chat_id, f"➡️ Your order is #{position} in the queue.")
        elif position > 1 and position <= 3:
            self.bot.sendMessage(chat_id, f"➡️ Your order is #{position} in the queue! Get ready to collect it")
        elif position == 1:
            self.bot.sendMessage(chat_id, f"➡️ Your order is next in line!")
                             
    def send_order_confirmation(self, chat_id, cocktail_name):
        self.bot.sendMessage(chat_id, f"🍹 Your {cocktail_name} is being prepared. Please wait a moment...")

    def send_completion(self, chat_id, cocktail_name):
        self.bot.sendMessage(chat_id, f"✅ Your {cocktail_name} is ready! Enjoy! 🎉")

    def stop(self):
        # Stop the bot and the message loop thread gracefully
        try:
            self.stop_event.set()  # Signal the message loop to stop
            if self.message_loop_thread:
                self.message_loop_thread.join(timeout=10)  # Wait for the message loop thread to stop
            if self.bot:
                self.bot = None
            self.logger.info("Telegram bot stopped successfully.")
        except Exception as e:
            self.logger.error(f"Error stopping Telegram bot: {e}")