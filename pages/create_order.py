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

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

# Gmail credentials (use app password)
GMAIL_USER = "yourgmail@gmail.com"
GMAIL_PASS = "your_app_password"


# ---------------------------------------------------
# QR CODE GENERATOR (UPDATED FOR NEW TRACKING PAGE)
# ---------------------------------------------------
def generate_qr_base64(order_id: str):
    tracking_url = f"https://yourwebsite.com/tracking.html?id={order_id}"  # UPDATED 🔥

    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(tracking_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------
# WHATSAPP LINK GENERATOR (UPDATED 🔥)
# ---------------------------------------------------
def get_whatsapp_link(phone, order_id, customer):

    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone.startswith("91"):
        clean_phone = "91" + clean_phone

    tracking_url = f"https://yourwebsite.com/tracking.html?id={order_id}"

    message = (
        f"Hello {customer}, your order {order_id} is created successfully!\n\n"
        f"Track your order live here:\n{tracking_url}\n\n"
        f"Thank you for choosing Shree Ram Packers!"
    )

    encoded = urllib.parse.quote(message)

    return f"https://wa.me/{clean_phone}?text={encoded}"


# ---------------------------------------------------
# SEND EMAIL (FREE)
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
# ROLE CHECK
# ---------------------------------------------------
if "role" not in st.session_state:
    st.session_state["role"] = "design"

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission.")
    st.stop()


# ---------------------------------------------------
# PAGE UI
# ---------------------------------------------------
st.title("📦 Create New Manufacturing Order")
st.caption("Effortlessly log new and repeat orders with smart auto-fill capability.")

all_orders = read("orders") or {}

customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None


# =====================================================
# STEP 1 – ORDER TYPE & CUSTOMER
# =====================================================
box = st.container(border=True)

with box:
    st.subheader("1️⃣ Order Type & Customer")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        order_type = st.radio("Order Type", ["New Order 🆕", "Repeat Order 🔄"], horizontal=True)
        order_type_simple = "New" if order_type.startswith("New") else "Repeat"

    with col2:
        customer = None
        customer_phone = ""
        customer_email = ""

        if order_type_simple == "New":
            customer = st.text_input("Customer Name")
            customer_phone = st.text_input("Customer Phone")
            customer_email = st.text_input("Customer Email")

        else:
            selected = st.selectbox("Select Existing Customer", ["Select"] + customer_list)
            if selected != "Select":
                customer = selected

                cust_orders = {
                    k: o for k, o in all_orders.items()
                    if o.get("customer") == customer
                }

                if cust_orders:
                    latest = sorted(
                        cust_orders.values(),
                        key=lambda x: x.get("received", "0000"),
                        reverse=True
                    )[0]

                    customer_phone = latest.get("customer_phone", "")
                    customer_email = latest.get("customer_email", "")

                st.text_input("Phone", customer_phone)
                st.text_input("Email", customer_email)


# =====================================================
# STEP 2 — AUTO-FILL REPEAT
# =====================================================
previous_order = None

if order_type_simple == "Repeat" and customer:
    cust_orders = {
        k: o for k, o in all_orders.items()
        if o.get("customer") == customer
    }

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order to Auto-Fill")

        sorted_orders = sorted(
            cust_orders.values(),
            key=lambda o: o.get("received", "0000"),
            reverse=True
        )

        options = [f"{o['order_id']} — {o['item']}" for o in sorted_orders]

        sel = st.selectbox("Choose", ["--- Select ---"] + options)

        if sel != "--- Select ---":
            sel_id = sel.split("—")[0].strip()
            for o in sorted_orders:
                if o["order_id"] == sel_id:
                    previous_order = o
                    st.success("Auto-fill applied!")
                    break

st.session_state["previous_order"] = previous_order


# =====================================================
# STEP 3 — MAIN FORM
# =====================================================
with st.form("order_form", clear_on_submit=True):

    st.subheader("3️⃣ Order Specification Form")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = previous_order or {}

    col1, col2, col3 = st.columns(3)
    with col1:
        product_type = st.selectbox("Product Type", ["Bag", "Box"], 
                                    index=["Bag","Box"].index(prev.get("product_type","Bag")))
    with col2:
        qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 100)))
    with col3:
        priority = st.selectbox("Priority", ["High","Medium","Low"], 
                                index=["High","Medium","Low"].index(prev.get("priority","Medium")))

    item = st.text_area("Product Description", value=prev.get("item",""))

    receive_date = st.date_input("Received Date", value=date.today())
    due_date = st.date_input("Due Date", value=date.today())

    advance = st.radio("Advance Received?", ["Yes","No"])

    foil = st.text_input("Foil ID", value=prev.get("foil_id",""))
    spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id",""))
    brand = st.text_input("Brand Thickness ID", value=prev.get("brand_thickness_id",""))
    paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id",""))
    size = st.text_input("Size ID", value=prev.get("size_id",""))

    rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate",0.0)))
    total_value = qty * rate
    st.metric("Total Value", f"₹{total_value:,.2f}")

    submitted = st.form_submit_button("🚀 Create Order", type="primary")

    if submitted:

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
            "brand_thickness_id": brand,
            "paper_thickness_id": paper,
            "size_id": size,
            "rate": rate,
            "stage": "Design",
        }

        push("orders", data)

        # ---------------------------------
        # QR CODE + WhatsApp + Email
        # ---------------------------------
        qr_b64 = generate_qr_base64(order_id)
        whatsapp_link = get_whatsapp_link(customer_phone, order_id, customer)
        tracking_link = f"https://srppackaging.com/tracking.html?id={order_id}"

        html_email = f"""
        <h2>Your Order {order_id} is Created</h2>
        <p>Hello {customer},</p>
        <p>Your order has been successfully created.</p>
        <p><b>Track your order</b> here:</p>
        <p><a href="{tracking_link}">{tracking_link}</a></p>
        <p>Thank you!</p>
        """

        if customer_email:
            send_gmail(customer_email, f"Order {order_id} Created", html_email)

        st.success("🎉 Order Created Successfully!")
        st.image(base64.b64decode(qr_b64), width=200)

        st.markdown(f"[💬 Send via WhatsApp]({whatsapp_link})")

        st.balloons()
