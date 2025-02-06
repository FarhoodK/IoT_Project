import threading
import time
from collections import deque
from logger import Logger

class Orders:
    def __init__(self, smartender):
        # Order manager that handles queued drink requests using deque.
        self.smartender = smartender
        self.logger = Logger("ORDERS")
        self.order_queue = deque()
        self.lock = threading.Lock()
        self.processing = False

        # Start the background thread for processing orders
        self.queue_thread = threading.Thread(target=self._process_orders, daemon=True)
        self.queue_thread.start()

    def add_order(self, cocktail_name, user, chat_id):
        # Add a new order to the queue in a thread-safe way.
        with self.lock:
            order_id = str(time.time()) + "_" + str(chat_id)  # Unique order ID
            order = {
                "id": order_id,
                "cocktail_name": cocktail_name,
                "chat_id": chat_id
                }
            self.order_queue.append(order)
            position_in_queue = len(self.order_queue)
            self.smartender.telegram_bot.send_queue_position(chat_id, position_in_queue)
        self.logger.info(f"{order_id} Order added: {cocktail_name} for {user}")

    def _process_orders(self):
        # Background worker thread to process orders one by one.
        while True:
            with self.lock:
                if self.order_queue and not self.processing:
                    self.processing = True
                    order_id = self.order_queue[0]["id"]  # FIFO order
                    cocktail_name = self.order_queue[0]["cocktail_name"]
                    chat_id = self.order_queue[0]["chat_id"]
                    self.smartender.telegram_bot.send_order_confirmation(chat_id, cocktail_name)
                    
            if self.processing and self.smartender.status == "Idle":
                self.logger.info(f"Processing order: {order_id}")

                # Call Smartender to prepare the drink
                try:
                    self.smartender.make_cocktail(order_id)
                except Exception as e:
                    self.logger.error(f"❌ Error preparing {cocktail_name} for {chat_id}: {e}")
                self.order_queue.popleft()  # Remove the processed order
                self.processing = False  # Ready for next order

            time.sleep(1)  # Prevent CPU overuse
