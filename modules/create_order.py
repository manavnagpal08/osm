import streamlit as st
# 👇 PRODUCTION IMPORTS: Using the provided firebase.py
from firebase import read, push, update 
from datetime import date, datetime 
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

# ===================================================
# UTILITY FUNCTIONS
# ===================================================

def generate_order_id(all_orders: dict):
    """
    Generates the next sequential order ID in SRPXXX format by reading 
    the largest existing ID from the 'orders' data.
    """
    # Extract existing numeric IDs (only those starting with 'SRP')
    current_numbers = []
    
    # Use .values() to iterate over the actual order data
    for order_data in all_orders.values():
        if isinstance(order_data, dict):
            order_id = order_data.get("order_id", "")
            
            # Check for SRP prefix and ensure the remainder is numeric
            if order_id.startswith("SRP") and len(order_id) > 3 and order_id[3:].isdigit():
                try:
                    current_numbers.append(int(order_id[3:]))
                except ValueError:
                    continue # Should not happen if isdigit() is true, but safe programming
    
    # Determine the next number
    if not current_numbers:
        next_number = 1
    else:
        next_number = max(current_numbers) + 1
        
    # Format to SRP followed by minimum 3 digits (SRP001, SRP010, SRP100, SRP1000)
    return f"SRP{next_number:03d}"

# ---------------------------------------------------
# General Helper Functions (No changes needed)
# ---------------------------------------------------

def generate_qr_base64(order_id: str):
    # NOTE: The URL in the QR code now points to the Firebase DB structure for tracking
    tracking_url = f"https://omss-2ccc6-default-rtdb.firebaseio.com/orders/{order_id}"
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def get_whatsapp_link(phone, order_id, customer):
    clean_phone = "".join(filter(str.isdigit, phone))
    # Ensure standard Indian format for WhatsApp linking
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

def generate_order_pdf(data, qr_b64):
    logo_path = "srplogo.png" 
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    qr_temp = None

    try:
        c = canvas.Canvas(temp_file.name, pagesize=A4)
        width, height = A4
        x_margin = 40
        HEADER_HEIGHT = 160

        c.setFillColorRGB(0.05, 0.48, 0.22)
        c.rect(0, height - HEADER_HEIGHT, width, HEADER_HEIGHT, stroke=0, fill=1)

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
        c.drawString(x_margin, y, f"Received Date: {data['received']}") 
        y -= 18
        c.drawString(x_margin, y, f"Due Date: {data['due']}")         
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
        if qr_temp and os.path.exists(qr_temp.name):
            os.unlink(qr_temp.name)


# ---------------------------------------------------
# CONFIG & INITIALIZATION
# ---------------------------------------------------
st.title("📦 Create New Manufacturing Order")

# 🚨 Data is now read live from Firebase
all_orders = read("orders") or {} 
customer_list = sorted(list(set(
    o.get("customer", "").strip() for o in all_orders.values() if isinstance(o, dict)
)))

categories = read("product_categories") or {} 
# Fallback structure for categories if database returns None or empty
default_categories = {
    "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
    "Bag": ["Paper Bags", "SOS Envelopes"]
}
if not categories:
    categories = default_categories


# Session State Initialization and Reset
if "order_created_flag" not in st.session_state:
    st.session_state["order_created_flag"] = False
# ... (rest of session state initialization as before) ...
if "last_order_pdf" not in st.session_state: st.session_state["last_order_pdf"] = None
if "current_product_type" not in st.session_state: st.session_state["current_product_type"] = None
if "order_type" not in st.session_state: st.session_state["order_type"] = "New Order 🆕"
for key in ["customer_name_final", "customer_phone_final", "customer_email_final"]:
    if key not in st.session_state: st.session_state[key] = ""

PLACEHOLDER = "--- Select Type ---" 

def update_product_type():
    st.session_state.current_product_type = st.session_state.product_type_select

def reset_all_session_vars():
    st.session_state["order_created_flag"] = False
    st.session_state["current_product_type"] = None 
    st.session_state["customer_name_final"] = ""
    st.session_state["customer_phone_final"] = ""
    st.session_state["customer_email_final"] = ""


