import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
from typing import Optional, Dict, Any, Union
import os # Imported for path/name manipulation

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
def extract_file_info(uploaded_file):
    """Reads file and returns a structured dictionary for Firebase storage."""
    if not uploaded_file:
        return None

    uploaded_file.seek(0)
    b64_data = base64.b64encode(uploaded_file.read()).decode("utf-8")
    
    # Extract extension and name
    name = uploaded_file.name
    ext = os.path.splitext(name)[-1].lstrip('.')
    
    return {
        "data": b64_data,
        "name": name,
        "ext": ext,
        "mime": uploaded_file.type if uploaded_file.type else "application/octet-stream"
    }

def get_file_details(file_data: Union[str, Dict[str, str]]):
    """
    Retrieves file details, handling both old (str) and new (dict) storage formats.
    Returns: {'data': b64_str, 'name': str, 'ext': str, 'mime': str} or None
    """
    if not file_data:
        return None
        
    if isinstance(file_data, str):
        # Old format: just the base64 string.
        # We must guess the extension/name, which is prone to error.
        # Fallback name and extension are provided here.
        return {
            "data": file_data,
            "name": "downloaded_file",
            "ext": "file",
            "mime": "application/octet-stream"
        }
    
    if isinstance(file_data, dict) and 'data' in file_data:
        # New format
        return file_data
        
    return None

def preview_file(file_info: Optional[Dict[str, str]], label: str):
    """Displays a preview for base64 encoded image or PDF data."""
    if not file_info:
        return

    b64_data = file_info.get("data")
    if not b64_data:
        return

    decoded = base64.b64decode(b64_data)
    ext = file_info.get("ext", "").lower()

    # 1. Attempt to display as IMAGE (for PNG/JPG)
    if ext in ["png", "jpg", "jpeg"]:
        try:
            st.image(decoded, caption=f"{label} Preview", use_container_width=True)
            return
        except:
            pass

    # 2. Attempt to display as PDF (using iframe)
    if ext == "pdf":
        try:
             # Basic check using the extension instead of just magic number
             st.markdown(
                f"""
                <iframe src="data:application/pdf;base64,{b64_data}"
                        width="100%" height="600px"
                        style="border:2px solid #ccc;border-radius:12px;">
                </iframe>
                """,
                unsafe_allow_html=True
            )
             return
        except:
            pass
            
    # Fallback message for unsupported previews
    st.info(f"File type (.**{ext}**) is not supported for inline preview.")


