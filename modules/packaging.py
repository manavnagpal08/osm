import streamlit as st
# NOTE: The 'firebase' module used below is assumed to be a custom wrapper
# for connecting to a database (like Firebase Realtime DB or Firestore).
# You must have this module (with read/update functions) available in your environment.
from firebase import read, update 
import base64
import io
import qrcode
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict, List, Tuple

# Set Streamlit page configuration for a wider, cleaner layout
st.set_page_config(page_title="Logistics Department", page_icon="🚚", layout="wide")

# ---------------- ROLE & USER CHECK ----------------
REQUIRED_ROLES = ["packaging", "dispatch", "admin"]
if "role" not in st.session_state:
    # In a real app, you would redirect to a login page here.
    # st.switch_page("pages/login.py")
    pass 

# Placeholder for user identity if not logged in (for local testing)
if "role" not in st.session_state:
    st.session_state["role"] = "admin" # Default for testing
    st.session_state["username"] = "TestUser"
    
if st.session_state.get("role") not in REQUIRED_ROLES:
    st.error("❌ You do not have permission to access this page. Required roles: Packaging, Dispatch, Admin.")
    st.stop()
    
USER_IDENTITY = st.session_state.get("username", st.session_state["role"]) 
st.markdown(f"### 👋 Logged in as: **{USER_IDENTITY}** ({st.session_state['role'].title()})")

# ---------------- TITLE & HEADER ----------------
st.title("🚚 Logistics Department (Packing, Storage & Dispatch)")
st.caption("Manage orders through the Packing, Storage, and Dispatch stages with streamlined UI.")

# ---------------- LOAD ORDERS ----------------
@st.cache_data(ttl=1) # Cache data for 1 second to improve responsiveness
def load_and_categorize_orders():
    # Attempt to read data from the database.
    try:
        orders = read("orders") or {}
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        orders = {}
        
    pending_packing: Dict[str, Any] = {}
    pending_storage: Dict[str, Any] = {}
    pending_dispatch: Dict[str, Any] = {}
    completed_final: Dict[str, Any] = {}

    for key, o in orders.items():
        if not isinstance(o, dict):
            continue

        stage = o.get("stage")

        if stage == "Packing":
            pending_packing[key] = o
        elif stage == "Storage":
            pending_storage[key] = o
        elif stage == "Dispatch":
            pending_dispatch[key] = o
        elif stage == "Completed":
            completed_final[key] = o
    
    return pending_packing, pending_storage, pending_dispatch, completed_final

pending_packing, pending_storage, pending_dispatch, completed_final = load_and_categorize_orders()
all_orders = {**pending_packing, **pending_storage, **pending_dispatch, **completed_final}


# ---------------- UI: MAIN SCREEN GLOBAL FILTERS ----------------
st.markdown("---")
st.subheader("🌐 Global Filters")

# Prepare filter options
all_customers = sorted(list(set(o.get("customer") for o in all_orders.values() if o.get("customer"))))
customer_options = ["All"] + all_customers
priority_options = ["All", "High", "Medium", "Low"]

col_p, col_c = st.columns(2)

with col_p:
    selected_priority = st.selectbox("Filter by Priority", priority_options, key="global_priority_filter")

with col_c:
    selected_customer = st.selectbox("Filter by Customer", customer_options, key="global_customer_filter")
    
st.markdown("---")


