import streamlit as st
# Assuming these are custom modules; ensure they are accessible
# from firebase import read, push, update 
# from utils import generate_order_id
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
from datetime import date, datetime, timezone, timedelta
import os 
import time # For the mock functions

# ---------------------------------------------------
# MOCK IMPORTS (Replace with your actual firebase/utils if testing locally)
# ---------------------------------------------------

# MOCK Firebase Functions
def read(key):
    """Mock read function. In a real app, this reads from Firebase."""
    if key == "orders":
        return {
            "O1": {"order_id": "O1", "customer": "ABC Traders", "item": "Standard Folding Box", "product_type": "Box", "category": "Folding Box", "qty": 1000, "rate": 5.5, "board_thickness_id": "B-03", "paper_thickness_id": "P-10", "size_id": "S-101", "foil_id": "No", "spotuv_id": "Yes", "priority": "Medium", "advance": "Yes"},
            "O2": {"order_id": "O2", "customer": "ABC Traders", "item": "Luxury Rigid Box", "product_type": "Box", "category": "Rigid Box", "qty": 500, "rate": 12.0, "board_thickness_id": "B-05", "paper_thickness_id": "P-12", "size_id": "S-205", "foil_id": "Yes", "spotuv_id": "No", "priority": "High", "advance": "Yes"},
            "O3": {"order_id": "O3", "customer": "XYZ Bags", "item": "Plain Kraft Bag", "product_type": "Bag", "category": "Paper Bags", "qty": 2000, "rate": 3.0, "board_thickness_id": "", "paper_thickness_id": "P-08", "size_id": "S-301", "foil_id": "No", "spotuv_id": "No", "priority": "Low", "advance": "No"},
        }
    if key == "product_categories":
        return {
            "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
            "Bag": ["Paper Bags", "SOS Envelopes"]
        }
    return {}

def push(key, data):
    """Mock push function."""
    st.success(f"Mock Data Pushed to {key}: {data['order_id']}")
    time.sleep(0.5)

def update(key, data):
    """Mock update function."""
    st.success(f"Mock Data Updated for {key}.")
    time.sleep(0.5)

def generate_order_id():
    """Mock order ID generator."""
    return f"SRP-{int(time.time())}"


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

# WARNING: Replace with your actual credentials!
GMAIL_USER = "yourgmail@gmail.com" 
GMAIL_PASS = "your_app_password" 

if "order_created_flag" not in st.session_state:
    st.session_state["order_created_flag"] = False

if "last_order_pdf" not in st.session_state:
    st.session_state["last_order_pdf"] = None

# Set IST timezone once
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------
# QR GENERATOR
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


# ---------------------------------------------------
# WHATSAPP LINK
# ---------------------------------------------------
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


