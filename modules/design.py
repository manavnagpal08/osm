import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Design Department", layout="wide", page_icon="🎨")

# ---------------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["design", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department Dashboard")
st.caption("Manage artwork, files, notes, and track design time efficiently.")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
# Assuming 'read' returns a dictionary of orders where keys are Firebase document IDs
orders = read("orders") or {}

pending_orders = {}
completed_orders = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # An order is pending design if its stage is exactly "Design"
    if o.get("stage") == "Design":
        pending_orders[key] = o
    # An order is considered "completed" (historically) if the design_completed_at timestamp exists,
    # regardless of its current stage (it might be in 'Printing' or 'Done').
    elif o.get("design_completed_at"):
        completed_orders[key] = o


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def encode_file(uploaded):
    """Reads an uploaded file and returns its base64 encoded string."""
    if uploaded:
        uploaded.seek(0)
        return base64.b64encode(uploaded.read()).decode("utf-8")
    return None


def preview_file(b64_data: Optional[str], label: str):
    """Displays a preview for base64 encoded image or PDF data."""
    if not b64_data:
        return

    decoded = base64.b64decode(b64_data)

    # Attempt to display as IMAGE (for PNG/JPG)
    try:
        st.image(decoded, caption=f"{label} Preview", use_container_width=True)
        return # If successful, stop here
    except:
        pass

    # Attempt to display as PDF (using iframe)
    # The image attempt might fail for non-image files, so we proceed to PDF
    # This also fails gracefully for non-image/non-pdf binary files
    try:
        if b64_data.startswith("%PDF"): # Basic check for PDF magic number (or similar logic if file extension is tracked)
             st.markdown(
                f"""
                <iframe src="data:application/pdf;base64,{b64_data}"
                        width="100%" height="900px"
                        style="border:2px solid #ccc;border-radius:12px;">
                </iframe>
                """,
                unsafe_allow_html=True
            )
    except:
        pass


def download_button_ui(file_data, filename, label, key):
    """Creates a standardized download button for base64 file data."""
    if not file_data:
        return
    decoded = base64.b64decode(file_data)
    st.download_button(
        label=label,
        data=decoded,
        file_name=filename,
        mime="application/octet-stream",
        use_container_width=True,
        key=key
    )


def calculate_time_diff(start, end):
    """Calculates the time difference between two ISO-formatted datetime strings."""
    if start and end:
        try:
            s = datetime.fromisoformat(start)
            e = datetime.fromisoformat(end)
            diff = e - s
            # Format to show HH:MM:SS
            return f"Total: **{str(diff).split('.')[0]}**"
        except:
            return "Time error"
    elif start and not end:
        return "⏳ Running…"
    return "Not started"


# ---------------------------------------------------------
# FILE CARD (Component for managing file uploads/downloads)
# ---------------------------------------------------------
def file_card(col, order_id, file_key, label, allowed, firebase_key):
    """
    Renders the UI for a single file upload/download/preview slot.

    :param col: Streamlit column object to render in.
    :param order_id: The user-facing order ID (for filename generation).
    :param file_key: The internal key in the 'design_files' dict (e.g., 'final').
    :param label: The display name (e.g., 'Final Art').
    :param allowed: List of allowed file extensions for st.file_uploader.
    :param firebase_key: The unique Firebase document ID for the order.
    """
    order = orders[firebase_key]
    design_files = order.get("design_files", {})
    existing_file = design_files.get(file_key)

    with col:
        st.markdown(f"**{'✔️' if existing_file else '➕'} {label}**")

        upload = st.file_uploader(
            f"Upload {label}",
            type=allowed,
            label_visibility="collapsed",
            key=f"up_{file_key}_{order_id}"
        )

        # 1. Save button logic
        if st.button(f"💾 Save {label}",
                     key=f"save_{file_key}_{order_id}",
                     disabled=not upload,
                     use_container_width=True):
            encoded = encode_file(upload)
            design_files[file_key] = encoded

            # Update the specific field in Firebase
            update(f"orders/{firebase_key}", {"design_files": design_files})
            st.toast(f"{label} saved!")
            st.rerun()

        # 2. Preview
        if existing_file:
            st.divider()
            preview_file(existing_file, label)

        # 3. Download button
        download_button_ui(
            existing_file,
            f"{order_id}_{file_key}_{label}.file", # Changed filename slightly for clarity
            f"⬇️ Download {label}",
            f"dl_{file_key}_{order_id}"
        )


# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------
tab_pending, tab_completed = st.tabs([
    f"🛠️ Pending Designs ({len(pending_orders)})",
    f"✅ Completed Designs ({len(completed_orders)})"
])