# ---------------- FILTERING & SORTING LOGIC ----------------
def apply_filters(orders_dict: Dict[str, Any], search_term: str, priority_filter: str, customer_filter: str) -> List[Tuple[str, Any]]:
    """Applies global filters (search, priority, customer) to an order dictionary."""
    filtered_list = []
    search_term = search_term.lower().strip()
    
    for key, o in orders_dict.items():
        # 1. Search Filter (Order ID or Item)
        search_match = True
        if search_term:
            order_id = str(o.get("order_id", "")).lower()
            item = str(o.get("item", "")).lower()
            if search_term not in order_id and search_term not in item:
                search_match = False
        
        # 2. Priority Filter
        priority_match = True
        if priority_filter != "All":
            if o.get("priority", "Medium") != priority_filter:
                priority_match = False
                
        # 3. Customer Filter
        customer_match = True
        if customer_filter != "All":
            if o.get("customer", "") != customer_filter:
                customer_match = False

        if search_match and priority_match and customer_match:
            filtered_list.append((key, o))
            
    # Sort the results by priority and then by arrival time
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    
    if not orders_dict: 
        return []

    # Determine the correct timestamp for sorting based on the stage
    current_stage = next(iter(orders_dict.values())).get("stage", "Packing") if orders_dict else "Packing"
    
    sort_key_map = {
        "Packing": "assembly_completed_at",
        "Storage": "packing_completed_at",
        "Dispatch": "storage_completed_at", 
        "Completed": "completed_at"
    }
    
    def dispatch_sort_key(item):
        o = item[1]
        timestamp = o.get("storage_completed_at") or o.get("packing_completed_at") or "2099-12-31"
        return (
            priority_rank.get(o.get("priority", "Medium"), 1),
            timestamp
        )
        
    if current_stage == "Dispatch":
        sorted_results = sorted(filtered_list, key=dispatch_sort_key)
    elif current_stage == "Completed":
        sorted_results = sorted(
            filtered_list, 
            key=lambda x: (x[1].get(sort_key_map["Completed"], "0000-01-01")), 
            reverse=True
        )
    else:
        sort_key = sort_key_map.get(current_stage, "assembly_completed_at")
        sorted_results = sorted(
            filtered_list,
            key=lambda x: (
                priority_rank.get(x[1].get("priority", "Medium"), 1),
                x[1].get(sort_key, "2099-12-31")
            )
        )
        
    return sorted_results

# ---------------- UTILITIES ----------------

def parse_datetime_robust(date_str: str) -> Optional[datetime]:
    """Tries to parse datetime from ISO format, then from the custom format."""
    if not date_str:
        return None
    dt = None
    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        try:
            IST = timezone(timedelta(hours=5, minutes=30))
            dt = datetime.strptime(date_str, '%d %b %Y, %I:%M %p').replace(tzinfo=IST).astimezone(timezone.utc)
        except Exception:
            return None
    if dt and dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def calculate_time_diff(start: Optional[str], end: Optional[str]) -> str:
    """
    FIXED VERSION:
    - If end timestamp exists but start is missing → show 0:00:00 (completed).
    - If both exist → show real duration.
    - If only start exists → Running…
    - If neither exists → Not Started.
    """
    t1 = parse_datetime_robust(start)
    t2 = parse_datetime_robust(end)

    # End exists, start missing → Completed with zero duration
    if t2 and not t1:
        return "Total Time: **0:00:00**"

    # Normal case: start and end both exist
    if t1 and t2:
        try:
            diff = t2 - t1
            return f"Total Time: **{str(diff).split('.')[0]}**"
        except:
            return "Time Calculation Error"

    # Running task
    if t1:
        return "⏳ Running…"

    # Not started at all
    return "Not Started"


def detect_file_type(data: Optional[str]):
    """Detects file type from base64 data."""
    if not data:
        return None, None, None
    if len(data) % 4 != 0:
        data += '=' * (4 - len(data) % 4)
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception:
        return "bin", "application/octet-stream", ".bin"
    header = raw[:10]
    if header.startswith(b"%PDF"): return "pdf", "application/pdf", ".pdf"
    if header.startswith(b"\x89PNG"): return "png", "image/png", ".png"
    if header[:3] == b"\xff\xd8\xff": return "jpg", "image/jpeg", ".jpg"
    return "bin", "application/octet-stream", ".bin"

def download_button_ui(label: str, b64: Optional[str], order_id: str, fname: str, key_suffix: str):
    """Standard download button wrapper."""
    if not b64: return
    if len(b64) % 4 != 0:
        b64 += '=' * (4 - len(b64) % 4)
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        st.error(f"Error decoding base64 data for {label}. File may be corrupted.")
        return
    _, mime, ext = detect_file_type(b64)
    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime or "application/octet-stream",
        key=f"dl_{fname}_{order_id}_{key_suffix}",
        use_container_width=True
    )

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
tab1, tab2, tab3, tab4 = st.tabs([
    f"📦 Pending Packing",
    f"🏬 Storage",
    f"🚀 Pending Dispatch",
    f"✅ Finalized Orders"
])

