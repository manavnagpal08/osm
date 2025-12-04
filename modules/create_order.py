import streamlit as st
from firebase import read, push, update
from utils import generate_order_id
from datetime import date, datetime, timezone, timedelta
import qrcode, base64, io, smtplib, urllib.parse, tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")


# --------------------------- QR MAKER -----------------------------
def generate_qr_base64(order_id):
    url = f"https://srppackaging.com/tracking.html?id={order_id}"
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# --------------------------- WHATSAPP -----------------------------
def get_whatsapp(phone, order_id, customer):
    phone = "".join(filter(str.isdigit, phone))
    if not phone.startswith("91"):
        phone = "91" + phone
    url = f"https://srppackaging.com/tracking.html?id={order_id}"
    msg = urllib.parse.quote(
        f"Hello {customer}, your order {order_id} is created.\nTrack here:\n{url}\n\nShree Ram Packers"
    )
    return f"https://wa.me/{phone}?text={msg}"


# --------------------------- PDF MAKER ----------------------------
def generate_order_pdf(data, qr_b64):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp.name, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "Shree Ram Packers")
    y -= 40

    c.setFont("Helvetica", 12)
    for k, v in data.items():
        if k == "order_qr":
            continue
        c.drawString(40, y, f"{k}: {v}")
        y -= 18

    qr_bytes = base64.b64decode(qr_b64)
    qr_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_file.write(qr_bytes)
    qr_file.close()
    c.drawImage(qr_file.name, width - 180, 100, width=130, height=130)

    c.save()
    return temp.name


# --------------------------- LOAD DATA ----------------------------
orders = read("orders") or {}
customers = sorted({o.get("customer", "") for o in orders.values() if isinstance(o, dict)})

# Load categories
categories = read("product_categories") or {
    "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
    "Bag": ["Paper Bags", "SOS Envelopes"]
}


# --------------------------- CATEGORY ADMIN ------------------------
st.subheader("⚙️ Manage Categories")
with st.expander("Add Category"):
    t = st.selectbox("Product Type", ["Box", "Bag"])
    new = st.text_input("New Category Name")
    if st.button("Add"):
        new = new.strip()
        if new and new not in categories[t]:
            categories[t].append(new)
            update("product_categories", categories)
            st.success("Category Added!")
            st.rerun()


# --------------------------- CUSTOMER ------------------------------
st.subheader("1️⃣ Customer Information")
customer = st.text_input("Customer Name")
phone = st.text_input("Customer Phone")
email = st.text_input("Customer Email")


# --------------------------- REPEAT ORDER ---------------------------
prev_order = None
cust_orders = [o for o in orders.values() if o.get("customer") == customer]

if cust_orders:
    st.subheader("Previous Order")
    opts = [f"{o['order_id']} — {o.get('item','')}" for o in cust_orders]
    sel = st.selectbox("Select", ["---"] + opts)
    if sel != "---":
        oid = sel.split("—")[0].strip()
        prev_order = next(o for o in cust_orders if o["order_id"] == oid)
        st.success("Auto-fill applied!")


# --------------------------- ORDER FORM ----------------------------
st.subheader("3️⃣ Order Details")

with st.form("order_form"):
    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST).time()

    recv_date = st.date_input("Received Date", value=date.today())
    due_date = st.date_input("Due Date", value=date.today())

    recv_dt = datetime.combine(recv_date, now).strftime("%Y-%m-%d %H:%M:%S IST")
    due_dt = datetime.combine(due_date, now).strftime("%Y-%m-%d %H:%M:%S IST")

    # ---------------- PRODUCT TYPE ----------------
    product_type = st.selectbox("Product Type", ["Bag", "Box"])

    # ---------------- CATEGORY (FIXED) ----------------
    # category appears ONLY AFTER product type selection
    if product_type:
        cat_list = categories.get(product_type, [])
        if not cat_list:
            st.warning("No categories found for this type. Add categories above.")
            category = ""
        else:
            category = st.selectbox("Product Category", cat_list)
    else:
        category = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        qty = st.number_input("Quantity", min_value=1)
    with col2:
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    with col3:
        advance = st.radio("Advance Received?", ["Yes", "No"])

    item = st.text_area("Product Description")

    board = st.text_input("Board Thickness ID")
    paper = st.text_input("Paper Thickness ID")
    size = st.text_input("Size ID")

    foil = st.radio("Foil Required?", ["No", "Yes"])
    uv = st.radio("Spot UV Required?", ["No", "Yes"])

    rate = st.number_input("Unit Rate ₹", min_value=0.0)
    total = qty * rate
    st.metric("Total Value", f"₹{total:,}")

    submit = st.form_submit_button("🚀 Create Order")

    if submit:

        data = {
            "order_id": order_id,
            "customer": customer,
            "customer_phone": phone,
            "customer_email": email,
            "product_type": product_type,
            "category": category,
            "qty": qty,
            "priority": priority,
            "item": item,
            "received": recv_dt,
            "due": due_dt,
            "advance": advance,
            "board_thickness_id": board,
            "paper_thickness_id": paper,
            "size_id": size,
            "foil_id": foil,
            "spotuv_id": uv,
            "rate": rate,
            "stage": "Design"
        }

        qr = generate_qr_base64(order_id)
        data["order_qr"] = qr

        push("orders", data)

        pdf_path = generate_order_pdf(data, qr)
        with open(pdf_path, "rb") as f:
            st.session_state["pdf"] = f.read()

        st.session_state["oid"] = order_id
        st.session_state["qr"] = qr
        st.session_state["wa"] = get_whatsapp(phone, order_id, customer)
        st.session_state["ok"] = True

        st.rerun()


# --------------------------- SUCCESS -------------------------------
if st.session_state.get("ok"):

    st.success(f"🎉 Order {st.session_state['oid']} Created!")

    st.download_button(
        "📄 Download PDF",
        st.session_state["pdf"],
        file_name=f"{st.session_state['oid']}.pdf",
        mime="application/pdf"
    )

    st.image(base64.b64decode(st.session_state["qr"]), width=180)

    st.markdown(f"[💬 WhatsApp]({st.session_state['wa']})")
