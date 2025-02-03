import streamlit as st
import pandas as pd
from smartender import Smartender
from smartender_bot import SmartenderBot
from publisher import MqttClient
import time

# Initialize session state components
if "smartender" not in st.session_state:
    st.session_state.smartender = Smartender("cocktails.json")
if "selected_cocktails" not in st.session_state:
    st.session_state.selected_cocktails = []
if "mqtt_messages" not in st.session_state:
    st.session_state.mqtt_messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Initialize MQTT Subscriber
if "mqtt_subscriber" not in st.session_state:
    st.session_state.mqtt_subscriber = MqttClient(
        broker="mqtt.eclipseprojects.io",
        topic="smartender/"
    )
    st.session_state.mqtt_subscriber.connect()

# Create placeholders for dynamic content
cocktail_status_placeholder = st.empty()
pump_status_placeholder = st.empty()

# Initialize SmartenderBot if not initialized already
if "smartender_bot" not in st.session_state:
    st.session_state.smartender_bot = SmartenderBot(
        "6401650950:AAEZq16vHRDu9sQyFYKUqfhWFH1LZtDKHZA", st.session_state.smartender
    )

# Start the bot only once using a session state flag
if "bot_started" not in st.session_state or not st.session_state.bot_started:
    st.session_state.smartender_bot.start()
    st.session_state.bot_started = True

smartender = st.session_state.smartender
smartender_bot = st.session_state.smartender_bot

# Sidebar menu
menu = st.sidebar.selectbox("Menu", [
    "Home",
    "Status",
    "Configure"
])

# Home Page
if menu == "Home":
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

# Status Page
elif menu == "Status":
    st.subheader("Smartender Status")

    # Create placeholders for dynamic content
    cocktail_status_placeholder = st.empty()

    # Process MQTT messages and update status if relevant
    new_messages = st.session_state.mqtt_subscriber.get_messages()
    if new_messages:
        for msg in new_messages:
            msg_type = msg.get('type', '')
            if msg_type in ["cocktail_order", "cocktail_status"]:
                st.session_state.current_user = msg.get('user', 'unknown')
                st.session_state.current_cocktail = msg.get('cocktail_name', 'Unknown beverage')
                st.session_state.cocktail_status = msg.get('status', 'Processing...')
            st.session_state.mqtt_messages.append(msg)

        # Keep only the last 50 messages
        st.session_state.mqtt_messages = st.session_state.mqtt_messages[-50:]

        # Trigger a page rerun to refresh content
        st.rerun()

    # Dynamically update the cocktail status section
    if "current_cocktail" in st.session_state and st.session_state.current_cocktail:
        with cocktail_status_placeholder:
            st.markdown(f"Request by **{st.session_state.current_user}**")
            st.markdown(f"🍹 **Preparing:** {st.session_state.current_cocktail}")
            st.markdown(f"⏳ **Status:** {st.session_state.cocktail_status}")

        if st.session_state.cocktail_status.lower() == "done":
            cocktail_status_placeholder.success(f"✅ {st.session_state.current_cocktail} is ready!")
        elif st.session_state.cocktail_status.lower() == "error":
            cocktail_status_placeholder.error(f"⚠️ Error preparing {st.session_state.current_cocktail}. Check the system.")
    else:
        cocktail_status_placeholder.write("Smartender is idle. Ready to make a cocktail.")


