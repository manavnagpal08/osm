import streamlit as st
from firebase import read, update
from datetime import datetime, timedelta
import base64
import io
import qrcode
from typing import Optional, Any, Dict

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
pending: Dict[str, Any] = {}
completed: Dict[str, Any] = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue
    if o.get("stage") == "Packing":
        pending[key] = o
    elif o.get("packing_completed_at"):
        completed[key] = o

# --------- SORT BY PRIORITY ----------
priority_rank = {"High": 0, "Medium": 1, "Low": 2}

sorted_pending = sorted(
    pending.items(),
    key=lambda x: (
        priority_rank.get(x[1].get("priority", "Medium"), 1),
        x[1].get("received", "2099-12-31")
    )
)

# ---------- UTILITIES ----------

def calculate_time_diff(start: Optional[str], end: Optional[str]) -> str:
    if start and end:
        try:
            diff = datetime.fromisoformat(end) - datetime.fromisoformat(start)
            return f"Total Time: **{str(diff).split('.')[0]}**"
        except:
            return "Time Calculation Error"
    elif start:
        return "⏳ Running…"
    return "Not Started"

def detect_file_type(data: Optional[str]):
    if not data: return None, None, None
    raw = base64.b64decode(data)
    head = raw[:10]
    if head.startswith(b"%PDF"): return "pdf", "application/pdf", ".pdf"
    if head.startswith(b"\x89PNG"): return "png", "image/png", ".png"
    if head[:3] == b"\xff\xd8\xff": return "jpg", "image/jpeg", ".jpg"
    return "bin", "application/octet-stream", ".bin"

def download_button_ui(label, b64, order_id, fname):
    if not b64: return
    raw = base64.b64decode(b64)
    _, mime, ext = detect_file_type(b64)
    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime or "application/octet-stream",
        use_container_width=True
    )

# ---------- QR CODE GENERATOR ----------
def generate_qr_base64(data: str):
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ---------- PDF SLIP ----------
def generate_packing_slip(o, assign, material, notes):
    lines = [
        "PACKING DEPARTMENT – JOB SLIP",
        "===============================",
        "",
        f"Order ID : {o.get('order_id')}",
        f"Customer : {o.get('customer')}",
        f"Item     : {o.get('item')}",
        f"Qty      : {o.get('qty')}",
        "",
        f"Assigned To  : {assign or 'N/A'}",
        f"Material Used: {material or 'N/A'}",
        "",
        "Notes:",
        notes or "No notes.",
        "",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]
    pdf_text = "BT\n/F1 12 Tf\n50 750 Td\n"
    for ln in lines:
        safe = ln.replace("(", "\\(").replace(")", "\\)").encode("ascii", "replace").decode()
        pdf_text += f"({safe}) Tj\n0 -18 Td\n"
    pdf_text += "ET"

    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj <<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources << /Font << /F1 5 0 R >> >>
/Contents 4 0 R
>> endobj
4 0 obj << /Length {len(pdf_text)} >> stream
{pdf_text}
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000065 00000 n
0000000130 00000 n
0000000305 00000 n
0000000550 00000 n
trailer << /Root 1 0 R /Size 6 >>
startxref
700
%%EOF"""
    return pdf.encode("utf-8", errors="ignore")

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
        packing_file = o.get("packing_file")

        # ----- WARNING: 36-hour delay check -----
        arrived = o.get("assembly_completed_at")
        hours = 0
        if arrived:
            hours = (datetime.now() - datetime.fromisoformat(arrived)).total_seconds() / 3600

        # ----- QR CONTENT (HUMAN READABLE) -----
        qr_text = f"""
Order ID: {o.get('order_id')}
Customer: {o.get('customer')}
Item: {o.get('item')}
Qty: {o.get('qty')}
Priority: {o.get('priority')}
Stage: Packing
Assigned To: {o.get('packing_assigned',"")}
Material Used: {o.get('packing_material',"")}
Notes: {o.get('packing_notes',"")}
Next Stage: Dispatch
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
""".strip()

        qr_b64 = generate_qr_base64(qr_text)

        # -------- UI CARD --------
        with st.container(border=True):

            st.markdown(f"## 📦 Order {order_id}")
            st.caption(f"{o.get('customer')} — {o.get('item')}")

            if hours > 36:
                st.error(f"⚠ Packing delayed **{int(hours)} hours**")
            else:
                st.info(f"Time since assembly: **{int(hours)} hours**")

            st.divider()

            col1, col2 = st.columns([1, 1.3])

            # ----------------------------------
            # COLUMN 1: TIME + QR
            # ----------------------------------
            with col1:
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

                st.markdown("---")

                st.subheader("🔳 QR Code (Readable Text)")
                st.image(base64.b64decode(qr_b64), width=200)

                st.download_button(
                    "⬇ Download QR Code",
                    base64.b64decode(qr_b64),
                    file_name=f"{order_id}_QR.png",
                    mime="image/png",
                    use_container_width=True
                )

                st.markdown("---")

                slip_pdf = generate_packing_slip(o, o.get("packing_assigned"), o.get("packing_material"), o.get("packing_notes"))
                st.download_button(
                    "📥 Download Packing Slip",
                    slip_pdf,
                    file_name=f"{order_id}_slip.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            # ----------------------------------
            # COLUMN 2: DETAILS + FILE
            # ----------------------------------
            with col2:

                st.subheader("📋 Packing Details")

                assign = st.text_input("Assigned To", o.get("packing_assigned",""), key=f"assign_{order_id}")
                material = st.text_input("Material Used", o.get("packing_material",""), key=f"material_{order_id}")
                notes = st.text_area("Notes", o.get("packing_notes",""), height=80, key=f"notes_{order_id}")

                if st.button("💾 Save", key=f"save_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {
                        "packing_assigned": assign,
                        "packing_material": material,
                        "packing_notes": notes
                    })
                    st.success("Saved")
                    st.rerun()

                st.markdown("---")

                st.subheader("📁 Final Output File")

                if packing_file:
                    ft, _, _ = detect_file_type(packing_file)
                    if ft in ["png","jpg"]:
                        st.image(base64.b64decode(packing_file), use_container_width=True)
                    else:
                        st.info("PDF uploaded.")
                    download_button_ui("⬇ Download File", packing_file, order_id, "packing_output")

                up = st.file_uploader("Upload Output", type=["png","jpg","jpeg","pdf"], key=f"file_{order_id}")

                if st.button("Upload File", key=f"upload_{order_id}", disabled=not up, use_container_width=True):
                    encoded = base64.b64encode(up.read()).decode()
                    update(f"orders/{key}", {"packing_file": encoded})
                    st.success("Uploaded")
                    st.rerun()

                st.markdown("---")

                ready = bool(end and packing_file)

                if ready:
                    if st.button("🚚 Move to Dispatch", key=f"move_{order_id}", type="primary", use_container_width=True):
                        update(f"orders/{key}", {
                            "stage": "Dispatch",
                            "packing_completed_at": datetime.now().isoformat()
                        })
                        st.balloons()
                        st.rerun()
                else:
                    st.warning("Complete packing time + upload file to continue.")

# ---------------- TAB 2: COMPLETED ----------------
with tab2:
    if not completed:
        st.info("No completed packing jobs yet.")
        st.stop()

    for key, o in completed.items():
        with st.expander(f"✔ {o['order_id']} — Completed: {o.get('packing_completed_at')}"):
            st.json({
                "Assigned To": o.get("packing_assigned"),
                "Material": o.get("packing_material"),
                "Notes": o.get("packing_notes"),
                "Completed At": o.get("packing_completed_at")
            })
