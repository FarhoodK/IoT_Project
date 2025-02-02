import json
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


class SmartenderBot:
    def __init__(self, token, smartender):
        """Initialize the Telegram bot for Smartender."""
        self.token = token
        self.smartender = smartender
        self.bot = None

    def start(self):
        """Initialize and start the bot."""
        try:
            self.bot = telepot.Bot(self.token)

            # Set up message handlers
            MessageLoop(self.bot, {
                'chat': self.handle_message,
                'callback_query': self.handle_callback_query
            }).run_as_thread()

            print("Telegram bot initialized successfully!")
            print("Bot username:", self.bot.getMe()['username'])

        except Exception as e:
            print(f"Error initializing Telegram bot: {e}")
            self.bot = None

    def handle_message(self, msg):
        """Handle incoming Telegram messages."""
        content_type, chat_type, chat_id = telepot.glance(msg)

        # Get the username, if available
        user_username = msg['from'].get('username', 'No Username')

        if content_type == 'text':
            command = msg['text'].lower()

            if command == '/start':
                self.send_welcome_message(chat_id, user_username)
                self.send_cocktail_menu(chat_id, user_username)
                print(f"{user_username} - {command}")
            elif command == '/help':
                self.send_help_message(chat_id, user_username)
                print(f"{user_username} - {command}")
            elif command == '/menu':
                self.send_cocktail_menu(chat_id, user_username)
                print(f"{user_username} - {command}")

    def handle_callback_query(self, msg):
        """Handle callback queries from inline keyboard buttons."""
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        user_name = msg['from']['username']
        # Print the callback query to the terminal
        print(f"Received callback query from {user_name}, chat {chat_id}: {query_data}")

        # Make the selected cocktail
        self.bot.answerCallbackQuery(query_id, text=f"Starting to prepare {query_data}!")
        self.bot.sendMessage(chat_id, f"Preparing your {query_data}... Please wait!")
        try:
            self.smartender.make_cocktail(query_data, user_name)
            self.bot.sendMessage(chat_id, f"✨ Your {query_data} is ready! Enjoy! 🍸")
        except Exception as e:
            self.bot.sendMessage(chat_id, f"Sorry, there was an error preparing your cocktail: {str(e)}")

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

    def send_cocktail_menu(self, chat_id, username):
        """Send the cocktail selection menu with inline buttons, including ingredients."""
        try:
            with open('selected_cocktails.json', 'r') as file:
                data = json.load(file)
                cocktails = data['selected_cocktails']

                # Initialize a message to hold all the cocktail names and ingredients
                message_text = "🍹 Available cocktails:\n\n"
                keyboard = []

                for idx, cocktail in enumerate(cocktails, 1):
                    # Get the cocktail's name and ingredients
                    cocktail_name = cocktail['name']
                    ingredients = cocktail.get('ingredients', [])

                    # Format the ingredients list
                    if ingredients:
                        ingredients_text = ' ▾ '.join(ingredients)
                    else:
                        ingredients_text = 'No ingredients listed.'

                    # Create the clickable button for the cocktail name
                    cocktail_button = InlineKeyboardButton(
                        text=cocktail_name,  # Cocktail name button
                        callback_data=cocktail_name  # Callback for selecting the cocktail
                    )

                    # Add the cocktail name and ingredients to the message
                    message_text += f"🔸 {cocktail_name}:\n{ingredients_text}\n\n"

                    # Add the button for selecting the cocktail (if needed)
                    keyboard.append([cocktail_button])

                # Send the message with all cocktail names and ingredients
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                self.bot.sendMessage(
                    chat_id,
                    message_text,
                    reply_markup=markup
                )

        except Exception as e:
            self.bot.sendMessage(
                chat_id,
                "Sorry, there was an error loading the cocktail menu. Please try again later."
            )
