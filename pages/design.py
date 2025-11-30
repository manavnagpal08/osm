import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

st.set_page_config(page_title="Design Department", layout="wide", page_icon="🎨")

# ===========================================================
# ROLE CHECK
# ===========================================================
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["design", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department")
st.caption("Handle artwork creation and move orders to the next production stage.")

# ===========================================================
# LOAD ORDERS FROM FIREBASE
# ===========================================================
orders = read("orders") or {}

pending_orders = {}
completed_orders = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue
    if o.get("stage") == "Design":
        pending_orders[key] = o
    elif o.get("design_completed_at"):
        completed_orders[key] = o

# ===========================================================
# FILTER DROPDOWN
# ===========================================================
st.subheader("Filter Orders")

choice = st.selectbox(
    "View Orders",
    ["Pending", "Completed", "All"]
)

if choice == "Pending":
    show_orders = pending_orders
elif choice == "Completed":
    show_orders = completed_orders
else:
    show_orders = orders

st.divider()

if not show_orders:
    st.info("No orders match this filter.")
    st.stop()

# ===========================================================
# FILE FUNCTIONS
# ===========================================================

def encode_file(file):
    if file:
        return base64.b64encode(file.read()).decode("utf-8")
    return None

def preview_file(file_data, label):
    if not file_data:
        return

    decoded = base64.b64decode(file_data)

    st.markdown(f"### 📄 {label} Preview")

    # Try as image
    try:
        st.image(decoded, use_column_width=True)
        return
    except:
        pass

    # Try as PDF
    try:
        st.pdf(decoded)
        return
    except:
        pass

    # Otherwise not previewable
    st.info(f"Preview not supported for this file type.")

def download_button(file_data, filename, label):
    if not file_data:
        return
    decoded = base64.b64decode(file_data)

    st.download_button(
        label=f"⬇️ {label}",
        data=decoded,
        file_name=filename,
        mime="application/octet-stream"
    )

# ===========================================================
# DISPLAY ORDERS
# ===========================================================
for key, order in show_orders.items():

    order_id = order.get("order_id", "Unknown")
    customer = order.get("customer", "Unknown")
    item = order.get("item", "No description")
    product_type = order.get("product_type", "Bag")

    with st.expander(f"{order_id} — {customer} | {item}"):

        st.markdown(f"**Product Type:** {product_type}")

        # Load existing files
        design_files = order.get("design_files", {
            "reference": None,
            "template": None,
            "final": None
        })

        # ===========================================================
        # TIME TRACKING
        # ===========================================================
        st.subheader("⏱️ Time Tracking")

        start = order.get("design_start_time")
        end = order.get("design_end_time")

        if not start:
            if st.button(f"▶️ Start Work ({order_id})", key=f"start_{order_id}"):
                update(f"orders/{key}", {
                    "design_start_time": datetime.now().isoformat()
                })
                st.rerun()
        else:
            st.success(f"Started: {start}")

        if start and not end:
            if st.button(f"⏹️ End Work ({order_id})", key=f"end_{order_id}"):
                update(f"orders/{key}", {
                    "design_end_time": datetime.now().isoformat()
                })
                st.rerun()
        elif end:
            st.success(f"Ended: {end}")
            try:
                t1 = datetime.fromisoformat(start)
                t2 = datetime.fromisoformat(end)
                st.info(f"Total Time: **{t2 - t1}**")
            except:
                pass

        st.divider()

        # ===========================================================
        # FILE UPLOAD SECTION (FULL FIXED)
        # ===========================================================
        st.subheader("📁 Design Files")

        col1, col2, col3 = st.columns(3)

        # ---- Reference ----
        with col1:
            st.write("### 📌 Reference Design")

            ref_up = st.file_uploader(
                "Upload Reference",
                type=["png", "jpg", "jpeg", "pdf", "svg", "zip"],
                key=f"ref_{order_id}"
            )

            if st.button("💾 Save Reference", key=f"save_ref_{order_id}"):
                if ref_up:
                    encoded = encode_file(ref_up)
                    design_files["reference"] = encoded
                    update(f"orders/{key}/design_files", design_files)
                    st.success("Reference saved!")
                    st.rerun()

            if design_files.get("reference"):
                preview_file(design_files["reference"], "Reference")
                download_button(design_files["reference"], "reference_file", "Download Reference")

        # ---- Template ----
        with col2:
            st.write("### 📐 Drawing Template")

            temp_up = st.file_uploader(
                "Upload Template",
                type=["png", "jpg", "jpeg", "pdf", "svg", "zip"],
                key=f"temp_{order_id}"
            )

            if st.button("💾 Save Template", key=f"save_temp_{order_id}"):
                if temp_up:
                    encoded = encode_file(temp_up)
                    design_files["template"] = encoded
                    update(f"orders/{key}/design_files", design_files)
                    st.success("Template saved!")
                    st.rerun()

            if design_files.get("template"):
                preview_file(design_files["template"], "Template")
                download_button(design_files["template"], "template_file", "Download Template")

        # ---- Final ----
        with col3:
            st.write("### 🎉 Final Design")

            final_up = st.file_uploader(
                "Upload Final Design",
                type=["png", "jpg", "jpeg", "pdf", "svg", "zip"],
                key=f"final_{order_id}"
            )

            if st.button("💾 Save Final", key=f"save_final_{order_id}"):
                if final_up:
                    encoded = encode_file(final_up)
                    design_files["final"] = encoded
                    update(f"orders/{key}/design_files", design_files)
                    st.success("Final saved!")
                    st.rerun()

            if design_files.get("final"):
                preview_file(design_files["final"], "Final")
                download_button(design_files["final"], "final_file", "Download Final")

        st.divider()

        # ===========================================================
        # NOTES SECTION
        # ===========================================================
        st.subheader("📝 Instructions")

        design_notes = st.text_area(
            "Designer Notes",
            value=order.get("design_notes", ""),
            height=100,
            key=f"notes_{order_id}"
        )

        admin_instructions = st.text_area(
            "Admin Instructions",
            value=order.get("admin_instructions", ""),
            height=100,
            key=f"admin_notes_{order_id}"
        )

        if st.button("💾 Save Notes", key=f"save_notes_{order_id}"):
            update(f"orders/{key}", {
                "design_notes": design_notes,
                "admin_instructions": admin_instructions
            })
            st.success("Notes updated!")
            st.rerun()

        st.divider()

        # ===========================================================
        # MARK DESIGN COMPLETED
        # ===========================================================
        next_stage = order.get("next_after_printing", "Assembly")

        if st.button(f"🚀 Mark Design Completed → {next_stage}", key=f"done_{order_id}"):
            update(f"orders/{key}", {
                "stage": next_stage,
                "design_completed_at": datetime.now().isoformat()
            })
            st.success(f"Design complete! Order moved to **{next_stage}**.")
            st.balloons()
            st.rerun()
