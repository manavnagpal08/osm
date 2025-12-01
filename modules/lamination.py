import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
import pytz

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Lamination Department",
    layout="wide",
    page_icon="🛡️"
)

# ---------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------
IS_ADMIN = st.session_state.get("role") == "admin"

if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["lamination", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🛡️ Lamination Department")
st.caption("Apply protective film (Lamination/Varnishing) to printed sheets and move to the next finishing stage.")
st.markdown("---")

# ========================================================
# TIME HELPERS — IST FORMAT
# ========================================================
IST = pytz.timezone("Asia/Kolkata")

def now_ist_formatted():
    """Returns human-readable format: 01 Dec 2025, 4:20 PM"""
    return datetime.now(IST).strftime("%d %b %Y, %I:%M %p")

def calculate_duration(start_time_str: str, end_time_str: str) -> str:
    """Calculates duration between two IST formatted strings."""
    if not start_time_str or not end_time_str:
        return "N/A"
    
    try:
        dt_format = "%d %b %Y, %I:%M %p" 
        start_dt = datetime.strptime(start_time_str, dt_format).replace(tzinfo=IST)
        end_dt = datetime.strptime(end_time_str, dt_format).replace(tzinfo=IST)
        
        duration = end_dt - start_dt
        
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        
        return f"{hours}h {minutes}m"
    except Exception:
        return "N/A (Time Error)"

# ---------------------------------------------------
# LOAD ORDERS & USERS
# ---------------------------------------------------
orders = read("orders") or {}
users_data = read("users") or {}

lamination_operators = ["Unassigned"]
for user_dict in users_data.values():
    if isinstance(user_dict, dict) and user_dict.get('role') == 'lamination' and user_dict.get('name'):
        lamination_operators.append(user_dict['name'])

if len(lamination_operators) == 1:
    lamination_operators.extend(["Lam Op 1", "Lam Op 2"]) 

all_pending_orders = {}
all_completed_orders = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # Lamination handles orders coming from Printing
    if o.get("stage") == "Lamination":
        all_pending_orders[key] = o
    elif o.get("lamination_completed_at"):
        all_completed_orders[key] = o


# ========================================================
# FILTER AND SEARCH SETUP
# ========================================================

st.header("🔎 Job Filters")
search_col, assign_col = st.columns([3, 2])

with search_col:
    search_query = st.text_input(
        "Search by Order ID or Customer Name", 
        key="lamination_search_global",
        placeholder="Enter Order ID or Customer Name..."
    ).lower()

with assign_col:
    assign_filter = st.selectbox(
        "Filter by Assigned Operator",
        options=["All"] + lamination_operators,
        index=0,
        key="lamination_assign_filter",
        label_visibility="visible"
    )
    
st.markdown("---")

# Function to apply filters
def apply_filters(orders_dict, search_q, assign_f):
    filtered_orders = {}
    for key, order in orders_dict.items():
        
        assigned_to = order.get("lamination_assigned_to", "Unassigned")
        assign_match = (assign_f == "All" or assigned_to == assign_f)
        
        search_match = True
        if search_q:
            order_id = order.get("order_id", "").lower()
            customer = order.get("customer", "").lower()
            
            if search_q not in order_id and search_q not in customer:
                search_match = False
                
        if assign_match and search_match:
            filtered_orders[key] = order
            
    # Sort pending jobs by order of entry (e.g., key/oldest first)
    return dict(sorted(filtered_orders.items(), key=lambda item: item[1].get('printing_completed_at', 'Z')))


# Apply filters
filtered_pending = apply_filters(all_pending_orders, search_query, assign_filter)
filtered_completed = apply_filters(all_completed_orders, search_query, assign_filter)


# ---------------------------------------------------
# FILE DOWNLOAD HANDLER (Auto-detect file type)
# ---------------------------------------------------
def download_button(label, b64_data, order_id, fname, key_prefix):
    """Handles file download using base64 data."""
    if not b64_data:
        return

    raw = base64.b64decode(b64_data)
    head = raw[:10]

    mime_map = {
        b"%PDF": ("pdf", "application/pdf"),
        b"\x89PNG": ("png", "image/png"),
        b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    }
    
    ext, mime = ".bin", "application/octet-stream"
    
    # Check for known file headers
    for header, (e, m) in mime_map.items():
        if raw.startswith(header):
            ext, mime = f".{e}", m
            break
        elif header == b"\xff\xd8\xff" and head[:3] == header:
            ext, mime = f".{e}", m
            break

    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime,
        key=f"{key_prefix}_{order_id}",
        use_container_width=True
    )

