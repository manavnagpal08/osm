import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

st.set_page_config(page_title="Design Department", layout="wide", page_icon="🎨")

# ------------------------------
# ROLE CHECK
# ------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["design", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department")
st.caption("Handle artwork creation and move orders to the next production stage.")

# ------------------------------
# LOAD ORDERS
# ------------------------------
orders = read("orders") or {}

# categorize
pending_orders = {}
completed_orders = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Design":
        pending_orders[key] = o
    elif o.get("design_completed_at"):
        completed_orders[key] = o

# ------------------------------
# FILTER DROPDOWN
# ------------------------------
st.subheader("Filter Orders")

filter_choice = st.selectbox(
    "Choose View",
    ["Pending", "Completed", "All"]
)

if filter_choice == "Pending":
    show_orders = pending_orders
elif filter_choice == "Completed":
    show_orders = completed_orders
else:
    show_orders = orders

st.divider()

# ------------------------------
# FILE HELPERS (base64)
# ------------------------------

def encode_file(uploaded):
    if uploaded:
        return base64.b64encode(uploaded.read()).decode("utf-8")
    return None

def download_button(file_data, filename):
    if not file_data:
        return
    
    decoded = base64.b64decode(file_data)
    st.download_button(
        label=f"⬇️ Download {filename}",
        data=decoded,
        file_name=filename
    )

# ------------------------------
# SHOW ORDERS
# ------------------------------
if not show_orders:
    st.info("No orders found for this filter.")
    st.stop()

for key, order in show_orders.items():

    order_id = order.get("order_id", "Unknown")
    cust = order.get("customer", "Unknown")
    item = order.get("item", "No description")
    product_type = order.get("product_type", "")

    # Minimal card header
    with st.expander(f"{order_id} — {cust} | {item}"):

        st.markdown(f"**Product Type:** {product_type}")

        # Load design_files object if exists
        design_files = order.get("design_files", {
            "reference": None,
            "template": None,
            "final": None
        })

        # ------------------------------------
        # TIME TRACKING
        # ------------------------------------
        st.subheader("⏱️ Time Tracking")

        start_time = order.get("design_start_time")
        end_time = order.get("design_end_time")

        if not start_time:
            if st.button(f"▶️ Start Work on {order_id}", key=f"start_{order_id}"):
                update(f"orders/{key}", {
                    "design_start_time": datetime.now().isoformat()
                })
                st.rerun()
        else:
            st.success(f"Started: {start_time}")

        if start_time and not end_time:
            if st.button(f"⏹️ End Work on {order_id}", key=f"end_{order_id}"):
                update(f"orders/{key}", {
                    "design_end_time": datetime.now().isoformat()
                })
                st.rerun()
        elif end_time:
            st.success(f"Ended: {end_time}")

            # total time
            try:
                t1 = datetime.fromisoformat(start_time)
                t2 = datetime.fromisoformat(end_time)
                diff = t2 - t1
                st.info(f"Total Time: **{diff}**")
            except:
                pass

        st.divider()

        # ------------------------------------
        # FILE UPLOADS
        # ------------------------------------
        st.subheader("📁 Design Files")

        col1, col2, col3 = st.columns(3)

        with col1:
            ref = st.file_uploader(
                f"Reference Design ({order_id})",
                type=["png","jpg","jpeg","pdf","zip","svg"],
                key=f"ref_{order_id}"
            )
            if st.button(f"💾 Save Reference", key=f"save_ref_{order_id}"):
                encoded = encode_file(ref)
                if encoded:
                    design_files["reference"] = encoded
                    update(f"orders/{key}/design_files", design_files)
                    st.success("Reference design saved!")
                    st.rerun()

            if design_files.get("reference"):
                st.success("Reference Uploaded ✔")
                download_button(design_files["reference"], "reference_file")

        with col2:
            temp = st.file_uploader(
                f"Drawing Template ({order_id})",
                type=["png","jpg","jpeg","pdf","zip","svg"],
                key=f"temp_{order_id}"
            )
            if st.button(f"💾 Save Template", key=f"save_temp_{order_id}"):
                encoded = encode_file(temp)
                if encoded:
                    design_files["template"] = encoded
                    update(f"orders/{key}/design_files", design_files)
                    st.success("Template saved!")
                    st.rerun()

            if design_files.get("template"):
                st.success("Template Uploaded ✔")
                download_button(design_files["template"], "drawing_template")

        with col3:
            final = st.file_uploader(
                f"Final Design ({order_id})",
                type=["png","jpg","jpeg","pdf","zip","svg"],
                key=f"final_{order_id}"
            )
            if st.button(f"💾 Save Final Design", key=f"save_final_{order_id}"):
                encoded = encode_file(final)
                if encoded:
                    design_files["final"] = encoded
                    update(f"orders/{key}/design_files", design_files)
                    st.success("Final design saved!")
                    st.rerun()

            if design_files.get("final"):
                st.success("Final Uploaded ✔")
                download_button(design_files["final"], "final_design")

        st.divider()

        # ------------------------------------
        # INSTRUCTIONS BOX
        # ------------------------------------
        st.subheader("📝 Instructions")

        designer_note = st.text_area(
            f"Designer Notes for {order_id}",
            value=order.get("design_notes", ""),
            height=120,
            key=f"notes_{order_id}"
        )

        admin_note = st.text_area(
            f"Admin Instructions for {order_id}",
            value=order.get("admin_instructions", ""),
            height=120,
            key=f"admin_{order_id}"
        )

        if st.button(f"💾 Save Notes (Admin + Designer)", key=f"savenotes_{order_id}"):
            update(f"orders/{key}", {
                "design_notes": designer_note,
                "admin_instructions": admin_note
            })
            st.success("Notes updated!")
            st.rerun()

        st.divider()

        # ------------------------------------
        # COMPLETE DESIGN
        # ------------------------------------
        next_stage = order.get("next_after_printing", "Assembly")

        if st.button(f"🚀 Mark Design Completed → Move to {next_stage}", key=f"complete_{order_id}"):
            update(f"orders/{key}", {
                "stage": next_stage,
                "design_completed_at": datetime.now().isoformat()
            })
            st.success(f"Design completed! Order moved to **{next_stage}**")
            st.balloons()
            st.rerun()
