import streamlit as st
from firebase import read, update
from datetime import datetime
import base64

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Printing Department", layout="wide", page_icon="🖨️")

# ---------------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["printing", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🖨️ Printing Department Dashboard")
st.caption("Manage printing workflow, uploads, and time tracking.")

# ---------------------------------------------------------
# LOAD ORDERS
# ---------------------------------------------------------
orders = read("orders") or {}

pending_bag = {}
pending_box = {}
completed_print = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Printing":
        if o.get("product_type") == "Bag":
            pending_bag[key] = o
        else:
            pending_box[key] = o

    elif o.get("printing_completed_at"):
        completed_print[key] = o

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def encode_file(uploaded):
    if uploaded:
        uploaded.seek(0)
        return base64.b64encode(uploaded.read()).decode("utf-8")
    return None

def preview_file(b64_data, label):
    if not b64_data:
        return
    try:
        decoded = base64.b64decode(b64_data)
        st.image(decoded, caption=f"{label} Preview", use_container_width=True)
    except:
        pass
    try:
        pdf_iframe = f"""
        <iframe src="data:application/pdf;base64,{b64_data}" width="100%" height="900px" style="border-radius:12px;"></iframe>
        """
        st.markdown(pdf_iframe, unsafe_allow_html=True)
    except:
        pass

def download_button(file_data, filename, label, key):
    if not file_data:
        return
    decoded = base64.b64decode(file_data)
    st.download_button(label, decoded, file_name=filename, key=key)

# ---------------------------------------------------------
# FILE CARD
# ---------------------------------------------------------
def file_card(col, order_id, file_key, label, allowed, db_key):
    with col:
        files = orders[db_key].get("printing_files", {})
        exists = files.get(file_key)

        st.markdown(f"**{'✔️' if exists else '➕'} {label}**")

        upload = st.file_uploader(
            f"Upload {label}", type=allowed, label_visibility="collapsed", key=f"up_pr_{file_key}_{order_id}"
        )

        if st.button(f"💾 Save {label}", key=f"save_pr_{file_key}_{order_id}", disabled=not upload):
            encoded = encode_file(upload)
            fset = orders[db_key].get("printing_files", {})
            fset[file_key] = encoded
            update(f"orders/{db_key}", {"printing_files": fset})
            st.toast(f"{label} saved!")
            st.rerun()

        if exists:
            preview_file(exists, label)

        download_button(exists, f"{order_id}_{file_key}.file", f"⬇️ Download {label}", f"dl_pr_{file_key}_{order_id}")

# ---------------------------------------------------------
# MAIN TABS
# ---------------------------------------------------------
tab_bag, tab_box, tab_done = st.tabs([
    f"👜 Bag Printing ({len(pending_bag)})",
    f"📦 Box Printing ({len(pending_box)})",
    f"✅ Completed ({len(completed_print)})"
])

# ---------------------------------------------------------
# BAG PRINTING
# ---------------------------------------------------------
with tab_bag:
    st.header("👜 Bag Printing Queue")

    if not pending_bag:
        st.success("No Bag orders pending for printing.")

    for key, order in pending_bag.items():
        order_id = order.get("order_id")

        with st.container(border=True):
            st.markdown(f"### **{order_id}** — {order.get('customer')}")
            st.markdown(f"**Item:** {order.get('item')}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Qty", order.get("qty"))
            c2.metric("Priority", order.get("priority"))
            c3.metric("Due", order.get("due"))

            st.divider()

            # TIME + FILES + NEXT
            tcol, fcol, ncol = st.columns([1.2, 3, 2])

            # TIME
            with tcol:
                st.subheader("⏱️ Time")

                start = order.get("printing_start_time")
                end = order.get("printing_end_time")

                if not start:
                    if st.button("▶️ Start", key=f"pr_start_{order_id}"):
                        update(f"orders/{key}", {"printing_start_time": datetime.now().isoformat()})
                        st.rerun()
                elif not end:
                    if st.button("⏹️ Stop", key=f"pr_stop_{order_id}"):
                        update(f"orders/{key}", {"printing_end_time": datetime.now().isoformat()})
                        st.rerun()
                else:
                    st.success("Completed")

            # FILES
            with fcol:
                st.subheader("📁 Files")

                f1, f2 = st.columns(2)
                file_card(f1, order_id, "print_sheet", "Print Sheet", ["png", "jpg", "pdf"], key)
                file_card(f2, order_id, "plate_art", "Plate Art", ["pdf", "ai", "zip"], key)

            # NEXT
            with ncol:
                st.subheader("🚀 Move Next")

                if st.button("Send to Lamination", key=f"next_bag_{order_id}", type="primary"):
                    now = datetime.now().isoformat()

                    start = order.get("printing_start_time")
                    end = order.get("printing_end_time")

                    if start and not end:
                        end = now

                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "printing_completed_at": now,
                        "printing_end_time": end or now
                    })

                    st.balloons()
                    st.toast("Sent to Lamination")
                    st.rerun()

            st.markdown("---")