# ---------------------------------------------------
# PURE PYTHON PDF SLIP GENERATOR
# ---------------------------------------------------
def generate_lamination_slip(order, film_type, temp, pressure, assign_to, qc_status):

    # Build final text with multiple lines
    lines = [
        "LAMINATION DEPARTMENT – JOB SLIP",
        "",
        f"Order ID: {order.get('order_id')}",
        f"Customer: {order.get('customer')}",
        f"Item: {order.get('item')}",
        f"Product Type: {order.get('product_type', 'N/A')}",
        "",
        "--- LAMINATION SPECIFICATIONS ---",
        f"Film Type: {film_type}",
        f"Temperature: {temp}",
        f"Pressure: {pressure}",
        f"Assigned To: {assign_to}",
        f"Quality Check: {qc_status}",
        "",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]

    # Escape PDF special characters
    def esc(s):
        return s.replace("(", "\\(").replace(")", "\\)")

    # Build PDF text block with each line
    pdf_text = "BT\n/F1 12 Tf\n50 750 Td\n"
    for line in lines:
        if line.startswith('---'):
             pdf_text += "/F1 14 Tf\n" # Larger font for headers
        else:
             pdf_text += "/F1 12 Tf\n"
        pdf_text += f"({esc(line)}) Tj\n0 -18 Td\n"
    pdf_text += "ET"

    # Assemble the PDF structure (Standard PDF Boilerplate)
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources << /Font << /F1 5 0 R >> >>
/Contents 4 0 R
>>
endobj
4 0 obj
<< /Length {len(pdf_text)} >>
stream
{pdf_text}
endstream
endobj
5 0 obj
<< /Type /Font
   /Subtype /Type1
   /BaseFont /Courier
