import streamlit as st
import random
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import stripe
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Stripe API Initialization
stripe.api_key = "sk_test_51QNEGrIb4tfjcNCChY8bmoDqK40a8hw3uXbaNrkK1M9dBf6QGSQVGzFjAUQhTylKy81YNaSeN7gNmb92LmI7fK1f005aQm8i8m"  # Replace with your actual Stripe secret key

# Initialize session state variables
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'order_history' not in st.session_state:
    st.session_state.order_history = []
if 'inventory' not in st.session_state:
    st.session_state.inventory = {'Americano': 10, 'Latte': 10, 'Cappuccino': 10, 'Macchiato': 10}
if 'sales_data' not in st.session_state:
    st.session_state.sales_data = []
if 'users_db' not in st.session_state:
    st.session_state.users_db = {}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# Helper function to store sales data
def record_sale(drink_type, quantity, total_price, date):
    st.session_state.sales_data.append({
        "Drink": drink_type,
        "Quantity": quantity,
        "Total Price": total_price,
        "Date": date
    })

# Payment Integration
def process_payment(amount, token):
    try:
        charge = stripe.Charge.create(
            amount=amount,
            currency="usd",
            description="Coffee Shop Order",
            source=token
        )
        return charge
    except stripe.error.StripeError as e:
        st.error(f"Payment failed: {e}")
        return None

def generate_invoice(order_id, customer_name, items, total_price):
    pdf_filename = f"invoice_{order_id}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    c.drawString(100, 750, f"Invoice #{order_id}")
    c.drawString(100, 730, f"Customer: {customer_name}")
    c.drawString(100, 710, f"Items: {', '.join(items)}")
    c.drawString(100, 690, f"Total Price: ${total_price:.2f}")
    c.save()
    return pdf_filename

# Function to handle sign-up
def sign_up(email, password, username, role="User"):
    if email in st.session_state.users_db:
        st.warning("This email is already registered. Please log in.")
    else:
        st.session_state.users_db[email] = {"password": password, "username": username, "role": role}
        st.success(f"Account created successfully as {role}! Please log in.")

# Function to handle login
def log_in(email, password):
    if email in st.session_state.users_db and st.session_state.users_db[email]["password"] == password:
        st.session_state.username = st.session_state.users_db[email]["username"]
        st.session_state.useremail = email
        st.session_state.logged_in = True
        st.session_state.user_role = st.session_state.users_db[email]["role"]
        st.success(f"Logged in successfully as {st.session_state.user_role}!")
        st.rerun()
    else:
        st.error("Invalid email or password.")

# Function to log out
def log_out():
    st.session_state.username = ''
    st.session_state.useremail = ''
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.success("You have logged out.")
    st.rerun()

