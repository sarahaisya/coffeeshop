import streamlit as st
import random
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import stripe
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import time
import random
import datetime
import streamlit as st

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
if 'coupons' not in st.session_state:
    st.session_state.coupons = {}

# Function to display notifications
def display_notifications():
    # Example: Notify about low stock items
    low_stock_items = {item: stock for item, stock in st.session_state.inventory.items() if stock < 5}
    if low_stock_items:
        st.warning("⚠️ Low Stock Alert!")
        for item, stock in low_stock_items.items():
            st.write(f"- {item}: Only {stock} left in stock. Please restock soon!")

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

# Function to apply coupon
def apply_coupon(total_cost, coupon_code):
    # Check if the coupon is valid
    if coupon_code in st.session_state.coupons:
        coupon = st.session_state.coupons[coupon_code]
        # Check if the coupon is still valid based on today's date
        if datetime.date.today() <= coupon['validity_date']:
            discount = coupon['discount_percentage']
            discount_amount = (discount / 100) * total_cost
            total_cost -= discount_amount
            st.success(f"Coupon applied! You get a {discount}% discount. Discount amount: RM {discount_amount:.2f}")
        else:
            st.error("Coupon has expired.")
    else:
        st.error("Invalid coupon code.")
    return total_cost



# Function to confirm order with coupon input
def confirm_order():
    if not st.session_state.cart:
        st.error("Your cart is empty!")
        return

    booking_number = f"ORDER-{random.randint(1000, 9999)}"
    total_cost = sum(item['price'] for item in st.session_state.cart)

    # Set fixed preparation time to 1 minute
    total_preparation_time = 1* sum(item['quantity'] for item in st.session_state.cart) # 1 minute for every order

    # Display order summary
    st.write(f"### Order Summary")
    st.write(f"Booking Number: {booking_number}")
    st.write(f"Estimated Preparation Time: {total_preparation_time} minute")
    st.write(f"Total: RM {total_cost:.2f}")
    
    # Coupon input field
    coupon_code = st.text_input("Enter Coupon Code (if any)")

    # Apply coupon if a code is entered
    if coupon_code:
        total_cost = apply_coupon(total_cost, coupon_code)

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
                'order_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'ready_at': (datetime.datetime.now() + datetime.timedelta(minutes=total_preparation_time)).strftime("%Y-%m-%d %H:%M:%S")
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

            # Clear the cart
            st.session_state.cart.clear()

# Function to check if any orders are ready for pickup
def check_order_readiness():
    current_time = datetime.datetime.now()
    for order in st.session_state.order_history:
        ready_time = datetime.datetime.strptime(order['ready_at'], "%Y-%m-%d %H:%M:%S")
        if current_time >= ready_time and not order.get('notified', False):
            st.info(f"📢 Order {order['booking_number']} is ready for pickup!")
            order['notified'] = True  # Mark order as notified

# Call the readiness check periodically
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

check_order_readiness()

# Function to display the order status page
def display_order_status():
    st.title(f"Order Status for {st.session_state.username}")

    # Check if there are any orders
    if st.session_state.order_history:
        for order in st.session_state.order_history:
            # Calculate elapsed and remaining preparation time
            current_time = datetime.datetime.now()
            order_time = datetime.datetime.strptime(order['order_date'], "%Y-%m-%d %H:%M:%S")
            elapsed_time = (current_time - order_time).total_seconds() / 60
            remaining_time = max(order['estimated_time'] - int(elapsed_time), 0)

            # Display order status
            if remaining_time > 0:
                st.warning(f"Your order is being prepared. Estimated wait time: {remaining_time:.0f} minutes.")
            else:
                st.success(f"Your order is ready for pickup!")
                st.balloons()

            # Display order details
            st.write(f"**Booking Number:** {order['booking_number']}")
            st.write(f"**Order Date:** {order['order_date']}")
            st.write(f"**Estimated Ready At:** {order['ready_at']}")
            st.write("**Items:**")
            st.table(pd.DataFrame(order['items']))  # Display items in a table format
            st.write("---")
    else:
        st.write("No current orders found.")

    # Refresh button
    if st.button("Refresh Status"):
        st.rerun()