def download_button_ui(file_info: Optional[Dict[str, str]], label: str, key: str):
    """Creates a standardized download button for file info dictionary."""
    if not file_info or not file_info.get("data"):
        return
    
    b64_data = file_info["data"]
    filename = file_info.get("name", f"download_{file_info.get('ext', 'file')}")
    mime_type = file_info.get("mime", "application/octet-stream")
    
    decoded = base64.b64decode(b64_data)
    
    st.download_button(
        label=label,
        data=decoded,
        file_name=filename,
        mime=mime_type, # Using the stored MIME type if available
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
            return f"Total Time: **{str(diff).split('.')[0]}**"
        except:
            return "Time error"
    elif start and not end:
        return "⏳ Running…"
    return "Not started"

def get_ext_display(file_info):
    """Returns a styled markdown string for the file extension."""
    ext = file_info.get('ext', 'file').upper()
    return f"`{ext}`"


# ---------------------------------------------------------
# FILE CARD (Component for managing file uploads/downloads)
# ---------------------------------------------------------
def file_card(col, order_id, file_key, label, allowed, firebase_key):
    """
    Renders the UI for a single file upload/download/preview slot.
    """
    order = orders[firebase_key]
    design_files = order.get("design_files", {})
    existing_file_raw = design_files.get(file_key)
    existing_file_info = get_file_details(existing_file_raw)

    with col:
        st.markdown(f"**{'✔️' if existing_file_info else '➕'} {label}**")

        if existing_file_info:
            st.markdown(f"File: **{existing_file_info['name']}** {get_ext_display(existing_file_info)}")
        else:
            st.info(f"Accepted types: {', '.join(allowed).upper()}")

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
            
            new_file_info = extract_file_info(upload)
            design_files[file_key] = new_file_info # Store the dict
            
            # Update the specific field in Firebase
            update(f"orders/{firebase_key}", {"design_files": design_files})
            st.toast(f"{label} saved!")
            st.rerun()

        # 2. Download button
        download_button_ui(
            existing_file_info,
            f"⬇️ Download {label} {get_ext_display(existing_file_info) if existing_file_info else ''}",
            f"dl_{file_key}_{order_id}"
        )
        
        # 3. Preview
        if existing_file_info:
            with st.expander(f"👁️ View {label} Preview"):
                preview_file(existing_file_info, label)


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
    st.markdown("Easily track time, upload art files, and communicate progress to the next stage.")

    if not pending_orders:
        st.success("No pending work 🎉")

    # Iterate through pending orders
    for firebase_key, order in pending_orders.items():
        order_id = order.get("order_id")

        with st.expander(f"**{order_id}** — {order.get('customer')} | Item: {order.get('item')}", expanded=False):

            st.markdown(f"**Order ID:** `{order_id}`")
            st.markdown(f"**Item Description:** *{order.get('item')}*")

            # Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Priority", order.get("priority"), help="Urgency level set by Sales.")
            c2.metric("Quantity", order.get("qty"))
            c3.metric("Product Type", order.get("product_type"))
            c4.metric("Due Date", order.get("due"))

            st.divider()

            # Main workflow columns
            tcol, fcol, ncol = st.columns([1.5, 3, 2.5])

            # TIME TRACKING
            with tcol:
                st.subheader("⏱️ Time Tracking")

                start = order.get("design_start_time")
                end = order.get("design_end_time")
                
                # Time control logic
                if not start:
                    if st.button("▶️ START WORK", key=f"start_{order_id}", type="primary", use_container_width=True):
                        update(f"orders/{firebase_key}",
                               {"design_start_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Press Start to begin tracking design time.")

                elif not end:
                    st.info(f"Started: {start.split('T')[0]} @ {start.split('T')[1][:5]}")
                    if st.button("⏹️ STOP WORK", key=f"stop_{order_id}", type="secondary", use_container_width=True):
                        update(f"orders/{firebase_key}",
                               {"design_end_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Time is currently being tracked.")

                else:
                    st.success("Time Tracking Complete")
                    st.markdown(calculate_time_diff(start, end))
                    st.caption(f"Started: {start.split('T')[1][:5]} | Stopped: {end.split('T')[1][:5]}")

            # FILES
            with fcol:
                st.subheader("📁 Art Files")
                f1, f2, f3 = st.columns(3)

                # File card components
                file_card(f1, order_id, "reference", "Reference Art", ["png", "jpg", "jpeg", "pdf"], firebase_key)
                file_card(f2, order_id, "template", "Template/Mockup", ["pdf", "ai", "zip"], firebase_key)
                file_card(f3, order_id, "final", "Final Art", ["pdf", "ai", "zip"], firebase_key)

            # NOTES + COMPLETE
            with ncol:
                st.subheader("📝 Designer Notes")
                notes = st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", ""),
                    key=f"notes_{order_id}",
                    height=100,
                    placeholder="Add details about colors, fonts, or special instructions here."
                )

                # Save Notes button
                if st.button("💾 Save Notes", key=f"save_notes_{order_id}", use_container_width=True):
                    update(f"orders/{firebase_key}", {"design_notes": notes})
                    st.toast("Notes saved!")
                    st.rerun()

                st.markdown("---")

                final_exists = get_file_details(order.get("design_files", {}).get("final"))

                if final_exists:
                    # Move to Printing button (Primary action)
                    if st.button("🚀 COMPLETE & SEND TO PRINTING", type="primary", key=f"move_{order_id}", use_container_width=True):

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
                    st.warning("Upload Final Art file to enable completion.")

# =========================================================
# TAB 2 — COMPLETED
# =========================================================
with tab_completed:
    st.header("✅ Completed Designs History")

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
                st.write(f"Customer: **{order.get('customer')}**")
                st.caption(f"Completed: {order.get('design_completed_at', '')[:10]}")
                st.markdown(calculate_time_diff(order.get("design_start_time"),
                                               order.get("design_end_time")))

            # MID Column: Item, Notes
            with mid:
                st.write(f"**Item:** {order.get('item')}")
                with st.expander("View Designer Notes"):
                    st.text(order.get('design_notes', 'No notes provided.'))


            # RIGHT Column: Files (Download)
            with right:
                st.subheader("📁 Files")
                df = order.get("design_files", {})

                # Loop through expected file keys
                for fk, label in {
                    "reference": "Reference",
                    "template": "Template",
                    "final": "Final Art"
                }.items():
                    file_info = get_file_details(df.get(fk))

                    if file_info:
                        download_button_ui(
                            file_info,
                            f"⬇️ Download {label} {get_ext_display(file_info)}",
                            f"dl_c_{fk}_{order_id}"
                        )
                    else:
                        st.markdown(f"~~{label}~~ (N/A)")

            st.markdown("---")
