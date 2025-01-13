import streamlit as st
from smartender import Smartender
import time

# Initialize Smartender instance and session state
if "smartender" not in st.session_state:
    st.session_state.smartender = Smartender("cocktails.json")
if "selected_cocktails" not in st.session_state:
    st.session_state.selected_cocktails = []

smartender = st.session_state.smartender

# Sidebar menu
menu = st.sidebar.selectbox("Menu", ["Home", "Configure Your Smartender", "Pump Status", "Make Cocktail"])

# Home Page
if menu == "Home":
    st.title("Welcome to Smartender!")
    st.write("Your automated cocktail mixing solution.")
    
    # Add an image for visual appeal (optional)
    # Uncomment the line below to add an image
    # st.image("cocktail_image.jpg", caption="Enjoy your custom cocktails!", use_column_width=True)
    
    # Add a short introduction to Smartender
    st.write("""
        Smartender is a fully automated cocktail-making system that helps you mix your favorite drinks with ease. 
        Simply select the cocktails you want to prepare, and Smartender will take care of the rest. 
        It's an efficient and fun way to enjoy perfect cocktails every time!
    """)
    
    # Add some steps to show how the system works
    st.write("### How it works:")
    st.write("1. **Configure Your Smartender**: Select your favorite cocktails and configure the pumps.")
    st.write("2. **Pump Status**: Check the status of the pumps to ensure everything is ready.")
    st.write("3. **Make Cocktail**: Choose a cocktail and let Smartender prepare it for you.")
    
    # Add a footer or contact information (optional)
    st.write("### Contact Us:")
    st.write("For more information, please visit our [website](https://www.smartender.com) or contact support.")


# Configure Your Smartender
elif menu == "Configure Your Smartender":
    st.subheader("Configure Your Smartender")

    # Display Available Cocktails
    st.write("### Available Cocktails")

    # Create columns for grid layout (adjust the number of columns per row as needed)
    cols = st.columns(3)

    for idx, cocktail in enumerate(smartender.available_cocktails):
        col_idx = idx % 3
        with cols[col_idx]:
            # Display cocktail name as a clickable expander
            with st.expander(cocktail.name):
                # Show cocktail details when clicked
                st.write("### Ingredients:")
                for ingredient, details in cocktail.ingredients.items():
                    st.write(f"- {ingredient}: {details['quantity']}ml at {details['optimal_temp_C']}°C")


    # Select Cocktails to Prepare
    st.write("### Select Cocktails to Prepare")
    selected_cocktails = st.multiselect(
        "Select cocktails", 
        [c.name for c in smartender.available_cocktails],
        default=st.session_state.selected_cocktails,
    )

    # Save Configuration
    if st.button("Save Configuration"):
        st.session_state.selected_cocktails = selected_cocktails
        for cocktail_name in selected_cocktails:
            smartender.add_cocktail(cocktail_name)
        smartender.setup_pumps()
        st.success("Pumps configured successfully!")

# Pump Status Page
elif menu == "Pump Status":
    st.subheader("Pump Status")

    if not smartender.active_pumps:
        st.warning("No pumps have been configured yet. Please configure pumps in the 'Configure your Smartender' section.")
    else:
        # Create columns for grid layout
        cols = st.columns(3)

        for idx, pump in enumerate(smartender.active_pumps):
            col_idx = idx % 3
            with cols[col_idx]:
                # Display pump ID as a clickable expander
                with st.expander(f"Pump {pump.id}"):
                    # Show pump details when clicked
                    st.write(f"**Ingredient:** {pump.ingredient}")
                    st.write(f"**Remaining Quantity:** {round(pump.float_switch.left_quantity, 2)}%")
                    st.write(f"**Current Temperature:** {pump.temperature_sensor.read_temperature(pump.last_refill_time)}°C")
                    st.write(f"**Maintenance Needed:** {pump.float_switch.maintenance}")
                    st.write(f"**Configured for Cocktails:** {', '.join(pump.cocktails)}")

# Make Cocktail Page
elif menu == "Make Cocktail":
    st.subheader("Make a Cocktail")
    if not smartender.selected_cocktails:
        st.warning("No cocktails selected. Please configure your Smartender first.")
    else:
        # Create columns for grid layout (adjust the number of columns per row as needed)
        cols = st.columns(3)
        for idx, cocktail in enumerate(smartender.selected_cocktails):
            col_idx = idx % 3
            with cols[col_idx]:
                # Display cocktail name as a clickable expander
                with st.expander(cocktail.name):
                    # Show cocktail details when clicked
                    st.write("### Ingredients:")
                    for ingredient, details in cocktail.ingredients.items():
                        st.write(f"- {ingredient}: {details['quantity']}ml at {details['optimal_temp_C']}°C")

        selected_cocktail = st.selectbox(
            "Choose a cocktail to prepare", [c.name for c in smartender.selected_cocktails]
        )

        if st.button("Make Cocktail"):
            st.success(f"Preparing your {selected_cocktail}. Please wait...")

            # Find the selected cocktail
            cocktail_to_make = next(
                (c for c in smartender.selected_cocktails if c.name == selected_cocktail), None
            )

            if cocktail_to_make:
                with st.spinner("Mixing your cocktail..."):
                    total_steps = len(cocktail_to_make.ingredients)
                    progress_bar = st.progress(0)

                    for i, (ingredient, details) in enumerate(cocktail_to_make.ingredients.items(), start=1):
                        ingredient_name = ingredient
                        ml = details['quantity']
                        optimal_temp = details['optimal_temp_C']

                        # Simulate erogation for each ingredient
                        for pump in smartender.active_pumps:
                            if pump.ingredient == ingredient_name:
                                pump.erogate(ingredient_name, ml, optimal_temp, (ml / 10))
                                st.write(
                                    f"Erogating {ml}ml of {ingredient_name} at {optimal_temp}°C..."
                                )
                                time.sleep(2)  # Simulated delay for erogation

                        # Update the progress bar
                        progress_bar.progress(i / total_steps)

                    st.success(f"Your {selected_cocktail} is ready! Enjoy!")
            else:
                st.error(f"Error: Could not find the cocktail '{selected_cocktail}' to prepare.")