# ---------------------------------------------------
# EMAIL
# ---------------------------------------------------
def send_gmail(to, subject, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, to, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False


# ---------------------------------------------------
# PDF GENERATOR
# ---------------------------------------------------
def generate_order_pdf(data, qr_b64):
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

        # Logo
        try:
            c.drawImage(logo_path, x_margin, height - HEADER_HEIGHT + 30, width=130,
                        preserveAspectRatio=True, mask="auto")
        except:
            pass 

        separator_x = x_margin + 160
        c.setStrokeColorRGB(1, 1, 1)
        c.setLineWidth(1.4)
        c.line(separator_x, height - HEADER_HEIGHT + 20, separator_x, height - 20)

        left_block_x = separator_x + 20
        top_y = height - 60

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(left_block_x, top_y, "Shree Ram Packers")

        c.setFont("Helvetica", 14)
        c.drawString(left_block_x, top_y - 25, "Premium Packaging & Printing Solutions")

        info_y = top_y - 55
        c.setFont("Helvetica", 12)
        for line in ["Mobile: 9312215239", "GSTIN: 29BCIPK6225L1Z6", "Website: https://srppackaging.com/"]:
            c.drawString(left_block_x, info_y, line)
            info_y -= 18

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

        total_value = data["qty"] * data["rate"]

        customer_details = [
            ("Customer Name", data["customer"]),
            ("Phone", data["customer_phone"]),
            ("Email", data["customer_email"]),
            ("Received Date", data["received"]),
            ("Due Date", data["due"]),
        ]
        
        for label, value in customer_details:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x_margin, y, f"{label}:")
            c.setFont("Helvetica", 11)
            c.drawString(x_margin + 150, y, str(value))
            y -= 18

        y -= 20

        # Order Info
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Order Details")
        y -= 35

        order_details = [
            ("Order ID", data["order_id"]),
            ("Product Type", data["product_type"]),
            ("Category", data["category"]),
            ("Priority", data["priority"]),
            ("Quantity", data["qty"]),
            ("Rate (₹)", f"₹{data['rate']:,.2f}"),
            ("Total Value (₹)", f"₹{total_value:,.2f}"),
            ("Advance Received", data["advance"]),
            ("Board Thickness", data["board_thickness_id"]),
            ("Paper Thickness", data["paper_thickness_id"]),
            ("Size ID", data["size_id"]),
            ("Foil", data["foil_id"]),
            ("Spot UV", data["spotuv_id"]),
            ("Description", data["item"]),
        ]

        for label, value in order_details:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x_margin, y, f"{label}:")
            c.setFont("Helvetica", 11)
            
            # Handle long description wrapping (simple)
            if label == "Description":
                desc_lines = str(value).split('\n')
                current_y = y
                for line in desc_lines:
                    c.drawString(x_margin + 180, current_y, line)
                    current_y -= 12
                y = current_y + 12
            else:
                c.drawString(x_margin + 180, y, str(value))
            
            y -= 18

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
for t in default_categories:
    if t not in categories:
        categories[t] = default_categories[t]


# ---------------------------------------------------
# CATEGORY ADMIN PANEL (MOVED TO SIDEBAR)
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


# ---------------------------------------------------
# 1️⃣ CUSTOMER BLOCK
# ---------------------------------------------------
st.header("1️⃣ Customer Information")

col1, col2 = st.columns(2)
with col1:
    customer_input = st.text_input("Customer Name (Required)", placeholder="e.g., ABC Traders")
with col2:
    customer_phone_input = st.text_input("Customer Phone (Required)", placeholder="e.g., 9312215239")
    customer_email_input = st.text_input("Customer Email (Optional)", placeholder="e.g., contact@abctraders.com")

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
        sel = st.selectbox("Choose Previous Order", ["--- Select ---"] + options, label_visibility="collapsed")

        if sel != "--- Select ---":
            sel_id = sel.split("—")[0].strip()
            previous_order = next((o for o in cust_orders if o["order_id"] == sel_id), None)
            st.info(f"Loaded details from order **{sel_id}**.")
            
st.markdown("---")