# Configure Page
elif menu == "Configure":
    st.subheader("Configure your Smartender")

    if not st.session_state.get('authenticated', False):
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")

            if submit_button:
                if username == "admin" and password == "password":
                    st.session_state.authenticated = True
                    st.rerun()  # Immediately rerun to update the page
                else:
                    st.error("Invalid credentials")
    else:
        st.success("Logged in as admin")
        if st.button("Logout"):
            st.session_state.authenticated = False

        # Admin Tabs
        tab_configure, tab_status = st.tabs(["Configure Your Smartender", "Pump Status"])

        with tab_configure:
            st.subheader("Configure Your Smartender")
            cols = st.columns(3)
            for idx, cocktail in enumerate(smartender.available_cocktails):
                col_idx = idx % 3
                with cols[col_idx]:
                    with st.expander(cocktail.name):
                        st.write("### Ingredients:")
                        for ingredient, details in cocktail.ingredients.items():
                            st.write(f"- {ingredient}: {details['quantity']}ml at {details['optimal_temp_C']}°C")
            selected_cocktails = st.multiselect(
                "Select cocktails",
                [c.name for c in smartender.available_cocktails],
                default=st.session_state.selected_cocktails,
            )
            if st.button("Save Configuration"):
                st.session_state.selected_cocktails = selected_cocktails
                for cocktail_name in selected_cocktails:
                    smartender.add_cocktail(cocktail_name)
                    smartender.save_selected_cocktails(cocktail_name)
                smartender.selected_to_json()
                smartender.setup_pumps()
                st.success("Pumps configured successfully!")

        with tab_status:
            st.subheader("System Status")

            tab_pumps, tab_messages = st.tabs(["Pump Monitoring", "System Messages"])

            with tab_pumps:
                pump_data = {}
                for msg in st.session_state.mqtt_messages:
                    if 'Pump_Number' in msg:
                        pump_id = msg['Pump_Number']
                        if pump_id not in pump_data:
                            pump_data[pump_id] = {
                                'timestamps': [],
                                'temperatures': [],
                                'quantities': []
                            }
                        if 'Current_Temperature' in msg:
                            pump_data[pump_id]['timestamps'].append(msg.get('timestamp', ''))
                            pump_data[pump_id]['temperatures'].append(msg['Current_Temperature'])
                        if 'Remaining_Quantity' in msg:
                            pump_data[pump_id]['quantities'].append(msg['Remaining_Quantity'])

                if not smartender.active_pumps:
                    st.warning("No pumps configured yet. Configure pumps first.")
                else:
                    for pump in smartender.active_pumps:
                        with st.expander(f"Pump {pump.id} - {pump.ingredient}", expanded=True):
                            current_temp = pump.temperature_sensor.read_temperature(pump.last_refill_time)
                            current_qty = round(pump.float_switch.left_quantity, 2)

                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Current Temperature", f"{current_temp}°C")
                            with col2:
                                st.metric("Remaining Quantity", f"{current_qty}%")

                            st.caption(f"Maintenance Status: {pump.float_switch.maintenance}")
                            st.caption(f"Configured Cocktails: {', '.join(pump.cocktails)}")

                            if pump.id in pump_data:
                                tab1, tab2 = st.tabs(["Temperature History", "Quantity History"])

                                with tab1:
                                    if len(pump_data[pump.id]['temperatures']) > 1:
                                        temp_df = pd.DataFrame({
                                            'timestamp': pd.to_datetime(pump_data[pump.id]['timestamps']),
                                            'temperature': pump_data[pump.id]['temperatures']
                                        }).set_index('timestamp')
                                        st.line_chart(temp_df, y='temperature')
                                    else:
                                        st.info("Collecting temperature data...")

                                with tab2:
                                    if len(pump_data[pump.id]['quantities']) > 1:
                                        qty_df = pd.DataFrame({
                                            'timestamp': pd.to_datetime(pump_data[pump.id]['timestamps']),
                                            'quantity': pump_data[pump.id]['quantities']
                                        }).set_index('timestamp')
                                        st.line_chart(qty_df, y='quantity')
                                    else:
                                        st.info("Collecting quantity data...")

            with tab_messages:
                if st.session_state.mqtt_messages:
                    st.write("Recent MQTT Messages:")
                    for msg in st.session_state.mqtt_messages:
                        st.write(msg)
                else:
                    st.info("No messages yet.")

                    for idx, msg in enumerate(reversed(st.session_state.mqtt_messages)):
                        st.write(f"**{msg.get('type', 'Event').title()} {len(st.session_state.mqtt_messages)-idx}**")
                        st.json(msg)
                        st.caption(f"Timestamp: {msg.get('timestamp', 'Unknown')}")
                        st.divider()
