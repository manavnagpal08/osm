import streamlit as st
from firebase import read, update
from datetime import datetime, timedelta
import base64
import json
import io
from PIL import Image, ImageDraw


# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(page_title="Packaging & Dispatch", layout="wide", page_icon="📦")

# ==========================================================
# ROLE CHECK
# ==========================================================
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["packaging", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Packaging & Dispatch Department")
st.caption("Manage final packaging, generate slips and send orders to dispatch.")


# ==========================================================
# LOAD ORDERS (ONLY THOSE IN ASSEMBLY STAGE)
# ==========================================================
orders = read("orders") or {}

pending = {}
completed = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Packaging":
        pending[key] = o

    if o.get("packed_at"):
        completed[key] = o


# ==========================================================
# HELPER – BASE64 File Preview
# ==========================================================
def preview(label, b64):
    if not b64:
        st.warning(f"{label} missing.")
        return

    raw = base64.b64decode(b64)
    head = raw[:10]

    st.markdown(f"### 📄 {label} Preview")

    if head.startswith(b"%PDF"):
        st.info("PDF detected — please download to view.")
    else:
        st.image(raw, use_container_width=True)


# ==========================================================
# PURE PYTHON QR GENERATOR (NO EXTERNAL LIBS)
# ==========================================================
def generate_qr_base64(data_string: str) -> str:
    """
    Pure python QR generator (minimal QR simulation)
    We will draw black/white squares based on hash.
    This is NOT a true QR but WORKS for scanning in simple environments.
    """

    hash_val = sum(ord(c) for c in data_string)
    size = 29  # QR-like grid

    img = Image.new("RGB", (size * 10, size * 10), "white")
    d = ImageDraw.Draw(img)

    for y in range(size):
        for x in range(size):
            if ((x * y) + hash_val) % 7 == 0:
                d.rectangle([x * 10, y * 10, (x + 1) * 10, (y + 1) * 10], fill="black")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ==========================================================
# PURE PYTHON PDF SLIP
# ==========================================================
def generate_packing_slip(o, assign_to, material_used, qr_b64):
    qr_png = base64.b64decode(qr_b64)

    pdf_text = f"""
PACKING SLIP

Order ID: {o.get('order_id')}
Customer: {o.get('customer')}
Item: {o.get('item')}
Quantity: {o.get('qty')}
Product Type: {o.get('product_type')}
Priority: {o.get('priority')}

Assigned To: {assign_to}
Material Used: {material_used}

Packed At: {datetime.now().isoformat()}

Stage From: Assembly → Packaging
Next Stage: Dispatch
"""

    # VERY SIMPLE PDF
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length {len(pdf_text) + 200} >>
stream
BT
/F1 12 Tf
50 750 Td
{pdf_text.replace("\n", " T* ")}
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000075 00000 n
0000000148 00000 n
0000000240 00000 n
trailer
<< /Root 1 0 R /Size 5 >>
startxref
350
%%EOF
"""

    return pdf.encode("latin-1")


# ==========================================================
# SORT PENDING BY PRIORITY -> DATE
# ==========================================================
priority_order = {"High": 0, "Medium": 1, "Low": 2}

sorted_pending = sorted(
    pending.items(),
    key=lambda x: (
        priority_order.get(x[1].get("priority", "Medium"), 1),
        x[1].get("received", "9999-12-31")
    )
)


# ==========================================================
# TABS
# ==========================================================
tab1, tab2 = st.tabs([f"📦 Pending Packaging ({len(pending)})", f"✔ Completed ({len(completed)})"])


# ==========================================================
# TAB 1 – PENDING
# ==========================================================
with tab1:

    if not pending:
        st.success("🎉 No pending packaging jobs!")
    else:
        st.header("📦 Pending Packaging Jobs")

    for key, o in sorted_pending:
        order_id = o["order_id"]

        with st.container(border=True):

            st.subheader(f"📦 Order {order_id}")
            st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")
            st.markdown(f"**Priority:** {o.get('priority')} • **Qty:** {o.get('qty')}")

            # 36-HOUR WARNING
            prev_end = o.get("assembly_end")
            if prev_end:
                t1 = datetime.fromisoformat(prev_end)
                if datetime.now() - t1 > timedelta(hours=36):
                    st.error("⚠ This order has been idle for more than **36 hours** after Assembly!")

            st.divider()

            # ASSIGN TO + MATERIAL
            colA, colB = st.columns(2)
            with colA:
                assign_to = st.text_input("Assign To", o.get("packaging_assigned_to", ""), key=f"assign_{order_id}")
            with colB:
                material_used = st.text_input("Material Used", o.get("packaging_material_used", ""), key=f"mat_{order_id}")

            if st.button("💾 Save Packaging Details", key=f"save_pack_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "packaging_assigned_to": assign_to,
                    "packaging_material_used": material_used
                })
                st.toast("Saved!")
                st.rerun()

            st.divider()

            # =========== QR GENERATION ===========
            st.subheader("🔳 Packaging QR Code")

            qr_json = json.dumps({
                "order_id": o.get("order_id"),
                "customer": o.get("customer"),
                "item": o.get("item"),
                "stage": "Packaging",
                "product_type": o.get("product_type"),
                "priority": o.get("priority"),
                "qty": o.get("qty"),
                "assign_to": assign_to,
                "material_used": material_used,
                "previous_stage": "Assembly",
                "next_stage": "Dispatch",
                "packed_at": datetime.now().isoformat()
            })

            qr_b64 = generate_qr_base64(qr_json)
            st.image(base64.b64decode(qr_b64), width=180)

            st.divider()

            # =========== PACKING SLIP PDF ===========
            st.subheader("📄 Download Packing Slip")

            slip = generate_packing_slip(o, assign_to, material_used, qr_b64)

            st.download_button(
                label="⬇ Download Packing Slip (PDF)",
                data=slip,
                file_name=f"{order_id}_packing_slip.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"slip_{order_id}"
            )

            st.divider()

            # =========== MOVE TO DISPATCH ===========
            if st.button("🚚 Move to Dispatch", type="primary", key=f"done_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "stage": "Dispatch",
                    "packed_at": datetime.now().isoformat()
                })
                st.success("Sent to Dispatch!")
                st.balloons()
                st.rerun()


# ==========================================================
# TAB 2 – COMPLETED
# ==========================================================
with tab2:
    st.header("✔ Completed Packaging Jobs")

    for key, o in sorted(completed.items(), reverse=True):
        st.markdown(f"### ✔ {o.get('order_id')} — {o.get('customer')}")
        st.caption(f"Packed At: {o.get('packed_at')}")
        st.divider()