# Display user menu
def display_menu():
    display_notifications()
    st.title("Coffee Menu")

    # Dictionary with coffee names and their corresponding image paths or URLs
    coffee_images = {
        "Americano":"https://raw.githubusercontent.com/sarahaisya/coffeeshop/main/americano.png",
        "Latte": "https://raw.githubusercontent.com/sarahaisya/coffeeshop/main/latte.png",
        "Cappuccino": "https://raw.githubusercontent.com/sarahaisya/coffeeshop/main/cappucino.png",
        "Macchiato": "https://raw.githubusercontent.com/sarahaisya/coffeeshop/main/machiato.png"
    }

    for coffee, stock in st.session_state.inventory.items():
        base_price = 5.0
        price_options = {'small': base_price - 1, 'regular': base_price, 'big': base_price + 1}
        
        # Display the coffee name, stock, and image
        st.write(f"### {coffee} (Stock: {stock})")
        st.image(coffee_images.get(coffee, "images/default.jpg"), width=150, caption=coffee)  # Fallback to default image
        
        # Coffee options
        st.write(f"Base Price: RM {base_price:.2f}")
        quantity = st.number_input(f"Quantity for {coffee}", min_value=0, max_value=stock, step=1, key=f"{coffee}_qty")
        size = st.selectbox(f"Size for {coffee}", ["small", "regular", "big"], key=f"{coffee}_size")
        sugar = st.selectbox(f"Sugar level for {coffee}", ["less sugar", "regular", "extra sugar"], key=f"{coffee}_sugar")

        if quantity > 0:
            price = price_options[size] * quantity
            if st.button(f"Add {coffee} to Cart", key=f"{coffee}_add_to_cart"):
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

# Add coupon section in session state
if 'coupons' not in st.session_state:
    st.session_state.coupons = {}

# Function to create a coupon
def create_coupon():
    st.title("Create Coupon")
    coupon_code = st.text_input("Coupon Code")
    discount_percentage = st.slider("Discount Percentage", 1, 100, 10)  # Default 10%
    validity_date = st.date_input("Validity Date")

    if st.button("Create Coupon"):
        if coupon_code and validity_date:
            # Store coupon in session state
            st.session_state.coupons[coupon_code] = {
                'discount_percentage': discount_percentage,
                'validity_date': validity_date
            }
            st.success(f"Coupon '{coupon_code}' created successfully!")
        else:
            st.error("Please provide a valid coupon code and validity date.")

# Function to manage coupons
def manage_coupons():
    st.title("Manage Coupons")
    if st.session_state.coupons:
        st.write("### Available Coupons")
        for coupon_code, details in st.session_state.coupons.items():
            st.write(f"**Coupon Code:** {coupon_code}")
            st.write(f"**Discount Percentage:** {details['discount_percentage']}%")
            st.write(f"**Validity Date:** {details['validity_date']}")
            st.write("---")
    else:
        st.write("No coupons available.")

# Update the Admin navigation to include the coupon creation
def admin_panel():
    display_notifications()
    st.sidebar.title("Admin Navigation")
    nav = st.sidebar.radio("Admin Options", ["View Sales Report", "Create Coupon", "Manage Coupons", "Update Inventory", "Manage Orders", "Logout"])

   
    if nav == "View Sales Report":
        admin_dashboard()
    elif nav == "Create Coupon":
        create_coupon()  # Calls the coupon creation function
    elif nav == "Manage Coupons":
        manage_coupons()  # Calls the manage coupons function
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

# Function to display the About Page
def about_page():
    st.title("About Us")
    st.write("---")  # Horizontal line for design

    # Team name and description
    st.markdown("""
    ## Team Name: **Late Comers**
    ---
    We are a group of passionate students from the coffee tech innovation lab. Our goal is to create an efficient and user-friendly coffee shop management application. Meet our incredible team below!
    """)

    # Team Members Section
    st.markdown("### **Team Members**")
    
    members = [
        {"name": "Nadhirah Wardah Binti Ahmad Sayuti", "id": "20001328"},
        {"name": "Nur Shakirah Binti Zuratmi", "id": "21001193"},
        {"name": "Nur Dania Adlina Binti Ahmad Jais", "id": "21001719"},
        {"name": "Nurain Alyaa Binti Hajid", "id": "21001272"},
        {"name": "Sarah Aisyah Binti Isnani", "id": "21001863"}
    ]

    for idx, member in enumerate(members, start=1):
        st.markdown(f"""
        <div style="border: 2px solid #f39c12; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: #fef5e7;">
            <h4 style="color: #d35400;">{idx}. {member['name']}</h4>
            <p style="font-size: 16px; margin: 0;"><b>ID:</b> {member['id']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Closing Note
    st.markdown("""
    ---
    ### Thank You for Visiting!
    We appreciate your support and hope you enjoy our application. Feel free to reach out for any suggestions or feedback. 😊
    """)


# Main function to include the About Page in navigation
def main():
    if not st.session_state.logged_in:
        login_interface()
    else:
        if st.session_state.user_role == "User":
            page = st.sidebar.radio("Navigation", ["Menu", "Order History", "Order status", "About", "Logout"])
            if page == "Menu":
                display_menu()
            elif page == "Order History":
                display_order_history()
            elif page == "Order status":
                display_order_status()
            elif page == "About":
                about_page()
            elif page == "Logout":
                log_out()
        elif st.session_state.user_role == "Admin":
            page = st.sidebar.radio("Navigation", ["Admin Panel", "About", "Logout"])
            if page == "Admin Panel":
                admin_panel()
            elif page == "About":
                about_page()
            elif page == "Logout":
                log_out()

if __name__ == "__main__":
    main()
