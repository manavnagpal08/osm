import streamlit as st
from firebase import read, update
import base64
import io
# import qrcode # Removed: replaced by barcode
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
import barcode # Added: Barcode generation library
from barcode.writer import ImageWriter # Added: To output barcode as an image

st.set_page_config(page_title="Logistics Department", page_icon="🚚", layout="wide")

# ---------------- ROLE & USER CHECK ----------------
REQUIRED_ROLES = ["packaging", "dispatch", "admin"]
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in REQUIRED_ROLES:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

# Determine the user's identity for logging and accountability
USER_IDENTITY = st.session_state.get("username", st.session_state["role"]) 
# Removed the visible debug/identity display: 
# st.subheader(f"👋 Logged in as: {USER_IDENTITY} ({st.session_state['role'].title()})")


st.title("🚚 Logistics Department (Packing & Dispatch)")
st.caption("Manage orders through the Packing and Dispatch stages.")

# ---------------- LOAD ORDERS ----------------
orders = read("orders") or {}
pending_packing: Dict[str, Any] = {}
pending_dispatch: Dict[str, Any] = {}
completed_final: Dict[str, Any] = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    stage = o.get("stage")

    if stage == "Packing":
        pending_packing[key] = o
    elif stage == "Dispatch":
        pending_dispatch[key] = o
    elif stage == "Completed":
        completed_final[key] = o

# --------- SORT BY PRIORITY (Packing & Dispatch) ----------
priority_rank = {"High": 0, "Medium": 1, "Low": 2}

sorted_packing = sorted(
    pending_packing.items(),
    key=lambda x: (
        priority_rank.get(x[1].get("priority", "Medium"), 1),
        x[1].get("assembly_completed_at", "2099-12-31") # Sort by when it arrived from assembly
    )
)

sorted_dispatch = sorted(
    pending_dispatch.items(),
    key=lambda x: (
        priority_rank.get(x[1].get("priority", "Medium"), 1),
        x[1].get("packing_completed_at", "2099-12-31") # Sort by when it arrived from packing
    )
)

# ---------- UTILITIES ----------

def parse_datetime_robust(date_str: str) -> Optional[datetime]:
    """Tries to parse datetime from ISO format, then from the custom format."""
    if not date_str:
        return None
    
    dt = None
    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        try:
            # Try the old custom format ('01 Dec 2025, 04:52 PM')
            dt = datetime.strptime(date_str, '%d %b %Y, %I:%M %p')
            # If successful, assume it was saved as IST/local time and make it UTC-aware
            IST = timezone(timedelta(hours=5, minutes=30))
            dt = dt.replace(tzinfo=IST).astimezone(timezone.utc)
        except Exception:
            return None
    
    if dt and dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    return dt

def calculate_time_diff(start: Optional[str], end: Optional[str]) -> str:
    """Calculate how long the task took using robust parsing."""
    t1 = parse_datetime_robust(start)
    t2 = parse_datetime_robust(end)

    if t1 and t2:
        try:
            diff = t2 - t1
            return f"Total Time: **{str(diff).split('.')[0]}**"
        except:
            return "Time Calculation Error"
    elif t1:
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

def download_button_ui(label: str, b64: Optional[str], order_id: str, fname: str, key_suffix: str):
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
        key=f"dl_{fname}_{order_id}_{key_suffix}",
        use_container_width=True
    )

# --- NEW BARCODE GENERATION FUNCTION ---
def generate_barcode_base64(data_string: str) -> str:
    """Generates Code128 barcode for given string and returns base64 PNG."""
    try:
        # Code 128 is robust for alphanumeric data
        Code128 = barcode.get_barcode_class('code128')
        
        # Configure the writer for visual output
        writer = ImageWriter()
        writer.text_distance = 5
        writer.font_size = 12
        writer.write_text = True 

        barcode_instance = Code128(data_string.replace('|', '-'), writer=writer)

        # Write to an in-memory buffer
        buffer = io.BytesIO()
        # Ensure minimal width for better display in Streamlit
        barcode_instance.write(buffer, options={"module_width": 0.3, "module_height": 10, "quiet_zone": 5})
        
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.error(f"Barcode generation failed. Is 'python-barcode' installed? Error: {e}")
        return ""

