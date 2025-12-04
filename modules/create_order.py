import streamlit as st
# NOTE: Using placeholder functions for read, push, and generate_order_id since you commented out the imports.
# You MUST replace these with your live function calls.
# from firebase import read, push
# from utils import generate_order_id
from datetime import date, datetime, timezone, timedelta
import qrcode
import base64
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.parse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile
import os
import time

# ===================================================
# FIREBASE/UTILITY FUNCTIONS (PLACEHOLDERS)
# ===================================================

def read(key):
    # This mock data is necessary to test the Repeat Customer logic!
    if key == "orders":
        return {
            "ORD001": {"customer": "ABC Traders", "customer_phone": "9312215239", "customer_email": "abc@trade.com", "product_type": "Box", "item": "Luxury Gift Box", "received": "2023-10-01", "due": "2023-11-01", "priority": "High", "qty": 1000, "rate": 50.0, "advance": "Yes", "board_thickness_id": "1.5mm", "foil_id": "Yes", "spotuv_id": "No", "paper_thickness_id": "120gsm", "size_id": "A4"},
            "ORD002": {"customer": "XYZ Corp", "customer_phone": "9876543210", "customer_email": "xyz@corp.in", "product_type": "Bag", "item": "Shopping Bags", "received": "2023-11-15", "due": "2023-12-15", "priority": "Medium", "qty": 5000, "rate": 5.0, "advance": "No", "board_thickness_id": "N/A", "foil_id": "No", "spotuv_id": "No", "paper_thickness_id": "180gsm", "size_id": "L"},
        }
    return {} # Replace with YOUR_REAL_READ_FUNCTION(key) if available

def push(key, data):
    # YOUR_FIREBASE_PUSH_LOGIC(key, data)
    pass 

def generate_order_id():
    # return YOUR_ID_GENERATION_LOGIC()
    return f"ORD{int(time.time())}"
# ===================================================


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

GMAIL_USER = "yourgmail@gmail.com"
GMAIL_PASS = "your_app_password"

# ---------------------------------------------------
# HELPER INITIALISATION
# ---------------------------------------------------
if "order_created_flag" not in st.session_state:
    st.session_state["order_created_flag"] = False