# =================================================================
# TAB 1: PENDING PACKING
# =================================================================
with tab1:
    search_packing = st.text_input("Search Packing Orders (ID/Item)", key="search_packing_key", placeholder="Enter Order ID or Item Name...")
    
    # Apply filters to the raw data
    filtered_packing = apply_filters(pending_packing, search_packing, selected_priority, selected_customer)
    st.subheader(f"Orders to Pack ({len(filtered_packing)})")
    
    if not filtered_packing:
        st.success("🎉 No pending packing work matching your criteria!")

    for key, o in filtered_packing:
        order_id = o["order_id"]
        start = o.get("packing_start")
        end = o.get("packing_end")
        packing_file = o.get("packing_file")

        # --- DEADLINE WATCH ---
        arrived_str = o.get("assembly_completed_at")
        status_message = "Waiting for Assembly completion."
        status_type = st.info
        
        if arrived_str:
            arrived_dt = parse_datetime_robust(arrived_str)
            if arrived_dt:
                now_utc = datetime.now(timezone.utc)
                time_diff = now_utc - arrived_dt
                deadline = timedelta(hours=36) # 36 hours limit
                
                if time_diff > deadline:
                    overdue_by = time_diff - deadline
                    status_message = f"⛔ OVERDUE by **{str(overdue_by).split('.')[0]}**"
                    status_type = st.error
                else:
                    remaining_time = deadline - time_diff
                    status_message = f"🟢 Remaining: **{str(remaining_time).split('.')[0]}**"
                    status_type = st.success

        # Get current details for fields (use session state for unsaved changes)
        current_assign = st.session_state.get(f"p_assign_{order_id}", o.get("packing_assigned", ""))
        current_material = st.session_state.get(f"p_material_{order_id}", o.get("packing_material", ""))
        current_notes = st.session_state.get(f"p_notes_{order_id}", o.get("packing_notes", ""))

        # --- UI: Expander for each order ---
        header_cols = st.columns([0.5, 3, 1, 2, 2])
        header_cols[0].markdown(f"### {order_id}")
        header_cols[1].markdown(f"**{o.get('item')}** for *{o.get('customer')}*")
        header_cols[2].metric("Qty", f"{o.get('qty', 0):,}")
        header_cols[3].metric("Priority", o.get("priority", "Medium"))
        with header_cols[4]:
            st.caption("Time from Assembly:")
            status_type(status_message, icon="⏱️")
            
        with st.expander(f"📦 Details for Order {order_id}", expanded=False):
            
            col_time_files, col_details = st.columns([1, 1.5])
            
            # COLUMN 1: TIME & FILES
            with col_time_files:
                st.subheader("⏱ Time Tracking & Tags")

                # Time Tracking
                time_container = st.container(border=True)
                with time_container:
                    if not start:
                        if st.button("▶️ Start Packing", key=f"p_start_{order_id}", use_container_width=True, type="secondary"):
                            update(f"orders/{key}", {
                                "packing_start": datetime.now(timezone.utc).isoformat(),
                                "packing_started_by": USER_IDENTITY
                            }) 
                            st.rerun()
                    elif not end:
                        if st.button("⏹ End Packing", key=f"p_end_{order_id}", use_container_width=True, type="primary"):
                            update(f"orders/{key}", {
                                "packing_end": datetime.now(timezone.utc).isoformat(),
                                "packing_ended_by": USER_IDENTITY
                            }) 
                            st.rerun()
                        start_dt = parse_datetime_robust(start)
                        st.info(f"Running since: **{start_dt.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M IST')}**" if start_dt else "Running...")
                        st.caption(f"Started by: `{o.get('packing_started_by', 'N/A')}`")
                    else:
                        st.success("✅ Task Completed")
                        st.markdown(calculate_time_diff(start, end))
                        st.caption(f"Completed by: `{o.get('packing_ended_by', 'N/A')}`")

                st.markdown("---")

                # QR Code & Slip
                st.subheader("🔳 Order QR Tag")
                qr_b64 = o.get("order_qr") 
                if qr_b64:
                    qr_col, dl_col = st.columns([1, 1])
                    with qr_col:
                        st.image(base64.b64decode(qr_b64), width=150)
                    with dl_col:
                        st.markdown("For quick scanning & audit.")
                        download_button_ui("⬇ Download Order QR (PNG)", qr_b64, order_id, "order_QR", key)
                else:
                    st.error("QR Code Missing.")
                
                # Generate PDF Slip 
                slip_details = {
                    "assign": current_assign, "material": current_material, 
                    "notes": current_notes, "generated_by": USER_IDENTITY
                }
                slip_pdf = generate_slip_pdf(o, slip_details, "Packing Job", [
                    ("Assigned To", "assign"), ("Material Used", "material")
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
                
                # Input fields
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
                file_container = st.container(border=True)
                with file_container:
                    if packing_file:
                        st.success("✅ Output File Uploaded")
                        file_type, _, _ = detect_file_type(packing_file)
                        if file_type in ["png", "jpg"]: 
                            st.image(base64.b64decode(packing_file), use_container_width=True, caption="Packing Proof Preview")
                        else: 
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
                
                # --- MOVE TO STORAGE ---
                is_time_ended = bool(end)
                is_file_uploaded = bool(packing_file)
                is_ready = is_time_ended and is_file_uploaded

                if is_ready:
                    if st.button("🏬 Move to Storage", key=f"p_next_{order_id}", type="primary", use_container_width=True):
                        now = datetime.now(timezone.utc).isoformat()
                        update(f"orders/{key}", {
                            "stage": "Storage",
                            "packing_end": now, 
                            "packing_completed_at": now 
                        })
                        st.success("✅ Order moved to Storage queue!")
                        st.balloons()
                        st.rerun()
                else:
                    st.error("⚠ **NOT READY TO MOVE TO STORAGE**")
                    missing_items = []
                    if not is_time_ended: missing_items.append("⏹ End Packing Time")
                    if not is_file_uploaded: missing_items.append("📁 Upload Final Output/Proof File")
                    st.markdown("**:red[Missing:]** " + ", ".join(missing_items))
        st.markdown("---")


# =================================================================
# TAB 2: STORAGE
# =================================================================
with tab2:
    search_storage = st.text_input("Search Storage Orders (ID/Item)", key="search_storage_key", placeholder="Enter Order ID or Item Name...")

    # Apply filters
    filtered_storage = apply_filters(pending_storage, search_storage, selected_priority, selected_customer)
    st.subheader(f"Orders in Storage ({len(filtered_storage)})")
    
    if not filtered_storage:
        st.success("🎉 No orders currently in storage matching your criteria!")
    
    for key, o in filtered_storage:
        order_id = o["order_id"]
        
        with st.container(border=True):
            # ---- HEADER ----
            col_id, col_priority, col_time, col_action = st.columns([3, 1.5, 3, 2])
            
            col_id.markdown(f"### 📦 Order {order_id}")
            col_id.caption(f"**Item:** {o.get('item')} | **Customer:** {o.get('customer')}")
            col_priority.metric("Priority", o.get("priority", "Medium"))
            
            arrived_str = o.get("packing_completed_at")
            if arrived_str:
                arrived_dt = parse_datetime_robust(arrived_str)
                if arrived_dt:
                    time_in_storage = datetime.now(timezone.utc) - arrived_dt
                    col_time.metric("Time in Storage", str(time_in_storage).split('.')[0], delta_color="off")
                else:
                    col_time.info("Time of arrival missing.")
            
            with col_action:
                 if st.button("🚀 Pull for Dispatch", key=f"s_next_{order_id}", type="primary", use_container_width=True):
                    now = datetime.now(timezone.utc).isoformat()
                    update(f"orders/{key}", {
                        "stage": "Dispatch",
                        "storage_completed_at": now # Track time out of storage
                    })
                    st.toast("✅ Order moved to Dispatch queue!")
                    st.rerun()
            
            st.divider()

            col_audit, col_proof = st.columns(2)
            
            with col_audit:
                st.markdown("##### 🔍 Packing Audit Details")
                st.markdown(f"""
                - **Packed By:** `{o.get("packing_ended_by", "N/A")}`
                - **Material Used:** `{o.get("packing_material", "N/A")}`
                - **Notes:** *{o.get("packing_notes", "None")}*
                """)
                
            with col_proof:
                st.markdown("##### 📁 Packing Proof")
                if o.get("packing_file"):
                    download_button_ui(
                        "⬇ Download Packing Proof", 
                        o["packing_file"], 
                        o["order_id"], 
                        "packing_final_proof",
                        key
                    )
                else:
                    st.warning("No final file uploaded.")
        st.markdown("---")

# =================================================================
# TAB 3: PENDING DISPATCH
# =================================================================
with tab3:
    search_dispatch = st.text_input("Search Dispatch Orders (ID/Item)", key="search_dispatch_key", placeholder="Enter Order ID or Item Name...")
    
    # Apply filters
    filtered_dispatch = apply_filters(pending_dispatch, search_dispatch, selected_priority, selected_customer)
    st.subheader(f"Orders for Dispatch ({len(filtered_dispatch)})")
    
    if not filtered_dispatch:
        st.success("🎉 No pending dispatch work matching your criteria!")
    
    for key, o in filtered_dispatch:
        order_id = o["order_id"]
        start = o.get("dispatch_start")
        end = o.get("dispatch_end")
        
        # --- DEADLINE WATCH ---
        arrived_str = o.get("storage_completed_at") or o.get("packing_completed_at")
        status_message = "Waiting for previous stage completion."
        status_type = st.info
        
        if arrived_str:
            arrived_dt = parse_datetime_robust(arrived_str)
            if arrived_dt:
                now_utc = datetime.now(timezone.utc)
                time_diff = now_utc - arrived_dt
                deadline = timedelta(hours=48) # 48 hours for dispatch
                
                if time_diff > deadline:
                    remaining_time = time_diff - deadline
                    status_message = f"⛔ OVERDUE by **{str(remaining_time).split('.')[0]}**"
                    status_type = st.error
                else:
                    remaining_time = deadline - time_diff
                    status_message = f"🟢 Remaining: **{str(remaining_time).split('.')[0]}**"
                    status_type = st.success

        # Get current details
        current_courier = st.session_state.get(f"d_courier_{order_id}", o.get("courier", ""))
        current_tracking = st.session_state.get(f"d_tracking_{order_id}", o.get("tracking_number", ""))
        current_notes = st.session_state.get(f"d_notes_{order_id}", o.get("dispatch_notes", ""))

        # --- UI: Expander for each order ---
        header_cols = st.columns([0.5, 3, 1, 2, 2])
        header_cols[0].markdown(f"### {order_id}")
        header_cols[1].markdown(f"**{o.get('item')}** for *{o.get('customer')}*")
        header_cols[2].metric("Qty", f"{o.get('qty', 0):,}")
        header_cols[3].metric("Priority", o.get("priority", "Medium"))
        with header_cols[4]:
            st.caption("Time from Storage:")
            status_type(status_message, icon="⏱️")
            
        with st.expander(f"🚀 Details for Order {order_id}", expanded=False):
            
            col_time_files, col_details = st.columns([1, 1.5])

            # COLUMN 1: TIME & TAGS
            with col_time_files:
                st.subheader("⏱ Time Tracking & Tags")

                # Time Tracking
                time_container = st.container(border=True)
                with time_container:
                    if not start:
                        if st.button("▶️ Start Dispatch", key=f"d_start_{order_id}", use_container_width=True, type="secondary"):
                            update(f"orders/{key}", {
                                "dispatch_start": datetime.now(timezone.utc).isoformat(),
                                "dispatch_started_by": USER_IDENTITY
                            }) 
                            st.rerun()
                    elif not end:
                        if st.button("⏹ End Dispatch", key=f"d_end_{order_id}", use_container_width=True, type="primary"):
                            update(f"orders/{key}", {
                                "dispatch_end": datetime.now(timezone.utc).isoformat(),
                                "dispatch_ended_by": USER_IDENTITY
                            }) 
                            st.rerun()
                        start_dt = parse_datetime_robust(start)
                        st.info(f"Running since: **{start_dt.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M IST')}**" if start_dt else "Running...")
                        st.caption(f"Started by: `{o.get('dispatch_started_by', 'N/A')}`")
                    else:
                        st.success("✅ Task Completed")
                        st.markdown(calculate_time_diff(start, end))
                        st.caption(f"Completed by: `{o.get('dispatch_ended_by', 'N/A')}`")


                st.markdown("---")

                # QR Code & Slip
                st.subheader("🔳 Order QR Tag")
                qr_b64 = o.get("order_qr") 
                if qr_b64:
                    qr_col, dl_col = st.columns([1, 1])
                    with qr_col:
                        st.image(base64.b64decode(qr_b64), width=150)
                    with dl_col:
                        st.markdown("For quick scanning & audit.")
                        download_button_ui("⬇ Download Order QR (PNG)", qr_b64, order_id, "order_QR", key)
                else:
                    st.error("QR Code Missing.")
                
                # Generate PDF Slip 
                slip_details = {
                    "courier": current_courier, "tracking": current_tracking, 
                    "notes": current_notes, "generated_by": USER_IDENTITY
                }
                slip_pdf = generate_slip_pdf(o, slip_details, "Dispatch", [
                    ("Courier", "courier"), ("Tracking No", "tracking")
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
                        update(f"orders/{key}", {
                            "stage": "Completed",
                            "completed_at": now, 
                            "dispatch_end": o.get("dispatch_end") or now,   # FIX ADDED
                            "dispatch_completed_at": now,
                            "dispatch_completed_by": USER_IDENTITY
                        })
                        st.success("✅ Order marked as COMPLETED and dispatched!")
                        st.balloons()
                        st.rerun()
                else:
                    st.error("⚠ **NOT READY TO MARK AS COMPLETED**")
                    missing_items = []
                    if not is_time_ended: missing_items.append("⏹ End Dispatch Time")
                    if not is_details_filled: missing_items.append("Tracking Number and Courier")
                    st.markdown("**:red[Missing:]** " + ", ".join(missing_items))
        st.markdown("---")

# =================================================================
# TAB 4: FINALIZED ORDERS
# =================================================================
with tab4:
    search_completed = st.text_input("Search Completed Orders (ID/Item)", key="search_completed_key", placeholder="Enter Order ID or Item Name...")

    # Apply filters
    filtered_completed = apply_filters(completed_final, search_completed, selected_priority, selected_customer)
    st.subheader(f"Finalized Orders ({len(filtered_completed)})")
    
    if not filtered_completed:
        st.info("No orders have been finalized yet or match the filters.")
        
    for key, o in filtered_completed:
        # Get times for display
        packing_start = o.get("packing_start")
        packing_end = o.get("packing_end")
        dispatch_start = o.get("dispatch_start")
        dispatch_end = o.get("dispatch_end")
        
        # Convert completion time to IST for display
        comp_dt_ist = 'N/A'
        try:
            comp_dt_utc = parse_datetime_robust(o.get('completed_at', ''))
            if comp_dt_utc:
                IST = timezone(timedelta(hours=5, minutes=30))
                comp_dt_ist = comp_dt_utc.astimezone(IST).strftime('%Y-%m-%d %H:%M IST')
        except:
             pass

        with st.expander(f"✅ {o['order_id']} — **{o.get('item')}** | Finalized: **{comp_dt_ist.split(' ')[0]}**", expanded=False):
            
            st.markdown(f"#### Order {o['order_id']} Audit Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("Packing Time", calculate_time_diff(packing_start, packing_end), delta_color="off")
            c2.metric("Dispatch Time", calculate_time_diff(dispatch_start, dispatch_end), delta_color="off")
            c3.metric("Finalized At", comp_dt_ist, delta_color="off")
            
            st.divider()
            
            col_packing, col_dispatch = st.columns(2)

            with col_packing:
                st.markdown("##### 📦 Packing Details")
                st.markdown(f"""
                - **Assigned To:** `{o.get("packing_assigned", "N/A")}`
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
            
            with col_dispatch:
                st.markdown("##### 🚀 Dispatch Details")
                st.markdown(f"""
                - **Courier:** `{o.get("courier", "N/A")}`
                - **Tracking No:** `{o.get("tracking_number", "N/A")}`
                - **Completed By:** `{o.get("dispatch_completed_by", "N/A")}`
                """)
                st.caption(f"Notes: {o.get('dispatch_notes', 'None')}")
        st.markdown("---")
