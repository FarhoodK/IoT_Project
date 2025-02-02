import os
import threading
from smartender import Smartender
from smartender_bot import SmartenderBot


def run_streamlit():
    os.system("streamlit run app.py")


if __name__ == "__main__":
    smartender = Smartender('cocktails.json')
    smartender_bot = SmartenderBot("6401650950:AAEZq16vHRDu9sQyFYKUqfhWFH1LZtDKHZA", smartender)
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()
    smartender_bot.start()
    streamlit_thread.join()
    smartender.show_cocktails(smartender.available_cocktails)
    smartender.configure()
