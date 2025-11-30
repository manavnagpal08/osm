import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

st.set_page_config(page_title="Lamination Department", layout="wide", page_icon="🟦")

# ---------------------------
# ROLE CHECK
# ---------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["lamination", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🟦 Lamination Department")
st.caption("Upload lamination output, track time, and move orders to DieCut.")

# ---------------------------
# LOAD ORDERS
# ---------------------------
orders = read("orders") or {}

pending = {}
completed = {}

for key, o in orders.items():

    if not isinstance(o, dict):
        continue

    # SHOW ONLY BOX ORDERS
    if o.get("product_type") != "Box":
        continue

    if o.get("stage") == "Lamination":
        pending[key] = o
    elif o.get("lamination_completed_at"):
        completed[key] = o

# ---------------------------
# FILE DOWNLOAD + DETECTION
# ---------------------------
def file_download_button(label, b64_data, order_id, file_label, prefix):
    if not b64_data:
        st.warning("No file available.")
        return

    raw = base64.b64decode(b64_data)
    header = raw[:10]

    if header.startswith(b"%PDF"):
        ext, mime = ".pdf", "application/pdf"
    elif header.startswith(b"\x89PNG"):
        ext, mime = ".png", "image/png"
    elif header[:3] == b"\xff\xd8\xff":
        ext, mime = ".jpg", "image/jpeg"
    else:
        ext, mime = ".bin", "application/octet-stream"

    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{file_label}{ext}",
        mime=mime,
        key=f"{prefix}_{order_id}",
        use_container_width=True
    )

# PREVIEW
def preview_file(label, b64):
    if not b64:
        st.warning(f"{label} missing.")
        return

    raw = base64.b64decode(b64)
    header = raw[:10]

    st.markdown(f"### 📄 {label} Preview")

    if header.startswith(b"%PDF"):
        st.info("PDF detected — preview not supported. Use download button.")
    elif header.startswith(b"\x89PNG") or header[:3] == b"\xff\xd8\xff":
        st.image(raw, use_container_width=True)

# ---------------------------
# TABS
# ---------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Lamination ({len(pending)})",
    f"✅ Completed Lamination ({len(completed)})"
])

# ---------------------------
# TAB 1: PENDING
# ---------------------------
with tab1:

    if not pending:
        st.success("🎉 No pending lamination work!")
    else:
        for key, o in pending.items():

            order_id = o["order_id"]
            lam_file = o.get("lamination_file")

            with st.container(border=True):

                st.subheader(f"🟦 Order {order_id}")
                st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")

                st.divider()

                # TIME TRACKING
                colT = st.columns(1)[0]
                start = o.get("lamination_start")
                end = o.get("lamination_end")

                with colT:
                    st.subheader("⏱ Time Tracking")

                    if not start:
                        if st.button("▶️ Start Lamination", key=f"start_{order_id}", use_container_width=True):
                            update(f"orders/{key}", {"lamination_start": datetime.now().isoformat()})
                            st.rerun()

                    elif start and not end:
                        if st.button("⏹ End Lamination", key=f"end_{order_id}", use_container_width=True):
                            update(f"orders/{key}", {"lamination_end": datetime.now().isoformat()})
                            st.rerun()

                        st.info(f"Started: {start}")
                    else:
                        st.success("Completed")
                        st.caption(f"Start: {start}")
                        st.caption(f"End: {end}")

                st.divider()

                # FILE UPLOAD
                st.subheader("📁 Lamination Output File (Required)")

                upload = st.file_uploader(
                    "Upload output file",
                    type=["png", "jpg", "jpeg", "pdf"],
                    key=f"up_{order_id}"
                )

                if st.button("💾 Save File", key=f"save_{order_id}", use_container_width=True) and upload:
                    encoded = base64.b64encode(upload.read()).decode()
                    update(f"orders/{key}", {"lamination_file": encoded})
                    st.success("File saved!")
                    st.rerun()

                # Show preview + download
                if lam_file:
                    preview_file("Lamination Output", lam_file)

                    file_download_button(
                        "⬇️ Download Lamination Output",
                        lam_file,
                        order_id,
                        "lamination",
                        "dl_lam"
                    )

                st.divider()

                # Move forward
                if lam_file:
                    if st.button(f"🚀 Move to DieCut", key=f"next_{order_id}", type="primary", use_container_width=True):

                        now = datetime.now().isoformat()
                        update(f"orders/{key}", {
                            "stage": "DieCut",
                            "lamination_completed_at": now
                        })

                        st.balloons()
                        st.success("Moved to DieCut!")
                        st.rerun()
                else:
                    st.warning("Upload lamination file first.")

# ---------------------------
# TAB 2: COMPLETED
# ---------------------------
with tab2:

    if not completed:
        st.info("No completed lamination orders yet.")
    else:
        for key, o in completed.items():

            order_id = o["order_id"]

            with st.container(border=True):

                st.subheader(f"✔ {order_id} — {o.get('customer')}")
                st.caption(f"Completed at {o.get('lamination_completed_at')}")

                lam_file = o.get("lamination_file")

                if lam_file:
                    preview_file("Lamination Output", lam_file)
                    file_download_button(
                        "⬇️ Download Lamination Output",
                        lam_file,
                        order_id,
                        "lamination",
                        "dl_lam_comp"
                    )

                st.divider()
