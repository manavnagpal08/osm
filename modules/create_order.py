import streamlit as st
from firebase import read, push
from utils import generate_order_id
from datetime import date
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

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

GMAIL_USER = "yourgmail@gmail.com"
GMAIL_PASS = "your_app_password"

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
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_file.name, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, y, "Shree Ram Packers – Order Confirmation")
    y -= 30
    c.line(40, y, width - 40, y)
    y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Order ID: {data['order_id']}")
    y -= 40

    c.setFont("Helvetica", 12)
    for label, value in [
        ("Customer", data["customer"]),
        ("Phone", data["customer_phone"]),
        ("Email", data["customer_email"]),
        ("Order Type", data["type"]),
        ("Product Type", data["product_type"]),
        ("Priority", data["priority"]),
        ("Quantity", data["qty"]),
        ("Received", data["received"]),
        ("Due", data["due"]),
        ("Advance?", data["advance"]),
        ("Product Description", data["item"]),
        ("Foil ID", data["foil_id"]),
        ("Spot UV ID", data["spotuv_id"]),
        ("Board Thickness ID", data["board_thickness_id"]),
        ("Paper Thickness ID", data["paper_thickness_id"]),
        ("Size ID", data["size_id"]),
        ("Rate", data["rate"]),
    ]:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 12)
        c.drawString(200, y, str(value))
        y -= 22
        if y < 100:
            c.showPage()
            y = height - 40

    qr_img = base64.b64decode(qr_b64)
    qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_temp.write(qr_img)
    qr_temp.close()
    c.drawImage(qr_temp.name, width - 180, 80, width=130, height=130)

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(40, 40, "Generated automatically by OMS – Shree Ram Packers")

    c.save()
    return temp_file.name

# ---------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------
if "role" not in st.session_state:
    st.session_state["role"] = "design"

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission.")
    st.stop()

# ---------------------------------------------------
# UI
# ---------------------------------------------------
st.title("📦 Create New Manufacturing Order")

all_orders = read("orders") or {}
customer_list = sorted(list(set(
    o.get("customer", "").strip() for o in all_orders.values() if isinstance(o, dict)
)))

# ---------------------------------------------------
# STEP 1 – CUSTOMER
# ---------------------------------------------------
box = st.container(border=True)
with box:
    st.subheader("1️⃣ Customer Information")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        order_type = st.radio("Order Type", ["New Order 🆕", "Repeat Order 🔄"], horizontal=True)
        order_type_simple = "New" if order_type.startswith("New") else "Repeat"

    with col2:
        # Persist new order inputs so Streamlit doesn't clear them
        customer_input = st.session_state.get("customer_input", "")
        customer_phone_input = st.session_state.get("customer_phone_input", "")
        customer_email_input = st.session_state.get("customer_email_input", "")

        if order_type_simple == "New":
            customer_input = st.text_input("Customer Name (Required)", value=customer_input)
            st.session_state["customer_input"] = customer_input

            customer_phone_input = st.text_input("Customer Phone (Required)", value=customer_phone_input)
            st.session_state["customer_phone_input"] = customer_phone_input

            customer_email_input = st.text_input("Customer Email", value=customer_email_input)
            st.session_state["customer_email_input"] = customer_email_input

        else:
            selected = st.selectbox("Select Existing Customer", ["Select"] + customer_list)

            if selected != "Select":
                customer_input = selected.strip()

                cust_orders = [
                    o for o in all_orders.values()
                    if o.get("customer") == customer_input
                ]

                if cust_orders:
                    latest = sorted(
                        cust_orders,
                        key=lambda x: x.get("received", "0000"),
                        reverse=True
                    )[0]

                    customer_phone_input = latest.get("customer_phone", "")
                    customer_email_input = latest.get("customer_email", "")

            customer_phone_input = st.text_input("Phone", customer_phone_input)
            customer_email_input = st.text_input("Email", customer_email_input)

# ---------------------------------------------------
# STEP 2 – PREVIOUS ORDER AUTOFILL
# ---------------------------------------------------
previous_order = None

if order_type_simple == "Repeat" and customer_input:
    cust_orders = [
        o for o in all_orders.values()
        if o.get("customer") == customer_input
    ]

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order")
        options = [f"{o['order_id']} — {o['item']}" for o in cust_orders]
        sel = st.selectbox("Choose", ["--- Select ---"] + options)

        if sel != "--- Select ---":
            sel_id = sel.split("—")[0].strip()
            for o in cust_orders:
                if o["order_id"] == sel_id:
                    previous_order = o
                    st.success("Auto-fill applied!")
                    break

