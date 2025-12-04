import streamlit as st
# 👇 USING REAL IMPORTS (Ensure these are available in your environment)
# from firebase import read, push, update 
# from utils import generate_order_id
from datetime import date, datetime, timezone, timedelta
import qrcode
import base64
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.parse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import tempfile
import os 
import time 

# ---------------------------------------------------
# MOCK FUNCTIONS (REPLACE WITH YOUR REAL ONES)
# ---------------------------------------------------
# MOCK: Replace these with your actual database read/write functions
def read(key):
    # Mock database read
    if key == "orders":
        return {
            "ORD001": {"customer": "ABC Traders", "customer_phone": "9312215239", "customer_email": "abc@trade.com", "product_type": "Box", "category": "Rigid Box", "item": "Luxury Gift Box", "received": "2023-10-01 10:00:00 IST", "due": "2023-11-01 10:00:00 IST", "priority": "High", "qty": 1000, "rate": 50.0, "advance": "Yes", "board_thickness_id": "1.5mm", "paper_thickness_id": "120gsm", "size_id": "A4", "foil_id": "Yes", "spotuv_id": "No"},
            "ORD002": {"customer": "XYZ Corp", "customer_phone": "9876543210", "customer_email": "xyz@corp.in", "product_type": "Bag", "category": "Paper Bags", "item": "Shopping Bags", "received": "2023-11-15 11:00:00 IST", "due": "2023-12-15 11:00:00 IST", "priority": "Medium", "qty": 5000, "rate": 5.0, "advance": "No", "board_thickness_id": "N/A", "paper_thickness_id": "180gsm", "size_id": "L", "foil_id": "No", "spotuv_id": "No"},
            "ORD003": {"customer": "ABC Traders", "customer_phone": "9312215239", "customer_email": "abc@trade.com", "product_type": "Box", "category": "Folding Box", "item": "Pizza Box", "received": "2024-01-20 12:00:00 IST", "due": "2024-02-20 12:00:00 IST", "priority": "Medium", "qty": 2000, "rate": 15.0, "advance": "Yes", "board_thickness_id": "3-ply", "paper_thickness_id": "N/A", "size_id": "12in", "foil_id": "No", "spotuv_id": "No"},
        }
    elif key == "product_categories":
        return {
            "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
            "Bag": ["Paper Bags", "SOS Envelopes"]
        }
    return {}

def push(key, data):
    # Mock database push
    st.success(f"MOCK: Pushing data to '{key}' with ID {data.get('order_id')}")
    pass

def update(key, data):
    # Mock database update
    st.success(f"MOCK: Updating data for '{key}'")
    pass

def generate_order_id():
    # Mock order ID generator
    return f"ORD{int(time.time())}"
# ---------------------------------------------------


# ---------------------------------------------------
# CONFIG & INITIALIZATION
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

GMAIL_USER = "yourgmail@gmail.com" 
GMAIL_PASS = "your_app_password" 

# Session State Initialization
if "order_created_flag" not in st.session_state:
    st.session_state["order_created_flag"] = False
if "last_order_pdf" not in st.session_state:
    st.session_state["last_order_pdf"] = None
if "current_product_type" not in st.session_state:
    st.session_state["current_product_type"] = None
if "order_type" not in st.session_state:
    st.session_state["order_type"] = "New Order 🆕"

# Customer input values (for New Order persistence)
for key in ["customer_input", "customer_phone_input", "customer_email_input"]:
    if key not in st.session_state:
        st.session_state[key] = ""

PLACEHOLDER = "--- Select Type ---" 
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------
# HELPER FUNCTIONS 
# ---------------------------------------------------
def generate_qr_base64(order_id: str):
    tracking_url = f"https://srppackaging.com/tracking.html?id={order_id}"
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def get_whatsapp_link(phone, order_id, customer):
    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone.startswith("91"):
        clean_phone = "91" + clean_phone
    tracking_url = f"https://srppackaging.com/tracking.html?id={order_id}"
    message = (
        f"Hello {customer}, your order {order_id} has been created successfully!\n"
        f"Track your order:\n{tracking_url}\n\n"
        f"Thank you – Shree Ram Packers"
    )
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded}"