# ---------------------------------------------------------
# BOX PRINTING
# ---------------------------------------------------------
with tab_box:
    st.header("📦 Box Printing Queue")

    if not pending_box:
        st.info("No Box orders pending for printing.")

    for key, order in pending_box.items():
        order_id = order.get("order_id")

        with st.container(border=True):
            st.markdown(f"### **{order_id}** — {order.get('customer')}")
            st.markdown(f"**Item:** {order.get('item')}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Qty", order.get("qty"))
            c2.metric("Priority", order.get("priority"))
            c3.metric("Due", order.get("due"))

            st.divider()

            tcol, fcol, ncol = st.columns([1.2, 3, 2])

            # TIME
            with tcol:
                st.subheader("⏱️ Time")

                start = order.get("printing_start_time")
                end = order.get("printing_end_time")

                if not start:
                    if st.button("▶️ Start", key=f"pr_start_box_{order_id}"):
                        update(f"orders/{key}", {"printing_start_time": datetime.now().isoformat()})
                        st.rerun()
                elif not end:
                    if st.button("⏹️ Stop", key=f"pr_stop_box_{order_id}"):
                        update(f"orders/{key}", {"printing_end_time": datetime.now().isoformat()})
                        st.rerun()
                else:
                    st.success("Completed")

            # FILES
            with fcol:
                st.subheader("📁 Files")

                f1, f2 = st.columns(2)
                file_card(f1, order_id, "print_sheet", "Print Sheet", ["png", "jpg", "pdf"], key)
                file_card(f2, order_id, "plate_art", "Plate Art", ["pdf", "ai", "zip"], key)

            # NEXT
            with ncol:
                st.subheader("🚀 Move Next")

                if st.button("Send to Lamination", key=f"next_box_{order_id}", type="primary"):
                    now = datetime.now().isoformat()

                    start = order.get("printing_start_time")
                    end = order.get("printing_end_time")

                    if start and not end:
                        end = now

                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "printing_completed_at": now,
                        "printing_end_time": end or now
                    })

                    st.balloons()
                    st.toast("Sent to Lamination")
                    st.rerun()

            st.markdown("---")

# ---------------------------------------------------------
# COMPLETED PRINTING JOBS
# ---------------------------------------------------------
with tab_done:
    st.header("✅ Completed Printing Jobs")

    if not completed_print:
        st.info("No completed printing jobs yet.")

    for key, order in completed_print.items():
        order_id = order.get("order_id")

        with st.container(border=True):
            left, right = st.columns([2, 3])

            with left:
                st.subheader(order_id)
                st.write(order.get("customer"))
                st.caption(f"Completed: {order.get('printing_completed_at', '-')[:10]}")

            with right:
                st.subheader("📁 Files")
                files = order.get("printing_files", {})

                for fk, label in {
                    "print_sheet": "Print Sheet",
                    "plate_art": "Plate Art"
                }.items():
                    if files.get(fk):
                        st.markdown(f"**{label}**")
                        preview_file(files[fk], label)
                        download_button(files[fk], f"{order_id}_{fk}.file", "⬇️ Download", f"dl_done_{fk}_{order_id}")

            st.markdown("---")
