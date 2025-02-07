import json
import paho.mqtt.client as mqtt
import streamlit as st
import requests
import pandas as pd
from logger import Logger

class SmartenderUI:
    def __init__(self, api_base_url="http://localhost:8080", mqtt_broker="mqtt.eclipseprojects.io", mqtt_port=1883):
        self.api_base_url = api_base_url
        self.setup_page()
        self.initialize_session_state()
        self.logger = Logger("STREAMLIT")

        # MQTT client for subscribing to Smartender status updates.
        self.mqtt_client = mqtt.Client(client_id="SmartenderUI", protocol=mqtt.MQTTv311, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_port = mqtt_port
        self.mqtt_broker = mqtt_broker
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_subscribe = self.on_subscribe

    def setup_page(self):
        st.set_page_config(page_title="Smartender", page_icon="🍹")
        
    def initialize_session_state(self):
        # Initialize session state components if they don't exist
        if "selected_cocktails" not in st.session_state:
            st.session_state.selected_cocktails = []
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "status" not in st.session_state:
            st.session_state.status = "Idle"
        if "pump_status" not in st.session_state:
            st.session_state.pump_status = {}

    def start_mqtt_client(self):
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)
            self.mqtt_client.loop_start()
        except Exception as e:
            st.error(f"Error connecting to MQTT broker: {e}")
            self.logger.error(f"Error connecting to MQTT broker: {e}")

    def on_connect(self, client, userdata, flags, rc):
        # Called when the client connects to the broker.
        client.subscribe("smartender/#")  # Subscribe to topics you want to listen to
        self.logger.info("Connected to MQTT Broker")

    def on_message(self, client, userdata, message):
        # Called when a new message is received.
        try:
            payload = json.loads(message.payload.decode())  # Decode the incoming message payload
        
            # Process different topics based on their names
            if message.topic == "smartender/pump_status":
                self.update_pump_status(payload)
                self.logger.info(f"Received pump status: {payload}")
            elif message.topic == "smartender/status":
                self.update_status(payload)
                self.logger.info(f"Received status update: {payload}")

        except json.JSONDecodeError as e:
            st.error(f"Error decoding MQTT message on topic {message.topic}: {e}")
        except Exception as e:
            self.logger.error(f"Error handling MQTT message on topic {message.topic}: {e}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        # Optional: handle subscription confirmation
        self.logger.info(f"Subscribed to topic with QoS {granted_qos} and message ID {mid}")

    def update_pump_status(self, status_data):
        pump_id = status_data['Pump_Number']
        if pump_id is not None:
            st.session_state.pump_status[pump_id] = status_data
        
    def update_status(self, status_data):
        st.session_state.status = status_data['status']
    
    def fetch_available_cocktails(self):
        try:
            response = requests.get(f"{self.api_base_url}/cocktails")
            return response.json()
        except Exception as e:
            st.error(f"Error fetching cocktails: {e}")
            return []

    def render_home_page(self):
        st.title("Welcome to Smartender!🍹")
        st.write("""
            Smartender is a fully automated cocktail-making system that helps you mix your favorite drinks with ease. 
            Simply select the cocktails you want to prepare, and Smartender will take care of the rest. 
            It's an efficient and fun way to enjoy perfect cocktails every time!
        """)

        st.image("cheers.jpg", use_container_width=True, caption="Cheers!")
        st.write("### How it works:")
        st.write("1. **Configure Your Smartender**: Select your favorite cocktails and configure the pumps (Admin required).")
        st.write("2. **Pump Status**: Check the status of the pumps to ensure everything is ready (Admin required).")
        st.write("3. **Make Cocktail**: Choose a cocktail and let Smartender prepare it for you.")

    def render_configure_page(self):
        st.subheader("Configure your Smartender")

        if not st.session_state.get('authenticated', False):
            # Login Form
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit_button = st.form_submit_button("Login")

                if submit_button:
                    if username == "admin" and password == "password":
                        st.session_state.authenticated = True
                        st.rerun()
                        self.logger.info("Admin logged in successfully")
                    else:
                        st.error("Invalid credentials")
        else:
            st.success("Logged in as admin")
            if st.button("Logout"):
                st.session_state.authenticated = False

            # Admin Tabs
            tab_configure, tab_pumps = st.tabs(["Configure Your Smartender", "Status"])

            with tab_configure:
                st.subheader("Configure Your Smartender")
                cocktails = self.fetch_available_cocktails()
                
                # Cocktail configuration grid
                cols = st.columns(3)
                for idx, cocktail in enumerate(cocktails):
                    col = cols[idx % 3]
                    with col:
                        with st.expander(cocktail['name']):
                            st.write("### Ingredients:")
                            ingredients_text = "\n".join([
                                f"- {ing}: {details['quantity']}ml at {details.get('optimal_temp_C', 'N/A')}°C" 
                                for ing, details in cocktail['ingredients'].items()
                            ])
                            st.text(ingredients_text)

                # Multiselect for cocktails
                selected_cocktails = st.multiselect(
                    "Select cocktails",
                    [c['name'] for c in cocktails],
                    default=st.session_state.selected_cocktails,
                )

                if st.button("Save Configuration"):
                    st.session_state.selected_cocktails = selected_cocktails
                    # Send selected cocktails to backend
                    try:
                        response = requests.post(
                            f"{self.api_base_url}/configure_cocktails", 
                            json={"cocktails": selected_cocktails}
                        )
                        if response.status_code == 200:
                            st.success("Pumps configured successfully!")
                        else:
                            st.error("Failed to configure pumps")
                    except Exception as e:
                        st.error(f"Error configuring pumps: {e}")

            with tab_pumps:
                st.subheader("Smartender Status")
                st.write(f"Current Status: {st.session_state.status}")
                st.subheader("Pumps Status")
                if not st.session_state.pump_status:
                    st.warning("No pumps configured or no data received yet.")
                else:
                    for pump_id, pump_data in st.session_state.pump_status.items():
                        with st.expander(f"Pump {pump_id} - {pump_data.get('Ingredient', 'Unknown')}", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Current Temperature", f"{pump_data.get('Current_Temperature', 'N/A')}°C")
                            with col2:
                                st.metric("Remaining Quantity", f"{pump_data.get('Remaining_Quantity', 'N/A')}%")

                            st.caption(f"Maintenance Status: {pump_data.get('Maintenance', 'Unknown')}")
                            st.caption(f"Configured Cocktails: {', '.join(pump_data.get('Cocktails', []))}")

                            tab1, tab2 = st.tabs(["Temperature History", "Quantity History"])

                            with tab1:
                                if 'Temperature_History' in pump_data and len(pump_data['Temperature_History']) > 1:
                                    temp_df = pd.DataFrame(pump_data['Temperature_History'])
                                    temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
                                    temp_df.set_index('timestamp', inplace=True)
                                    st.line_chart(temp_df, y='temperature')
                                else:
                                    st.info("Collecting temperature data...")

                            with tab2:
                                if 'Quantity_History' in pump_data and len(pump_data['Quantity_History']) > 1:
                                    qty_df = pd.DataFrame(pump_data['Quantity_History'])
                                    qty_df['timestamp'] = pd.to_datetime(qty_df['timestamp'])
                                    qty_df.set_index('timestamp', inplace=True)
                                    st.line_chart(qty_df, y='quantity')
                                else:
                                    st.info("Collecting quantity data...")

    def render_ui(self):
        # Sidebar menu
        menu = st.sidebar.selectbox("Menu", [
            "Home",
            "Configure"
        ])

        # Render appropriate page based on menu selection
        if menu == "Home":
            self.render_home_page()
        elif menu == "Configure":
            self.render_configure_page()

if __name__ == "__main__":
    ui = SmartenderUI() # Initialize UI
    ui.render_ui()      # Render the UI