# Note: Keeping the PDF generator function complete for robustness
def generate_order_pdf(data, qr_b64):
    # This is a mock path, replace "srplogo.png" with your actual path
    logo_path = "srplogo.png" 
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    qr_temp = None

    try:
        c = canvas.Canvas(temp_file.name, pagesize=A4)
        width, height = A4
        x_margin = 40
        HEADER_HEIGHT = 160

        # Header BG
        c.setFillColorRGB(0.05, 0.48, 0.22)
        c.rect(0, height - HEADER_HEIGHT, width, HEADER_HEIGHT, stroke=0, fill=1)

        # Logo placeholder or image (if path exists)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(x_margin, height - 60, "Shree Ram Packers")

        c.setStrokeColorRGB(0.07, 0.56, 0.27)
        c.setLineWidth(3)
        c.line(x_margin, height - HEADER_HEIGHT - 10, width - x_margin,
            height - HEADER_HEIGHT - 10)

        c.setFillColorRGB(0, 0, 0)
        y = height - HEADER_HEIGHT - 40

        # Customer Info
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Customer Details")
        y -= 35
        c.setFont("Helvetica", 11)
        c.drawString(x_margin, y, f"Customer Name: {data['customer']}")
        y -= 18
        c.drawString(x_margin, y, f"Phone: {data['customer_phone']}")
        y -= 18

        y -= 20

        # Order Info
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Order Details")
        y -= 35
        c.setFont("Helvetica", 11)
        c.drawString(x_margin, y, f"Order ID: {data['order_id']}")
        y -= 18
        c.drawString(x_margin, y, f"Product Type: {data['product_type']}")
        y -= 18
        c.drawString(x_margin, y, f"Category: {data['category']}")
        y -= 18
        c.drawString(x_margin, y, f"Quantity: {data['qty']}")
        
        # QR
        y_qr = height - HEADER_HEIGHT - 40
        qr_img = base64.b64decode(qr_b64)
        qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        qr_temp.write(qr_img)
        qr_temp.close()
        c.drawImage(qr_temp.name, width - 180, y_qr, width=130, height=130)

        c.save()
        return temp_file.name
    
    finally:
        # Clean up temporary QR file
        if qr_temp and os.path.exists(qr_temp.name):
            os.unlink(qr_temp.name)


# ---------------------------------------------------
# LOAD DATA & INITIAL SETUP
# ---------------------------------------------------
st.title("📦 Create New Manufacturing Order")

all_orders = read("orders") or {}
customer_list = sorted(list(set(
    o.get("customer", "").strip() for o in all_orders.values() if isinstance(o, dict)
)))

categories = read("product_categories") or {}
default_categories = {
    "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
    "Bag": ["Paper Bags", "SOS Envelopes"]
}
for t in default_categories:
    if t not in categories:
        categories[t] = default_categories[t]

# Helper function to reset inputs when switching order type
def reset_customer_inputs():
    # Only reset if we switch to Repeat, to clear New order inputs
    if st.session_state.order_type == "Repeat Order 🔄":
        st.session_state["customer_input"] = ""
        st.session_state["customer_phone_input"] = ""
        st.session_state["customer_email_input"] = ""
        st.session_state["current_product_type"] = PLACEHOLDER # Reset type when customer selection clears

# Function to update product type state
def update_product_type():
    st.session_state.current_product_type = st.session_state.product_type_select

# Function to reset all state for a brand new order (used by success button)
def reset_all_session_vars():
    st.session_state["order_created_flag"] = False
    st.session_state["current_product_type"] = None 
    st.session_state["customer_input"] = ""
    st.session_state["customer_phone_input"] = ""
    st.session_state["customer_email_input"] = ""


# ---------------------------------------------------
# SIDEBAR DEBUG & ADMIN
# ---------------------------------------------------
st.sidebar.subheader("🐞 Debug Variables")
st.sidebar.code(f"""
    Order Created: {st.session_state.order_created_flag}
    Order Type: {st.session_state.order_type}
    Customer Name: '{st.session_state.customer_input}'
    Session PT: '{st.session_state.current_product_type}'
""")

# (Category Admin Panel code removed for brevity, keep it in your full code)

# ---------------------------------------------------
# STEP 1 — CUSTOMER BLOCK
# ---------------------------------------------------
box = st.container(border=True)
with box:
    st.subheader("1️⃣ Customer Information")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        order_type = st.radio(
            "Order Type", 
            ["New Order 🆕", "Repeat Order 🔄"], 
            horizontal=True, 
            key="order_type", 
            on_change=reset_customer_inputs
        )
        order_type_simple = "New" if order_type.startswith("New") else "Repeat"

    with col2:
        if order_type_simple == "New":
            st.session_state.customer_input = st.text_input("Customer Name (Required)", key="customer_input_new")
            st.session_state.customer_phone_input = st.text_input("Customer Phone (Required)", key="customer_phone_input_new")
            st.session_state.customer_email_input = st.text_input("Customer Email", key="customer_email_input_new")
            
        else: # Repeat
            # The selectbox value is stored directly in st.session_state.repeat_customer_select
            selected = st.selectbox(
                "Select Existing Customer", 
                ["Select"] + customer_list, 
                key="repeat_customer_select"
            )
            
            if selected != "Select":
                final_customer_name = selected.strip()
                st.session_state.customer_input = final_customer_name
                
                cust_orders = [o for o in all_orders.values() if o.get("customer") == final_customer_name]

                # Autofill logic for phone/email from latest order
                customer_phone_val = ""
                customer_email_val = ""
                if cust_orders:
                    latest = sorted(cust_orders, key=lambda x: x.get("received", "0000"), reverse=True)[0]
                    customer_phone_val = latest.get("customer_phone", "")
                    customer_email_val = latest.get("customer_email", "")
                
                # Display inputs allowing for last-minute edits
                st.session_state.customer_phone_input = st.text_input("Phone", customer_phone_val, key="customer_phone_input_repeat")
                st.session_state.customer_email_input = st.text_input("Email", customer_email_val, key="customer_email_input_repeat")
            
            else:
                # Reset if "Select" is chosen in Repeat mode
                st.session_state.customer_input = ""
                st.session_state.customer_phone_input = st.text_input("Phone", "", key="customer_phone_input_repeat_empty", disabled=True)
                st.session_state.customer_email_input = st.text_input("Email", "", key="customer_email_input_repeat_empty", disabled=True)


