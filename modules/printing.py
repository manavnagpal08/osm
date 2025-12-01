import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
import pytz

st.set_page_config(page_title="Printing Department", layout="wide", page_icon="🖨️")

# ---------------------------
# ROLE CHECK
# ---------------------------
IS_ADMIN = st.session_state.get("role") == "admin"

if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["printing", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🖨️ Printing Department")
st.markdown("---")
st.caption("Efficiently manage print production, material specifications, and job communication.")

# ========================================================
# TIME HELPERS — IST FORMAT
# ========================================================
IST = pytz.timezone("Asia/Kolkata")

def now_ist_raw():
    """Returns ISO datetime string in IST timezone."""
    return datetime.now(IST).isoformat()

def now_ist_formatted():
    """Returns human-readable format: 01 Dec 2025, 4:20 PM"""
    return datetime.now(IST).strftime("%d %b %Y, %I:%M %p")


# ---------------------------
# LOAD ORDERS & USERS (Safe Load)
# ---------------------------
orders = read("orders") or {}
users_data = read("users") or {} 
printer_names = ["Unassigned"]

for user_dict in users_data.values():
    if isinstance(user_dict, dict) and user_dict.get('role') == 'printing' and user_dict.get('name'):
        printer_names.append(user_dict['name'])

if len(printer_names) == 1:
    printer_names.extend(["Printer A", "Printer B"]) 

all_pending_orders = {}
all_completed_orders = {}
all_paper_qualities = set() 

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    printing_specs = o.get("printing_specs", {})
    paper_quality = printing_specs.get("paper_quality")
    if paper_quality and paper_quality.strip():
        all_paper_qualities.add(paper_quality.strip())

    if o.get("stage") == "Printing":
        all_pending_orders[key] = o
    elif o.get("printing_completed_at"):
        all_completed_orders[key] = o

paper_quality_options = ["All"] + sorted(list(all_paper_qualities))
assigned_to_options = ["All"] + printer_names

# ========================================================
# FILTER AND SEARCH SETUP (MAIN PAGE)
# ========================================================

st.header("🔎 Job Filters")
search_col, assign_col, quality_col = st.columns([2, 1, 1.5])

with search_col:
    search_query = st.text_input(
        "Search by Order ID or Customer Name", 
        key="printing_search_global",
        placeholder="Enter Order ID or Customer Name..."
    ).lower()

with assign_col:
    assign_filter = st.selectbox(
        "Filter by Assigned Printer",
        options=assigned_to_options,
        index=0,
        key="assign_filter",
        label_visibility="visible"
    )

with quality_col:
    quality_filter = st.selectbox(
        "Filter by Paper Quality",
        options=paper_quality_options,
        index=0,
        key="quality_filter",
        label_visibility="visible"
    )

st.markdown("---")


# Function to apply filters
def apply_filters(orders_dict, search_q, assign_f, quality_f):
    filtered_orders = {}
    for key, order in orders_dict.items():
        
        printing_specs = order.get("printing_specs", {})
        
        assigned_to = printing_specs.get("assigned_to", "Unassigned")
        assign_match = (assign_f == "All" or assigned_to == assign_f)
        
        paper_quality = printing_specs.get("paper_quality", "")
        quality_match = (quality_f == "All" or paper_quality == quality_f)
        
        search_match = True
        if search_q:
            order_id = order.get("order_id", "").lower()
            customer = order.get("customer", "").lower()
            
            if search_q not in order_id and search_q not in customer:
                search_match = False
                
        if assign_match and quality_match and search_match:
            filtered_orders[key] = order
            
    return filtered_orders

# Apply filters
filtered_pending = apply_filters(all_pending_orders, search_query, assign_filter, quality_filter)
filtered_completed = apply_filters(all_completed_orders, search_query, assign_filter, quality_filter)

# ========================================================
# HTML REPORT GENERATION FUNCTION 
# ========================================================
def generate_order_report(order: dict) -> bytes:
    """Generates a detailed HTML report string for professional print-to-PDF."""
    
    order_id = order.get("order_id", "N/A")
    design_specs = order.get("design_specs", {})
    printing_specs = order.get("printing_specs", {})
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Production Report - {order_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #264b97; color: white; padding: 15px; text-align: center; border-radius: 5px; margin-bottom: 20px; }}
            h1 {{ margin: 0; font-size: 24px; }}
            .metadata {{ text-align: right; font-size: 10px; color: #666; }}
            .section {{ margin-top: 30px; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
            h2 {{ color: #264b97; font-size: 18px; border-left: 5px solid #ff4b4b; padding-left: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }}
            th {{ background-color: #f2f2f2; }}
            .notes-box {{ background-color: #f9f9f9; border: 1px dashed #ccc; padding: 10px; margin-top: 5px; white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>PRODUCTION REPORT</h1>
            <h3>Order ID: {order_id}</h3>
        </div>
        <p class="metadata">Generated by Manufacturing System on: {now_ist_formatted()}</p>

        <div class="section">
            <h2>General Order Details</h2>
            <table>
                <tr>
                    <th>Customer Name</th>
                    <td>{order.get('customer', 'N/A')}</td>
                    <th>Item/Product</th>
                    <td>{order.get('item', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Quantity</th>
                    <td>{order.get('qty', 'N/A')}</td>
                    <th>Due Date</th>
                    <td>{order.get('due', 'N/A')}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Printing Specifications</h2>
            <table>
                <tr>
                    <th>Assigned To</th>
                    <td>{printing_specs.get('assigned_to', 'N/A')}</td>
                    <th>Paper Quality</th>
                    <td>{printing_specs.get('paper_quality', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Paper Size</th>
                    <td>{printing_specs.get('paper_size', 'N/A')}</td>
                    <th>Board Size</th>
                    <td>{printing_specs.get('board_size', 'N/A')}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Communication & Notes</h2>
            <p><strong>Admin/Sales Instructions:</strong></p>
            <div class="notes-box">{order.get('admin_notes', 'No specific instructions from Admin/Sales.')}</div>
            <p style="margin-top: 15px;"><strong>Printing Team Notes:</strong></p>
            <div class="notes-box">{printing_specs.get('printing_notes', 'No internal notes recorded.')}</div>
        </div>

        <div class="section">
            <h2>Design Stage History</h2>
            <table>
                <tr>
                    <th>Designer</th>
                    <td>{design_specs.get('assigned_to', 'N/A')}</td>
                    <th>Design Completed</th>
                    <td>{order.get('design_end_time', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Design Notes</th>
                    <td colspan="3">{order.get('design_notes', 'N/A')}</td>
                </tr>
            </table>
        </div>
        
        <p style="text-align: center; margin-top: 50px; font-size: 12px; color: #999;">--- End of Production Report ---</p>
    </body>
    </html>
    """
    return html_content.encode("utf-8")

# ---------------------------
# FILE UTILITIES
# ---------------------------

def file_download_button(label, file_entry, order_id, file_label, key_prefix):
    """Handles file download using the file entry dictionary."""
    if not file_entry or not file_entry.get("data"):
        return
    
    b64_data = file_entry.get("data")
    file_ext = file_entry.get("ext", "bin") 

    try:
        raw = base64.b64decode(b64_data)
    except Exception:
        st.error("File decode failed!")
        return

    mime_map = {
        "pdf":  "application/pdf",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "ai":   "application/postscript",
        "zip":  "application/zip"
    }

    mime = mime_map.get(file_ext.lower(), "application/octet-stream")
    
    filename = f"{order_id}_{file_label}.{file_ext}"

    st.download_button(
        label=label,
        data=raw,
        file_name=filename,
        mime=mime,
        key=f"{key_prefix}_{order_id}",
        use_container_width=True
    )

def preview_file(label, file_entry):
    """Preview PDF / PNG / JPG inline using the file entry dictionary."""
    if not file_entry or not file_entry.get("data"):
        st.info(f"Awaiting **{label}** upload.")
        return

    b64_data = file_entry.get("data")
    raw = base64.b64decode(b64_data)
    header = raw[:10]

    st.markdown(f"**{label}**")

    if header.startswith(b"\x89PNG") or header[0:3] == b"\xff\xd8\xff":
        st.image(raw, use_container_width=True)

    elif header.startswith(b"%PDF"):
        st.caption("PDF file detected. Use the **Download** button to view.")

    else:
        st.caption("File type not suitable for inline preview (AI, ZIP, etc.).")
    
    return raw

# ---------------------------
# MAIN TABS
# ---------------------------
tab1, tab2 = st.tabs([
    f"🛠️ Pending Jobs ({len(filtered_pending)})",
    f"✅ Completed Jobs ({len(filtered_completed)})"
])

# ---------------------------
# TAB 1 - PENDING
# ---------------------------
with tab1:

    if not filtered_pending:
        st.success("🎉 No pending printing jobs matching your filters!")
    else:
        for key, o in filtered_pending.items():

            order_id = o.get("order_id")
            design_files = o.get("design_files", {})
            mockup_files = o.get("printing_mockups", {})
            
            printing_specs = o.get("printing_specs", {})
            
            # Fetch admin notes from order data
            current_admin_notes = o.get("admin_notes", "No specific instructions from Admin/Sales.")
            
            with st.container(border=True):
                
                # ROW: ORDER HEADER AND METRICS
                header_col, metric_col, report_col = st.columns([2, 1, 1])

                with header_col:
                    st.markdown(f"## 🖨️ Job: **{order_id}**")
                    st.markdown(f"Customer: **{o.get('customer')}** | Item: **{o.get('item')}**")
                
                with metric_col:
                    st.metric("Qty", o.get('qty', 'N/A'))
                    st.metric("Due Date", o.get('due', 'N/A'))

                # REPORT BUTTON
                with report_col:
                    st.markdown("##### ") 
                    report_content = generate_order_report(o)
                    st.download_button(
                        label="📄 Generate Full Report (HTML/PDF)",
                        data=report_content,
                        file_name=f"{order_id}_Production_Report.html",
                        mime="text/html", 
                        key=f"report_dl_{key}",
                        use_container_width=True
                    )
                    st.caption("Open HTML file and use browser's 'Print to PDF' function.")


                st.markdown("---")

                # ===============================================
                # SECTION 1: Assignment and Specs
                # ===============================================
                st.subheader("⚙️ Specifications & Assignment")
                
                # Layout based on role (Admin gets 4 columns, Printer gets 3 fields + 1 read-only assignment)
                if IS_ADMIN:
                    a_col, pq_col, ps_col, bs_col = st.columns([1.5, 1.5, 1, 1])
                else:
                    a_col, pq_col, ps_col, bs_col = st.columns([1.5, 1.5, 1, 1])
                
                current_assignee = printing_specs.get("assigned_to", "Unassigned")
                
                # Assigned To (Controlled Access)
                with a_col:
                    if IS_ADMIN:
                        # Admin sees editable select box
                        new_assignee = st.selectbox(
                            "Assigned To",
                            options=printer_names,
                            index=printer_names.index(current_assignee) if current_assignee in printer_names else 0,
                            key=f"assign_{key}"
                        )
                    else:
                        # Printing team sees read-only text
                        st.text_input("Assigned To (Admin Only)", value=current_assignee, disabled=True, key=f"assign_ro_{key}")
                        new_assignee = current_assignee # Keep current value for save operation (if admin changes other specs)

                # Paper Quality
                with pq_col:
                    new_paper_quality = st.text_input(
                        "Paper Quality",
                        value=printing_specs.get("paper_quality", ""),
                        placeholder="e.g., 300GSM Matt",
                        key=f"pq_{key}"
                    )

                # Paper Size
                with ps_col:
                    new_paper_size = st.text_input(
                        "Paper Size",
                        value=printing_specs.get("paper_size", ""),
                        placeholder="e.g., 19x25",
                        key=f"ps_{key}"
                    )

                # Board Size
                with bs_col:
                    new_board_size = st.text_input(
                        "Board Size",
                        value=printing_specs.get("board_size", ""),
                        placeholder="Optional",
                        key=f"bs_{key}"
                    )

                # Save Specs Button (Handles assignment if Admin, and specs if Admin/Printer)
                if st.button("💾 Save Specifications", key=f"save_specs_{key}", type="secondary", use_container_width=True):
                    updated_specs = {
                        "assigned_to": new_assignee, 
                        "paper_quality": new_paper_quality,
                        "paper_size": new_paper_size,
                        "board_size": new_board_size
                    }
                    current_notes = printing_specs.get("printing_notes")
                    if current_notes is not None:
                         updated_specs["printing_notes"] = current_notes
                         
                    update(f"orders/{key}", {"printing_specs": updated_specs})
                    st.toast("Printing specs and assignment saved!", icon="💾")
                    st.rerun()

                st.markdown("---")

                # ===============================================
                # SECTION 2: Files (In Expander for Cleanliness)
                # ===============================================
                with st.expander("🖼️ View/Upload Files & Artwork", expanded=False):
                    file_col1, file_col2 = st.columns(2)
                    
                    # PRINT READY FILE (from Design)
                    with file_col1:
                        st.subheader("🎨 Final Design Art")
                        final_art_entry = design_files.get("final") 
                        
                        if not final_art_entry:
                            st.warning("⚠️ Final design file missing from Design Department!")
                        else:
                            preview_file("Print Ready File", final_art_entry)
                            st.markdown("---")
                            file_download_button(
                                "⬇️ Download Print Ready File",
                                final_art_entry, 
                                order_id,
                                "print_ready",
                                f"dl_ready_{key}"
                            )

                    # MOCKUP FILE (upload)
                    with file_col2:
                        st.subheader("✅ Production Mockup Upload")
                        upload = st.file_uploader(
                            "Upload finished product mockup (JPG, PNG, PDF)", 
                            type=["png", "jpg", "jpeg", "pdf"], 
                            key=f"mockup_upload_{key}"
                        )
                        
                        mock_entry = mockup_files.get("mockup")
                        
                        if st.button("💾 Save Mockup", key=f"save_mockup_{key}", use_container_width=True, disabled=not upload):
                            if upload:
                                upload.seek(0)
                                encoded = base64.b64encode(upload.read()).decode()
                                ext = upload.name.split(".")[-1].lower()
                                
                                new_mockup_entry = {"data": encoded, "ext": ext}
                                update(f"orders/{key}", {"printing_mockups": {"mockup": new_mockup_entry}})

                                st.success("Mockup saved!")
                                st.rerun()

                        st.markdown("---")
                        if mock_entry:
                            preview_file("Mockup Preview", mock_entry)
                            file_download_button(
                                "⬇️ Download Mockup File",
                                mock_entry,
                                order_id,
                                "mockup",
                                f"dl_mock_{key}"
                            )
                        else:
                            st.info("No mockup uploaded yet.")

                st.markdown("---")

                # ===============================================
                # SECTION 3: Messages and Completion
                # ===============================================
                
                msg_admin, msg_print = st.columns(2)
                
                with msg_admin:
                    st.markdown("### 🗣️ Communication Log (Admin/Sales)")
                    
                    # --- BUG FIX IMPLEMENTED HERE ---
                    # Admin can edit, others see read-only.
                    new_admin_notes = st.text_area(
                        "Admin/Sales Notes",
                        value=current_admin_notes,
                        height=120,
                        disabled=not IS_ADMIN, # ONLY ADMIN can change this
                        key=f"admin_msg_{key}"
                    )
                    
                    if IS_ADMIN and st.button("✍️ Save Admin Notes", key=f"save_admin_notes_{key}", type="secondary", use_container_width=True):
                        update(f"orders/{key}", {"admin_notes": new_admin_notes})
                        st.toast("Admin notes saved!", icon="✍️")
                        st.rerun()
                    elif not IS_ADMIN:
                        st.caption("This field is read-only for the Printing Department.")
                    # -----------------------------------
                    

                with msg_print:
                    st.markdown("### ✍️ Printing Team Notes")
                    st.caption("Internal notes for this print job.")
                    current_print_notes = printing_specs.get("printing_notes", "")
                    new_print_notes = st.text_area(
                        "Add/Edit Printing Notes",
                        value=current_print_notes,
                        height=120,
                        key=f"print_notes_{key}"
                    )
                    
                    if st.button("💾 Save Printing Notes", key=f"save_print_notes_{key}", use_container_width=True):
                        current_specs_before_save = read(f"orders/{key}").get("printing_specs", {})
                        
                        current_specs_before_save["printing_notes"] = new_print_notes
                        update(f"orders/{key}", {"printing_specs": current_specs_before_save})
                        st.toast("Printing notes saved!", icon="💾")
                        st.rerun()

                st.markdown("---")
                
                # COMPLETE PRINTING BUTTON
                if st.button(f"🚀 Job Complete: Move to LAMINATION", key=f"done_{key}", type="primary", use_container_width=True):

                    now_fmt = now_ist_formatted()

                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "printing_completed_at": now_fmt
                    })

                    st.balloons()
                    st.success("Moved to Lamination!")
                    st.rerun()

# ---------------------------
# TAB 2 - COMPLETED
# ---------------------------
with tab2:

    st.header("✅ Completed Printing Jobs")
    
    if not filtered_completed:
        st.info("No completed printing orders matching your filters yet.")
    else:
        for key, o in filtered_completed.items():

            order_id = o.get("order_id")
            design_files = o.get("design_files", {})
            mockup_files = o.get("printing_mockups", {})
            printing_specs = o.get("printing_specs", {})

            with st.container(border=True):

                st.markdown(f"## ✔️ Order **{order_id}** — {o.get('customer')}")
                st.caption(f"Completed on: **{o.get('printing_completed_at','N/A')}** | Assigned Printer: **{printing_specs.get('assigned_to', 'N/A')}**")

                st.subheader("Job Details")
                spec_cols = st.columns(3)
                spec_cols[0].markdown(f"**Paper Quality:** `{printing_specs.get('paper_quality', 'N/A')}`")
                spec_cols[1].markdown(f"**Paper Size:** `{printing_specs.get('paper_size', 'N/A')}`")
                spec_cols[2].markdown(f"**Board Size:** `{printing_specs.get('board_size', 'N/A')}`")

                # Report download button
                report_content = generate_order_report(o)
                st.download_button(
                    label="📄 Download Archived Report (HTML/PDF)",
                    data=report_content,
                    file_name=f"{order_id}_Production_Report_ARCHIVED.html",
                    mime="text/html",
                    key=f"report_comp_dl_{key}",
                    use_container_width=False
                )

                st.markdown("---")

                # Files in an expander
                with st.expander("📁 View Artwork and Mockup"):
                    col1, col2 = st.columns(2)

                    # Print Ready File Preview (Completed)
                    with col1:
                        st.subheader("Print Ready File")
                        final_art_entry = design_files.get("final")
                        
                        if final_art_entry:
                            preview_file("Print Ready File", final_art_entry)
                            file_download_button(
                                "⬇️ Download Print Ready File",
                                final_art_entry,
                                order_id,
                                "print_ready",
                                f"comp_dl_ready_{key}"
                            )

                    # Mockup File Preview (Completed)
                    with col2:
                        st.subheader("Mockup File")
                        mockup_entry = mockup_files.get("mockup")
                        
                        if mockup_entry:
                            preview_file("Mockup", mockup_entry)
                            file_download_button(
                                "⬇️ Download Mockup File",
                                mockup_entry,
                                order_id,
                                "mockup",
                                f"comp_dl_mock_{key}"
                            )

                st.markdown("---")

                # Notes Log
                st.subheader("💬 Notes Log")
                note_col1, note_col2 = st.columns(2)
                
                with note_col1:
                    # Display Admin notes
                    st.info(f"**Admin/Sales Note:** {o.get('admin_notes', 'N/A')}")
                with note_col2:
                    # Display Printing notes
                    st.info(f"**Printing Note:** {printing_specs.get('printing_notes', 'N/A')}")
                
                st.markdown("---")
