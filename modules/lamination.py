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
# FILE PREVIEW
# ---------------------------------------------------
def preview(label, b64):
    """Previews an image or PDF placeholder."""
    if not b64:
        st.warning(f"{label} missing.")
        return

    raw = base64.b64decode(b64)
    head = raw[:10]

    st.markdown(f"#### 📄 {label} Preview")

    if raw.startswith(b"%PDF"):
        st.info("PDF detected — Please download to view.")
    elif raw.startswith(b"\x89PNG") or raw[:3] == b"\xff\xd8\xff":
        # Check if it's an image before displaying
        try:
            st.image(raw, use_container_width=True)
        except Exception:
            st.warning("File is uploaded but format is not suitable for inline preview.")
    else:
        st.caption("File type not suitable for inline preview (AI, ZIP, etc.).")


# ---------------------------------------------------
# STYLED HTML REPORT GENERATOR (Replaces simple PDF slip)
# ---------------------------------------------------
def generate_lamination_html_report(order, film_type, temp, pressure, assign_to, qc_status):
    """Generates a styled HTML report for Lamination for browser printing to PDF."""

    order_id = order.get('order_id')
    customer = order.get('customer')
    item = order.get('item')
    product_type = order.get('product_type', 'N/A')
    
    # Simple SVG logo (Shield) base64 data for visual appeal
    logo_svg_base64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMyNTY0YmMiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xMiAyMnM4LTQgOC0xMmg0LjVhNC41IDQuNSAwIDAgMC0zLjUtNFYyTDIwLjUgNFYycy00LjUuNS00LjUgNC41VjIyaDR6Ii8+PC9zdmc+"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lamination Job Report - {order_id}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
            .report-container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
            .header {{ display: flex; align-items: center; border-bottom: 3px solid #007bff; padding-bottom: 15px; margin-bottom: 25px; }}
            .logo {{ width: 50px; height: 50px; margin-right: 20px; }}
            h1 {{ color: #2564bc; margin: 0; font-size: 28px; font-weight: 600; }}
            h2 {{ color: #007bff; border-left: 4px solid #007bff; padding-left: 10px; margin-top: 30px; margin-bottom: 15px; font-size: 20px; }}
            .section {{ margin-bottom: 20px; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #e9ecef; }}
            .detail-label {{ font-weight: 600; color: #495057; width: 30%; }}
            .detail-value {{ width: 65%; text-align: right; color: #343a40; }}
            .notes-box {{ border: 1px solid #ced4da; padding: 15px; border-radius: 4px; background-color: #f8f9fa; white-space: pre-wrap; }}
            .footer {{ border-top: 1px solid #ced4da; margin-top: 40px; padding-top: 15px; text-align: center; font-size: 12px; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header">
                <img src="data:image/svg+xml;base64,{logo_svg_base64}" alt="Logo" class="logo">
                <h1>LAMINATION JOB REPORT</h1>
            </div>

            <h2>General Information</h2>
            <div class="section">
                <div class="detail-row"><span class="detail-label">Order ID:</span><span class="detail-value">{order_id}</span></div>
                <div class="detail-row"><span class="detail-label">Customer:</span><span class="detail-value">{customer}</span></div>
                <div class="detail-row"><span class="detail-label">Item Description:</span><span class="detail-value">{item}</span></div>
                <div class="detail-row"><span class="detail-label">Product Type:</span><span class="detail-value">{product_type}</span></div>
            </div>
            
            <h2>Lamination Specifications</h2>
            <div class="section">
                <div class="detail-row"><span class="detail-label">Film/Finish Type:</span><span class="detail-value">{film_type}</span></div>
                <div class="detail-row"><span class="detail-label">Temperature Used:</span><span class="detail-value">{temp}</span></div>
                <div class="detail-row"><span class="detail-label">Pressure Setting:</span><span class="detail-value">{pressure}</span></div>
            </div>

            <h2>Execution & Quality Control</h2>
            <div class="section">
                <div class="detail-row"><span class="detail-label">Assigned Operator:</span><span class="detail-value">{assign_to}</span></div>
                <div class="detail-row"><span class="detail-label">QC Status:</span><span class="detail-value" style="color: {'green' if qc_status == 'Pass' else 'red'}; font-weight: bold;">{qc_status}</span></div>
            </div>

            <h2>Operator Notes</h2>
            <div class="notes-box">{order.get('lamination_notes', 'No specific notes recorded by the operator.')}</div>

            <div class="footer">
                Report Generated: {now_ist_formatted()} <br>
                For Internal Use Only.
            </div>
        </div>
    </body>
    </html>
    """
    return html_content.encode("utf-8")


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
        lamination_file = o.get("lamination_file")
        
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

            # ---------------- FILE UPLOAD & REPORT DOWNLOAD ----------------
            col_file, col_slip = st.columns(2)

            with col_file:
                st.subheader("📁 Upload Lamination Output Proof")
                up = st.file_uploader(
                    "Upload File (Final Proof Image/PDF)",
                    type=["pdf", "png", "jpg"],
                    key=f"upl_{order_id}"
                )

                if st.button("💾 Save File", key=f"save_file_{order_id}", use_container_width=True, disabled=not up):
                    if up:
                        up.seek(0)
                        encoded = base64.b64encode(up.read()).decode()
                        update(f"orders/{key}", {"lamination_file": encoded})
                        st.success("File Uploaded!")
                        st.rerun()

                if lamination_file:
                    st.markdown("---")
                    preview("Current Lamination Proof", lamination_file)
                    download_button("⬇ Download Current File", lamination_file, order_id, "lamination_proof", f"dl_{order_id}")


            with col_slip:
                st.subheader("📄 Download Job Report")
                st.info("The report is an HTML file. Open it and use your browser's 'Print to PDF' feature for a styled document.")
                
                report_bytes = generate_lamination_html_report(
                    o, film_type, temp, pressure, assign_to, qc_status
                )

                st.download_button(
                    label="⬇ Download Lamination Report (HTML)",
                    data=report_bytes,
                    file_name=f"{order_id}_lamination_report.html",
                    mime="text/html",
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
        lamination_file_b64 = o.get("lamination_file")
        
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

            if lamination_file_b64:
                st.markdown("---")
                download_button("⬇ Download Archived Proof", lamination_file_b64, order_id, "lamination_archived_proof", f"dl2_{order_id}")

            st.markdown("---")
