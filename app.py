import streamlit as st
import pandas as pd
from smartender import Smartender
import time
from publisher import MqttClient

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
        topic="smartender/status"
    )
    st.session_state.mqtt_subscriber.connect()

# Process MQTT messages
new_messages = st.session_state.mqtt_subscriber.get_messages()
if new_messages:
    st.session_state.mqtt_messages.extend(new_messages)
    st.session_state.mqtt_messages = st.session_state.mqtt_messages[-50:]

smartender = st.session_state.smartender

# Sidebar menu
menu = st.sidebar.selectbox("Menu", [
    "Home", 
    "Make Cocktail",
    "Admin"
])

# Home Page
if menu == "Home":
    st.title("Welcome to Smartender!🍹")
    st.write("""
        Smartender is a fully automated cocktail-making system that helps you mix your favorite drinks with ease. 
        Simply select the cocktails you want to prepare, and Smartender will take care of the rest. 
        It's an efficient and fun way to enjoy perfect cocktails every time!
    """)

    st.image("/Users/lapodalessandris/Desktop/IoT Project/undefined-Imgur-ezgif.com-effects.gif",
             use_container_width=True,
             caption="Cheers!"
             )
    
    st.write("### How it works:")
    st.write("1. **Configure Your Smartender**: Select your favorite cocktails and configure the pumps (Admin required).")
    st.write("2. **Pump Status**: Check the status of the pumps to ensure everything is ready (Admin required).")
    st.write("3. **Make Cocktail**: Choose a cocktail and let Smartender prepare it for you.")

# Make Cocktail Page
elif menu == "Make Cocktail":
    st.subheader("Make a Cocktail")
    if not smartender.selected_cocktails:
        st.warning("No cocktails available. Please ask admin to configure the system.")
    else:
        cols = st.columns(3)
        for idx, cocktail in enumerate(smartender.selected_cocktails):
            col_idx = idx % 3
            with cols[col_idx]:
                with st.expander(cocktail.name):
                    st.write("### Ingredients:")
                    for ingredient, details in cocktail.ingredients.items():
                        st.write(f"- {ingredient}: {details['quantity']}ml at {details['optimal_temp_C']}°C")
        selected_cocktail = st.selectbox(
            "Choose cocktail", [c.name for c in smartender.selected_cocktails]
        )
        if st.button("Make Cocktail"):
            with st.spinner(f"Preparing {selected_cocktail}..."):
                cocktail_to_make = next(
                    (c for c in smartender.selected_cocktails if c.name == selected_cocktail), None
                )
                if cocktail_to_make:
                    total_steps = len(cocktail_to_make.ingredients)
                    progress_bar = st.progress(0)
                    for i, (ingredient, details) in enumerate(cocktail_to_make.ingredients.items(), 1):
                        for pump in smartender.active_pumps:
                            if pump.ingredient == ingredient:
                                pump.erogate(ingredient, details['quantity'], details['optimal_temp_C'], details['quantity']/10)
                                st.write(
                                    f"Dispensing {details['quantity']} ml of {ingredient} at {details['optimal_temp_C']}°C...")

                        progress_bar.progress(i/total_steps)
                    st.success(f"Your {selected_cocktail} is ready! Enjoy!")

# Admin Section
elif menu == "Admin":
    st.subheader("Admin Portal")
    
    if not st.session_state.authenticated:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if username == "admin" and password == "password":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.success("Logged in as admin")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        
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
                st.subheader("System Messages Log")
                if not st.session_state.mqtt_messages:
                    st.info("No system messages yet")
                else:
                    col1, col2 = st.columns([4, 1])
                    with col2:
                        if st.button("Clear Messages"):
                            st.session_state.mqtt_messages = []
                            st.rerun()
                    
                    for idx, msg in enumerate(reversed(st.session_state.mqtt_messages)):
                        st.write(f"**{msg.get('type', 'Event').title()} {len(st.session_state.mqtt_messages)-idx}**")
                        st.json(msg)
                        st.caption(f"Timestamp: {msg.get('timestamp', 'Unknown')}")
                        st.divider()