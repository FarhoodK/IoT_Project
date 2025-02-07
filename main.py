from logger import Logger
import threading
import subprocess
from smartender_API import SmartenderAPI
from smartender_core import Smartender

logger = Logger("MAIN")

def start_api_server(smartender):
    # Start the CherryPy API server.
    try:
        logger.info("Starting the Smartender API server...")
        SmartenderAPI.run_server(smartender)
    except Exception as e:
        logger.error(f"API server startup failed: {e}", exc_info=True)

def start_streamlit_app():
    # Start the Streamlit app.
    try:
        logger.info("Starting the Streamlit app...")
        subprocess.Popen(["streamlit", "run", "streamlit.py"])
    except Exception as e:
        logger.error(f"Failed to start Streamlit app: {e}")

def main():
    # Main entry point to start the system.
    try:
        try:
            logger.info("Initializing the Smartender system...")
            # Initialize Smartender instance
            cocktails_path = "cocktails.json"
            bot_token = "6401650950:AAFFt3FyX0mWb4RURHIMTed2Mkv5d3uMK1g"
            mqtt_broker, mqtt_port, mqtt_topic = ("mqtt.eclipseprojects.io", 1883, "smartender")
            smartender = Smartender(cocktails_path, bot_token, mqtt_broker, mqtt_port, mqtt_topic)
        
            # Start the Smartender system
            smartender.load_cocktails()
            smartender.start_telegram_bot()
    
        except Exception as e:
            logger.error(f"Failed to start Smartender system: {e}")

        try:
            # Start the API server and pass the existing Smartender instance
            threading.Thread(target=start_api_server, args=(smartender,), daemon=True).start()

            # Start the Streamlit app
            threading.Thread(target=start_streamlit_app, daemon=True).start()

            logger.info("Smartender system, API server, and Streamlit app are running...")

            # Keep the main thread running to allow the server and background services to run
            while True:
                pass
        except:
            logger.error("Error starting the API server and Streamlit app", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Shutting down Smartender system...")
        smartender.telegram_bot.stop()

if __name__ == '__main__':
    main()
