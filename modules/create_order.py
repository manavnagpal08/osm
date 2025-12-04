import streamlit as st
from firebase import read, push, update
from utils import generate_order_id
from datetime import date, datetime, timezone, timedelta
import qrcode, base64, io, tempfile, urllib.parse, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")


# ----------------------------------------------------------------
# QR GENERATOR
# ----------------------------------------------------------------
def generate_qr_base64(order_id):
    url = f"https://srppackaging.com/tracking.html?id={order_id}"
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ----------------------------------------------------------------
# WHATSAPP LINK
# ----------------------------------------------------------------
def get_whatsapp(phone, order_id, customer):
    phone = "".join(filter(str.isdigit, phone))
    if not phone.startswith("91"):
        phone = "91" + phone

    url = f"https://srppackaging.com/tracking.html?id={order_id}"

    msg = urllib.parse.quote(
        f"Hello {customer}, your order {order_id} has been created.\nTrack here:\n{url}\n\nShree Ram Packers"
    )

    return f"https://wa.me/{phone}?text={msg}"


# ----------------------------------------------------------------
# PDF GENERATOR
# ----------------------------------------------------------------
def generate_order_pdf(data, qr_b64):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp.name, pagesize=A4)

    y = 800
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, y, "Shree Ram Packers")
    y -= 50

    c.setFont("Helvetica", 12)
    for k, v in data.items():
        if k == "order_qr": continue
        c.drawString(40, y, f"{k}: {v}")
        y -= 18

    qr_bytes = base64.b64decode(qr_b64)
    qr_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_img.write(qr_bytes)
    qr_img.close()

    c.drawImage(qr_img.name, 400, 100, width=140, height=140)
    c.save()
    return temp.name


# -------------------------------------------------
# LOAD ORDERS
# -------------------------------------------------
orders = read("orders") or {}
customer_list = sorted({o.get("customer", "") for o in orders.values() if isinstance(o, dict)})

# -------------------------------------------------
# LOAD PRODUCT CATEGORIES
# -------------------------------------------------
categories = read("product_categories") or {
    "Box": ["Rigid Box", "Folding Box", "Mono Cartons"],
    "Bag": ["Paper Bags", "SOS Envelopes"]
}


# -------------------------------------------------
# CATEGORY ADMIN
# -------------------------------------------------
st.subheader("⚙️ Manage Product Categories")
with st.expander("Add Category"):
    type_choice = st.selectbox("Product Type", ["Box", "Bag"])
    new_cat = st.text_input("New Category Name")

    if st.button("Add Category"):
        if new_cat.strip():
            if new_cat not in categories[type_choice]:
                categories[type_choice].append(new_cat)
                update("product_categories", categories)
                st.success("Category added!")
                st.rerun()
            else:
                st.warning("Category already exists.")


# -------------------------------------------------
# CUSTOMER DETAILS
# -------------------------------------------------
st.subheader("1️⃣ Customer Information")

customer = st.text_input("Customer Name (Required)")
phone = st.text_input("Customer Phone (Required)")
email = st.text_input("Customer Email")


# -------------------------------------------------
# PREVIOUS ORDER AUTOFILL
# -------------------------------------------------
prev_order = None
cust_orders = [o for o in orders.values() if o.get("customer") == customer]

if cust_orders:
    st.subheader("Previous Order (Optional)")
    opts = [f"{o['order_id']} — {o.get('item','')}" for o in cust_orders]
    selected = st.selectbox("Select", ["---"] + opts)

    if selected != "---":
        oid = selected.split("—")[0].strip()
        prev_order = next(o for o in cust_orders if o["order_id"] == oid)
        st.success("Auto-fill Applied!")


# -------------------------------------------------
# ORDER FORM
# -------------------------------------------------
st.subheader("3️⃣ Order Specification")

with st.form("order_form"):

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    now = datetime.now(timezone(timedelta(hours=5, 30))).time()
    recv_date = st.date_input("Received Date", date.today())
    due_date = st.date_input("Due Date", date.today())

    recv_dt = f"{recv_date} {now} IST"
    due_dt = f"{due_date} {now} IST"

    # ---------------------------
    # PRODUCT TYPE (NO AUTOSELECT)
    # ---------------------------
    if "selected_product_type" not in st.session_state:
        st.session_state.selected_product_type = "Select Product Type"

    product_type = st.selectbox(
        "Product Type",
        ["Select Product Type", "Bag", "Box"],
        index=["Select Product Type", "Bag", "Box"].index(st.session_state.selected_product_type),
    )

    # Detect change
    if product_type != st.session_state.selected_product_type:
        st.session_state.selected_product_type = product_type
        st.session_state.selected_category = None
        st.rerun()

    # ---------------------------
    # PRODUCT CATEGORY (SHOW ONLY AFTER TYPE)
    # ---------------------------
    category = ""

    if st.session_state.selected_product_type in ["Bag", "Box"]:
        cat_list = categories.get(st.session_state.selected_product_type, [])

        if cat_list:
            category = st.selectbox(
                "Product Category",
                cat_list,
                index=0 if st.session_state.selected_category is None else
                      cat_list.index(st.session_state.selected_category)
            )

            if category != st.session_state.get("selected_category"):
                st.session_state.selected_category = category

        else:
            st.warning("No categories found. Add some above.")

    # -------------------------------------------
    # REMAINING ORDER FIELDS
    # -------------------------------------------
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
    st.metric("Total Value", f"₹{qty * rate:,}")

    submit = st.form_submit_button("🚀 Create Order")

    if submit:

        if product_type == "Select Product Type":
            st.error("Please select a Product Type!")
            st.stop()

        if not st.session_state.selected_category:
            st.error("Please select a Product Category!")
            st.stop()

        qr = generate_qr_base64(order_id)

        data = {
            "order_id": order_id,
            "customer": customer,
            "customer_phone": phone,
            "customer_email": email,
            "product_type": st.session_state.selected_product_type,
            "category": st.session_state.selected_category,
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
            "stage": "Design",
            "order_qr": qr
        }

        push("orders", data)

        pdf_path = generate_order_pdf(data, qr)
        with open(pdf_path, "rb") as f:
            st.session_state["pdf"] = f.read()

        st.session_state["oid"] = order_id
        st.session_state["wa"] = get_whatsapp(phone, order_id, customer)
        st.session_state["qr"] = qr
        st.session_state["ok"] = True

        st.rerun()


# -------------------------------------------------
# SUCCESS VIEW
# -------------------------------------------------
if st.session_state.get("ok"):

    st.success(f"🎉 Order {st.session_state['oid']} Created Successfully!")

    st.download_button(
        "📄 Download PDF",
        st.session_state["pdf"],
        file_name=f"{st.session_state['oid']}.pdf",
        mime="application/pdf"
    )

    st.image(base64.b64decode(st.session_state["qr"]), width=160)

    st.markdown(f"[💬 Send via WhatsApp]({st.session_state['wa']})")
