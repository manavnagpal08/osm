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
from fpdf import FPDF # New Library for PDF generation

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
    tracking_url = f"https://srppackaging.com/tracking.html?id={order_id}"

    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(tracking_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------
# WHATSAPP LINK GENERATOR
# ---------------------------------------------------
def get_whatsapp_link(phone, order_id, customer):

    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone.startswith("91"):
        clean_phone = "91" + clean_phone

    tracking_url = f"https://srppackaging.com/tracking.html?id={order_id}"

    message = (
        f"Hello {customer}, your order {order_id} is created successfully!\n\n"
        f"Track your order live here:\n{tracking_url}\n\n"
        f"Thank kindness for choosing Shree Ram Packers!"
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
# PDF GENERATOR FUNCTION (NEW 🔥)
# ---------------------------------------------------
class PDF(FPDF):
    def header(self):
        # Logo
        # self.image('logo.png', 10, 8, 33) # Uncomment if you have a logo
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SRP Packaging - Manufacturing Order', 0, 1, 'C')
        self.line(10, 20, 200, 20)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, title, 0, 1, 'L')
        self.set_text_color(100, 100, 100) # grey color
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        self.set_text_color(0, 0, 0) # black color

    def chapter_body(self, data: dict):
        self.set_font('Arial', '', 10)
        col_width = 60
        for key, value in data.items():
            self.set_font('Arial', 'B', 10)
            self.cell(col_width, 6, f"{key}:", 0, 0, 'L')
            self.set_font('Arial', '', 10)
            # Encode to avoid fpdf unicode issues, also stringify all data
            self.multi_cell(0, 6, str(value).encode('latin-1', 'replace').decode('latin-1'), 0, 'L')
        self.ln(5)

def create_order_pdf(data: dict) -> bytes:
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Order ID and Customer Info
    pdf.chapter_title("Order & Customer Details")
    pdf.chapter_body({
        "Order ID": data['order_id'],
        "Customer Name": data['customer'],
        "Phone": data['customer_phone'],
        "Email": data['customer_email'],
        "Order Type": data['type'],
        "Received Date": data['received'],
        "Due Date": data['due'],
    })

    # Product and Financial Info
    pdf.chapter_title("Product Specification & Financials")
    pdf.chapter_body({
        "Product Description": data['item'],
        "Product Type": data['product_type'],
        "Quantity": f"{data['qty']:,}",
        "Unit Rate": f"₹{data['rate']:,.2f}",
        "Total Value": f"₹{data['qty'] * data['rate']:,.2f}",
        "Priority": data['priority'],
        "Advance Received": data['advance'],
    })
    
    # Manufacturing IDs
    pdf.chapter_title("Manufacturing IDs")
    pdf.chapter_body({
        "Foil ID": data['foil_id'],
        "Spot UV ID": data['spotuv_id'],
        "Brand Thickness ID": data['brand_thickness_id'],
        "Paper Thickness ID": data['paper_thickness_id'],
        "Size ID": data['size_id'],
    })
    
    # QR Code for Tracking
    pdf.chapter_title("Live Tracking QR Code")
    qr_b64 = generate_qr_base64(data['order_id'])
    qr_img_data = base64.b64decode(qr_b64)
    with io.BytesIO(qr_img_data) as img_io:
        pdf.image(img_io, x=80, y=pdf.get_y(), w=40)
    pdf.ln(50)
    
    # Convert PDF to bytes
    return pdf.output(dest='S').encode('latin-1')


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

# Safely create customer list, filtering out non-dict entries
customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() 
    if isinstance(o, dict) and o.get("customer")
)))

if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None


# =====================================================
# STEP 1 – ORDER TYPE & CUSTOMER (Updated for validation 🔥)
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
        # Initialize variables before conditional assignment
        customer = ""
        customer_phone = ""
        customer_email = ""

        if order_type_simple == "New":
            # Made customer and phone mandatory with help text
            customer = st.text_input("Customer Name **(Mandatory)**")
            customer_phone = st.text_input("Customer Phone **(Mandatory)**")
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

                st.text_input("Phone", customer_phone, disabled=True)
                st.text_input("Email", customer_email, disabled=True)
                
                # For Repeat Orders, we ensure the phone is available from the latest order
                if not customer_phone:
                    st.warning("Customer phone number missing from the last order. Please update the customer's phone number.")


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
                    st.session_state["previous_order"] = previous_order
                    st.success("Auto-fill applied!")
                    break

st.session_state["previous_order"] = previous_order


# =====================================================
# STEP 3 — MAIN FORM
# =====================================================
# Added a placeholder to display submission status (e.g., validation errors)
form_status = st.empty() 

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
        # ---------------------------------
        # VALIDATION (New 🔥)
        # ---------------------------------
        validation_error = False
        if not customer or customer.strip() == "" or customer == "Select":
            form_status.error("❌ Customer Name is mandatory.")
            validation_error = True
        
        # Clean phone number for validation
        clean_phone = "".join(filter(str.isdigit, customer_phone))
        if not customer_phone or len(clean_phone) < 10:
            form_status.error("❌ Customer Phone is mandatory and must be a valid number (at least 10 digits).")
            validation_error = True
            
        if validation_error:
            st.stop()
            
        # ---------------------------------
        # DATA PUSH
        # ---------------------------------
        data = {
            "order_id": order_id,
            "customer": customer,
            # Ensure we use the non-disabled/validated phone number
            "customer_phone": customer_phone if order_type_simple == "New" else clean_phone, 
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
        
        # Update data for Repeat order if phone was pulled from latest order
        if order_type_simple == "Repeat" and previous_order:
             data["customer_phone"] = previous_order.get("customer_phone", "")
             data["customer_email"] = previous_order.get("customer_email", "")

        push("orders", data)
        form_status.success("🎉 Order Created Successfully!")


        # ---------------------------------
        # POST-SUBMISSION ACTIONS
        # ---------------------------------
        
        # Re-fetch the correct phone number after potential update from Repeat
        final_phone = data["customer_phone"]
        
        qr_b64 = generate_qr_base64(order_id)
        whatsapp_link = get_whatsapp_link(final_phone, order_id, customer)
        tracking_link = f"https://srppackaging.com/tracking.html?id={order_id}"

        html_email = f"""
        <h2>Your Order {order_id} is Created</h2>
        <p>Hello {customer},</p>
        <p>Your order has been successfully created.</p>
        <p><b>Track your order</b> here:</p>
        <p><a href="{tracking_link}">{tracking_link}</a></p>
        <p>Thank you!</p>
        """

        if data["customer_email"]:
            send_gmail(data["customer_email"], f"Order {order_id} Created", html_email)

        st.balloons()
        
        col_res1, col_res2, col_res3 = st.columns([1,1,1])
        
        with col_res1:
            st.subheader("QR Code")
            st.image(base64.b64decode(qr_b64), width=200)
            st.caption(f"Scan for live tracking of **Order {order_id}**")
        
        with col_res2:
            st.subheader("Actions")
            st.markdown(f"[💬 Send Tracking Link via WhatsApp]({whatsapp_link})")
            
            # PDF Download Button (New 🔥)
            pdf_bytes = create_order_pdf(data)
            st.download_button(
                label="📄 Download Order PDF",
                data=pdf_bytes,
                file_name=f"order_{order_id}_{customer}.pdf",
                mime="application/pdf"
            )

        with col_res3:
             st.subheader("Summary")
             st.info(f"Customer: **{customer}**")
             st.info(f"Quantity: **{qty:,}**")
             st.info(f"Total Value: **₹{total_value:,.2f}**")
