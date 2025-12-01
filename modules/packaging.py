import streamlit as st
from firebase import read, update
from datetime import datetime, timedelta
import base64
import io
import qrcode
import json # Import json for dumps
from typing import Optional, Any, Dict

st.set_page_config(page_title="Packing Department", page_icon="📦", layout="wide")

# ---------------- ROLE CHECK ----------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["packaging", "admin"]:
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
    """Calculate how long the task took."""
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
    """Detects file type from base64 data."""
    if not data:
        return None, None, None
    raw = base64.b64decode(data)
    header = raw[:10]
    if header.startswith(b"%PDF"): return "pdf", "application/pdf", ".pdf"
    if header.startswith(b"\x89PNG"): return "png", "image/png", ".png"
    if header[:3] == b"\xff\xd8\xff": return "jpg", "image/jpeg", ".jpg"
    return "bin", "application/octet-stream", ".bin"

def download_button_ui(label: str, b64: Optional[str], order_id: str, fname: str):
    """Standard download button wrapper."""
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
    # Increased box_size and border for better readability of large JSON strings
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ---------- PDF SLIP ----------
def generate_packing_slip(o, assign, material, notes):
    """Generates a simple PDF packing slip."""
    
    # We use a pure Python approach for simplicity, but the QR code image must be
    # attached separately as the PDF generation here is text-only.
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
    
    # Enhanced escaping: escape PDF literals and aggressively replace non-ASCII characters
    # to prevent UnicodeEncodeError and ensure compatibility with the Courier font.
    def esc(t):
        t = str(t)
        # Escape PDF literal characters: backslash, parenthesis
        t = t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        # Replace non-ASCII characters with '?' (safe for Courier font)
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
    # The final encoding of the PDF structure string remains UTF-8 with errors ignored,
    # as the content is now ASCII-safe.
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

        # Time check (36 hours delay warning)
        arrived = o.get("assembly_completed_at")
        hours_passed = 0
        status_message = ""
        
        if arrived:
            arrived_dt = datetime.fromisoformat(arrived)
            hours_passed = (datetime.now() - arrived_dt).total_seconds() / 3600
            
            if hours_passed > 36:
                status_message = f"⛔ OVERDUE by **{int(hours_passed)} hours**"
                status_type = st.error
            else:
                status_message = f"🟢 Time since arrived: **{int(hours_passed)} hours**"
                status_type = st.success
        else:
            status_message = "Waiting for Assembly completion timestamp."
            status_type = st.info
        
        # Get current details for QR encoding
        current_assign = st.session_state.get(f"assign_{order_id}", o.get("packing_assigned", ""))
        current_material = st.session_state.get(f"material_{order_id}", o.get("packing_material", ""))
        current_notes = st.session_state.get(f"notes_{order_id}", o.get("packing_notes", ""))

        # -------- QR CODE (JSON ENCODED) --------
        qr_json_data = {
            "order_id": o.get("order_id"),
            "customer": o.get("customer"),
            "item": o.get("item"),
            "qty": o.get("qty"),
            "priority": o.get("priority"),
            "stage": "Packing",
            "product_type": o.get("product_type"),
            "assign_to": current_assign,
            "material_used": current_material,
            "notes": current_notes,
            "next_stage": "Dispatch",
            "timestamp": datetime.now().isoformat()
        }

        json_text = json.dumps(qr_json_data)
        
        # FIX: Generate QR code using the full JSON string
        qr_b64 = generate_qr_base64(json_text) 

        with st.container(border=True):

            # ---- HEADER ----
            col_id, col_priority, col_status = st.columns([3, 1.5, 3])
            
            col_id.markdown(f"### 📦 Order {order_id}")
            col_id.caption(f"**Customer:** {o.get('customer')} | **Item:** {o.get('item')}")
            
            col_priority.metric("Priority", o.get("priority", "Medium"), help="Job Priority")
            
            with col_status:
                st.caption("Time since previous stage:")
                status_type(status_message)


            st.divider()
            
            col_time_files, col_details = st.columns([1, 1.5])
            
            # ==================================
            # COLUMN 1: TIME & FILES
            # ==================================
            with col_time_files:
                st.subheader("⏱ Time Tracking")

                if not start:
                    if st.button("▶️ Start Packing", key=f"start_{order_id}", use_container_width=True, type="secondary"):
                        update(f"orders/{key}", {"packing_start": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Awaiting start signal.")
                elif not end:
                    if st.button("⏹ End Packing", key=f"end_{order_id}", use_container_width=True, type="primary"):
                        update(f"orders/{key}", {"packing_end": datetime.now().isoformat()})
                        st.rerun()
                    st.info(f"Running since: {start.split('T')[1][:5]}")
                else:
                    st.success("Task Completed")
                    st.markdown(calculate_time_diff(start, end))

                st.markdown("---")

                # -------- QR CODE --------
                st.subheader("🔳 QR Code Tag")
                # Increased display width for better readability
                st.image(base64.b64decode(qr_b64), width=200) 
                
                # --- ADDED NOTE FOR NEW SCANNER APP ---
                st.info(
                    "To view product details in a readable format after scanning this QR code, "
                    "navigate to the **QR Code Scanner App** page in the sidebar."
                )

                # DEBUG: Show the size of the data and the JSON content
                st.info(f"QR Data Size: **{len(json_text)} bytes**")
                with st.expander("View Encoded JSON Data (Debug)"):
                    st.code(json_text, language="json")

                st.download_button(
                    label="⬇ Download QR Code (PNG)",
                    data=base64.b64decode(qr_b64),
                    file_name=f"{order_id}_QR.png",
                    mime="image/png",
                    key=f"dlqr_{order_id}",
                    use_container_width=True
                )
                
                st.markdown("---")

                # -------- SLIP --------
                st.subheader("📄 Job Slip")
                # Using the temporary/saved values for the PDF slip
                slip_pdf = generate_packing_slip(o, current_assign, current_material, current_notes)

                st.download_button(
                    label="📥 Download Packing Slip (PDF)",
                    data=slip_pdf,
                    file_name=f"{order_id}_packing_slip.pdf",
                    mime="application/pdf",
                    key=f"dlslip_{order_id}",
                    use_container_width=True
                )


            # ==================================
            # COLUMN 2: DETAILS & ACTION
            # ==================================
            with col_details:
                
                st.subheader("📋 Packing Details")

                assign = st.text_input("Assign To", o.get("packing_assigned", ""), key=f"assign_{order_id}")
                material = st.text_input("Material Used", o.get("packing_material", ""), key=f"material_{order_id}")
                notes = st.text_area("Notes", o.get("packing_notes", ""), height=80, key=f"notes_{order_id}")

                if st.button("💾 Save Details", key=f"save_{order_id}", type="secondary", use_container_width=True):
                    update(f"orders/{key}", {
                        "packing_assigned": assign,
                        "packing_material": material,
                        "packing_notes": notes
                    })
                    st.toast("Details Saved!")
                    st.rerun()

                st.markdown("---")

                # -------- FILE UPLOAD --------
                st.subheader("📁 Final Output/Proof File")

                # Display uploaded file preview
                if packing_file:
                    st.success("✅ Output File Uploaded")
                    file_type, _, _ = detect_file_type(packing_file)
                    
                    if file_type in ["png", "jpg"]:
                        st.image(base64.b64decode(packing_file), use_container_width=True)
                    else:
                        st.info("PDF or unknown file type uploaded. Use the download button.")

                    download_button_ui(
                        "⬇ Download Final Output", 
                        packing_file, 
                        order_id, 
                        "packing_proof"
                    )

                else:
                    st.warning("A final file upload is required to proceed.")
                
                up = st.file_uploader("Upload Packing Proof Image/PDF", type=["png", "jpg", "jpeg", "pdf"], key=f"file_{order_id}", label_visibility="collapsed")

                if st.button("💾 Upload & Save File", key=f"save_file_{order_id}", use_container_width=True, disabled=not up):
                    up.seek(0)
                    encoded = base64.b64encode(up.read()).decode()
                    update(f"orders/{key}", {"packing_file": encoded})
                    st.toast("File uploaded successfully!")
                    st.rerun()

                st.divider()
                
                # -------- MARK ORDER AS COMPLETED (FINAL STAGE) --------
                is_time_ended = bool(end)
                is_file_uploaded = bool(packing_file)

                is_ready = is_time_ended and is_file_uploaded

                if is_ready:
                    if st.button("🎉 Mark Order Completed", key=f"complete_{order_id}", type="primary", use_container_width=True):
                        now = datetime.now().isoformat()

                        update(f"orders/{key}", {
                            "stage": "Completed",
                            "completed_at": now,
                            "packing_completed_at": now
                        })

                        st.success("✅ Order marked as COMPLETED and delivered to customer!")
                        st.balloons()
                        st.rerun()

                else:
                    st.error("⚠ **ORDER NOT READY TO MARK AS COMPLETED**")

                    missing_items = []
                    if not is_time_ended:
                        missing_items.append("⏹ End Packing Time")
                    if not is_file_uploaded:
                        missing_items.append("📁 Upload Final Output/Proof File")

                    if missing_items:
                        st.markdown(
                            "**Please complete the following requirements:**<br>- " +
                            "<br>- ".join(missing_items),
                            unsafe_allow_html=True
                        )


# ---------------- TAB 2: COMPLETED ----------------
with tab2:

    if not completed:
        st.info("No completed packing jobs yet.")
        st.stop()
        
    # Sort completed by completion date
    sorted_completed = sorted(
        completed.items(),
        key=lambda i: i[1].get("packing_completed_at", "0000-01-01"),
        reverse=True
    )

    for key, o in sorted_completed:
        start = o.get("packing_start")
        end = o.get("packing_end")
        
        with st.expander(f"✔ {o['order_id']} — {o.get('customer')} | Completed: {o.get('packing_completed_at', '').split('T')[0]}"):
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Job Time", calculate_time_diff(start, end))
            c2.metric("Assigned To", o.get("packing_assigned", "N/A"))
            c3.metric("Next Stage", o.get("stage", "N/A"))
            
            st.divider()
            
            col_data, col_files = st.columns([1, 1])

            with col_data:
                st.markdown("#### Production Details")
                st.json({
                    "Material Used": o.get("packing_material", "N/A"),
                    "Order Notes": o.get("packing_notes", "None"),
                    "Completion Time": o.get('packing_completed_at', 'N/A')
                })
            
            with col_files:
                st.markdown("#### Final Output File & QR")
                qr_json_data = {
                    "order_id": o.get("order_id"),
                    "customer": o.get("customer"),
                    "item": o.get("item"),
                    "qty": o.get("qty"),
                    "stage": "Completed/Dispatch",
                    "completion_time": o.get('packing_completed_at', 'N/A')
                }
                data_text_completed = json.dumps(qr_json_data)
                qr_b64 = generate_qr_base64(data_text_completed)
                
                st.image(base64.b64decode(qr_b64), width=100)
                st.caption("QR Code for identification.")
                
                # DEBUG: Show the size of the data and the JSON content
                st.info(f"QR Data Size: **{len(data_text_completed)} bytes**")
                with st.expander("View Encoded JSON Data (Debug)"):
                    st.code(data_text_completed, language="json")

                if o.get("packing_file"):
                    download_button_ui(
                        "⬇ Download Final Proof", 
                        o["packing_file"], 
                        o["order_id"], 
                        f"packing_final_{o['order_id']}"
                    )
                else:
                    st.warning("No final file uploaded.")
