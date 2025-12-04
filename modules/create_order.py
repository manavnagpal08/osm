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

if "order_created_flag" not in st.session_state:
    st.session_state["order_created_flag"] = False

if "last_order_pdf" not in st.session_state:
    st.session_state["last_order_pdf"] = None

if "current_product_type" not in st.session_state:
    st.session_state["current_product_type"] = None

# Define constant placeholder
PLACEHOLDER = "--- Select Type ---" 

# Set IST timezone once
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------
# HELPER FUNCTIONS (No changes needed here)
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

def send_gmail(to, subject, html):
    # ... (function body remains the same)
    pass # Placeholder for brevity, keep the full function in your code

def generate_order_pdf(data, qr_b64):
    # ... (function body remains the same)
    # Ensure you keep the full PDF generation function
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    # Simplified return for example
    return temp_file.name


# ---------------------------------------------------
# LOAD DATA & INITIAL SETUP
# ---------------------------------------------------
st.title("📦 Manufacturing Order Management")
st.caption("Create and track new production orders for Shree Ram Packers.")

all_orders = read("orders") or {}
customer_list = sorted({
    o.get("customer", "").strip()
    for o in all_orders.values()
    if isinstance(o, dict)
})

# Load Product Categories
categories = read("product_categories") or {}
default_categories = {
    "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
    "Bag": ["Paper Bags", "SOS Envelopes"]
}
# Fallback to defaults if DB is empty
for t in default_categories:
    if t not in categories:
        categories[t] = default_categories[t]


# ---------------------------------------------------
# CATEGORY ADMIN PANEL & DEBUG
# ---------------------------------------------------
st.sidebar.subheader("⚙️ Manage Product Categories")

with st.sidebar.expander("Add/View Categories"):
    type_choice_admin = st.selectbox("Select Product Type", ["Box", "Bag"], key="admin_type")
    new_cat = st.text_input("New Category Name", key="admin_cat_name")

    if st.button("Add Category", key="admin_add_btn"):
        if new_cat.strip():
            new_cat_clean = new_cat.strip()
            if new_cat_clean not in categories.get(type_choice_admin, []):
                if type_choice_admin not in categories:
                    categories[type_choice_admin] = []
                categories[type_choice_admin].append(new_cat_clean)
                update("product_categories", categories)
                st.success(f"Category '{new_cat_clean}' added to {type_choice_admin}!")
                st.rerun()
            else:
                st.warning("Category already exists.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Current Categories:**")
    for t, cats in categories.items():
        st.sidebar.markdown(f"**{t}**:")
        st.sidebar.write(", ".join(cats))

# Debug panel for inspection
st.sidebar.subheader("🐞 Debug Variables")
st.sidebar.code(f"""
    Session PT: '{st.session_state.current_product_type}'
    PT Selectbox Key: 'product_type_select'
    Category List: {categories.get(st.session_state.current_product_type, 'N/A')}
""")


# ---------------------------------------------------
# 1️⃣ CUSTOMER BLOCK
# ---------------------------------------------------
st.header("1️⃣ Customer Information")

col1, col2 = st.columns(2)
with col1:
    customer_input = st.text_input("Customer Name (Required)", placeholder="e.g., ABC Traders", key="customer_name")
with col2:
    customer_phone_input = st.text_input("Customer Phone (Required)", placeholder="e.g., 9312215239", key="customer_phone")
    customer_email_input = st.text_input("Customer Email (Optional)", placeholder="e.g., contact@abctraders.com", key="customer_email")

st.markdown("---")


# ---------------------------------------------------
# 🔁 REPEAT ORDER AUTOFILL
# ---------------------------------------------------
previous_order = None
cust_orders = [
    o for o in all_orders.values()
    if o.get("customer") == customer_input
]

if cust_orders:
    st.subheader("🔁 Repeat Order Autofill")
    repeat_container = st.container(border=True)
    with repeat_container:
        st.markdown("**Load Details from a Previous Order**")
        options = [f"{o['order_id']} — {o.get('item','[No Description]')}" for o in cust_orders]
        sel = st.selectbox("Choose Previous Order", ["--- Select ---"] + options, key="repeat_order_select")

        if sel != "--- Select ---":
            sel_id = sel.split("—")[0].strip()
            previous_order = next((o for o in cust_orders if o["order_id"] == sel_id), None)
            st.info(f"Loaded details from order **{sel_id}**.")
            
st.markdown("---")

# ---------------------------------------------------
# 2️⃣ ORDER SPECIFICATION (No Form)
# ---------------------------------------------------
st.header("2️⃣ Order Specification")

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
    due_date = st.date_input("📤 Due Date", value=date.today(), key="due_date")
    
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

# Function to handle selectbox change and update session state
def update_product_type():
    st.session_state.current_product_type = st.session_state.product_type_select

product_type_options = [PLACEHOLDER] + sorted(list(categories.keys()))

# Use previous type if available, otherwise use the PLACEHOLDER
initial_pt = prev.get("product_type", st.session_state.current_product_type or PLACEHOLDER)
pt_index = product_type_options.index(initial_pt) if initial_pt in product_type_options else 0

with col5:
    product_type = st.selectbox(
        "Product Type",
        product_type_options,
        index=pt_index,
        key="product_type_select", 
        on_change=update_product_type # 👈 Crucial: Update session state immediately
    )

# --- CATEGORY LOGIC ---
category = None 
current_type = st.session_state.current_product_type # Use the session state value
is_product_type_selected = current_type and current_type != PLACEHOLDER

with col6:
    if is_product_type_selected:
        category_list = categories.get(current_type, [])
        
        if category_list:
            
            # Use previous category from autofill or the first in the list
            default_cat = prev.get("category", category_list[0])
            
            try:
                cat_index = category_list.index(default_cat)
            except ValueError:
                cat_index = 0
            
            # Use the current_type for the dynamic key
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

if submitted:
    # --- Validation ---
    if not customer_input:
        st.error("Customer Name required")
        st.stop()
    if not customer_phone_input:
        st.error("Phone required")
        st.stop()
    if not is_product_type_selected: # Checks the session state value
        st.error("Please select a Product Type.")
        st.stop()
    # Check the category value retrieved from the selectbox
    if not category: 
        st.error("Product Category required")
        st.stop()

    # --- Data Generation ---
    qr_b64 = generate_qr_base64(order_id)

    data = {
        "order_id": order_id,
        "customer": customer_input,
        "customer_phone": customer_phone_input,
        "customer_email": customer_email_input,
        "product_type": current_type, # Use the confirmed session state value
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

    pdf_path = generate_order_pdf(data, qr_b64)
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        st.session_state["last_order_pdf"] = pdf_bytes

    if os.path.exists(pdf_path):
        os.unlink(pdf_path)


    # --- Session State Update for Success ---
    st.session_state["last_order_id"] = order_id
    st.session_state["last_qr"] = qr_b64
    st.session_state["last_whatsapp"] = get_whatsapp_link(customer_phone_input, order_id, customer_input)
    st.session_state["last_tracking"] = f"https://srppackaging.com/tracking.html?id={order_id}"
    st.session_state["order_created_flag"] = True
    st.session_state["current_product_type"] = None # Reset session state for a new order

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