# ---------------------------------------------------
# STEP 3 – MAIN FORM
# ---------------------------------------------------
with st.form("order_form", clear_on_submit=True):

    st.subheader("3️⃣ Order Specification")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = previous_order or {}

    col1, col2, col3 = st.columns(3)

    with col1:
        product_type = st.selectbox(
            "Product Type", ["Bag", "Box"],
            index=["Bag", "Box"].index(prev.get("product_type", "Bag"))
        )

    with col2:
        qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 100)))

    with col3:
        priority = st.selectbox(
            "Priority", ["High", "Medium", "Low"],
            index=["High", "Medium", "Low"].index(prev.get("priority", "Medium"))
        )

    item = st.text_area("Product Description", value=prev.get("item", ""))

    receive_date = st.date_input("Received Date", value=date.today())
    due_date = st.date_input("Due Date", value=date.today())

    advance = st.radio("Advance Received?", ["Yes", "No"])

    board = st.text_input("Board Thickness ID", value=prev.get("board_thickness_id", ""))
    foil = st.text_input("Foil ID", value=prev.get("foil_id", ""))
    spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id", ""))
    paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id", ""))
    size = st.text_input("Size ID", value=prev.get("size_id", ""))

    rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate", 0.0)))
    total_value = qty * rate
    st.metric("Total Value", f"₹{total_value:,.2f}")

    submitted = st.form_submit_button("🚀 Create Order")

    if submitted:

        customer = customer_input.strip()
        customer_phone = customer_phone_input.strip()
        customer_email = customer_email_input.strip()

        if not customer:
            st.error("⚠️ Customer Name is required.")
            st.stop()

        if not customer_phone:
            st.error("⚠️ Customer Phone Number is required.")
            st.stop()

        if len("".join(filter(str.isdigit, customer_phone))) < 10:
            st.error("⚠️ Enter a valid phone number.")
            st.stop()

        data = {
            "order_id": order_id,
            "customer": customer,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "type": order_type_simple,
            "product_type": product_type,
            "priority": priority,
            "item": item,
            "qty": qty,
            "received": str(receive_date),
            "due": str(due_date),
            "advance": advance,
            "foil_id": foil,
            "spotuv_id": spotuv,
            "board_thickness_id": board,
            "paper_thickness_id": paper,
            "size_id": size,
            "rate": rate,
            "stage": "Design",
        }

        push("orders", data)

        qr_b64 = generate_qr_base64(order_id)
        pdf_path = generate_order_pdf(data, qr_b64)

        with open(pdf_path, "rb") as f:
            st.session_state["last_order_pdf"] = f.read()

        st.session_state["last_qr"] = qr_b64
        st.session_state["last_order_id"] = order_id
        st.session_state["last_whatsapp"] = get_whatsapp_link(customer_phone, order_id, customer)
        st.session_state["last_tracking"] = f"https://srppackaging.com/tracking.html?id={order_id}"

        if customer_email:
            html_email = f"""
            <h2>Your Order {order_id} is Created</h2>
            <p>Hello {customer},</p>
            <p>Your order has been successfully created.</p>
            <p><b>Track your order here:</b></p>
            <p><a href="{st.session_state['last_tracking']}">{st.session_state['last_tracking']}</a></p>
            """
            send_gmail(customer_email, f"Order {order_id} Created", html_email)

        st.session_state["order_created_flag"] = True
        st.rerun()

# ---------------------------------------------------
# SUCCESS BLOCK (OUTSIDE FORM)
# ---------------------------------------------------
if st.session_state.get("order_created_flag"):

    st.success(f"🎉 Order {st.session_state['last_order_id']} Created Successfully!")

    st.download_button(
        label="📄 Download Order PDF",
        data=st.session_state["last_order_pdf"],
        file_name=f"{st.session_state['last_order_id']}_order.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

    st.image(base64.b64decode(st.session_state["last_qr"]), width=200)

    st.markdown(f"[💬 Send via WhatsApp]({st.session_state['last_whatsapp']})")

    st.balloons()

    st.session_state["order_created_flag"] = False