# Consistent Session State Initialization for customer input values (FIXED)
for key in ["customer_name_final", "customer_phone_final", "customer_email_final"]:
    if key not in st.session_state:
        st.session_state[key] = ""


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
# WHATSAPP
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

        # Header Background
        c.setFillColorRGB(0.05, 0.48, 0.22)
        c.rect(0, height - HEADER_HEIGHT, width, HEADER_HEIGHT, stroke=0, fill=1)

        # Logo placeholder (Replace with actual drawing logic if 'srplogo.png' is available)
        # For simplicity, drawing text instead of image path that might not exist
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x_margin, height - 50, "SRP") 

        # Separator Line
        separator_x = x_margin + 160
        c.setStrokeColorRGB(1, 1, 1)
        c.setLineWidth(1.4)
        c.line(separator_x, height - HEADER_HEIGHT + 20, separator_x, height - 20)

        # Company Name + Tagline
        left_block_x = separator_x + 20
        top_y = height - 60

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(left_block_x, top_y, "Shree Ram Packers")

        c.setFont("Helvetica", 14)
        c.drawString(left_block_x, top_y - 25, "Premium Packaging & Printing Solutions")

        # Contact info under tagline
        info_y = top_y - 55
        c.setFont("Helvetica", 12)
        for line in [
            "Mobile: 9312215239",
            "GSTIN: 29BCIPK6225L1Z6",
            "Website: https://srppackaging.com/"
        ]:
            c.drawString(left_block_x, info_y, line)
            info_y -= 18

        # Header Divider
        c.setStrokeColorRGB(0.07, 0.56, 0.27)
        c.setLineWidth(3)
        c.line(x_margin, height - HEADER_HEIGHT - 10, width - x_margin, height - HEADER_HEIGHT - 10)

        c.setFillColorRGB(0, 0, 0)
        y = height - HEADER_HEIGHT - 40

        # Customer Details
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Customer Details")
        y -= 20
        c.line(x_margin, y, width - x_margin, y)
        y -= 15

        for label, value in [
            ("Customer Name", data["customer"]),
            ("Phone", data["customer_phone"]),
            ("Email", data["customer_email"]),
            ("Received Date", data["received"]),
            ("Due Date", data["due"]),
        ]:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x_margin, y, f"{label}:")
            c.setFont("Helvetica", 11)
            c.drawString(x_margin + 150, y, str(value))
            y -= 18

        y -= 15

        # Order Details
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, "Order Details")
        y -= 20
        c.line(x_margin, y, width - x_margin, y)
        y -= 20

        # Data for PDF needs to use the key 'item' not 'category' or 'product_type' for description
        # Using a fixed list for detailed printing:
        order_details_list = [
            ("Order ID", data["order_id"]),
            ("Product Type", data["product_type"]),
            ("Priority", data["priority"]),
            ("Quantity", data["qty"]),
            ("Rate (₹)", data["rate"]),
            ("Advance Received", data["advance"]),
            ("Description", data["item"]), # Use 'item' for description
            ("Board Thickness ID", data.get("board_thickness_id", "N/A")),
            ("Paper Thickness ID", data.get("paper_thickness_id", "N/A")),
            ("Size ID", data.get("size_id", "N/A")),
            ("Foil ID", data.get("foil_id", "N/A")),
            ("Spot UV ID", data.get("spotuv_id", "N/A")),
        ]

        for label, value in order_details_list:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x_margin, y, f"{label}:")
            c.setFont("Helvetica", 11)
            # Handle multiline description
            if label == "Description":
                description_lines = str(value).split('\n')
                current_y = y
                for line in description_lines:
                    c.drawString(x_margin + 180, current_y, line)
                    current_y -= 14
                y = current_y + 14 # Reset y based on the last line printed
            else:
                c.drawString(x_margin + 180, y, str(value))
            
            y -= 18
            if y < 140:
                c.showPage()
                y = height - 80

        y -= 15

        # QR Code
        qr_img = base64.b64decode(qr_b64)
        qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        qr_temp.write(qr_img)
        qr_temp.close()

        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.05, 0.48, 0.22)
        c.drawString(width - 200, 150, "Scan to Track Order")
        c.setFillColorRGB(0, 0, 0)

        c.drawImage(qr_temp.name, width - 180, 70, width=130, height=130)

        # Footer
        c.line(x_margin, 60, width - x_margin, 60)
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(x_margin, 45, "Generated automatically by SRP OMS")
        c.drawRightString(width - x_margin, 45, "Powered by SRP Automation")

        c.save()
        return temp_file.name
    finally:
        if qr_temp and os.path.exists(qr_temp.name):
            os.unlink(qr_temp.name)


# ---------------------------------------------------
# UI STARTS
# ---------------------------------------------------
st.title("📦 Create New Manufacturing Order")

all_orders = read("orders") or {}
customer_list = sorted(list(set(
    o.get("customer", "").strip() for o in all_orders.values() if isinstance(o, dict)
)))


