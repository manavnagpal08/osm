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
st.caption("Manage print jobs, preview artwork, and upload mockup files.")

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
# LOAD ORDERS
# ---------------------------
orders = read("orders") or {}

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
# FILE UTILITIES
# ---------------------------

def file_download_button(label, file_entry, order_id, file_label, key_prefix):
    """Handles file download using the file entry dictionary."""
    if not file_entry or not file_entry.get("data"):
        st.warning("No file available for download.")
        return
    
    # Extract Base64 data and extension from the file entry dictionary
    b64_data = file_entry.get("data")
    file_ext = file_entry.get("ext", "bin") # Use stored extension, default to bin

    try:
        raw = base64.b64decode(b64_data)
    except Exception:
        st.error("File decode failed!")
        return

    # Determine MIME type based on the stored extension
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

            with st.container(border=True):

                st.subheader(f"🖨️ Order {order_id} — {o.get('customer')}")
                st.markdown(f"**Item:** {o.get('item')} | **Quantity:** {o.get('qty')}")

                st.divider()

                col1, col2 = st.columns(2)

                # ----------------------------
                # PRINT READY FILE (from Design)
                # ----------------------------
                with col1:
                    st.subheader("🎨 Print-Ready File (Final Art)")

                    # Final art is stored as a dictionary in design_files
                    final_art_entry = design_files.get("final") 
                    
                    if not final_art_entry:
                        st.error("❌ Final design file missing! Cannot proceed.")
                    else:
                        preview_file("Print Ready File", final_art_entry)

                        file_download_button(
                            "⬇️ Download Print Ready File",
                            final_art_entry, # Pass the dictionary entry
                            order_id,
                            "print_ready",
                            f"dl_ready_{key}" # Unique key
                        )

                # ----------------------------
                # MOCKUP FILE (upload)
                # ----------------------------
                with col2:
                    st.subheader("🖼️ Upload Mockup File")

                    upload = st.file_uploader(
                        "Upload finished product mockup (JPG, PNG, PDF)", 
                        type=["png", "jpg", "jpeg", "pdf"], 
                        key=f"mockup_upload_{key}" # Unique key
                    )
                    
                    mock_b64 = mockup_files.get("mockup")
                    
                    if st.button("💾 Save Mockup", key=f"save_mockup_{key}", use_container_width=True, disabled=not upload):
                        if upload:
                            upload.seek(0)
                            encoded = base64.b64encode(upload.read()).decode()
                            ext = upload.name.split(".")[-1].lower()
                            
                            new_mockup_entry = {"data": encoded, "ext": ext}

                            update(f"orders/{key}", {"printing_mockups": {"mockup": new_mockup_entry}})

                            st.success("Mockup saved!")
                            st.rerun()

                    # Show existing mockup preview
                    if mock_b64:
                        preview_file("Mockup", mock_b64)

                        file_download_button(
                            "⬇️ Download Mockup File",
                            mock_b64, # Pass the dictionary entry
                            order_id,
                            "mockup",
                            f"dl_mock_{key}" # Unique key
                        )

                st.divider()

                # ----------------------------
                # COMPLETE PRINTING
                # ----------------------------
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

    if not completed:
        st.info("No completed printing orders yet.")
    else:
        for key, o in completed.items():

            order_id = o.get("order_id")
            design_files = o.get("design_files", {})
            mockup_files = o.get("printing_mockups", {})

            with st.container(border=True):

                st.subheader(f"✔ {order_id} — {o.get('customer')}")
                st.caption(f"Finished: {o.get('printing_completed_at','N/A')}")

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
                            final_art_entry, # Pass the dictionary entry
                            order_id,
                            "print_ready",
                            f"comp_dl_ready_{key}" # Unique key
                        )

                # Mockup File Preview (Completed)
                with col2:
                    st.subheader("Mockup File")
                    mockup_entry = mockup_files.get("mockup")
                    
                    if mockup_entry:
                        preview_file("Mockup", mockup_entry)
                        file_download_button(
                            "⬇️ Download Mockup File",
                            mockup_entry, # Pass the dictionary entry
                            order_id,
                            "mockup",
                            f"comp_dl_mock_{key}" # Unique key
                        )

                st.divider()