def generate_slip_pdf(o, details, title, fields):
    """Generates a generic PDF slip (Job or Dispatch)."""
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST) 

    lines = [
        f"LOGISTICS DEPARTMENT – {title.upper()} SLIP",
        "===============================",
        "",
        f"Order ID : {o.get('order_id')}",
        f"Customer : {o.get('customer')}",
        f"Item     : {o.get('item')}",
        f"Qty      : {o.get('qty', 0):,}",
        "",
    ]
    for label, key in fields:
        lines.append(f"{label:<13}: {details.get(key, 'N/A')}")
    
    lines.extend([
        "",
        "Notes:",
        details.get("notes") or "No special notes.",
        "",
        f"Generated By: {details.get('generated_by', 'N/A')}",
        f"Generated At: {now.strftime('%Y-%m-%d %H:%M %Z')}"
    ])
    
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
tab1, tab2, tab3 = st.tabs([
    f"📦 Pending Packing ({len(sorted_packing)})",
    f"🚀 Pending Dispatch ({len(pending_dispatch)})",
    f"✅ Finalized Orders ({len(completed_final)})"
])

# =================================================================
# TAB 1: PENDING PACKING
# =================================================================
if st.session_state["role"] in ["packaging", "admin"]:
    with tab1:
        if not sorted_packing:
            st.success("🎉 No pending packing work!")

        for key, o in sorted_packing:
            order_id = o["order_id"]
            start = o.get("packing_start")
            end = o.get("packing_end")
            packing_file = o.get("packing_file")

            # --- DEADLINE WATCH ---
            arrived_str = o.get("assembly_completed_at")
            status_message = "Waiting for Assembly completion timestamp."
            status_type = st.info
            
            if arrived_str:
                arrived_dt = parse_datetime_robust(arrived_str)
                if arrived_dt:
                    now_utc = datetime.now(timezone.utc)
                    time_diff = now_utc - arrived_dt
                    hours_passed = time_diff.total_seconds() / 3600
                    
                    # 36 hours limit for Packing
                    if hours_passed > 36:
                        status_message = f"⛔ OVERDUE by **{str(time_diff - timedelta(hours=36)).split('.')[0]}**"
                        status_type = st.error
                    else:
                        status_message = f"🟢 Remaining: **{str(timedelta(hours=36) - time_diff).split('.')[0]}**"
                        status_type = st.success
                else:
                    status_message = "Cannot calculate deadline (Time Format Error)"
                    status_type = st.warning

            # Get current details for Barcode encoding/Display
            current_assign = st.session_state.get(f"p_assign_{order_id}", o.get("packing_assigned", ""))
            current_material = st.session_state.get(f"p_material_{order_id}", o.get("packing_material", ""))
            current_notes = st.session_state.get(f"p_notes_{order_id}", o.get("packing_notes", ""))

            # --- BARCODE CONTENT (Pipe-separated string for linear encoding) ---
            barcode_content = "|".join([
                f"P_ID:{order_id}",
                f"CUST:{o.get('customer', 'N/A')}",
                f"ITEM:{o.get('item', 'N/A')}",
                f"QTY:{o.get('qty', 0):,}",
                f"MAT:{current_material or 'NONE'}"
            ])
            barcode_b64 = generate_barcode_base64(barcode_content)  

            with st.container(border=True):
                # ---- HEADER ----
                col_id, col_priority, col_status = st.columns([3, 1.5, 3])
                col_id.markdown(f"### 📦 Order {order_id}")
                col_id.caption(f"**Customer:** {o.get('customer')} | **Item:** {o.get('item')}")
                col_priority.metric("Priority", o.get("priority", "Medium"))
                with col_status:
                    st.caption("Time since previous stage:")
                    status_type(status_message)

                st.divider()
                
                col_time_files, col_details = st.columns([1, 1.5])
                
                # COLUMN 1: TIME & FILES
                with col_time_files:
                    st.subheader("⏱ Time Tracking & Tags")

                    # Time Tracking
                    if not start:
                        if st.button("▶️ Start Packing", key=f"p_start_{order_id}", use_container_width=True, type="secondary"):
                            # LOG USER WHO STARTED THE TASK
                            update(f"orders/{key}", {
                                "packing_start": datetime.now(timezone.utc).isoformat(),
                                "packing_started_by": USER_IDENTITY
                            }) 
                            st.rerun()
                    elif not end:
                        if st.button("⏹ End Packing", key=f"p_end_{order_id}", use_container_width=True, type="primary"):
                            # LOG USER WHO ENDED THE TASK
                            update(f"orders/{key}", {
                                "packing_end": datetime.now(timezone.utc).isoformat(),
                                "packing_ended_by": USER_IDENTITY
                            }) 
                            st.rerun()
                        start_dt = parse_datetime_robust(start)
                        st.info(f"Running since: **{start_dt.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M IST')}**" if start_dt else "Running...")
                        st.caption(f"Started by: `{o.get('packing_started_by', 'N/A')}`")
                    else:
                        st.success("Task Completed")
                        st.markdown(calculate_time_diff(start, end))
                        st.caption(f"Completed by: `{o.get('packing_ended_by', 'N/A')}`")


                    st.markdown("---")

                    # Barcode & Slip
                    st.subheader("📶 Barcode Tag (Code 128)")
                    if barcode_b64:
                        st.image(base64.b64decode(barcode_b64), use_container_width=True) 
                        download_button_ui("⬇ Download Barcode (PNG)", barcode_b64, order_id, "packing_barcode", key)
                    else:
                        st.warning("Barcode could not be generated.")

                    with st.expander(f"View Encoded Barcode Data"):
                        st.code(barcode_content, language="text")
                    
                    st.markdown("---")

                    # Generate PDF Slip - Includes current user for audit trail
                    slip_details = {
                        "assign": current_assign, 
                        "material": current_material, 
                        "notes": current_notes,
                        "generated_by": USER_IDENTITY
                    }
                    slip_pdf = generate_slip_pdf(o, slip_details, "Packing Job", [
                        ("Assigned To", "assign"), 
                        ("Material Used", "material")
                    ])

                    st.download_button(
                        label="📥 Download Packing Slip (PDF)",
                        data=slip_pdf,
                        file_name=f"{order_id}_packing_slip.pdf",
                        mime="application/pdf",
                        key=f"dlslip_{order_id}_{key}",
                        use_container_width=True
                    )
                
                # COLUMN 2: DETAILS & ACTION
                with col_details:
                    st.subheader("📋 Packing Details")
                    # This field remains free-form for delegation/assignment
                    assign = st.text_input("Assigned To (User ID/Name)", current_assign, key=f"p_assign_{order_id}") 
                    material = st.text_input("Material Used", current_material, key=f"p_material_{order_id}")
                    notes = st.text_area("Notes", current_notes, height=80, key=f"p_notes_{order_id}")

                    if st.button("💾 Save Details", key=f"p_save_{order_id}", type="secondary", use_container_width=True):
                        update(f"orders/{key}", {
                            "packing_assigned": assign,
                            "packing_material": material,
                            "packing_notes": notes
                        })
                        st.toast("Details Saved!")
                        st.rerun()

                    st.markdown("---")

                    st.subheader("📁 Final Output/Proof File")
                    if packing_file:
                        st.success("✅ Output File Uploaded")
                        file_type, _, _ = detect_file_type(packing_file)
                        if file_type in ["png", "jpg"]: st.image(base64.b64decode(packing_file), use_container_width=True)
                        else: st.info("File uploaded. Use the download button.")
                        download_button_ui("⬇ Download Final Output", packing_file, order_id, "packing_proof", key)
                    else:
                        st.warning("A final file upload is required to proceed.")
                    
                    up = st.file_uploader("Upload Packing Proof Image/PDF", type=["png", "jpg", "jpeg", "pdf"], key=f"p_file_up_{order_id}", label_visibility="collapsed")
                    if st.button("💾 Upload & Save File", key=f"p_save_file_{order_id}", use_container_width=True, disabled=not up):
                        up.seek(0)
                        encoded = base64.b64encode(up.read()).decode()
                        update(f"orders/{key}", {"packing_file": encoded})
                        st.toast("File uploaded successfully!")
                        st.rerun()

                    st.divider()
                    
                    # --- MOVE TO DISPATCH ---
                    is_time_ended = bool(end)
                    is_file_uploaded = bool(packing_file)
                    is_ready = is_time_ended and is_file_uploaded

                    if is_ready:
                        if st.button("🚀 Move to Dispatch", key=f"p_next_{order_id}", type="primary", use_container_width=True):
                            now = datetime.now(timezone.utc).isoformat()
                            update(f"orders/{key}", {
                                "stage": "Dispatch",
                                "packing_completed_at": now 
                            })
                            st.success("✅ Order moved to Dispatch!")
                            st.balloons()
                            st.rerun()
                    else:
                        st.error("⚠ **ORDER NOT READY TO MOVE TO DISPATCH**")
                        missing_items = []
                        if not is_time_ended: missing_items.append("⏹ End Packing Time")
                        if not is_file_uploaded: missing_items.append("📁 Upload Final Output/Proof File")
                        st.markdown("**Please complete:**<br>- " + "<br>- ".join(missing_items), unsafe_allow_html=True)

