import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
import pytz

st.set_page_config(page_title="Printing Department", layout="wide", page_icon="🖨️")

# ---------------------------
# ROLE CHECK
# ---------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["printing", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🖨️ Printing Department")
st.caption("Manage print jobs, material specs, and track communication.")

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
# LOAD ORDERS & USERS
# ---------------------------
orders = read("orders") or {}
# Assuming you have a 'users' collection with names/roles
users = read("users") or {} 
printer_names = ["Unassigned"] + [u['name'] for u in users.values() if u.get('role') == 'printing'] 
# Fallback if no users list is available
if not printer_names:
    printer_names = ["Unassigned", "Printer A", "Printer B"] 

pending = {}
completed = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Printing":
        pending[key] = o
    elif o.get("printing_completed_at"):
        completed[key] = o

# ---------------------------
# FILE UTILITIES (Kept the same for brevity)
# ---------------------------

def file_download_button(label, file_entry, order_id, file_label, key_prefix):
    """Handles file download using the file entry dictionary."""
    if not file_entry or not file_entry.get("data"):
        st.warning("No file available for download.")
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

    st.markdown(f"### 📄 {label} Preview")

    # Preview image (PNG/JPG detection)
    if header.startswith(b"\x89PNG") or header[0:3] == b"\xff\xd8\xff":
        st.image(raw, use_container_width=True)

    # Indicate PDF
    elif header.startswith(b"%PDF"):
        st.info("PDF detected. Use the **Download** button to open it in full.")

    else:
        st.warning("File type not suitable for inline preview (AI, ZIP, etc.).")
    
    return raw

# ---------------------------
# MAIN TABS
# ---------------------------
tab1, tab2 = st.tabs([
    f"🛠️ Pending Printing ({len(pending)})",
    f"✅ Completed Printing ({len(completed)})"
])