# Function to confirm order
def confirm_order():
    if not st.session_state.cart:
        st.error("Your cart is empty!")
        return

    booking_number = f"ORDER-{random.randint(1000, 9999)}"
    total_cost = sum(item['price'] for item in st.session_state.cart)
    total_preparation_time = 5 * sum(item['quantity'] for item in st.session_state.cart)

    st.write(f"### Order Summary")
    st.write(f"Booking Number: {booking_number}")
    st.write(f"Estimated Preparation Time: {total_preparation_time} minutes")
    st.write(f"Total: RM {total_cost:.2f}")
    
    # Proceed to Payment
    if st.button("Proceed to Payment"):
        payment_token = "tok_visa"  # Mock token; replace with actual token from Stripe.js
        charge = process_payment(int(total_cost * 100), payment_token)  # Convert to cents
        if charge:
            st.success("Payment is successful!")
            order_details = {
                'booking_number': booking_number,
                'total': total_cost,
                'items': st.session_state.cart.copy(),
                'estimated_time': total_preparation_time,
                'order_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.order_history.append(order_details)

            # Update inventory and record sales
            for item in st.session_state.cart:
                drink = item['item']
                quantity = item['quantity']
                st.session_state.inventory[drink] -= quantity
                record_sale(drink, quantity, item['price'], order_details['order_date'])

            # Generate and offer invoice download
            customer_name = st.session_state.username
            invoice_file = generate_invoice(booking_number, customer_name, [f"{item['quantity']}x {item['item']}" for item in st.session_state.cart], total_cost)
            with open(invoice_file, "rb") as file:
                st.download_button(
                    label="Download Invoice",
                    data=file,
                    file_name=invoice_file,
                    mime="application/pdf"
                )

            st.session_state.cart.clear()

# Display user menu
def display_menu():
    st.title("Coffee Menu")
    for coffee, stock in st.session_state.inventory.items():
        base_price = 5.0
        price_options = {'small': base_price - 1, 'regular': base_price, 'big': base_price + 1}
        st.write(f"{coffee} (Stock: {stock}) - Base Price RM {base_price:.2f}")
        quantity = st.number_input(f"Quantity for {coffee}", min_value=0, max_value=stock, step=1, key=f"{coffee}_qty")
        size = st.selectbox(f"Size for {coffee}", ["small", "regular", "big"], key=f"{coffee}_size")
        sugar = st.selectbox(f"Sugar level for {coffee}", ["less sugar", "regular", "extra sugar"], key=f"{coffee}_sugar")

        if quantity > 0:
            price = price_options[size] * quantity
            if st.button(f"Add {coffee} to Cart"):
                st.session_state.cart.append({'item': coffee, 'quantity': quantity, 'size': size, 'sugar': sugar, 'price': price})
                st.success(f"{coffee} added to cart!")

    if st.session_state.cart:
        st.write("### Current Cart")
        for i, item in enumerate(st.session_state.cart, start=1):
            st.write(f"{i}. {item['quantity']} x {item['item']} ({item['size']}, {item['sugar']}) - RM {item['price']:.2f}")
        total_cost = sum(item['price'] for item in st.session_state.cart)
        st.write(f"**Total Cost: RM {total_cost:.2f}**")
        confirm_order()

# Display order history
def display_order_history():
    st.title("Order History")
    if st.session_state.order_history:
        for order in st.session_state.order_history:
            st.write(f"**Booking Number:** {order['booking_number']}")
            st.write(f"**Date:** {order['order_date']}")
            st.write(f"**Total Cost:** RM {order['total']:.2f}")
            st.write(f"**Estimated Time:** {order['estimated_time']} minutes")
            st.write("**Items:**")
            for item in order['items']:
                st.write(f"- {item['quantity']} x {item['item']} ({item['size']}, {item['sugar']}) - RM {item['price']:.2f}")
            st.write("---")
    else:
        st.write("No orders found.")

def update_inventory():
    st.title("Update Inventory")
    for item, stock in st.session_state.inventory.items():
        st.write(f"**{item}** - Current Stock: {stock}")
        new_stock = st.number_input(f"Update stock for {item}", min_value=0, value=stock, step=1, key=f"update_{item}")
        if st.button(f"Update {item} Stock", key=f"update_button_{item}"):
            st.session_state.inventory[item] = new_stock
            st.success(f"Stock for {item} updated to {new_stock}.")

# Admin navigation
def admin_panel():
    st.sidebar.title("Admin Navigation")
    nav = st.sidebar.radio("Admin Options", ["Dashboard", "View Sales Report", "Update Inventory", "Manage Orders", "Logout"])

    if nav == "Dashboard":
        admin_dashboard()
    elif nav == "View Sales Report":
        admin_dashboard()
    elif nav == "Update Inventory":
        update_inventory()  # Calls the updated inventory management function
    elif nav == "Manage Orders":
        display_order_history()
    elif nav == "Logout":
        log_out()

# Admin dashboard
def admin_dashboard():
    st.title("Admin Dashboard")
    if st.session_state.sales_data:
        sales_df = pd.DataFrame(st.session_state.sales_data)
        st.write("### Profit by Drink Type")
        profit_by_drink = sales_df.groupby('Drink')['Total Price'].sum()
        st.bar_chart(profit_by_drink)

        st.write("### Sales by Month")
        sales_df['Month'] = pd.to_datetime(sales_df['Date']).dt.month
        sales_by_month = sales_df.groupby('Month')['Total Price'].sum()
        st.line_chart(sales_by_month)
    else:
        st.write("No sales data available.")

# Login interface
def login_interface():
    st.title("Login / Sign Up")
    choice = st.radio("Login or Sign Up", ["Login", "Sign Up"])

    if choice == "Sign Up":
        email = st.text_input("Email")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["User", "Admin"])
        if st.button("Sign Up"):
            sign_up(email, password, username, role)
    elif choice == "Login":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            log_in(email, password)

# Main app functionality
def main():
    if not st.session_state.logged_in:
        login_interface()
    else:
        if st.session_state.user_role == "User":
            page = st.sidebar.radio("Navigation", ["Menu", "Order History", "Logout"])
            if page == "Menu":
                display_menu()
            elif page == "Order History":
                display_order_history()
            elif page == "Logout":
                log_out()
        elif st.session_state.user_role == "Admin":
            admin_panel()

if __name__ == "__main__":
    main()
