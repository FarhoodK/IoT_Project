import json
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import os


class SmartenderBot:
    def __init__(self, token, smartender):
        """Initialize the Telegram bot for Smartender."""
        self.token = token
        self.smartender = smartender
        self.bot = None
        self.message_loop_thread = None

    def start(self):
        """Initialize and start the bot."""
        try:
            self.bot = telepot.Bot(self.token)

            # Set up message handlers
            self.message_loop_thread = threading.Thread(target=self.run_message_loop)
            self.message_loop_thread.start()

            print("Telegram bot initialized successfully!")
            print("Bot username:", self.bot.getMe()['username'])

        except Exception as e:
            print(f"Error initializing Telegram bot: {e}")
            self.bot = None

    def run_message_loop(self):
        """Run the message loop in a separate thread."""
        MessageLoop(self.bot, {
            'chat': self.handle_message,
            'callback_query': self.handle_callback_query
        }).run_as_thread()

    def handle_message(self, msg):
        """Handle incoming Telegram messages."""
        content_type, chat_type, chat_id = telepot.glance(msg)

        # Get the username, if available, otherwise use chat_id
        user_username = msg['from'].get('username', None)
        if not user_username:
            user_username = f"User-{chat_id}"  # You can use chat_id to create a fallback name if no username is set

        if content_type == 'text':
            command = msg['text'].lower()

            if command == '/start':
                self.send_welcome_message(chat_id, user_username)
                self.send_cocktail_menu(chat_id)
                print(f"{user_username} ({chat_id}) - {command}")
            elif command == '/help':
                self.send_help_message(chat_id, user_username)
                print(f"{user_username} ({chat_id}) - {command}")
            elif command == '/menu':
                self.send_cocktail_menu(chat_id)
                print(f"{user_username} ({chat_id}) - {command}")

    def handle_callback_query(self, msg):
        """Handle callback queries from inline keyboard buttons."""
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        user_username = msg['from'].get('username', None)
        if not user_username:
            user_username = f"User-{chat_id}"

        # Print the callback query to the terminal
        print(f"Received callback query from {user_username}, chat {chat_id}: {query_data}")

        # Prepare the cocktail
        try:
            # Confirm cocktail order
            if any(query_data.lower() == cocktail.name.lower() for cocktail in self.smartender.selected_cocktails):
                self.bot.answerCallbackQuery(query_id, text=f"Starting to prepare {query_data}!")
                self.bot.sendMessage(chat_id, f"🍸 Preparing your {query_data}... Please wait!")

                # Store chat_id for potential future reference
                cocktail_order = {
                    'cocktail_name': query_data,
                    'user': user_username,
                    'chat_id': chat_id
                }
                # Publish cocktail order to MQTT
                self.smartender.mqtt_client.publish('cocktail_order', cocktail_order)

                # Attempt to make the cocktail
                self.smartender.make_cocktail(query_data, user_username, chat_id)
            else:
                self.bot.sendMessage(chat_id, f"{query_data} not in menu. Pick another cocktail.")
        except Exception as e:
            error_message = f"Sorry, there was an error preparing your cocktail: {str(e)}"
            self.bot.sendMessage(chat_id, error_message)

            # Publish error status
            self.smartender.mqtt_client.publish('cocktail_status', {
                'cocktail_name': query_data,
                'user': user_username,
                'status': 'error',
                'error_message': str(e)
            })

    def send_welcome_message(self, chat_id, username):
        """Send welcome message to new users."""
        welcome_text = (
            f"🍸 Welcome to Smartender, {username}! 🤖\n\n"
            "I'm your personal bartender bot. I can help you prepare "
            "delicious cocktails with precision and style.\n\n"
            "Use /menu to see available cocktails or /help for more commands."
        )
        self.bot.sendMessage(chat_id, welcome_text)

    def send_help_message(self, chat_id, username):
        """Send help message with available commands."""
        help_text = (
            "🤖 Smartender Bot Commands:\n\n"
            "/start - Start the bot and see welcome message\n"
            "/menu - Show available cocktails\n"
            "/help - Show this help message"
        )
        self.bot.sendMessage(chat_id, help_text)

    def send_cocktail_menu(self, chat_id):
        """Send the cocktail selection menu with inline buttons, including ingredients."""
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
        except json.JSONDecodeError:
            self.bot.sendMessage(
                chat_id,
                "⚠️ There was an error reading the menu file. It might be corrupted."
            )
        except ValueError as e:
            self.bot.sendMessage(
                chat_id,
                f"⚠️ {str(e)}"
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.bot.sendMessage(
                chat_id,
                "⚠️ An unexpected error occurred while loading the cocktail menu."
            )

    def stop(self):
        """Gracefully stop the bot and message loop."""
        if self.bot:
            print("Stopping the bot...")
            # Stop the message loop and cleanup any resources
            self.bot.MessageLoop__thread.stop()
            print("Bot stopped gracefully.")