# ---------------------------
# TAB 1 - PENDING
# ---------------------------
with tab1:

    if not pending:
        st.success("🎉 No pending printing jobs!")
    else:
        for key, o in pending.items():

            order_id = o.get("order_id")
            design_files = o.get("design_files", {})
            mockup_files = o.get("printing_mockups", {})
            
            # Load existing specs/notes
            printing_specs = o.get("printing_specs", {})
            admin_notes = o.get("admin_notes", "No specific instructions from Admin/Sales.")
            
            with st.container(border=True):

                st.subheader(f"🖨️ Order {order_id} — {o.get('customer')}")
                st.markdown(f"**Item:** {o.get('item')} | **Quantity:** {o.get('qty')} | **Due:** {o.get('due')}")

                st.divider()

                # ===============================================
                # ROW 1: Assignment and Specs
                # ===============================================
                st.markdown("### ⚙️ Printing Specs & Assignment")
                a_col, pq_col, ps_col, bs_col = st.columns([1.5, 1.5, 1, 1])

                # Assigned To (Selectbox)
                with a_col:
                    current_assignee = printing_specs.get("assigned_to", "Unassigned")
                    new_assignee = st.selectbox(
                        "Assigned To",
                        options=printer_names,
                        index=printer_names.index(current_assignee) if current_assignee in printer_names else 0,
                        key=f"assign_{key}"
                    )
                
                # Paper Quality
                with pq_col:
                    new_paper_quality = st.text_input(
                        "Paper Quality (e.g., 300GSM Matt)",
                        value=printing_specs.get("paper_quality", ""),
                        key=f"pq_{key}"
                    )

                # Paper Size
                with ps_col:
                    new_paper_size = st.text_input(
                        "Paper Size (e.g., 19x25)",
                        value=printing_specs.get("paper_size", ""),
                        key=f"ps_{key}"
                    )

                # Board Size
                with bs_col:
                    new_board_size = st.text_input(
                        "Board Size (Optional)",
                        value=printing_specs.get("board_size", ""),
                        key=f"bs_{key}"
                    )

                # Save Specs Button
                if st.button("💾 Save Specs & Assignment", key=f"save_specs_{key}", use_container_width=True):
                    updated_specs = {
                        "assigned_to": new_assignee,
                        "paper_quality": new_paper_quality,
                        "paper_size": new_paper_size,
                        "board_size": new_board_size
                    }
                    update(f"orders/{key}", {"printing_specs": updated_specs})
                    st.toast("Printing specs and assignment saved!", icon="💾")
                    st.rerun()

                st.divider()

                # ===============================================
                # ROW 2: Files
                # ===============================================
                col1, col2 = st.columns(2)
                
                # PRINT READY FILE (from Design)
                with col1:
                    st.subheader("🎨 Print-Ready File (Final Art)")
                    final_art_entry = design_files.get("final") 
                    
                    if not final_art_entry:
                        st.error("❌ Final design file missing! Cannot proceed.")
                    else:
                        preview_file("Print Ready File", final_art_entry)
                        file_download_button(
                            "⬇️ Download Print Ready File",
                            final_art_entry, 
                            order_id,
                            "print_ready",
                            f"dl_ready_{key}"
                        )

                # MOCKUP FILE (upload)
                with col2:
                    st.subheader("🖼️ Upload Mockup File")
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

                    if mock_entry:
                        preview_file("Mockup", mock_entry)
                        file_download_button(
                            "⬇️ Download Mockup File",
                            mock_entry,
                            order_id,
                            "mockup",
                            f"dl_mock_{key}"
                        )

                st.divider()

                # ===============================================
                # ROW 3: Messages and Completion
                # ===============================================
                msg_admin, msg_print = st.columns(2)
                
                with msg_admin:
                    st.markdown("### 💬 Message from Admin/Sales")
                    st.text_area(
                        "Admin/Sales Notes",
                        value=admin_notes,
                        height=150,
                        disabled=True, # Read-only
                        key=f"admin_msg_{key}"
                    )

                with msg_print:
                    st.markdown("### ✍️ Printing Department Notes")
                    current_print_notes = printing_specs.get("printing_notes", "")
                    new_print_notes = st.text_area(
                        "Add/Edit Printing Notes",
                        value=current_print_notes,
                        height=150,
                        key=f"print_notes_{key}"
                    )
                    
                    if st.button("💾 Save Printing Notes", key=f"save_print_notes_{key}", use_container_width=True):
                        # Merge the new note with existing specs
                        printing_specs["printing_notes"] = new_print_notes
                        update(f"orders/{key}", {"printing_specs": printing_specs})
                        st.toast("Printing notes saved!", icon="💾")
                        st.rerun()

                st.divider()
                
                # COMPLETE PRINTING BUTTON
                if st.button(f"🚀 Move to Lamination", key=f"done_{key}", type="primary", use_container_width=True):

                    now_raw = now_ist_raw()

                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "printing_completed_at": now_raw
                    })

                    st.balloons()
                    st.success("Moved to Lamination!")
                    st.rerun()

# ---------------------------
# TAB 2 - COMPLETED
# ---------------------------
with tab2:

    st.header("✅ Completed Printing")
    
    if not completed:
        st.info("No completed printing orders yet.")
    else:
        for key, o in completed.items():

            order_id = o.get("order_id")
            design_files = o.get("design_files", {})
            mockup_files = o.get("printing_mockups", {})
            printing_specs = o.get("printing_specs", {})

            with st.container(border=True):

                st.subheader(f"✔ {order_id} — {o.get('customer')}")
                st.caption(f"Finished: {o.get('printing_completed_at','N/A')} | Assigned: {printing_specs.get('assigned_to', 'N/A')}")

                spec_cols = st.columns(3)
                spec_cols[0].write(f"**Paper Quality:** {printing_specs.get('paper_quality', 'N/A')}")
                spec_cols[1].write(f"**Paper Size:** {printing_specs.get('paper_size', 'N/A')}")
                spec_cols[2].write(f"**Board Size:** {printing_specs.get('board_size', 'N/A')}")

                st.divider()

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

                st.divider()
                st.markdown("### 💬 Notes Log")
                st.write(f"**Admin/Sales Note:** {o.get('admin_notes', 'N/A')}")
                st.write(f"**Printing Note:** {printing_specs.get('printing_notes', 'N/A')}")
                st.divider()
