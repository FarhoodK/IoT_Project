import streamlit as st
import requests
import pandas as pd
from logger import Logger

class SmartenderUI:
    def __init__(self, api_base_url="http://localhost:8080"):
        self.api_base_url = api_base_url
        self.setup_page()
        self.initialize_session_state()
        self.logger = Logger("STREAMLIT")

    def setup_page(self):
        st.set_page_config(page_title="Smartender", page_icon="🍹")
        
    def initialize_session_state(self):
        # Initialize session state components if they don't exist
        if "selected_cocktails" not in st.session_state:
            st.session_state.selected_cocktails = []
        if "mqtt_messages" not in st.session_state:
            st.session_state.mqtt_messages = []
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "current_cocktail" not in st.session_state:
            st.session_state.current_cocktail = None
        if "current_user" not in st.session_state:
            st.session_state.current_user = None
        if "cocktail_status" not in st.session_state:
            st.session_state.cocktail_status = "Idle"

    def fetch_available_cocktails(self):
        try:
            response = requests.get(f"{self.api_base_url}/cocktails")
            return response.json()
        except Exception as e:
            st.error(f"Error fetching cocktails: {e}")
            return []

    def select_cocktail(self, cocktail_name):
        try:
            response = requests.post(
                f"{self.api_base_url}/select_cocktail", 
                json={"cocktail_name": cocktail_name}
            )
            if response.status_code == 200:
                st.success(f"{cocktail_name} selected successfully!")
                # Add the cocktail to selected cocktails in session state
                if cocktail_name not in st.session_state.selected_cocktails:
                    st.session_state.selected_cocktails.append(cocktail_name)
            else:
                st.error(f"Error selecting cocktail: {response.json().get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error selecting cocktail: {e}")

    def make_cocktail(self, cocktail_name):
        try:
            response = requests.post(
                f"{self.api_base_url}/make_cocktail", 
                json={"cocktail_name": cocktail_name, "user": "Streamlit User"}
            )
            if response.status_code == 200:
                st.session_state.current_cocktail = cocktail_name
                st.session_state.current_user = "Streamlit User"
                st.session_state.cocktail_status = "Processing..."
                st.success(f"Preparing {cocktail_name}...")
            else:
                st.error(f"Error making cocktail: {response.json().get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error making cocktail: {e}")

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

    def render_status_page(self):
        st.subheader("Smartender Status")

        # Placeholder for dynamic content
        cocktail_status_placeholder = st.empty()

        # Display current cocktail status if available
        if st.session_state.current_cocktail:
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
                        self.logger.info("Admin logged in successfully")
                        st.rerun()
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

            with tab_status:
                st.subheader("System Status")
                
                # Fetch system status
                try:
                    status_response = requests.get(f"{self.api_base_url}/status")
                    pump_response = requests.get(f"{self.api_base_url}/pump_status")
                    
                    system_status = status_response.json()
                    pump_status = pump_response.json()
                    
                    st.metric("Current Status", system_status.get('status', 'Unknown'))
                    st.metric("Current Task", system_status.get('current_task', 'None'))
                    
                    st.subheader("Active Pumps")
                    for pump in pump_status:
                        with st.expander(f"Pump {pump['id']}: {pump['ingredient']}"):
                            st.metric("Temperature", f"{pump['temperature']}°C")
                            st.metric("Remaining Quantity", f"{pump['remaining_quantity']}%")
                            st.text("Used in Cocktails:")
                            st.text(", ".join(pump['cocktails']))
                
                except Exception as e:
                    st.error(f"Error fetching system status: {e}")

    def render_ui(self):
        # Sidebar menu
        menu = st.sidebar.selectbox("Menu", [
            "Home",
            "Status", 
            "Configure"
        ])

        # Render appropriate page based on menu selection
        if menu == "Home":
            self.render_home_page()
        elif menu == "Status":
            self.render_status_page()
        elif menu == "Configure":
            self.render_configure_page()

if __name__ == "__main__":
    ui = SmartenderUI()  # Initialize UI
    ui.render_ui()  # Render the UI