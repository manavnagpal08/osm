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
from fpdf import FPDF 

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

# Gmail credentials (use app password)
GMAIL_USER = "yourgmail@gmail.com"
GMAIL_PASS = "your_app_password"


# ---------------------------------------------------
# QR CODE GENERATOR (Returns Base64 string for HTML/display)
# ---------------------------------------------------
def generate_qr_base64(order_id: str) -> str:
    """Generates QR code for tracking URL and returns it as a Base64 encoded string."""
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
def get_whatsapp_link(phone: str, order_id: str, customer: str) -> str:
    """Generates a WhatsApp link with a pre-filled message, robustly handling phone input."""
    
    if not isinstance(phone, str):
        try:
            phone = str(phone)
        except:
            phone = ""

    clean_phone = "".join(filter(str.isdigit, phone))
    
    if clean_phone and not clean_phone.startswith("91") and len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    elif len(clean_phone) < 10:
        clean_phone = "" 

    tracking_url = f"https://srppackaging.com/tracking.html?id={order_id}"

    message = (
        f"Hello {customer}, your order {order_id} is created successfully!\n\n"
        f"Track your order live here:\n{tracking_url}\n\n"
        f"Thank kindness for choosing Shree Ram Packers!"
    )

    encoded = urllib.parse.quote(message)

    return f"https://wa.me/{clean_phone}?text={encoded}"


# ---------------------------------------------------
# SEND EMAIL
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
# PDF GENERATOR CLASS AND FUNCTION
# ---------------------------------------------------
class PDF(FPDF):
    def header(self):
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
        self.set_text_color(100, 100, 100)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        self.set_text_color(0, 0, 0)

    def chapter_body(self, data: dict):
        self.set_font('Arial', '', 10)
        col_width = 60
        for key, value in data.items():
            self.set_font('Arial', 'B', 10)
            self.cell(col_width, 6, f"{key}:", 0, 0, 'L')
            self.set_font('Arial', '', 10)
            self.multi_cell(0, 6, str(value).encode('latin-1', 'replace').decode('latin-1'), 0, 'L')
        self.ln(5)

def create_order_pdf(data: dict) -> bytes:
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
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
    
    pdf.chapter_title("Manufacturing IDs")
    pdf.chapter_body({
        "Foil ID": data['foil_id'],
        "Spot UV ID": data['spotuv_id'],
        "Board Thickness ID": data['board_thickness_id'], 
        "Paper Thickness ID": data['paper_thickness_id'],
        "Size ID": data['size_id'],
    })
    
    pdf.chapter_title("Live Tracking QR Code")
    qr_b64 = generate_qr_base64(data['order_id'])
    qr_img_data = base64.b64decode(qr_b64)
    with io.BytesIO(qr_img_data) as img_io:
        pdf.image(img_io, x=80, y=pdf.get_y(), w=40, type='PNG') 
    pdf.ln(50)
    
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

customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() 
    if isinstance(o, dict) and o.get("customer")
)))

if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None


# =====================================================
# STEP 1 – ORDER TYPE & CUSTOMER (FIXED Variable Overwriting Bug 🔥)
# =====================================================
box = st.container(border=True)

# Initialize input variables
customer_input = ""
customer_phone_input = ""
customer_email_input = ""

# Initialize logic/display variables
customer = ""
customer_phone = ""
customer_email = ""


with box:
    st.subheader("1️⃣ Order Type & Customer")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        order_type = st.radio("Order Type", ["New Order 🆕", "Repeat Order 🔄"], horizontal=True)
        order_type_simple = "New" if order_type.startswith("New") else "Repeat"

    with col2:
        if order_type_simple == "New":
            # Use *_input variables here
            customer_input = st.text_input("Customer Name **(Mandatory)**", key="new_customer_name")
            customer_phone_input = st.text_input("Customer Phone **(Mandatory)**", key="new_customer_phone")
            customer_email_input = st.text_input("Customer Email", key="new_customer_email")

        else:
            # Repeat Order Logic
            selected_customer = st.selectbox("Select Existing Customer", ["--- Select Customer ---"] + customer_list, key="repeat_customer_select")
            
            if selected_customer != "--- Select Customer ---":
                customer = selected_customer # Assign to the logic variable for use in Step 2

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
                
                # UI enhancement for auto-fill data
                st.info(f"Phone: **{customer_phone if customer_phone else 'N/A'}** (Auto-filled)")
                st.caption(f"Email: {customer_email if customer_email else 'N/A'}")
                
                if not customer_phone:
                    st.warning("Customer phone number missing from the last order in database. Cannot send WhatsApp link.")

            else:
                 customer = "" # Ensure logic variable is clear if nothing is selected


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
        st.caption("This will fill the product details in Step 3.")

        sorted_orders = sorted(
            cust_orders.values(),
            key=lambda o: o.get("received", "0000"),
            reverse=True
        )

        options = [f"{o['order_id']} — {o['item']}" for o in sorted_orders]

        sel = st.selectbox("Choose Previous Order Details", ["--- Select Order ---"] + options, key="auto_fill_select")

        if sel != "--- Select Order ---":
            sel_id = sel.split("—")[0].strip()
            for o in sorted_orders:
                if o["order_id"] == sel_id:
                    previous_order = o
                    st.session_state["previous_order"] = previous_order
                    st.success("Auto-fill applied! Scroll to Step 3 to review/edit.")
                    break
        else:
            st.session_state["previous_order"] = None # Clear previous if 'Select Order' is chosen


# =====================================================
# STEP 3 — MAIN FORM
# =====================================================
form_status = st.empty() 

with st.form("order_form", clear_on_submit=True):

    st.subheader("3️⃣ Order Specification Form")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = st.session_state["previous_order"] or {} 

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
    
    board_thickness = st.text_input("Board Thickness ID", value=prev.get("board_thickness_id","")) 
    
    paper = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id",""))
    size = st.text_input("Size ID", value=prev.get("size_id",""))

    rate = st.number_input("Unit Rate ₹", min_value=0.0, value=float(prev.get("rate",0.0)))
    total_value = qty * rate
    st.metric("Total Value", f"₹{total_value:,.2f}")

    submitted = st.form_submit_button("🚀 Create Order", type="primary")

    if submitted:
        # ---------------------------------
        # Step 2: Assign Input Variables to Logic Variables (THE FIX 🔥)
        # ---------------------------------
        if order_type_simple == "New":
            customer = customer_input.strip()
            customer_phone = customer_phone_input.strip()
            customer_email = customer_email_input.strip()
        # For Repeat, 'customer', 'customer_phone', 'customer_email' are already set above 
        # (or are empty if '--- Select Customer ---' was chosen).

        # ---------------------------------
        # VALIDATION 
        # ---------------------------------
        validation_error = False
        
        # 1. Customer Name Check
        if not customer:
            form_status.error("❌ Customer Name is mandatory. Please enter a name or select an existing customer.")
            validation_error = True
        
        # 2. Customer Phone Check
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
            "board_thickness_id": board_thickness,
            "paper_thickness_id": paper,
            "size_id": size,
            "rate": rate,
            "stage": "Design",
        }

        push("orders", data)
        form_status.success("🎉 Order Created Successfully!")


        # ---------------------------------
        # POST-SUBMISSION ACTIONS
        # ---------------------------------
        
        final_phone = data["customer_phone"]
        
        qr_b64 = generate_qr_base64(order_id)
        whatsapp_link = get_whatsapp_link(final_phone, order_id, customer) 
        
        # Email functionality
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
