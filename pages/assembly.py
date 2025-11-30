import streamlit as st
from firebase import read, update
import base64
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

# -----------------------------------------
# PAGE CONFIG
# -----------------------------------------
st.set_page_config(page_title="Assembly Department", layout="wide", page_icon="🧩")

# -----------------------------------------
# ROLE CHECK
# -----------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["assembly", "admin"]:
    st.error("❌ Access Denied")
    st.stop()

st.title("🧩 Assembly Department")
st.caption("Manage assembly work, record output, assign workers, monitor deadlines, and generate job slips.")

# -----------------------------------------
# LOAD ORDERS
# -----------------------------------------
orders = read("orders") or {}

pending: Dict[str, Any] = {}
completed: Dict[str, Any] = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # Filter for orders in the current stage
    if o.get("stage") == "Assembly":
        pending[key] = o
    elif o.get("assembly_completed_at"):
        completed[key] = o


# -----------------------------------------
# UTILITIES
# -----------------------------------------

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

def preview_ui(label: str, b64: Optional[str], order_id: str):
    """File preview UI with expander."""
    if not b64:
        st.info(f"No {label} uploaded yet.")
        return
    
    raw = base64.b64decode(b64)
    file_type, _, _ = detect_file_type(b64)
    
    with st.expander(f"🖼️ View {label} ({file_type.upper()})"):
        if file_type in ["png", "jpg"]:
            st.image(raw, use_container_width=True)
        elif file_type == "pdf":
            st.warning("PDFs cannot be previewed directly in the web app, please download.")
        else:
            st.info(f"File ({len(raw)} bytes) is not a common image type for preview. Download required.")

        # Always provide the download button inside the preview pane for convenience
        download_button_ui(
            label="⬇️ Download File for Viewing", 
            b64=b64, 
            order_id=order_id, 
            fname=f"{label.lower().replace(' ', '_')}_preview"
        )


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


# -----------------------------------------
# PURE PYTHON PDF SLIP
# -----------------------------------------
def generate_slip(order, assembled_qty, assign_to, material, notes):

    lines = [
        "ASSEMBLY DEPARTMENT – WORK SLIP",
        "===============================",
        "",
        f"Order ID: {order.get('order_id')}",
        f"Customer: {order.get('customer')}",
        f"Item: {order.get('item')}",
        f"Order Quantity: {order.get('qty'):,}",
        f"Assembled Quantity: {assembled_qty:,}",
        f"Remaining: {max(order.get('qty', 0) - assembled_qty, 0):,}",
        "",
        f"Material Used: {material or 'N/A'}",
        f"Assigned To: {assign_to or 'Unassigned'}",
        "",
        "Notes:",
        notes or "No special notes.",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]

    def esc(t): return t.replace("(", "\\(").replace(")", "\\)")

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


# -----------------------------------------
# TABS
# -----------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Assembly ({len(pending)})",
    f"✔ Completed Assembly ({len(completed)})"
])


