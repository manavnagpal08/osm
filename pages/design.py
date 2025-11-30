import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
from typing import Dict, Any, Optional

# --- CONFIGURATION ---
st.set_page_config(page_title="Design Department", layout="wide", page_icon="🎨")

# ------------------------------
# ROLE CHECK
# ------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["design", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department Dashboard")
st.caption("Manage artwork creation, track time, and transition finished designs to production.")

# ------------------------------
# LOAD ORDERS & CATEGORIZE
# ------------------------------
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

# ------------------------------
# FILE HELPERS (base64)
# ------------------------------

def encode_file(uploaded: Optional[Any]) -> Optional[str]:
    """Encodes an uploaded file object to a base64 string."""
    if uploaded:
        # Reset the file pointer before reading
        uploaded.seek(0)
        return base64.b64encode(uploaded.read()).decode("utf-8")
    return None

def download_button(file_data: Optional[str], filename: str):
    """Generates a download button for base64 encoded data."""
    if not file_data:
        return
    
    try:
        decoded = base64.b64decode(file_data)
        st.download_button(
            label=f"⬇️ Download {filename}",
            data=decoded,
            file_name=filename,
            key=f"dl_{filename}_{datetime.now().timestamp()}" # Ensure unique key on rerun
        )
    except Exception as e:
        st.error(f"Error decoding file for download: {e}")

# ------------------------------
# FILTER DROPDOWN
# ------------------------------
st.subheader("Filter & View")
col_filt, col_count = st.columns([1, 4])

with col_filt:
    filter_choice = st.selectbox(
        "Choose View",
        ["Pending", "Completed", "All"],
        index=0 # Default to Pending
    )

if filter_choice == "Pending":
    show_orders = pending_orders
    col_count.info(f"**{len(show_orders)}** orders currently awaiting design work.")
elif filter_choice == "Completed":
    show_orders = completed_orders
    col_count.success(f"**{len(show_orders)}** designs completed.")
else:
    show_orders = orders
    col_count.info(f"**{len(show_orders)}** total orders.")

st.divider()

# ------------------------------
# SHOW ORDERS
# ------------------------------

if not show_orders:
    st.info("No orders found for this filter.")
    st.stop()

# Sort pending orders by priority and received date for better workflow management
if filter_choice == "Pending":
    # Sort by Priority (High -> Low) and then by received date (Oldest first)
    sorted_items = sorted(
        show_orders.items(),
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(item[1].get("priority", "Medium"), 1), # Priority sort
            item[1].get("received", "9999-12-31") # Received Date sort (oldest first)
        )
    )
else:
    # Sort others by completion time (newest first)
    sorted_items = sorted(
        show_orders.items(),
        key=lambda item: item[1].get("design_completed_at", "0000-01-01"),
        reverse=True
    )