# Get final customer details from session state for use in next steps
final_customer_input = st.session_state.customer_input
final_phone_input = st.session_state.customer_phone_input
final_email_input = st.session_state.customer_email_input


# ---------------------------------------------------
# STEP 2 — REPEAT ORDER AUTOFILL (Select Previous Order)
# ---------------------------------------------------
previous_order = None

if order_type_simple == "Repeat" and final_customer_input:
    
    cust_orders = [o for o in all_orders.values() if o.get("customer") == final_customer_input]

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order for Auto-fill")
        
        cust_orders.sort(key=lambda x: x.get("received", "0000"), reverse=True)
        
        options = ["--- Select for Auto-fill ---"] + [
            f"{o['order_id']} — {o.get('item', '[No Description]')}" 
            for o in cust_orders
        ]
        
        sel = st.selectbox("Choose Previous Order", options, key="autofill_order_select")

        if sel != "--- Select for Auto-fill ---":
            sel_id = sel.split("—")[0].strip()
            previous_order = next((o for o in cust_orders if o["order_id"] == sel_id), None)
            if previous_order:
                 st.info(f"Loaded details from order **{sel_id}** for auto-filling Step 3.")
            
st.markdown("---")

# ---------------------------------------------------
# STEP 3 — ORDER SPECIFICATION (Main Form Logic)
# ---------------------------------------------------
st.header("3️⃣ Order Specification")

prev = previous_order or {}
order_id = generate_order_id()
st.info(f"**New Order ID:** `{order_id}`")

## Core Details
st.subheader("Core Details")
colA, colB, colC, colD = st.columns(4)

now_ist = datetime.now(IST).time() 

with colA:
    receive_date = st.date_input("📥 Received Date", value=date.today(), key="receive_date")
with colB:
    # Robust date parsing logic
    default_due_date = date.today()
    if 'due' in prev and prev['due']:
        try:
            due_str = prev['due'].split(' ')[0]
            default_due_date = datetime.strptime(due_str, '%Y-%m-%d').date()
        except Exception:
            pass 

    due_date = st.date_input("📤 Due Date", value=default_due_date, key="due_date")
    
receive_dt = datetime.combine(receive_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")
due_dt = datetime.combine(due_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")

with colC:
    priority = st.select_slider("Priority", options=["Low", "Medium", "High"], value=prev.get("priority", "Medium"), key="priority_select")
with colD:
    advance_value = prev.get("advance", "No")
    advance = st.radio("Advance Received?", ["Yes", "No"], horizontal=True, index=["Yes", "No"].index(advance_value) if advance_value in ["Yes", "No"] else 1, key="advance_radio")


## Product Type, Category, Quantity
st.divider()
st.subheader("Product & Quantity")
col5, col6, col7 = st.columns(3)

product_type_options = [PLACEHOLDER] + sorted(list(categories.keys()))

# Default index logic: use current session state, or previous order, or placeholder
initial_pt = st.session_state.current_product_type or prev.get("product_type", PLACEHOLDER)
pt_index = product_type_options.index(initial_pt) if initial_pt in product_type_options else 0

with col5:
    product_type = st.selectbox(
        "Product Type",
        product_type_options,
        index=pt_index,
        key="product_type_select", 
        on_change=update_product_type 
    )
    # Ensure session state reflects the initial selected value right after the widget runs
    if st.session_state.product_type_select != st.session_state.current_product_type:
        st.session_state.current_product_type = st.session_state.product_type_select

# --- CATEGORY LOGIC ---
category = None 
current_type = st.session_state.current_product_type 
is_product_type_selected = current_type and current_type != PLACEHOLDER

with col6:
    if is_product_type_selected:
        category_list = categories.get(current_type, [])
        
        if category_list:
            default_cat = prev.get("category", category_list[0])
            try:
                cat_index = category_list.index(default_cat)
            except ValueError:
                cat_index = 0
            
            category = st.selectbox(
                "Product Category",
                category_list,
                index=cat_index,
                key=f"category_select_{current_type}" 
            )
        else:
            st.warning(f"No categories found for {current_type}. Add categories in sidebar.")
    else:
        st.info("Select a Product Type first") 

with col7:
    qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 1)), key="qty_input")
