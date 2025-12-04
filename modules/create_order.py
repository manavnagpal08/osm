import streamlit as st
# 👇 USING REAL IMPORTS
from firebase import read, push, update 
from utils import generate_order_id
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
# Initialization for the New/Repeat flow
if "order_type" not in st.session_state:
    st.session_state["order_type"] = "New Order 🆕"

# Customer input values (for New Order persistence)
for key in ["customer_input", "customer_phone_input", "customer_email_input"]:
    if key not in st.session_state:
        st.session_state[key] = ""

PLACEHOLDER = "--- Select Type ---" 
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------
# HELPER FUNCTIONS (PDF function checked for robustness)
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

# Note: Keeping the PDF generator simple for display, ensure your full version is used
def generate_order_pdf(data, qr_b64):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    qr_temp = None

    try:
        c = canvas.Canvas(temp_file.name, pagesize=A4)
        width, height = A4
        
        # --- PDF Content Generation (Simplified for display) ---
        c.drawString(40, height - 50, f"Order ID: {data['order_id']}")
        c.drawString(40, height - 70, f"Customer: {data['customer']}")
        c.drawString(40, height - 90, f"Product: {data['product_type']} / {data['category']}")
        
        # Add QR (decoded to temp file)
        qr_img = base64.b64decode(qr_b64)
        qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        qr_temp.write(qr_img)
        qr_temp.close()
        c.drawImage(qr_temp.name, width - 180, height - 150, width=100, height=100)

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

# Helper function to reset customer inputs when switching to Repeat
def reset_customer_inputs():
    if st.session_state.order_type == "Repeat Order 🔄":
        st.session_state.customer_input = ""
        st.session_state.customer_phone_input = ""
        st.session_state.customer_email_input = ""


# ---------------------------------------------------
# STEP 1 — CUSTOMER BLOCK (Updated to use your flow)
# ---------------------------------------------------
box = st.container(border=True)
with box:
    st.subheader("1️⃣ Customer Information")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # Use key and on_change to manage state transitions
        order_type = st.radio(
            "Order Type", 
            ["New Order 🆕", "Repeat Order 🔄"], 
            horizontal=True, 
            key="order_type", 
            on_change=reset_customer_inputs # Reset inputs when mode changes
        )
        order_type_simple = "New" if order_type.startswith("New") else "Repeat"

    customer_input = st.session_state.customer_input
    customer_phone_input = st.session_state.customer_phone_input
    customer_email_input = st.session_state.customer_email_input

    with col2:
        if order_type_simple == "New":
            # Direct two-way binding using key
            customer_input = st.text_input("Customer Name (Required)", key="customer_input_new")
            customer_phone_input = st.text_input("Customer Phone (Required)", key="customer_phone_input_new")
            customer_email_input = st.text_input("Customer Email", key="customer_email_input_new")
            
            # Update session state after widget read
            st.session_state.customer_input = customer_input
            st.session_state.customer_phone_input = customer_phone_input
            st.session_state.customer_email_input = customer_email_input
            

        else: # Repeat
            # The selectbox will drive the customer_input value
            selected = st.selectbox("Select Existing Customer", ["Select"] + customer_list, key="repeat_customer_select")
            
            if selected != "Select":
                customer_input = selected.strip()
                cust_orders = [
                    o for o in all_orders.values()
                    if o.get("customer") == customer_input
                ]

                if cust_orders:
                    # Find latest order details for pre-filling phone/email
                    latest = sorted(
                        cust_orders,
                        key=lambda x: x.get("received", "0000"),
                        reverse=True
                    )[0]

                    # Update inputs based on latest order, but allow user to edit
                    customer_phone_input = latest.get("customer_phone", "")
                    customer_email_input = latest.get("customer_email", "")

                # Update session state variables used for order creation
                st.session_state.customer_input = customer_input
                
                # Display inputs allowing for last-minute edits
                customer_phone_input = st.text_input("Phone", customer_phone_input, key="customer_phone_input_repeat")
                customer_email_input = st.text_input("Email", customer_email_input, key="customer_email_input_repeat")
                
                st.session_state.customer_phone_input = customer_phone_input
                st.session_state.customer_email_input = customer_email_input
            
            else:
                 # If "Select" is chosen in Repeat mode, clear inputs
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
    
    cust_orders = [
        o for o in all_orders.values()
        if o.get("customer") == final_customer_input
    ]

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order for Auto-fill")
        
        # Sort orders by date for display
        cust_orders.sort(
            key=lambda x: x.get("received", "0000"),
            reverse=True
        )
        
        options = ["--- Select for Auto-fill ---"] + [
            f"{o['order_id']} — {o.get('item', '[No Description]')}" 
            for o in cust_orders
        ]
        
        sel = st.selectbox("Choose Previous Order", options, key="autofill_order_select")

        if sel != "--- Select for Auto-fill ---":
            sel_id = sel.split("—")[0].strip()
            # Find the full order object
            previous_order = next((o for o in cust_orders if o["order_id"] == sel_id), None)
            if previous_order:
                 st.info(f"Loaded details from order **{sel_id}** for auto-filling Step 3.")
            