# ---------------------------------------------------
# 2️⃣ ORDER FORM
# ---------------------------------------------------
with st.form("order_form"):
    
    st.header("2️⃣ Order Specification")
    order_id = generate_order_id()
    st.info(f"**New Order ID:** `{order_id}`")

    prev = previous_order or {}
    
    # Dates & Core Details
    st.subheader("Core Details")
    colA, colB, colC, colD = st.columns(4)

    now_ist = datetime.now(IST).time() 

    with colA:
        receive_date = st.date_input("📥 Received Date", value=date.today())
    with colB:
        due_date = st.date_input("📤 Due Date", value=date.today())
        
    receive_dt = datetime.combine(receive_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")
    due_dt = datetime.combine(due_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")

    with colC:
        priority = st.select_slider(
            "Priority", 
            options=["Low", "Medium", "High"],
            value=prev.get("priority", "Medium")
        )
    with colD:
        advance_value = prev.get("advance", "No")
        advance = st.radio(
            "Advance Received?", 
            ["Yes", "No"], 
            horizontal=True, 
            index=["Yes", "No"].index(advance_value) if advance_value in ["Yes", "No"] else 1
        )


    # Product Type, Category, Quantity
    st.divider()
    st.subheader("Product & Quantity")
    col5, col6, col7 = st.columns(3)
    
    with col5:
        default_pt = prev.get("product_type", "Box")
        pt_options = ["Bag", "Box"]
        pt_index = pt_options.index(default_pt) if default_pt in pt_options else 1

        product_type = st.selectbox(
            "Product Type",
            pt_options,
            index=pt_index,
            key="product_type_select" # Added key for better stability
        )

    # FIX FOR CATEGORY NOT UPDATING: Use a dynamic key and proper index calculation
    category = ""
    category_list = categories.get(product_type, [])

    with col6:
        if category_list:
            
            # Determine the default category from the previous order (prev)
            default_cat = prev.get("category", category_list[0])
            
            # Check if the default category is actually in the NEW category_list.
            try:
                cat_index = category_list.index(default_cat)
            except ValueError:
                # If the old category is not found (Product Type changed), default to 0.
                cat_index = 0
            
            category = st.selectbox(
                "Product Category",
                category_list,
                index=cat_index,
                # Dynamic key forces reset when product_type changes!
                key=f"category_select_{product_type}" 
            )
        else:
            st.warning(f"No categories found for {product_type}. Add categories in sidebar.")

    with col7:
        qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 1)))

    item = st.text_area(
        "Product Description (Detailed specifications, content, etc.)", 
        value=prev.get("item", ""), 
        height=100
    )


    # Technical Specs (Expander for cleanliness)
    st.divider()
    st.subheader("Manufacturing Specifications")

    with st.expander("📐 Technical IDs and Finishes (Click to expand)"):
        col_id_1, col_id_2, col_id_3 = st.columns(3)
        with col_id_1:
            board = st.text_input("Board Thickness ID", value=prev.get("board_thickness_id", ""))
        with col_id_2:
            paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id", ""))
        with col_id_3:
            size = st.text_input("Size ID", value=prev.get("size_id", ""))

        col_finish_1, col_finish_2 = st.columns(2)
        with col_finish_1:
            foil_value = prev.get("foil_id", "No")
            foil = st.radio(
                "Foil Required?", 
                ["No", "Yes"], 
                horizontal=True, 
                index=["No", "Yes"].index(foil_value) if foil_value in ["No", "Yes"] else 0
            )
        with col_finish_2:
            spotuv_value = prev.get("spotuv_id", "No")
            spotuv = st.radio(
                "Spot UV Required?", 
                ["No", "Yes"], 
                horizontal=True, 
                index=["No", "Yes"].index(spotuv_value) if spotuv_value in ["No", "Yes"] else 0
            )


    # Pricing & Submit
    st.divider()
    st.subheader("Pricing")
    
    colP, colT = st.columns([1, 2])
    with colP:
        rate = st.number_input(
            "Unit Rate ₹", 
            min_value=0.0, 
            value=float(prev.get("rate", 0)), 
            step=0.01, 
            format="%.2f"
        )
    
    total_value = qty * rate

    with colT:
        st.metric("Total Order Value", f"₹{total_value:,.2f}", delta_color="off")


    st.markdown("---")
    submitted = st.form_submit_button("🚀 Create and Finalize Order", use_container_width=True)

    if submitted:
        # --- Validation ---
        if not customer_input:
            st.error("Customer Name required")
            st.stop()
        if not customer_phone_input:
            st.error("Phone required")
            st.stop()
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
            "product_type": product_type,
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

        # --- Database & File Operations ---
        push("orders", data)

        pdf_path = generate_order_pdf(data, qr_b64)
        
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            st.session_state["last_order_pdf"] = pdf_bytes

        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


        # --- Session State Update ---
        st.session_state["last_order_id"] = order_id
        st.session_state["last_qr"] = qr_b64
        st.session_state["last_whatsapp"] = get_whatsapp_link(customer_phone_input, order_id, customer_input)
        st.session_state["last_tracking"] = f"https://srppackaging.com/tracking.html?id={order_id}"
        st.session_state["order_created_flag"] = True

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