# ----------------------

item = st.text_area("Product Description (Detailed specifications, content, etc.)", value=prev.get("item", ""), height=100, key="item_description")


## Technical Specs
# (Specs and Pricing sections removed for brevity, keep the full code in your file)
st.divider()
rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate", 0)), step=0.01, format="%.2f", key="rate_input")
total_value = qty * rate
st.metric("Total Order Value", f"₹{total_value:,.2f}", delta_color="off")
st.markdown("---")


# The submission button
submitted = st.button("🚀 Create and Finalize Order", use_container_width=True, key="submit_button")


# ---------------------------------------------------
# SUBMISSION LOGIC (Handle PDF Creation and Cleanup)
# ---------------------------------------------------
if submitted:
    # --- Validation ---
    if not final_customer_input:
        st.error("Customer Name required (Step 1)")
        st.stop()
    if not final_phone_input:
        st.error("Phone required (Step 1)")
        st.stop()
    if not is_product_type_selected: 
        st.error("Please select a Product Type (Step 3).")
        st.stop()
    if not category: 
        st.error("Product Category required (Step 3).")
        st.stop()

    # --- Data Preparation ---
    qr_b64 = generate_qr_base64(order_id)
    # Mocking other inputs (replace with actual keys)
    board, paper, size, foil, spotuv = "", "", "", "No", "No"
    
    data = {
        "order_id": order_id, "customer": final_customer_input, "customer_phone": final_phone_input, 
        "customer_email": final_email_input, "product_type": current_type, "category": category,
        "priority": priority, "qty": qty, "item": item, "received": receive_dt, "due": due_dt,
        "advance": advance, "board_thickness_id": board, "paper_thickness_id": paper,
        "size_id": size, "foil_id": foil, "spotuv_id": spotuv, "rate": rate,
        "stage": "Design", "order_qr": qr_b64,
    }

    push("orders", data)

    # --- PDF Generation and Fix ---
    pdf_path = generate_order_pdf(data, qr_b64)
    
    try:
        # 1. Read the PDF content into memory (bytes)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            st.session_state["last_order_pdf"] = pdf_bytes
            
        # 2. THEN, delete the temporary file
        os.unlink(pdf_path)
    except Exception as e:
        st.error(f"Error handling PDF file during download preparation: {e}")
        st.stop()


    # --- Session State Update for Success ---
    st.session_state["last_order_id"] = order_id
    st.session_state["last_qr"] = qr_b64
    st.session_state["last_whatsapp"] = get_whatsapp_link(final_phone_input, order_id, final_customer_input)
    st.session_state["last_tracking"] = f"https://srppackaging.com/tracking.html?id={order_id}"
    st.session_state["order_created_flag"] = True
    # st.session_state["current_product_type"] = None <-- DO NOT RESET HERE

    st.rerun()


# ---------------------------------------------------
# SUCCESS BLOCK
# ---------------------------------------------------
if st.session_state.get("order_created_flag"):
    st.balloons()
    
    st.success(f"🎉 Order **{st.session_state['last_order_id']}** Created Successfully! What's next?")
    
    col_pdf, col_wa = st.columns(2)
    
    with col_pdf:
        st.download_button(
            label="📄 Download Order PDF",
            data=st.session_state["last_order_pdf"],
            file_name=f"{st.session_state['last_order_id']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        
    with col_wa:
        st.markdown(
            f"""
            <a href="{st.session_state['last_whatsapp']}" target="_blank">
                <button style='width: 100%; height: 38px; background-color: #25D366; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;'>
                    💬 Send Confirmation via WhatsApp
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    
    # Reset button to clear the success block and start a new order
    st.button("📦 Start New Order", on_click=reset_all_session_vars, use_container_width=True)

    col_qr, col_track = st.columns([1, 2])
    with col_qr:
        st.image(
            base64.b64decode(st.session_state["last_qr"]), 
            caption=f"QR for Order {st.session_state['last_order_id']}", 
            width=150
        )
    
    with col_track:
        st.markdown(f"**Tracking Link:**")
        st.code(st.session_state["last_tracking"], language=None)
        st.info("Share this link with your production team or customer for real-time tracking.")