# =================================================================
# TAB 2: PENDING DISPATCH
# =================================================================
if st.session_state["role"] in ["dispatch", "admin"]:
    with tab2:
        if not sorted_dispatch:
            st.success("🎉 No pending dispatch work!")
        else: # Only proceed if there are pending orders
            for key, o in sorted_dispatch:
                order_id = o["order_id"]
                start = o.get("dispatch_start")
                end = o.get("dispatch_end")
                
                # --- DEADLINE WATCH (48 hours from Packing Completion) ---
                arrived_str = o.get("packing_completed_at")
                status_message = "Waiting for Packing completion timestamp."
                status_type = st.info
                
                if arrived_str:
                    arrived_dt = parse_datetime_robust(arrived_str)
                    if arrived_dt:
                        now_utc = datetime.now(timezone.utc)
                        time_diff = now_utc - arrived_dt
                        
                        # 48 hours for dispatch
                        if time_diff.total_seconds() > 48 * 3600:
                            remaining_time = time_diff - timedelta(hours=48)
                            status_message = f"⛔ OVERDUE by **{str(remaining_time).split('.')[0]}**"
                            status_type = st.error
                        else:
                            remaining_time = timedelta(hours=48) - time_diff
                            status_message = f"🟢 Remaining: **{str(remaining_time).split('.')[0]}**"
                            status_type = st.success
                    else:
                        status_message = "Cannot calculate deadline (Time Format Error)"
                        status_type = st.warning

                # Get current details for Barcode encoding/Dispatch details
                current_courier = st.session_state.get(f"d_courier_{order_id}", o.get("courier", ""))
                current_tracking = st.session_state.get(f"d_tracking_{order_id}", o.get("tracking_number", ""))
                current_notes = st.session_state.get(f"d_notes_{order_id}", o.get("dispatch_notes", ""))

                # --- BARCODE CONTENT (Pipe-separated string for linear encoding) ---
                barcode_content = "|".join([
                    f"D_ID:{order_id}",
                    f"CUST:{o.get('customer', 'N/A')}",
                    f"ITEM:{o.get('item', 'N/A')}",
                    f"QTY:{o.get('qty', 0):,}",
                    f"COURIER:{current_courier or 'N/A'}",
                    f"TRACK:{current_tracking or 'N/A'}"
                ])
                barcode_b64 = generate_barcode_base64(barcode_content)  

                with st.container(border=True):
                    # ---- HEADER ----
                    col_id, col_priority, col_status = st.columns([3, 1.5, 3])
                    col_id.markdown(f"### 🚀 Order {order_id}")
                    col_id.caption(f"**Customer:** {o.get('customer')} | **Item:** {o.get('item')}")
                    col_priority.metric("Priority", o.get("priority", "Medium"))
                    with col_status:
                        st.caption("Time since previous stage:")
                        status_type(status_message)

                    st.divider()
                    
                    col_time_files, col_details = st.columns([1, 1.5])

                    # COLUMN 1: TIME & FILES
                    with col_time_files:
                        st.subheader("⏱ Time Tracking & Tags")

                        # Time Tracking
                        if not start:
                            if st.button("▶️ Start Dispatch", key=f"d_start_{order_id}", use_container_width=True, type="secondary"):
                                # LOG USER WHO STARTED THE TASK
                                update(f"orders/{key}", {
                                    "dispatch_start": datetime.now(timezone.utc).isoformat(),
                                    "dispatch_started_by": USER_IDENTITY
                                }) 
                                st.rerun()
                        elif not end:
                            if st.button("⏹ End Dispatch", key=f"d_end_{order_id}", use_container_width=True, type="primary"):
                                # LOG USER WHO ENDED THE TASK
                                update(f"orders/{key}", {
                                    "dispatch_end": datetime.now(timezone.utc).isoformat(),
                                    "dispatch_ended_by": USER_IDENTITY
                                }) 
                                st.rerun()
                            start_dt = parse_datetime_robust(start)
                            st.info(f"Running since: **{start_dt.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M IST')}**" if start_dt else "Running...")
                            st.caption(f"Started by: `{o.get('dispatch_started_by', 'N/A')}`")
                        else:
                            st.success("Task Completed")
                            st.markdown(calculate_time_diff(start, end))
                            st.caption(f"Completed by: `{o.get('dispatch_ended_by', 'N/A')}`")


                        st.markdown("---")

                        # Barcode & Slip
                        st.subheader("📶 Barcode Tag (Code 128)")
                        if barcode_b64:
                            st.image(base64.b64decode(barcode_b64), use_container_width=True) 
                            download_button_ui("⬇ Download Barcode (PNG)", barcode_b64, order_id, "dispatch_barcode", key)
                        else:
                            st.warning("Barcode could not be generated.")

                        with st.expander(f"View Encoded Barcode Data"):
                            st.code(barcode_content, language="text")

                        st.markdown("---")

                        # Generate PDF Slip - Includes current user for audit trail
                        slip_details = {
                            "courier": current_courier, 
                            "tracking": current_tracking, 
                            "notes": current_notes,
                            "generated_by": USER_IDENTITY
                        }
                        slip_pdf = generate_slip_pdf(o, slip_details, "Dispatch", [
                            ("Courier", "courier"), 
                            ("Tracking No", "tracking")
                        ])

                        st.download_button(
                            label="📥 Download Dispatch Slip (PDF)",
                            data=slip_pdf,
                            file_name=f"{order_id}_dispatch_slip.pdf",
                            mime="application/pdf",
                            key=f"dlslip_d_{order_id}_{key}",
                            use_container_width=True
                        )
                    
                    # COLUMN 2: DETAILS & ACTION
                    with col_details:
                        st.subheader("📋 Dispatch Details")
                        courier = st.text_input("Courier Service", current_courier, key=f"d_courier_{order_id}")
                        tracking = st.text_input("Tracking Number", current_tracking, key=f"d_tracking_{order_id}")
                        notes = st.text_area("Dispatch Notes", current_notes, height=80, key=f"d_notes_{order_id}")

                        if st.button("💾 Save Dispatch Details", key=f"d_save_{order_id}", type="secondary", use_container_width=True):
                            update(f"orders/{key}", {
                                "courier": courier,
                                "tracking_number": tracking,
                                "dispatch_notes": notes
                            })
                            st.toast("Dispatch Details Saved!")
                            st.rerun()

                        st.divider()
                        
                        # --- MARK AS COMPLETED ---
                        is_time_ended = bool(end)
                        is_details_filled = bool(courier and tracking)

                        is_ready = is_time_ended and is_details_filled

                        if is_ready:
                            if st.button("🎉 Mark Order Completed", key=f"d_final_{order_id}", type="primary", use_container_width=True):
                                now = datetime.now(timezone.utc).isoformat()
                                # LOG USER WHO FINALLY COMPLETED THE DISPATCH STEP
                                update(f"orders/{key}", {
                                    "stage": "Completed",
                                    "completed_at": now, 
                                    "dispatch_completed_at": now,
                                    "dispatch_completed_by": USER_IDENTITY # New audit field
                                })
                                st.success("✅ Order marked as COMPLETED and dispatched!")
                                st.balloons()
                                st.rerun()
                        else:
                            st.error("⚠ **ORDER NOT READY TO MARK AS COMPLETED**")
                            missing_items = []
                            if not is_time_ended: missing_items.append("⏹ End Dispatch Time")
                            if not is_details_filled: missing_items.append("Tracking Number and Courier")
                            st.markdown("**Please complete:**<br>- " + "<br>- ".join(missing_items), unsafe_allow_html=True)