st.markdown("---")

# ---------------------------------------------------
# STEP 3 — ORDER SPECIFICATION (Main Form Logic)
# ---------------------------------------------------

def update_product_type():
    st.session_state.current_product_type = st.session_state.product_type_select

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
    due_date = st.date_input("📤 Due Date", 
                             value=datetime.strptime(prev.get("due", date.today().strftime("%Y-%m-%d %H:%M:%S IST")).split(' ')[0], '%Y-%m-%d').date() if 'due' in prev else date.today(), 
                             key="due_date")
    
receive_dt = datetime.combine(receive_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")
due_dt = datetime.combine(due_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")

with colC:
    priority = st.select_slider(
        "Priority", 
        options=["Low", "Medium", "High"],
        value=prev.get("priority", "Medium"),
        key="priority_select"
    )
with colD:
    advance_value = prev.get("advance", "No")
    advance = st.radio(
        "Advance Received?", 
        ["Yes", "No"], 
        horizontal=True, 
        index=["Yes", "No"].index(advance_value) if advance_value in ["Yes", "No"] else 1,
        key="advance_radio"
    )


## Product Type, Category, Quantity
st.divider()
st.subheader("Product & Quantity")
col5, col6, col7 = st.columns(3)

product_type_options = [PLACEHOLDER] + sorted(list(categories.keys()))

initial_pt = prev.get("product_type", st.session_state.current_product_type or PLACEHOLDER)
pt_index = product_type_options.index(initial_pt) if initial_pt in product_type_options else 0

with col5:
    product_type = st.selectbox(
        "Product Type",
        product_type_options,
        index=pt_index,
        key="product_type_select", 
        on_change=update_product_type 
    )

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

item = st.text_area(
    "Product Description (Detailed specifications, content, etc.)", 
    value=prev.get("item", ""), 
    height=100,
    key="item_description"
)


## Technical Specs
st.divider()
st.subheader("Manufacturing Specifications")

with st.expander("📐 Technical IDs and Finishes (Click to expand)"):
    col_id_1, col_id_2, col_id_3 = st.columns(3)
    with col_id_1:
        board = st.text_input("Board Thickness ID", value=prev.get("board_thickness_id", ""), key="board_id")
    with col_id_2:
        paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id", ""), key="paper_id")
    with col_id_3:
        size = st.text_input("Size ID", value=prev.get("size_id", ""), key="size_id")

    col_finish_1, col_finish_2 = st.columns(2)
    with col_finish_1:
        foil_value = prev.get("foil_id", "No")
        foil = st.radio(
            "Foil Required?", 
            ["No", "Yes"], 
            horizontal=True, 
            index=["No", "Yes"].index(foil_value) if foil_value in ["No", "Yes"] else 0,
            key="foil_radio"
        )
    with col_finish_2:
        spotuv_value = prev.get("spotuv_id", "No")
        spotuv = st.radio(
            "Spot UV Required?", 
            ["No", "Yes"], 
            horizontal=True, 
            index=["No", "Yes"].index(spotuv_value) if spotuv_value in ["No", "Yes"] else 0,
            key="spotuv_radio"
        )


## Pricing & Submit
st.divider()
st.subheader("Pricing")

colP, colT = st.columns([1, 2])
with colP:
    rate = st.number_input(
        "Unit Rate ₹", 
        min_value=0.0, 
        value=float(prev.get("rate", 0)), 
        step=0.01, 
        format="%.2f",
        key="rate_input"
    )

total_value = qty * rate

with colT:
    st.metric("Total Order Value", f"₹{total_value:,.2f}", delta_color="off")


st.markdown("---")
# The submission button now triggers the final processing logic
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

    data = {
        "order_id": order_id,
        "customer": final_customer_input,
        "customer_phone": final_phone_input,
        "customer_email": final_email_input,
        "product_type": current_type, 
        "category": category,
        "priority": priority,
        "qty": qty,
        "item": item,
        "received": receive_dt,
        "due": due_dt,
        "advance": advance,
        "board_thickness_id": board,
        "paper_thickness_id": paper,
        "size_id": size,
        "foil_id": foil,
        "spotuv_id": spotuv,
        "rate": rate,
        "stage": "Design", 
        "order_qr": qr_b64,
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
    st.session_state["current_product_type"] = None 

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