# ---------------------------------------------------
# STEP 1 — CUSTOMER BLOCK (FIXED LOGIC)
# ---------------------------------------------------
box = st.container(border=True)
with box:
    st.subheader("1️⃣ Customer Information")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # Use key for consistent state tracking
        order_type = st.radio("Order Type", ["New Order 🆕", "Repeat Order 🔄"], horizontal=True, key="order_type_radio")
        order_type_simple = "New" if order_type.startswith("New") else "Repeat"

    with col2:
        # Define final variables reading from consistent session state keys
        customer_name_val = st.session_state.customer_name_final
        customer_phone_val = st.session_state.customer_phone_final
        customer_email_val = st.session_state.customer_email_final

        if order_type_simple == "New":
            # New Order: Inputs set session state directly
            st.session_state.customer_name_final = st.text_input(
                "Customer Name (Required)", 
                value=customer_name_val,
                key="customer_name_new"
            )
            st.session_state.customer_phone_final = st.text_input(
                "Customer Phone (Required)", 
                value=customer_phone_val,
                key="customer_phone_new"
            )
            st.session_state.customer_email_final = st.text_input(
                "Customer Email", 
                value=customer_email_val,
                key="customer_email_new"
            )

        else: # Repeat Order
            selected = st.selectbox(
                "Select Existing Customer", 
                ["Select"] + customer_list, 
                key="repeat_customer_select"
            )

            if selected != "Select":
                customer_name = selected.strip()
                st.session_state.customer_name_final = customer_name
                
                cust_orders = [
                    o for o in all_orders.values()
                    if o.get("customer") == customer_name
                ]

                # Fetch and assign values from the latest order for display
                if cust_orders:
                    latest = sorted(
                        cust_orders,
                        key=lambda x: x.get("received", "0000"),
                        reverse=True
                    )[0]
                    
                    customer_phone_val = latest.get("customer_phone", "")
                    customer_email_val = latest.get("customer_email", "")

                # Inputs now use fetched values and update the final session state keys
                st.session_state.customer_phone_final = st.text_input(
                    "Phone", 
                    value=customer_phone_val,
                    key="customer_phone_repeat"
                )
                st.session_state.customer_email_final = st.text_input(
                    "Email", 
                    value=customer_email_val,
                    key="customer_email_repeat"
                )
            
            else:
                # Clear state if "Select" is chosen
                st.session_state.customer_name_final = ""
                st.session_state.customer_phone_final = ""
                st.session_state.customer_email_final = ""

                # Display disabled inputs
                st.text_input("Phone", "", disabled=True, key="customer_phone_repeat_empty")
                st.text_input("Email", "", disabled=True, key="customer_email_repeat_empty")

# Final variables for submission now read directly from the fixed session state keys
final_customer_input = st.session_state.customer_name_final
final_phone_input = st.session_state.customer_phone_final
final_email_input = st.session_state.customer_email_final


# ---------------------------------------------------
# STEP 2 — REPEAT ORDER AUTOFILL
# ---------------------------------------------------
previous_order = None

if order_type_simple == "Repeat" and final_customer_input:
    cust_orders = [
        o for o in all_orders.values()
        if o.get("customer") == final_customer_input
    ]

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order")
        # Ensure order list is sorted for a logical selection order
        cust_orders.sort(key=lambda x: x.get("received", "0000"), reverse=True) 

        options = [f"{o['order_id']} — {o.get('item', '[No Description]')}" for o in cust_orders]
        sel = st.selectbox("Choose", ["--- Select ---"] + options, key="autofill_select")

        if sel != "--- Select ---":
            sel_id = sel.split("—")[0].strip()
            for o in cust_orders:
                if o["order_id"] == sel_id:
                    previous_order = o
                    st.success("Auto-fill applied!")
                    break