# =========================================================
# TAB 1 — PENDING DESIGNS
# =========================================================
with tab_pending:
    st.header("🛠️ Design Work In Progress")

    if not pending_orders:
        st.success("No pending work 🎉")

    # Iterate through pending orders
    for firebase_key, order in pending_orders.items():
        order_id = order.get("order_id")

        with st.container(border=True):

            st.markdown(f"### **{order_id}** — {order.get('customer')}")
            st.markdown(f"**Item:** {order.get('item')}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Priority", order.get("priority"))
            c2.metric("Qty", order.get("qty"))
            c3.metric("Type", order.get("product_type"))
            c4.metric("Due", order.get("due"))

            st.divider()

            tcol, fcol, ncol = st.columns([1.2, 3, 2])

            # TIME TRACKING
            with tcol:
                st.subheader("⏱️ Time")

                start = order.get("design_start_time")
                end = order.get("design_end_time")

                if not start:
                    # Start button
                    if st.button("▶️ Start", key=f"start_{order_id}", use_container_width=True):
                        update(f"orders/{firebase_key}",
                               {"design_start_time": datetime.now().isoformat()})
                        st.rerun()

                elif not end:
                    # Stop button
                    if st.button("⏹️ Stop", key=f"stop_{order_id}", use_container_width=True):
                        update(f"orders/{firebase_key}",
                               {"design_end_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption(f"Started: {start.split('T')[1][:5]}")

                else:
                    st.success("Completed")
                    st.caption(calculate_time_diff(start, end))

            # FILES
            with fcol:
                st.subheader("📁 Files")
                f1, f2, f3 = st.columns(3)

                # File card components
                file_card(f1, order_id, "reference", "Reference", ["png", "jpg", "pdf"], firebase_key)
                file_card(f2, order_id, "template", "Template", ["pdf", "ai", "zip"], firebase_key)
                file_card(f3, order_id, "final", "Final Art", ["pdf", "ai", "zip"], firebase_key)

            # NOTES + COMPLETE
            with ncol:
                st.subheader("📝 Notes")
                notes = st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", ""),
                    key=f"notes_{order_id}",
                    height=100
                )

                # Save Notes button
                if st.button("💾 Save Notes", key=f"save_notes_{order_id}", use_container_width=True):
                    update(f"orders/{firebase_key}", {"design_notes": notes})
                    st.toast("Notes saved!")
                    st.rerun()

                st.markdown("---")

                final_exists = order.get("design_files", {}).get("final")

                if final_exists:
                    # Move to Printing button (Primary action)
                    if st.button("🚀 Move to PRINTING", type="primary", key=f"move_{order_id}", use_container_width=True):

                        now = datetime.now().isoformat()
                        start = order.get("design_start_time")
                        end = order.get("design_end_time") or now # Ensure end time is set

                        update(f"orders/{firebase_key}", {
                            "stage": "Printing",
                            "design_completed_at": now,
                            "design_end_time": end
                        })

                        st.balloons()
                        st.toast("Design sent to PRINTING!")
                        st.rerun()

                else:
                    st.warning("Upload Final Art to complete order.")

            st.markdown("---")

# =========================================================
# TAB 2 — COMPLETED
# =========================================================
with tab_completed:
    st.header("✅ Completed Designs")

    if not completed_orders:
        st.info("No completed designs yet.")

    # Iterate through completed orders
    for firebase_key, order in completed_orders.items():
        order_id = order.get("order_id")

        with st.container(border=True):

            left, mid, right = st.columns([2, 3, 2])

            # LEFT Column: ID, Customer, Completion Date
            with left:
                st.subheader(order_id)
                st.write(order.get("customer"))
                st.caption(f"Completed: {order.get('design_completed_at', '')[:10]}")

            # MID Column: Item, Notes, Time Taken
            with mid:
                st.write(f"**Item:** {order.get('item')}")
                st.write(f"**Notes:** {order.get('design_notes', 'No notes.')}")
                st.caption(calculate_time_diff(order.get("design_start_time"),
                                               order.get("design_end_time")))

            # RIGHT Column: Files (Download/Preview)
            with right:
                st.subheader("📁 Files")
                df = order.get("design_files", {})

                # Loop through expected file keys
                for fk, label in {
                    "reference": "Reference",
                    "template": "Template",
                    "final": "Final Art"
                }.items():

                    if df.get(fk):
                        # Display file label and allow download/preview
                        st.markdown(f"**{label}**")

                        # Note: Previewing multiple large files here might slow down the UI
                        # The existing code tries to preview them sequentially.
                        # For completed section, a simple download link is often sufficient.

                        download_button_ui(
                            df[fk],
                            f"{order_id}_{fk}_{label}.file",
                            "⬇️ Download",
                            f"dl_c_{fk}_{order_id}"
                        )

            st.markdown("---")