# ---------------------------------------------------
# 1️⃣ CUSTOMER BLOCK 
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
        )

    with col2:
        pass


    # ---------------------------
    # NEW ORDER
    # ---------------------------
    if order_type == "New Order 🆕":
        st.session_state.customer_name_final = st.text_input(
            "Customer Name (Required)",
            value=st.session_state.get("customer_name_final", "")
        )

        st.session_state.customer_phone_final = st.text_input(
            "Customer Phone (Required)",
            value=st.session_state.get("customer_phone_final", "")
        )

        st.session_state.customer_email_final = st.text_input(
            "Customer Email",
            value=st.session_state.get("customer_email_final", "")
        )


    # ---------------------------
    # REPEAT ORDER
    # ---------------------------
    else:
        if st.session_state.order_type == "New Order 🆕":
            st.session_state.customer_name_final = ""
            st.session_state.customer_phone_final = ""
            st.session_state.customer_email_final = ""

        selected_customer = st.selectbox(
            "Select Existing Customer",
            ["Select Customer"] + customer_list,
            key="repeat_customer_select"
        )

        if selected_customer != "Select Customer":
            st.session_state.customer_name_final = selected_customer

            cust_orders = [
                o for o in all_orders.values()
                if o.get("customer") == selected_customer
            ]

            phone_val = ""
            email_val = ""

            if cust_orders:
                latest = sorted(
                    cust_orders,
                    key=lambda x: x.get("received", "0000"),
                    reverse=True
                )[0]

                phone_val = latest.get("customer_phone", "")
                email_val = latest.get("customer_email", "")

            st.session_state.customer_phone_final = phone_val
            st.session_state.customer_email_final = email_val

            st.text_input("Phone", value=phone_val, disabled=True)
            st.text_input("Email", value=email_val, disabled=True)

        else:
            st.session_state.customer_name_final = ""
            st.session_state.customer_phone_final = ""
            st.session_state.customer_email_final = ""
            st.info("Select a customer to load previous data.")
            st.text_input("Phone", value="", disabled=True)
            st.text_input("Email", value="", disabled=True)

final_customer_input = st.session_state.get("customer_name_final", "")
final_phone_input = st.session_state.get("customer_phone_final", "")
final_email_input = st.session_state.get("customer_email_final", "")


# ---------------------------------------------------
# 2️⃣ REPEAT ORDER AUTOFILL
# ---------------------------------------------------
previous_order = None
order_type_simple = "New" if order_type.startswith("New") else "Repeat"

if order_type_simple == "Repeat" and final_customer_input:
    
    cust_orders = [o for o in all_orders.values() if o.get("customer") == final_customer_input]

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order for Auto-fill")
        
        cust_orders.sort(key=lambda x: x.get("received", "0000"), reverse=True)
        
        options = ["--- Select for Auto-fill ---"] + [
            f"{o.get('order_id', 'N/A')} — {o.get('item', '[No Description]')}" 
            for o in cust_orders if o.get('order_id') # Filter out orders without an ID
        ]
        
        sel = st.selectbox("Choose Previous Order", options, key="autofill_order_select")

        if sel != "--- Select for Auto-fill ---":
            sel_id = sel.split("—")[0].strip()
            previous_order = next((
                o for o in cust_orders 
                if isinstance(o, dict) and o.get("order_id") == sel_id
            ), None)
            
            if previous_order:
                st.info(f"Loaded details from order **{sel_id}** for auto-filling Step 3.")
            
st.markdown("---")

# ---------------------------------------------------
# 3️⃣ ORDER SPECIFICATION (FULL FORM)
# ---------------------------------------------------
st.header("3️⃣ Order Specification")

prev = previous_order or {}
# 🚨 Use the new sequential ID generation logic
order_id = generate_order_id(all_orders) 
st.info(f"**New Order ID:** `{order_id}` (Generated sequentially in SRPXXX format)")

## Core Details
st.subheader("Core Details")
colA, colB, colC, colD = st.columns(4)

# 🚨 Use date.today(), which reflects the local IST date if the server is configured correctly.
with colA:
    receive_date = st.date_input("📥 Received Date (IST)", value=date.today(), key="receive_date")
with colB:
    default_due_date = date.today()
    if 'due' in prev and prev['due']:
        try:
            default_due_date = datetime.strptime(prev['due'], '%Y-%m-%d').date()
        except Exception:
            pass 

    due_date = st.date_input("📤 Due Date (IST)", value=default_due_date, key="due_date")
    
receive_dt = receive_date.strftime("%Y-%m-%d")
due_dt = due_date.strftime("%Y-%m-%d")

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
    if st.session_state.product_type_select != st.session_state.current_product_type:
        st.session_state.current_product_type = st.session_state.product_type_select

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
            st.warning(f"No categories found for {current_type}. Add categories in database.")
    else:
        st.info("Select a Product Type first") 

with col7:
    qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 1)), key="qty_input")

item = st.text_area("Product Description (Detailed specifications, content, etc.)", value=prev.get("item", ""), height=100, key="item_description")


## Manufacturing Specifications
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

## Pricing
st.divider()
st.subheader("Pricing")
colP, colT = st.columns([1, 2])
with colP:
    rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate", 0)), step=0.01, format="%.2f", key="rate_input")
total_value = qty * rate
with colT:
    st.metric("Total Order Value", f"₹{total_value:,.2f}", delta_color="off")
st.markdown("---")


submitted = st.button("🚀 Create and Finalize Order", use_container_width=True, key="submit_button")


# ---------------------------------------------------
# SUBMISSION LOGIC
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

    # 🚨 PUSH DATA TO FIREBASE
    try:
        push_result = push("orders", data)
    except Exception as e:
        st.error(f"Failed to save order to Firebase: {e}")
        st.stop()

    # --- PDF Generation and Fix ---
    pdf_path = generate_order_pdf(data, qr_b64)
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            st.session_state["last_order_pdf"] = pdf_bytes
            
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