# =================================================================
# TAB 3: FINALIZED ORDERS
# =================================================================
with tab3:
    if not completed_final:
        st.info("No orders have been finalized yet.")
    else: # Only proceed if there are completed orders
        # Sort completed by final completion date
        sorted_completed_final = sorted(
            completed_final.items(),
            key=lambda i: i[1].get("completed_at", "0000-01-01"),
            reverse=True
        )

        for key, o in sorted_completed_final:
            # Get times for display
            packing_start = o.get("packing_start")
            packing_end = o.get("packing_end")
            dispatch_start = o.get("dispatch_start")
            dispatch_end = o.get("dispatch_end")
            
            # Try to convert completion time to IST for display
            comp_dt_str = o.get('completed_at', '')
            comp_dt_ist = 'N/A'
            try:
                comp_dt_utc = parse_datetime_robust(comp_dt_str)
                if comp_dt_utc:
                    IST = timezone(timedelta(hours=5, minutes=30))
                    comp_dt_ist = comp_dt_utc.astimezone(IST).strftime('%Y-%m-%d %H:%M IST')
            except:
                comp_dt_ist = o.get('completed_at', 'N/A')

            with st.expander(f"✅ {o['order_id']} — {o.get('customer')} | Finalized: {comp_dt_ist.split(' ')[0]}"):
                
                st.markdown(f"#### Order Summary")
                c1, c2, c3 = st.columns(3)
                c1.metric("Packing Time", calculate_time_diff(packing_start, packing_end))
                c2.metric("Dispatch Time", calculate_time_diff(dispatch_start, dispatch_end))
                c3.metric("Finalized At", comp_dt_ist)
                
                st.divider()
                
                col_packing, col_dispatch = st.columns(2)

                with col_packing:
                    st.markdown("##### 📦 Packing Details")
                    st.markdown(f"""
                    - **Assigned To:** `{o.get("packing_assigned", "N/A")}`
                    - **Started By:** `{o.get("packing_started_by", "N/A")}`
                    - **Completed By:** `{o.get("packing_ended_by", "N/A")}`
                    - **Material Used:** `{o.get("packing_material", "N/A")}`
                    """)
                    st.caption(f"Notes: {o.get('packing_notes', 'None')}")

                    if o.get("packing_file"):
                        download_button_ui(
                            "⬇ Download Packing Proof", 
                            o["packing_file"], 
                            o["order_id"], 
                            "packing_final_proof",
                            key
                        )
                    else:
                        st.warning("No final file uploaded for packing.")
                
                with col_dispatch:
                    st.markdown("##### 🚀 Dispatch Details")
                    st.markdown(f"""
                    - **Courier:** `{o.get("courier", "N/A")}`
                    - **Tracking No:** `{o.get("tracking_number", "N/A")}`
                    - **Completed By:** `{o.get("dispatch_completed_by", "N/A")}`
                    - **Started By:** `{o.get("dispatch_started_by", "N/A")}`
                    """)
                    st.caption(f"Notes: {o.get('dispatch_notes', 'None')}")
