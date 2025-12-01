import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

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
# FILE DOWNLOAD HANDLER
# ---------------------------
def file_download_button(label, b64_data, order_id, file_label, key_prefix):
    """DOWNLOAD WORKS FOR PDF / JPG / PNG"""
    if not b64_data:
        st.warning("No file available.")
        return

    try:
        raw = base64.b64decode(b64_data)
    except Exception:
        st.error("File decode failed!")
        return

    header = raw[:10]

    # Detect PDF
    if header.startswith(b"%PDF"):
        ext = ".pdf"
        mime = "application/pdf"

    # Detect PNG
    elif header.startswith(b"\x89PNG"):
        ext = ".png"
        mime = "image/png"

    # Detect JPG
    elif header[0:3] == b"\xff\xd8\xff":
        ext = ".jpg"
        mime = "image/jpeg"

    else:
        ext = ".bin"
        mime = "application/octet-stream"

    filename = f"{order_id}_{file_label}{ext}"

    st.download_button(
        label=label,
        data=raw,
        file_name=filename,
        mime=mime,
        key=f"{key_prefix}_{order_id}",
        use_container_width=True
    )

# ---------------------------
# FILE PREVIEW HANDLER
# ---------------------------
def preview_file(label, b64_data):
    """Preview PDF / PNG / JPG inline."""
    if not b64_data:
        st.warning(f"{label} not uploaded yet.")
        return

    raw = base64.b64decode(b64_data)
    header = raw[:10]

    st.markdown(f"### 📄 {label} Preview")

    # Preview image
    if header.startswith(b"\x89PNG") or header[:3] == b"\xff\xd8\xff":
        st.image(raw, use_container_width=True)

    # Preview pdf
    elif header.startswith(b"%PDF"):
        st.markdown("PDF detected. Use download button to open it.")

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

                st.subheader(f"🖨️ Order {order_id}")
                st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")

                st.divider()

                col1, col2 = st.columns(2)

                # ----------------------------
                # PRINT READY FILE (from Design)
                # ----------------------------
                with col1:
                    st.subheader("🎨 Print-Ready File (from Design)")

                    ready = design_files.get("final")
                    if not ready:
                        st.error("❌ Final design file missing!")
                    else:
                        preview_file("Print Ready File", ready)

                        file_download_button(
                            "⬇️ Download Print Ready File",
                            ready,
                            order_id,
                            "print_ready",
                            "dl_ready"
                        )

                # ----------------------------
                # MOCKUP FILE (upload)
                # ----------------------------
                with col2:
                    st.subheader("🖼️ Upload Mockup File")

                    upload = st.file_uploader(
                        "Upload mockup", 
                        type=["png", "jpg", "jpeg", "pdf"], 
                        key=f"mockup_{order_id}"
                    )

                    if st.button("💾 Save Mockup", key=f"save_mockup_{order_id}", use_container_width=True) and upload:
                        encoded = base64.b64encode(upload.read()).decode()

                        existing = o.get("printing_mockups", {})
                        existing["mockup"] = encoded

                        update(f"orders/{key}", {"printing_mockups": existing})

                        st.success("Mockup saved!")
                        st.rerun()

                    # Show existing mockup preview
                    mock_b64 = mockup_files.get("mockup")
                    if mock_b64:
                        st.markdown("### Mockup Preview")
                        preview_file("Mockup", mock_b64)

                        file_download_button(
                            "⬇️ Download Mockup File",
                            mock_b64,
                            order_id,
                            "mockup",
                            "dl_mock"
                        )

                st.divider()

                # ----------------------------
                # COMPLETE PRINTING
                # ----------------------------
                if st.button(f"🚀 Move to Lamination", key=f"done_{order_id}", type="primary", use_container_width=True):

                    now = datetime.now().isoformat()

                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "printing_completed_at": now
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

                with col1:
                    st.subheader("Print Ready File")
                    if design_files.get("final"):
                        preview_file("Print Ready File", design_files["final"])
                        file_download_button(
                            "⬇️ Download Print Ready File",
                            design_files["final"],
                            order_id,
                            "print_ready",
                            "comp_dl_ready"
                        )

                with col2:
                    st.subheader("Mockup File")
                    if mockup_files.get("mockup"):
                        preview_file("Mockup", mockup_files["mockup"])
                        file_download_button(
                            "⬇️ Download Mockup File",
                            mockup_files["mockup"],
                            order_id,
                            "mockup",
                            "comp_dl_mock"
                        )

                st.divider()