for key, order in sorted_items:

    order_id = order.get("order_id", "Unknown")
    cust = order.get("customer", "Unknown")
    item = order.get("item", "No description")
    priority = order.get("priority", "Medium")
    product_type = order.get("product_type", "N/A")
    
    # Set expander color based on stage/priority for visual scanning
    expander_style = "green" if order.get("stage") != "Design" else ("red" if priority == "High" else "blue")
    
    with st.expander(f"**{order_id}** — {cust} | {item} (Priority: {priority})", expanded=order.get("stage") == "Design"):

        # Initial Order Specs Summary
        st.markdown(f"**Product Type:** `{product_type}` | **Qty:** `{order.get('qty', 'N/A')}` | **Due:** `{order.get('due', 'N/A')}`")
        st.markdown(f"**Specs:** Foil=`{order.get('foil_id', '-')}`, SpotUV=`{order.get('spotuv_id', '-')}`, Size=`{order.get('size_id', '-')}`")

        # Load design_files object
        design_files: Dict[str, Optional[str]] = order.get("design_files", {})
        
        st.divider()

        # ------------------------------------
        # TIME TRACKING
        # ------------------------------------
        st.subheader("⏱️ Time Tracking")
        col_start, col_end, col_total = st.columns(3)

        start_time = order.get("design_start_time")
        end_time = order.get("design_end_time")
        
        # Start/Stop Buttons Logic
        with col_start:
            if not start_time:
                if st.button(f"▶️ Start Work", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"design_start_time": datetime.now().isoformat()})
                    st.rerun()
            else:
                st.success(f"Started: **{datetime.fromisoformat(start_time).strftime('%Y-%m-%d %H:%M')}**")

        with col_end:
            if start_time and not end_time:
                if st.button(f"⏹️ End Work", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"design_end_time": datetime.now().isoformat()})
                    st.rerun()
            elif end_time:
                st.success(f"Ended: **{datetime.fromisoformat(end_time).strftime('%Y-%m-%d %H:%M')}**")
        
        # Total Time Calculation
        with col_total:
            if start_time and end_time:
                try:
                    t1 = datetime.fromisoformat(start_time)
                    t2 = datetime.fromisoformat(end_time)
                    diff = t2 - t1
                    st.info(f"Total Time: **{str(diff).split('.')[0]}**") # Format to drop milliseconds
                except:
                    st.error("Time calc error.")

        st.divider()

        # ------------------------------------
        # FILE UPLOADS & DOWNLOADS
        # ------------------------------------
        st.subheader("📁 Design Files")
        st.markdown("Upload **Reference**, **Template**, and the **Final Artwork**.")

        col_ref, col_temp, col_final = st.columns(3)
        
        # --- Helper function for file section content ---
        def render_file_section(col, type_key, display_name):
            with col:
                st.caption(f"**{display_name}**")
                
                # File Uploader
                uploaded_file = st.file_uploader(
                    f"Upload New {display_name}",
                    type=["png","jpg","jpeg","pdf","zip","ai","eps","svg"],
                    key=f"upload_{type_key}_{order_id}",
                    label_visibility="collapsed"
                )
                
                # Save Button
                if st.button(f"💾 Save {display_name}", key=f"save_{type_key}_{order_id}", use_container_width=True):
                    encoded = encode_file(uploaded_file)
                    if encoded:
                        design_files[type_key] = encoded
                        # Use set operation to update only the file data
                        update(f"orders/{key}", {"design_files": design_files}) 
                        st.toast(f"{display_name} saved!")
                        st.rerun()
                
                # Status and Download
                file_data = design_files.get(type_key)
                if file_data:
                    st.success("File Uploaded ✔")
                    download_button(file_data, f"{order_id}_{type_key}.file")
                else:
                    st.warning("File Missing ❗")

        render_file_section(col_ref, "reference", "Reference Design")
        render_file_section(col_temp, "template", "Drawing Template")
        render_file_section(col_final, "final", "Final Design (Required)")


        st.divider()

        # ------------------------------------
        # INSTRUCTIONS & NOTES
        # ------------------------------------
        st.subheader("📝 Instructions & Notes")

        col_design_note, col_admin_note = st.columns(2)
        
        with col_design_note:
            designer_note = st.text_area(
                "Designer Notes (For Production/Assembly)",
                value=order.get("design_notes", ""),
                height=120,
                key=f"notes_{order_id}",
                help="Crucial instructions for the next stages, e.g., 'Use specific dye color #F50'."
            )
        
        with col_admin_note:
            # Only admin should be able to edit this, but design needs to see it
            is_admin = st.session_state["role"] == "admin"
            admin_note = st.text_area(
                "Admin/Sales Instructions (Read-Only for Design)",
                value=order.get("admin_instructions", ""),
                height=120,
                key=f"admin_{order_id}",
                disabled=not is_admin,
                help="Instructions from sales or management."
            )

        if st.button(f"💾 Save All Notes", key=f"savenotes_{order_id}", type="secondary"):
            update_data = {
                "design_notes": designer_note
            }
            # Only update admin_instructions if the user is an admin
            if is_admin:
                 update_data["admin_instructions"] = admin_note
                 
            update(f"orders/{key}", update_data)
            st.toast("Notes updated!")
            st.rerun()

        st.divider()

        # ------------------------------------
        # COMPLETE DESIGN & STAGE TRANSITION
        # ------------------------------------
        next_stage = order.get("next_after_printing", "Assembly")
        
        # Ensure the final file is uploaded before allowing completion
        is_ready = design_files.get("final") is not None
        
        if is_ready:
            if st.button(
                f"🚀 Mark Design Completed → Move to **{next_stage}**", 
                key=f"complete_{order_id}", 
                type="primary", 
                use_container_width=True
            ):
                update(f"orders/{key}", {
                    "stage": next_stage,
                    "design_completed_at": datetime.now().isoformat()
                })
                st.success(f"Design completed! Order **{order_id}** moved to **{next_stage}**")
                st.balloons()
                st.rerun()
        else:
            st.warning("🚨 **Final Design File is required** before moving this order to the next stage.")