# -----------------------------------------
# PENDING TAB (IMPROVED UI)
# -----------------------------------------
with tab1:

    if not pending:
        st.success("🎉 All assembly jobs completed!")
    
    # Sort orders by priority (High, Medium, Low)
    sorted_pending = sorted(
        pending.items(),
        key=lambda i: (
            {"High": 0, "Medium": 1, "Low": 2}.get(i[1].get("priority", "Medium")),
            i[1].get("received", "9999-12-31")
        )
    )

    for key, o in sorted_pending:

        order_id = o["order_id"]
        file_asm = o.get("assembly_file")
        qty = o.get("qty", 1)
        assembled_qty = o.get("assembled_qty", 0)
        
        with st.container(border=True):

            # --- HEADER ROW: ID, CUSTOMER, PRIORITY, STAGE ---
            col_id, col_priority, col_status = st.columns([3, 1.5, 3])
            
            col_id.markdown(f"### 📦 Order {order_id}")
            col_id.caption(f"**Customer:** {o.get('customer')} | **Item:** {o.get('item')}")
            
            priority_emoji = {"High": "🚨", "Medium": "🟡", "Low": "🔵"}.get(o.get("priority", "Medium"), "⚪")
            col_priority.metric("Priority", o.get("priority", "Medium"), help="Job Priority")
            
            # ---------------- DEADLINE WATCH ----------------
            start_design_out = o.get("printing_completed_at") or o.get("diecut_completed_at")
            
            status_text = "N/A"
            if start_design_out:
                start_time = datetime.fromisoformat(start_design_out)
                # Assembly is given 36 hours from the completion of the previous step
                deadline = start_time + timedelta(hours=36)
                now = datetime.now()
                
                if now > deadline:
                    remaining = now - deadline
                    col_status.error(f"⛔ OVERDUE by {str(remaining).split('.')[0]}")
                    status_text = f"OVERDUE: {str(remaining).split('.')[0]}"
                else:
                    remaining = deadline - now
                    col_status.success(f"🟢 Remaining: {str(remaining).split('.')[0]}")
                    status_text = f"Remaining: {str(remaining).split('.')[0]}"

            col_status.caption(f"Time since prev. stage completion: {status_text}")
            
            st.divider()

            # --- MAIN TWO-COLUMN LAYOUT ---
            col_details, col_action = st.columns([1.5, 1])

            # ==================================
            # COLUMN 1: TIME TRACKING & DETAILS
            # ==================================
            with col_details:
                
                # --- TIME TRACKING & QUANTITY ---
                col_time, col_qty_info = st.columns(2)

                with col_time:
                    st.subheader("🕒 Job Timing")
                    start = o.get("assembly_start")
                    end = o.get("assembly_end")
                    
                    if not start:
                        if st.button("▶️ Start Assembly", key=f"start_{order_id}", use_container_width=True, type="secondary"):
                            update(f"orders/{key}", {"assembly_start": datetime.now().isoformat()})
                            st.rerun()
                        st.caption("Awaiting start signal.")
                    elif not end:
                        if st.button("⏹ End Assembly", key=f"end_{order_id}", use_container_width=True, type="primary"):
                            update(f"orders/{key}", {"assembly_end": datetime.now().isoformat()})
                            st.rerun()
                        st.info(f"Running since: {start.split('T')[1][:5]}")
                    else:
                        st.success("Task Completed")
                        st.markdown(calculate_time_diff(start, end))

                with col_qty_info:
                    st.subheader("🔢 Production Counts")
                    st.metric("Order Quantity", f"{qty:,}", delta=f"Assembled: {assembled_qty:,}")
                    remaining = qty - assembled_qty
                    
                    if remaining > 0:
                        st.warning(f"Remaining: **{remaining:,} pcs**")
                    else:
                        st.success("All units assembled!")

                st.markdown("---")

                # --- DETAILS FORM ---
                st.subheader("🧾 Assembly Details")

                assembled_qty_input = st.number_input(
                    "Assembled Quantity",
                    min_value=0,
                    max_value=qty,
                    value=assembled_qty,
                    key=f"asmqty_{order_id}",
                    help=f"Total units required: {qty}"
                )

                assign_to = st.text_input(
                    "Assigned Worker",
                    o.get("assembly_assigned_to", ""),
                    key=f"assign_{order_id}",
                    placeholder="e.g., Rohan / Sameer"
                )

                material = st.text_input(
                    "Material Used",
                    o.get("assembly_material", ""),
                    placeholder="e.g., White Glue, Staples, Tape",
                    key=f"mat_{order_id}"
                )

                notes = st.text_area(
                    "Notes for Assembly/Next Stage",
                    o.get("assembly_notes", ""),
                    key=f"notes_{order_id}",
                    height=80
                )

                if st.button("💾 Save All Details", key=f"save_{order_id}", use_container_width=True, type="secondary"):
                    update(f"orders/{key}", {
                        "assembled_qty": assembled_qty_input,
                        "assembly_assigned_to": assign_to,
                        "assembly_material": material,
                        "assembly_notes": notes
                    })
                    st.toast("Details Updated!")
                    st.rerun()
            
            # ==================================
            # COLUMN 2: FILES & ACTION
            # ==================================
            with col_action:
                
                # --- FILE UPLOAD ---
                st.subheader("📁 Final Output File")
                
                preview_ui("Assembly Output", file_asm, order_id)

                upload = st.file_uploader(
                    "Upload Final Assembly Sample Image/PDF",
                    type=["png", "jpg", "jpeg", "pdf"],
                    key=f"upasm_{order_id}",
                    label_visibility="collapsed"
                )

                if st.button("💾 Upload & Save File", key=f"svf_{order_id}", use_container_width=True, disabled=not upload):
                    upload.seek(0)
                    encoded = base64.b64encode(upload.read()).decode()
                    update(f"orders/{key}", {"assembly_file": encoded})
                    st.toast("File uploaded successfully!")
                    st.rerun()

                st.markdown("---")

                # --- SLIP DOWNLOAD ---
                st.subheader("📄 Job Slip")
                slip = generate_slip(o, assembled_qty_input, assign_to, material, notes)
                
                st.download_button(
                    "📥 Download Assembly Slip (PDF)",
                    data=slip,
                    file_name=f"{order_id}_assembly_slip.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                st.markdown("---")

                # --- MOVE TO NEXT STAGE ---
                is_ready = file_asm and end and assembled_qty_input > 0

                if is_ready:
                    if st.button("🚀 Move to Packing", key=f"next_{order_id}", type="primary", use_container_width=True):
                        update(f"orders/{key}", {
                            "stage": "Packing",
                            "assembly_completed_at": datetime.now().isoformat()
                        })
                        st.balloons()
                        st.rerun()
                else:
                    st.error("⚠ Cannot proceed. Ensure time tracking is ended, assembled quantity is recorded, and the output file is uploaded.")


# -----------------------------------------
# COMPLETED TAB (IMPROVED UI)
# -----------------------------------------
with tab2:
    if not completed:
        st.info("No completed Assembly work.")
        st.stop()

    # Sort completed by completion date
    sorted_completed = sorted(
        completed.items(),
        key=lambda i: i[1].get("assembly_completed_at", "0000-01-01"),
        reverse=True
    )

    for key, o in sorted_completed:
        
        order_id = o['order_id']
        file_asm = o.get("assembly_file")
        start = o.get("assembly_start")
        end = o.get("assembly_end")

        with st.expander(f"✅ {order_id} — {o['customer']} | Completed: {o.get('assembly_completed_at', '').split('T')[0]}"):
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Job Time", calculate_time_diff(start, end))
            c2.metric("Assigned To", o.get("assembly_assigned_to", "N/A"))
            c3.metric("Assembled Qty", f"{o.get('assembled_qty', 0):,}")
            c4.metric("Next Stage", o.get("stage", "N/A"))
            
            st.divider()
            
            col_data, col_files = st.columns([1, 1])

            with col_data:
                st.markdown("#### Production Details")
                st.json({
                    "Material Used": o.get("assembly_material", "N/A"),
                    "Order Notes": o.get("assembly_notes", "None"),
                    "Completion Time": o.get('assembly_completed_at', 'N/A')
                })
            
            with col_files:
                st.markdown("#### Final Output File")
                if file_asm:
                    preview_ui("Assembly File", file_asm, order_id)
                    download_button_ui(
                        "⬇ Download Final Output", 
                        file_asm, 
                        order_id, 
                        f"assembly_final_{order_id}"
                    )
                else:
                    st.warning("No final file uploaded.")
            
            st.divider()
            
            # Allow slip download for historical record
            slip = generate_slip(
                o, 
                o.get("assembled_qty", 0), 
                o.get("assembly_assigned_to", ""), 
                o.get("assembly_material", ""), 
                o.get("assembly_notes", "")
            )
            st.download_button(
                "📥 Download Original Work Slip (PDF)",
                data=slip,
                file_name=f"{order_id}_assembly_slip_ARCHIVE.pdf",
                mime="application/pdf",
                key=f"dl_slip_arch_{order_id}"
            )