>>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000075 00000 n 
0000000144 00000 n 
0000000334 00000 n 
0000000580 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
700
%%EOF
"""

    return pdf.encode("utf-8", errors="ignore")


# ---------------------------------------------------
# TABS
# ---------------------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Lamination ({len(filtered_pending)})",
    f"✔ Completed Lamination ({len(filtered_completed)})"
])

# ---------------------------------------------------
# TAB 1 — PENDING JOBS
# ---------------------------------------------------
with tab1:
    if not filtered_pending:
        st.success("🎉 No pending lamination work matching your filters!")
        
    for key, o in filtered_pending.items():
        order_id = o["order_id"]
        
        # Determine the next stage
        is_box = o.get("product_type", "").lower() == "box"
        next_stage = "DieCut" if is_box else "Assembly"
        next_stage_label = "DieCut (Box)" if is_box else "Assembly (Flat)"
        
        # Load existing specs/data
        film_type_current = o.get("film_type", "Gloss")
        temp_current = o.get("lamination_temp", "100°C")
        pressure_current = o.get("lamination_pressure", "Medium")
        qc_current = o.get("lamination_qc", "Pass")
        assign_current = o.get("lamination_assigned_to", "Unassigned")
        notes_current = o.get("lamination_notes", "")

        with st.container(border=True):
            st.subheader(f"🛡️ Order **{order_id}** — {o.get('product_type')}")
            st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")
            st.caption(f"From Printing: **{o.get('printing_completed_at', 'N/A')}**")
            st.divider()

            # ---------------- TIME TRACKING ----------------
            st.subheader("⏱ Time Tracking")

            start_time_ist = o.get("lamination_start")
            end_time_ist = o.get("lamination_end")

            col_start, col_end = st.columns(2)

            with col_start:
                if not start_time_ist:
                    if st.button("▶ Start Lamination", key=f"start_{order_id}", type="primary", use_container_width=True):
                        update(f"orders/{key}", {"lamination_start": now_ist_formatted()})
                        st.toast("Lamination job started!", icon="▶️")
                        st.rerun()
                else:
                    st.success(f"Started: **{start_time_ist}**")

            with col_end:
                if start_time_ist and not end_time_ist:
                    if st.button("⏹ End Lamination", key=f"end_{order_id}", use_container_width=True):
                        update(f"orders/{key}", {"lamination_end": now_ist_formatted()})
                        st.toast("Lamination job ended!", icon="⏹")
                        st.rerun()
                elif end_time_ist:
                    st.success(f"Ended: **{end_time_ist}**")
                else:
                    st.info("Awaiting start.")


            st.divider()

            # ---------------- DETAILS ----------------
            st.subheader("⚙️ Process Details")

            col1, col2, col3 = st.columns(3)

            with col1:
                film_type = st.selectbox(
                    "Film/Finish Type",
                    ["Gloss", "Matt", "Spot UV", "Aqueous Varnish"],
                    index=["Gloss", "Matt", "Spot UV", "Aqueous Varnish"].index(film_type_current) if film_type_current in ["Gloss", "Matt", "Spot UV", "Aqueous Varnish"] else 0,
                    key=f"film_type_{order_id}"
                )
            
            with col2:
                temp = st.text_input(
                    "Temperature", 
                    value=temp_current,
                    placeholder="e.g., 95°C",
                    key=f"temp_{order_id}"
                )
            
            with col3:
                pressure = st.selectbox(
                    "Pressure Setting",
                    ["Low", "Medium", "High"],
                    index=["Low", "Medium", "High"].index(pressure_current) if pressure_current in ["Low", "Medium", "High"] else 1,
                    key=f"pressure_{order_id}"
                )
                
            col4, col5 = st.columns(2)

            with col4:
                qc_status = st.selectbox(
                    "Quality Check Status",
                    ["Pass", "Rework Required", "Fail"],
                    index=["Pass", "Rework Required", "Fail"].index(qc_current) if qc_current in ["Pass", "Rework Required", "Fail"] else 0,
                    key=f"qc_status_{order_id}"
                )
            
            with col5:
                 assign_to = st.selectbox(
                    "Assign Work To",
                    options=lamination_operators,
                    index=lamination_operators.index(assign_current) if assign_current in lamination_operators else 0,
                    key=f"assign_{order_id}"
                )


            notes = st.text_area(
                "Notes (Lamination)",
                value=notes_current,
                key=f"notes_{order_id}"
            )
            
            if st.button("💾 Save Lamination Details", key=f"save_details_{order_id}", type="secondary", use_container_width=True):
                update(f"orders/{key}", {
                    "film_type": film_type,
                    "lamination_temp": temp,
                    "lamination_pressure": pressure,
                    "lamination_qc": qc_status,
                    "lamination_assigned_to": assign_to,
                    "lamination_notes": notes
                })
                st.toast("Details Saved!", icon="💾")
                st.rerun()

            st.divider()

            # ---------------- SLIP DOWNLOAD ----------------
            st.subheader("📄 Download Job Slip")
            
            slip_bytes = generate_lamination_slip(
                o, film_type, temp, pressure, assign_to, qc_status
            )

            st.download_button(
                label="⬇ Download Lamination Slip (PDF)",
                data=slip_bytes,
                file_name=f"{order_id}_lamination_slip.pdf",
                mime="application/pdf",
                key=f"slip_dl_{order_id}",
                use_container_width=True
            )
            
            st.divider()

            # ---------------- COMPLETE & MOVE TO NEXT ----------------
            if start_time_ist and end_time_ist:
                if qc_status == "Pass":
                    if st.button(f"🚀 Move to {next_stage_label}", key=f"move_{order_id}", type="primary", use_container_width=True):
                        now = now_ist_formatted()
                        update(f"orders/{key}", {
                            "stage": next_stage, # Next Stage
                            "lamination_completed_at": now,
                        })
                        st.success(f"Moved to {next_stage} Stage!")
                        st.balloons()
                        st.rerun()
                else:
                    st.error("Cannot move to next stage: Quality Check Status is not 'Pass'.")
            else:
                st.warning("Please record both **Start** and **End** times before moving to the next stage.")

# ---------------------------------------------------
# TAB 2 — COMPLETED JOBS
# ---------------------------------------------------
with tab2:
    st.header("✔ Completed Lamination Jobs")
    
    if not filtered_completed:
        st.info("No completed lamination orders matching your filters yet.")

    for key, o in filtered_completed.items():
        order_id = o.get("order_id")
        
        start_time = o.get("lamination_start")
        end_time = o.get("lamination_end")
        duration = calculate_duration(start_time, end_time)

        with st.container(border=True):
            st.write(f"### ✔️ Order **{order_id}** — {o.get('customer')}")
            st.caption(f"Completed At: **{o.get('lamination_completed_at')}** | Assigned: **{o.get('lamination_assigned_to', 'N/A')}**")
            
            is_box = o.get("product_type", "").lower() == "box"
            next_stage = "DieCut" if is_box else "Assembly"
            st.info(f"Moved to **{o.get('stage', next_stage)}** Stage.")
            
            # Metrics
            metric_cols = st.columns(3)
            metric_cols[0].metric("Start Time", start_time or "N/A")
            metric_cols[1].metric("End Time", end_time or "N/A")
            metric_cols[2].metric("Duration", duration)
            
            st.markdown("---")

            # Details
            st.subheader("Process Summary")
            spec_cols = st.columns(3)
            spec_cols[0].markdown(f"**Film/Finish:** `{o.get('film_type', 'N/A')}`")
            spec_cols[1].markdown(f"**Temperature:** `{o.get('lamination_temp', 'N/A')}`")
            spec_cols[2].markdown(f"**QC Status:** `{o.get('lamination_qc', 'N/A')}`")
            
            # Notes
            st.markdown(f"**Notes:** {o.get('lamination_notes', 'No notes recorded.')}")

            st.markdown("---")
