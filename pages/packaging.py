import streamlit as st
from firebase import read, update
from datetime import datetime, timedelta
import base64
import io
import qrcode
import json
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
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            diff = t2 - t1
            return f"Total Time: **{str(diff).split('.')[0]}**"
        except:
            return "Time Calculation Error"
    elif start:
        return "⏳ Running…"
    return "Not Started"

def detect_file_type(data: Optional[str]):
    if not data:
        return None, None, None
    raw = base64.b64decode(data)
    header = raw[:10]
    if header.startswith(b"%PDF"): return "pdf", "application/pdf", ".pdf"
    if header.startswith(b"\x89PNG"): return "png", "image/png", ".png"
    if header[:3] == b"\xff\xd8\xff": return "jpg", "image/jpeg", ".jpg"
    return "bin", "application/octet-stream", ".bin"

def download_button_ui(label: str, b64: Optional[str], order_id: str, fname: str):
    if not b64:
        return
    raw = base64.b64decode(b64)
    _, mime, ext = detect_file_type(b64)
    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime or "application/octet-stream",
        key=f"dl_{fname}_{order_id}",
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
        f"Qty      : {o.get('qty'):,}",
        "",
        f"Assigned To  : {assign or 'N/A'}",
        f"Material Used: {material or 'N/A'}",
        "",
        "Notes:",
        notes or "No special notes.",
        "",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]
    
    def esc(t):
        t = str(t)
        t = t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return t.encode('ascii', 'replace').decode('ascii')

    pdf_text = "BT\n/F1 12 Tf\n50 750 Td\n"
    for ln in lines:
        pdf_text += f"({esc(ln)}) Tj\n0 -18 Td\n"
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

        arrived = o.get("assembly_completed_at")
        hours_passed = 0
        
        if arrived:
            arrived_dt = datetime.fromisoformat(arrived)
            hours_passed = (datetime.now() - arrived_dt).total_seconds() / 3600
            if hours_passed > 36:
                time_status = st.error
                msg = f"⛔ OVERDUE by **{int(hours_passed)} hours**"
            else:
                time_status = st.success
                msg = f"🟢 Time since arrived: **{int(hours_passed)} hours**"
        else:
            time_status = st.info
            msg = "Waiting for Assembly timestamp."

        current_assign = o.get("packing_assigned", "")
        current_material = o.get("packing_material", "")
        current_notes = o.get("packing_notes", "")

        qr_json_data = {
            "order_id": o.get("order_id"),
            "customer": o.get("customer"),
            "item": o.get("item"),
            "qty": o.get("qty"),
            "priority": o.get("priority"),
            "stage": "Packing",
            "assign_to": current_assign,
            "material_used": current_material,
            "notes": current_notes,
            "next_stage": "Dispatch",
            "timestamp": datetime.now().isoformat()
        }

        json_text = json.dumps(qr_json_data)
        qr_b64 = generate_qr_base64(json_text)

        with st.container(border=True):

            col_id, col_priority, col_status = st.columns([3, 1.5, 3])
            col_id.markdown(f"### 📦 {order_id}")
            col_id.caption(f"{o.get('customer')} — {o.get('item')}")
            col_priority.metric("Priority", o.get("priority", "Medium"))
            col_status.caption("Status:")
            time_status(msg)

            st.divider()

            col1, col2 = st.columns([1, 2])

            # ---------------- TIME + QR ----------------
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
                    st.info(f"Started {start}")
                else:
                    st.success("Completed")
                    st.caption(calculate_time_diff(start, end))

                st.markdown("---")

                st.subheader("🔳 QR Code Tag")
                st.image(base64.b64decode(qr_b64), width=200)

                st.download_button(
                    "⬇ Download QR",
                    data=base64.b64decode(qr_b64),
                    file_name=f"{order_id}_qr.png",
                    mime="image/png",
                    use_container_width=True
                )

                st.markdown("---")

                st.subheader("📄 Packing Slip")
                slip_pdf = generate_packing_slip(o, current_assign, current_material, current_notes)
                st.download_button(
                    "⬇ Download Slip (PDF)",
                    data=slip_pdf,
                    file_name=f"{order_id}_packing_slip.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            # ---------------- DETAILS + FILE ----------------
            with col2:
                st.subheader("📋 Packing Details")

                assign = st.text_input("Assign To", current_assign, key=f"a_{order_id}")
                material = st.text_input("Material Used", current_material, key=f"m_{order_id}")
                notes = st.text_area("Notes", current_notes, height=80, key=f"n_{order_id}")

                if st.button("💾 Save Details", key=f"save_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {
                        "packing_assigned": assign,
                        "packing_material": material,
                        "packing_notes": notes
                    })
                    st.success("Saved")
                    st.rerun()

                st.divider()

                st.subheader("📁 Final Output File")

                if packing_file:
                    file_type, _, _ = detect_file_type(packing_file)

                    if file_type in ["png", "jpg"]:
                        st.image(base64.b64decode(packing_file), use_container_width=True)
                    else:
                        st.info("PDF uploaded — download to view.")

                    download_button_ui("⬇ Download Final Output", packing_file, order_id, "packing_output")

                up = st.file_uploader("Upload Final File", type=["png", "jpg", "jpeg", "pdf"], key=f"file_{order_id}")
                if st.button("📥 Upload File", key=f"upload_{order_id}", use_container_width=True, disabled=not up):
                    up.seek(0)
                    encoded = base64.b64encode(up.read()).decode()
                    update(f"orders/{key}", {"packing_file": encoded})
                    st.success("File Uploaded")
                    st.rerun()

                st.divider()

                # MOVE TO DISPATCH
                ready = bool(end) and bool(packing_file)

                if ready:
                    if st.button("🚚 Move to Dispatch", key=f"mv_{order_id}", type="primary", use_container_width=True):
                        update(f"orders/{key}", {
                            "stage": "Dispatch",
                            "packing_status": "Completed",   # ADDED
                            "packing_completed_at": datetime.now().isoformat()
                        })
                        st.balloons()
                        st.rerun()
                else:
                    st.error("⚠ Complete packing process before moving to dispatch.")

# ---------------- TAB 2: COMPLETED ----------------
with tab2:

    if not completed:
        st.info("No completed packing tasks yet.")
        st.stop()

    sorted_completed = sorted(
        completed.items(),
        key=lambda i: i[1].get("packing_completed_at", "0000-01-01"),
        reverse=True
    )

    for key, o in sorted_completed:
        start = o.get("packing_start")
        end = o.get("packing_end")
        
        with st.expander(f"✔ {o['order_id']} — {o.get('customer')} | Completed"):
            
            c1, c2 = st.columns(2)

            with c1:
                st.metric("Job Time", calculate_time_diff(start, end))
                st.metric("Assigned To", o.get("packing_assigned", "N/A"))
                st.metric("Material Used", o.get("packing_material", "N/A"))

            with c2:
                st.subheader("📁 Final File")
                if o.get("packing_file"):
                    download_button_ui("⬇ Download Final Output", o["packing_file"], o["order_id"], "final_output")
                else:
                    st.warning("No output file")

            st.markdown("#### Notes")
            st.write(o.get("packing_notes", "None"))