# ---------------------------------------------------
# STEP 3 — MAIN FORM
# ---------------------------------------------------
st.markdown("---")
with st.form("order_form"):

    st.subheader("3️⃣ Order Specification")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = previous_order or {}

    # ---------------------- DATE INPUTS (IST FIXED) ----------------------
    IST = timezone(timedelta(hours=5, minutes=30))

    colA, colB = st.columns(2)

    with colA:
        receive_date = st.date_input("📥 Received Date (IST)", value=date.today())

    with colB:
        default_due = date.today()
        if 'due' in prev and prev['due']:
             try:
                # Try to parse the date from the previous order, handling IST format
                dt_obj = datetime.strptime(prev['due'].split(" IST")[0], "%Y-%m-%d %H:%M:%S")
                default_due = dt_obj.date()
             except Exception:
                 pass

        due_date = st.date_input("📤 Due Date (IST)", value=default_due)

    now_ist = datetime.now(IST).time()

    receive_dt = datetime.combine(receive_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")
    due_dt = datetime.combine(due_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")
    # --------------------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        # Default product type logic
        default_pt = prev.get("product_type", "Bag")
        pt_options = ["Bag", "Box"]
        try:
             pt_index = pt_options.index(default_pt)
        except ValueError:
             pt_index = 0

        product_type = st.selectbox(
            "Product Type", pt_options,
            index=pt_index
        )
    
    # NOTE: Your provided code did not include Product Category selection, 
    # only Product Type. The form continues below using only 'product_type'.
    
    with col2:
        qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 100)))

    with col3:
        priority_options = ["High", "Medium", "Low"]
        default_priority = prev.get("priority", "Medium")
        try:
            priority_index = priority_options.index(default_priority)
        except ValueError:
            priority_index = 1
            
        priority = st.selectbox(
            "Priority", priority_options,
            index=priority_index
        )

    item = st.text_area("Product Description", value=prev.get("item", ""))

    advance_options = ["Yes", "No"]
    default_advance = prev.get("advance", "No")
    try:
        advance_index = advance_options.index(default_advance)
    except ValueError:
        advance_index = 1
        
    advance = st.radio("Advance Received?", advance_options, index=advance_index, horizontal=True)

    # Technical IDs
    board = st.text_input("Board Thickness ID", value=prev.get("board_thickness_id", ""))
    foil = st.text_input("Foil ID", value=prev.get("foil_id", ""))
    spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id", ""))
    paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id", ""))
    size = st.text_input("Size ID", value=prev.get("size_id", ""))

    # Pricing
    rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate", 0.0)))
    total_value = qty * rate
    st.metric("Total Value", f"₹{total_value:,.2f}")

    submitted = st.form_submit_button("🚀 Create Order")

    if submitted:

        # --- Validation using final_input variables ---
        if not final_customer_input.strip():
            st.error("⚠️ Customer Name is required.")
            st.stop()

        if not final_phone_input.strip():
            st.error("⚠️ Customer Phone Number is required.")
            st.stop()

        if len("".join(filter(str.isdigit, final_phone_input))) < 10:
            st.error("⚠️ Enter a valid phone number.")
            st.stop()

        # --- Submission Logic ---
        qr_b64 = generate_qr_base64(order_id)

        data = {
            "order_id": order_id,
            "customer": final_customer_input,
            "customer_phone": final_phone_input,
            "customer_email": final_email_input,
            "type": order_type_simple,
            "product_type": product_type,
            "priority": priority,
            "item": item,
            "qty": qty,
            "received": receive_dt,  
            "due": due_dt,           
            "advance": advance,
            "foil_id": foil,
            "spotuv_id": spotuv,
            "board_thickness_id": board,
            "paper_thickness_id": paper,
            "size_id": size,
            "rate": rate,
            "stage": "Design",
            "order_qr": qr_b64,
        }

        push("orders", data)

        pdf_path = generate_order_pdf(data, qr_b64)
        with open(pdf_path, "rb") as f:
            st.session_state["last_order_pdf"] = f.read()
        os.unlink(pdf_path) # Clean up temporary PDF

        st.session_state["last_qr"] = qr_b64
        st.session_state["last_order_id"] = order_id
        st.session_state["last_whatsapp"] = get_whatsapp_link(final_phone_input, order_id, final_customer_input)
        st.session_state["last_tracking"] = f"https://srppackaging.com/tracking.html?id={order_id}"
        st.session_state["order_created_flag"] = True

        # Send Email if needed
        if final_email_input:
            html_email = f"""
            <h2>Your Order {order_id} is Created</h2>
            <p>Hello {final_customer_input},</p>
            <p>Your order has been successfully created.</p>
            <p><b>Track your order here:</b></p>
            <p><a href="{st.session_state['last_tracking']}">{st.session_state['last_tracking']}</a></p>
            """
            send_gmail(final_email_input, f"Order {order_id} Created", html_email)

        st.rerun()


# ---------------------------------------------------
# SUCCESS BLOCK
# ---------------------------------------------------
if st.session_state.get("order_created_flag"):

    st.success(f"🎉 Order {st.session_state['last_order_id']} Created Successfully!")

    col_down, col_wa = st.columns(2)
    
    with col_down:
        st.download_button(
            label="📄 Download Order PDF",
            data=st.session_state["last_order_pdf"],
            file_name=f"{st.session_state['last_order_id']}_order.pdf",
            mime="application/pdf",
            use_container_width=True
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
    
    st.image(base64.b64decode(st.session_state["last_qr"]), caption="QR Code for Tracking", width=200)

    # Function to clear state and start new order
    def clear_state_and_rerun():
        for key in ["customer_name_final", "customer_phone_final", "customer_email_final", "order_created_flag", "last_order_pdf", "last_qr"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.button("📦 Start New Order", on_click=clear_state_and_rerun)
