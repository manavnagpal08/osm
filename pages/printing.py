import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
import imghdr

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
# HELPERS
# ---------------------------
def detect_file_type(b64_data: str):
    """Detect file extension & MIME type from base64 data."""
    raw = base64.b64decode(b64_data)

    # Detect image
    img_type = imghdr.what(None, raw)
    if img_type:
        return f".{img_type}", f"image/{img_type}", raw

    # PDF detection
    if raw[:4] == b"%PDF":
        return ".pdf", "application/pdf", raw

    # AI / EPS are binary, treat as octet-stream
    return ".bin", "application/octet-stream", raw


def preview_file(label, b64_data):
    """Display preview of image/PDF."""
    if not b64_data:
        st.warning(f"No {label} uploaded yet.")
        return

    ext, mime, raw = detect_file_type(b64_data)

    st.markdown(f"### 📄 {label} Preview")

    if mime.startswith("image/"):
        st.image(raw, use_column_width=True)

    elif mime == "application/pdf":
        st.download_button(
            label="⬇️ Download PDF",
            data=raw,
            file_name=f"{label}{ext}",
            mime=mime
        )
        st.markdown(f"[Open PDF]({st.experimental_get_query_params()})")

    return raw, ext, mime


# ---------------------------
# MAIN TABS
# ---------------------------
tab1, tab2 = st.tabs([
    f"🛠️ Pending Printing ({len(pending)})",
    f"✅ Completed Printing ({len(completed)})"
])

# ---------------------------
# TAB 1 - PENDING PRINTING
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
                st.markdown(f"**Customer:** {o.get('customer')}")

                st.divider()

                col1, col2 = st.columns(2)

                # ----------------------------
                # PRINT READY FILE (from design)
                # ----------------------------
                with col1:
                    st.subheader("🎨 Print-Ready File (from Design)")

                    final_file = design_files.get("final")

                    if not final_file:
                        st.error("❌ No final design file found!")
                    else:
                        raw, ext, mime = detect_file_type(final_file)

                        # Preview (image/pdf)
                        preview_file("Print Ready File", final_file)

                        # Download fixed
                        st.download_button(
                            label="⬇️ Download Print-Ready File",
                            data=raw,
                            file_name=f"{order_id}_print_ready{ext}",
                            mime=mime,
                            use_container_width=True
                        )

                # ----------------------------
                # MOCKUP FILE UPLOAD
                # ----------------------------
                with col2:
                    st.subheader("🖼️ Upload Mockup File")

                    upload = st.file_uploader(
                        "Upload Mockup (image/pdf)",
                        type=["png", "jpg", "jpeg", "pdf"],
                        key=f"mockup_{order_id}"
                    )

                    if st.button("💾 Save Mockup", use_container_width=True, key=f"save_mockup_{order_id}") and upload:
                        mockup_encoded = base64.b64encode(upload.read()).decode()

                        old_mockups = o.get("printing_mockups", {})
                        old_mockups["mockup"] = mockup_encoded

                        update(f"orders/{key}", {
                            "printing_mockups": old_mockups
                        })

                        st.success("Mockup saved!")
                        st.rerun()

                    # Show existing mockup
                    mock_file = mockup_files.get("mockup")
                    if mock_file:
                        st.markdown("### Existing Mockup")
                        preview_file("Mockup", mock_file)

                st.divider()

                # ----------------------------
                # COMPLETE BUTTON
                # ----------------------------
                if st.button(f"🚀 Move to Lamination", type="primary", key=f"done_{order_id}", use_container_width=True):

                    now = datetime.now().isoformat()

                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "printing_completed_at": now
                    })

                    st.balloons()
                    st.success("Moved to Lamination!")
                    st.rerun()


# ---------------------------
# TAB 2 - COMPLETED PRINTING
# ---------------------------
with tab2:

    if not completed:
        st.info("No completed printing orders yet.")
    else:
        for key, o in completed.items():

            order_id = o.get("order_id")

            with st.container(border=True):

                st.markdown(f"### ✔ {order_id} — {o.get('customer')}")
                st.caption(f"Completed at {o.get('printing_completed_at','N/A')}")

                design_files = o.get("design_files", {})
                mockup_files = o.get("printing_mockups", {})

                st.divider()

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Print-Ready File")
                    if design_files.get("final"):
                        preview_file("Print Ready", design_files.get("final"))

                with col2:
                    st.subheader("Mockup File")
                    if mockup_files.get("mockup"):
                        preview_file("Mockup", mockup_files.get("mockup"))

                st.divider()
