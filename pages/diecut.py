import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

st.set_page_config(page_title="DieCut Department", layout="wide", page_icon="🟥")

# ROLE CHECK
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["diecut", "admin"]:
    st.error("❌ No permission")
    st.stop()

st.title("🟥 DieCut Department")
st.caption("Upload diecut output, manage time, and move orders to Assembly.")

orders = read("orders") or {}

pending = {}
completed = {}

# Only BOX orders & stage = DieCut
for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("product_type") != "Box":
        continue

    if o.get("stage") == "DieCut":
        pending[key] = o
    elif o.get("diecut_completed_at"):
        completed[key] = o

# FILE HANDLERS
def download_button(label, b64, order_id, nm, key):
    if not b64:
        return

    raw = base64.b64decode(b64)
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
        file_name=f"{order_id}_{nm}{ext}",
        mime=mime,
        key=f"{key}_{order_id}"
    )

def preview(b64):
    if not b64:
        return
    raw = base64.b64decode(b64)
    header = raw[:10]
    if header.startswith(b"%PDF"):
        st.info("PDF detected — preview not supported.")
    else:
        st.image(raw, use_column_width=True)

tab1, tab2 = st.tabs([
    f"🛠 Pending DieCut ({len(pending)})",
    f"✔ Completed DieCut ({len(completed)})"
])

with tab1:
    for key, o in pending.items():
        order_id = o["order_id"]

        with st.container(border=True):
            st.subheader(f"🟥 Order {order_id}")
            st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")

            st.divider()

            # Time tracking
            start = o.get("diecut_start")
            end = o.get("diecut_end")

            if not start:
                if st.button("▶️ Start DieCut", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"diecut_start": datetime.now().isoformat()})
                    st.rerun()
            elif start and not end:
                if st.button("⏹ End DieCut", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"diecut_end": datetime.now().isoformat()})
                    st.rerun()
            else:
                st.success("DieCut completed")
                st.caption(f"Start: {start}")
                st.caption(f"End: {end}")

            st.divider()

            # Upload diecut file
            st.subheader("📁 DieCut Output File")

            upload = st.file_uploader(
                "Upload DieCut Output",
                type=["png", "jpg", "jpeg", "pdf"],
                key=f"up_{order_id}"
            )

            if st.button("💾 Save DieCut Output", key=f"save_{order_id}", use_container_width=True) and upload:
                encoded = base64.b64encode(upload.read()).decode()
                update(f"orders/{key}", {"diecut_file": encoded})
                st.success("Saved!")
                st.rerun()

            dc_file = o.get("diecut_file")

            if dc_file:
                preview(dc_file)
                download_button(
                    "⬇️ Download DieCut Output",
                    dc_file,
                    order_id,
                    "diecut",
                    "dl_dc"
                )

            st.divider()

            # Move to next
            if dc_file:
                if st.button("🚀 Move to Assembly", key=f"next_{order_id}", type="primary", use_container_width=True):
                    now = datetime.now().isoformat()
                    update(f"orders/{key}", {
                        "stage": "Assembly",
                        "diecut_completed_at": now
                    })
                    st.balloons()
                    st.rerun()
            else:
                st.warning("Upload diecut output first.")

with tab2:
    for key, o in completed.items():
        order_id = o["order_id"]

        with st.container(border=True):
            st.subheader(f"✔ {order_id} — {o.get('customer')}")
            st.caption(f"Completed at {o.get('diecut_completed_at')}")

            dc_file = o.get("diecut_file")

            if dc_file:
                preview(dc_file)
                download_button(
                    "⬇️ Download DieCut Output",
                    dc_file,
                    order_id,
                    "diecut",
                    "comp_dl_dc"
                )
