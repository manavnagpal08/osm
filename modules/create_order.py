import streamlit as st
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



# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

GMAIL_USER = "yourgmail@gmail.com"
GMAIL_PASS = "your_app_password"

if "order_created_flag" not in st.session_state:
    st.session_state["order_created_flag"] = False


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
        server = smtpltp.SMTP_SSL("smtp.gmail.com", 465)
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, to, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False



# ---------------------------------------------------
# PDF GENERATOR (UNCHANGED)
# ---------------------------------------------------
def generate_order_pdf(data, qr_b64):
    logo_path = "srplogo.png"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
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

    y -= 20

    # Order Info
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y, "Order Details")
    y -= 35

    for label, value in [
        ("Product Type", data["product_type"]),
        ("Category", data["category"]),
        ("Priority", data["priority"]),
        ("Quantity", data["qty"]),
        ("Rate (₹)", data["rate"]),
        ("Advance Received", data["advance"]),
        ("Board Thickness", data["board_thickness_id"]),
        ("Paper Thickness", data["paper_thickness_id"]),
        ("Size ID", data["size_id"]),
        ("Foil", data["foil_id"]),
        ("Spot UV", data["spotuv_id"]),
        ("Description", data["item"]),
    ]:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(x_margin + 180, y, str(value))
        y -= 18

    # QR
    y -= 30
    qr_img = base64.b64decode(qr_b64)
    qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_temp.write(qr_img)
    qr_temp.close()
    c.drawImage(qr_temp.name, width - 180, y, width=130, height=130)

    c.save()
    return temp_file.name



# ---------------------------------------------------
# LOAD ORDERS
# ---------------------------------------------------
st.title("📦 Create New Manufacturing Order")

all_orders = read("orders") or {}
customer_list = sorted({
    o.get("customer", "").strip()
    for o in all_orders.values()
    if isinstance(o, dict)
})



# ---------------------------------------------------
# LOAD PRODUCT CATEGORIES
# ---------------------------------------------------
categories = read("product_categories") or {}

default_categories = {
    "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
    "Bag": ["Paper Bags", "SOS Envelopes"]
}

for t in default_categories:
    if t not in categories:
        categories[t] = default_categories[t]



# ---------------------------------------------------
# CATEGORY ADMIN PANEL
# ---------------------------------------------------
st.subheader("⚙️ Manage Product Categories")

with st.expander("Add New Category"):
    type_choice = st.selectbox("Select Product Type", ["Box", "Bag"])
    new_cat = st.text_input("New Category Name")

    if st.button("Add Category"):
        if new_cat.strip():
            if new_cat not in categories[type_choice]:
                categories[type_choice].append(new_cat)
                update("product_categories", categories)
                st.success("Category added successfully!")
                st.rerun()
            else:
                st.warning("Category already exists.")



# ---------------------------------------------------
# CUSTOMER BLOCK
# ---------------------------------------------------
box = st.container(border=True)
with box:
    st.subheader("1️⃣ Customer Information")
    st.divider()

    customer_input = st.text_input("Customer Name (Required)")
    customer_phone_input = st.text_input("Customer Phone (Required)")
    customer_email_input = st.text_input("Customer Email")



# ---------------------------------------------------
# REPEAT ORDER AUTOFILL
# ---------------------------------------------------
previous_order = None

cust_orders = [
    o for o in all_orders.values()
    if o.get("customer") == customer_input
]

if cust_orders:
    st.subheader("Select Previous Order (Optional)")
    options = [f"{o['order_id']} — {o.get('item','')}" for o in cust_orders]
    sel = st.selectbox("Choose", ["--- Select ---"] + options)

    if sel != "--- Select ---":
        sel_id = sel.split("—")[0].strip()
        previous_order = next((o for o in cust_orders if o["order_id"] == sel_id), None)
        st.success("Auto-fill applied!")



# ---------------------------------------------------
# ORDER FORM
# ---------------------------------------------------
with st.form("order_form"):

    st.subheader("3️⃣ Order Specification")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = previous_order or {}

    # Dates (IST)
    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(IST).time()

    receive_date = st.date_input("📥 Received Date", value=date.today())
    due_date = st.date_input("📤 Due Date", value=date.today())

    receive_dt = datetime.combine(receive_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")
    due_dt = datetime.combine(due_date, now_ist).strftime("%Y-%m-%d %H:%M:%S IST")

    # Product Type
    product_type = st.selectbox(
        "Product Type (Select First)",
        ["Bag", "Box"],
        index=["Bag", "Box"].index(prev.get("product_type", "Bag"))
    )

    # Product Category — show only AFTER selecting product type
    category = None
    if product_type:
        category_list = categories.get(product_type, [])

        if category_list:
            category = st.selectbox(
                "Product Category",
                category_list,
                index=category_list.index(prev.get("category", category_list[0]))
                if prev.get("category") in category_list else 0
            )
        else:
            st.warning(f"No categories found for {product_type}. Add categories above.")

    col1, col2, col3 = st.columns(3)
    with col1:
        qty = st.number_input("Quantity", min_value=1, value=int(prev.get("qty", 1)))
    with col2:
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    with col3:
        advance = st.radio("Advance Received?", ["Yes", "No"])

    item = st.text_area("Product Description", value=prev.get("item", ""))

    # IDs
    board = st.text_input("Board Thickness ID", value=prev.get("board_thickness_id", ""))
    paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id", ""))
    size = st.text_input("Size ID", value=prev.get("size_id", ""))

    # Foil / Spot UV YES/NO
    foil = st.radio("Foil Required?", ["No", "Yes"])
    spotuv = st.radio("Spot UV Required?", ["No", "Yes"])

    rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate", 0)))
    total_value = qty * rate
    st.metric("Total Value", f"₹{total_value:,}")

    submitted = st.form_submit_button("🚀 Create Order")

    if submitted:

        if not customer_input:
            st.error("Customer Name required")
            st.stop()
        if not customer_phone_input:
            st.error("Phone required")
            st.stop()

        qr_b64 = generate_qr_base64(order_id)

        data = {
            "order_id": order_id,
            "customer": customer_input,
            "customer_phone": customer_phone_input,
            "customer_email": customer_email_input,
            "product_type": product_type,
            "category": category if category else "",
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
            st.session_state["last_order_pdf"] = f.read()

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

    st.success(f"🎉 Order {st.session_state['last_order_id']} Created Successfully!")

    st.download_button(
        label="📄 Download Order PDF",
        data=st.session_state["last_order_pdf"],
        file_name=f"{st.session_state['last_order_id']}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    st.image(base64.b64decode(st.session_state["last_qr"]), width=180)

    st.markdown(f"[💬 Send via WhatsApp]({st.session_state['last_whatsapp']})")
