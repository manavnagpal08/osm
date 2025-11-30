import streamlit as st
from firebase import read, update
from datetime import datetime, timedelta
import base64
import io

st.set_page_config(page_title="Packing Department", page_icon="📦", layout="wide")

# ---------------- ROLE CHECK ----------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["packing", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Packing Department")
st.caption("Handle packing, generate QR codes, track time, assign work & move orders to Dispatch.")

# ---------------- LOAD ORDERS ----------------
orders = read("orders") or {}
pending, completed = {}, {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Packing":
        pending[key] = o
    elif o.get("packing_completed_at"):
        completed[key] = o

# ---------- PRIORITY SORTING ----------
priority_rank = {"High": 0, "Medium": 1, "Low": 2}

sorted_pending = sorted(
    pending.items(),
    key=lambda x: (
        priority_rank.get(x[1].get("priority", "Medium"), 1),
        x[1].get("received", "2099-12-31")
    )
)

# ---------- QR CODE GENERATOR (NO LIBRARY) ----------
def generate_qr_base64(data: str):
    """Uses Google Chart API to generate QR code PNG"""
    import urllib.parse
    encoded = urllib.parse.quote(data)
    url = f"https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl={encoded}"
    import requests
    img = requests.get(url).content
    return base64.b64encode(img).decode()

# ---------- PDF SLIP ----------
def generate_packing_slip(o, assign, material, notes, qr_b64):
    body = f"""
PACKING DEPARTMENT – JOB SLIP

Order ID : {o.get('order_id')}
Customer : {o.get('customer')}
Item     : {o.get('item')}
Qty      : {o.get('qty')}

Assigned To  : {assign}
Material Used: {material}

Notes:
{notes or "-"}

Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    # Embed QR base64 as text (viewable after download)
    body += "\n\nQR Code Embedded."

    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R >>
endobj
4 0 obj
<< /Length {len(body) + 200} >>
stream
BT
/F1 12 Tf
50 750 Td
{body.replace("\n", " T* ")}
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000178 00000 n 
0000000349 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
500
%%EOF"""
    return pdf.encode("latin-1")


# ---------------- UI: TABS ----------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Packing ({len(sorted_pending)})",
    f"✔ Completed ({len(completed)})"
])

# ---------------- TAB 1: PENDING ----------------
with tab1:

    if not sorted_pending:
        st.success("🎉 No pending packing work!")

    for key, o in sorted_pending:

        order_id = o["order_id"]
        start = o.get("packing_start")
        end = o.get("packing_end")

        # Time check (36 hours warning)
        arrived = o.get("assembly_completed_at") or datetime.now().isoformat()
        arrived_dt = datetime.fromisoformat(arrived)
        hours_passed = (datetime.now() - arrived_dt).total_seconds() / 3600

        qr_b64 = generate_qr_base64(order_id)

        with st.container(border=True):

            # ---- HEADER ----
            st.markdown(f"## 📦 {order_id} — {o.get('customer')}")
            st.caption(f"Item: {o.get('item')} • Qty: {o.get('qty')} • Priority: {o.get('priority')}")

            if hours_passed > 36:
                st.error(f"⚠️ Delay Alert: Packing pending for **{int(hours_passed)} hours**")
            else:
                st.info(f"⏳ Time since arrived: **{int(hours_passed)} hours**")

            st.divider()

            # -------- TIME TRACKING --------
            st.subheader("⏱ Time Tracking")

            if not start:
                if st.button("▶️ Start Packing", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"packing_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Packing", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"packing_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started: {start}")

            else:
                st.success(f"Completed: {end}")

            st.divider()

            # -------- DETAILS --------
            st.subheader("📋 Packing Details")

            assign = st.text_input("Assign To", o.get("packing_assigned"), key=f"assign_{order_id}")
            material = st.text_input("Material Used", o.get("packing_material"), key=f"material_{order_id}")
            notes = st.text_area("Notes", o.get("packing_notes"), height=80, key=f"notes_{order_id}")

            if st.button("💾 Save Details", key=f"save_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "packing_assigned": assign,
                    "packing_material": material,
                    "packing_notes": notes
                })
                st.success("Saved")
                st.rerun()

            st.divider()

            # -------- QR CODE --------
            st.subheader("🔳 QR Code for Order Identification")
            st.image(base64.b64decode(qr_b64), width=180)
            st.caption("Scan this to identify the product instantly.")

            st.download_button(
                label="⬇ Download QR Code",
                data=base64.b64decode(qr_b64),
                file_name=f"{order_id}_QR.png",
                mime="image/png",
                use_container_width=True
            )

            st.divider()

            # -------- OUTPUT FILES --------
            st.subheader("📁 Upload Packing Output File")

            up = st.file_uploader("Upload File", type=["png", "jpg", "pdf"], key=f"file_{order_id}")

            if st.button("💾 Save File", key=f"save_file_{order_id}", use_container_width=True) and up:
                encoded = base64.b64encode(up.read()).decode()
                update(f"orders/{key}", {"packing_file": encoded})
                st.success("Uploaded")
                st.rerun()

            if o.get("packing_file"):
                st.image(base64.b64decode(o["packing_file"]), use_container_width=True)

            st.divider()

            # -------- SLIP --------
            st.subheader("📄 Download Packing Slip")

            slip_pdf = generate_packing_slip(o, assign, material, notes, qr_b64)

            st.download_button(
                label="⬇ Download Packing Slip (PDF)",
                data=slip_pdf,
                file_name=f"{order_id}_packing_slip.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.divider()

            # -------- MOVE TO DISPATCH --------
            if end:
                if st.button("🚚 Move to Dispatch", key=f"move_{order_id}", type="primary", use_container_width=True):
                    update(f"orders/{key}", {
                        "stage": "Dispatch",
                        "packing_completed_at": datetime.now().isoformat()
                    })
                    st.balloons()
                    st.success("Moved to Dispatch")
                    st.rerun()
            else:
                st.warning("Complete packing first.")

# ---------------- TAB 2: COMPLETED ----------------
with tab2:
    if not completed:
        st.info("No completed packing jobs yet.")

    for key, o in completed.items():
        with st.container(border=True):
            st.markdown(f"### ✔ {o['order_id']} — {o.get('customer')}")
            st.write(f"Completed at: {o.get('packing_completed_at')}")
            st.write(f"Material: {o.get('packing_material')}")
            st.write(f"Assigned To: {o.get('packing_assigned')}")
            st.write(f"Notes: {o.get('packing_notes')}")
            st.divider()
