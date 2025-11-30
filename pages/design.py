import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
from typing import Dict, Any, Optional

# --- CONFIGURATION ---
st.set_page_config(page_title="Design Department", layout="wide", page_icon="🎨")

# ------------------------------
# MOCK FIREBASE/UTILS FUNCTIONS (For testing standalone)
# NOTE: Replace these with your actual integration code.
# ------------------------------
MOCK_ORDERS_DB = {
    "ord001": {"order_id": "ORD001", "customer": "Acme Corp", "type": "New", "product_type": "Bag", "priority": "Medium", "item": "Standard Yellow Bag", "qty": 500, "received": "2025-10-01", "due": "2025-10-15", "stage": "Design", "next_after_printing": "Assembly", "customer_phone": "555-1234", "customer_email": "acme@test.com"},
    "ord002": {"order_id": "ORD002", "customer": "Beta Solutions", "type": "New", "product_type": "Box", "priority": "High", "item": "Premium Black Gift Box", "qty": 100, "received": "2025-10-05", "due": "2025-10-12", "stage": "Design", "next_after_printing": "DieCut", "design_start_time": "2025-11-30T10:00:00", "customer_phone": "555-5678", "customer_email": "beta@test.com"},
    "ord003": {"order_id": "ORD003", "customer": "Acme Corp", "type": "Repeat", "product_type": "Bag", "priority": "Low", "item": "Custom Blue Logo Bag", "qty": 1000, "received": "2025-11-01", "due": "2025-11-20", "stage": "Assembly", "design_completed_at": "2025-11-25T09:00:00", "design_start_time": "2025-11-24T10:00:00", "design_end_time": "2025-11-24T12:30:00", "next_after_printing": "Assembly", "customer_phone": "555-1234", "customer_email": "acme@test.com"}
}
def read(collection_name):
    if collection_name == "orders": return MOCK_ORDERS_DB
    return {}
def update(path, data):
    print(f"--- UPDATING: {path} with {data} ---")
    # Mock update logic (simplified)
    parts = path.split('/')
    if parts[0] == 'orders' and len(parts) >= 2:
        order_key = parts[1]
        current_data = MOCK_ORDERS_DB.get(order_key, {})
        if len(parts) == 2:
            current_data.update(data)
        elif len(parts) == 3 and parts[2] == 'design_files':
             # Special handling for nested design_files update
            current_data['design_files'] = current_data.get('design_files', {})
            current_data['design_files'].update(data)
        MOCK_ORDERS_DB[order_key] = current_data
# MOCKING LOGIN FOR DEMO
if "role" not in st.session_state: st.session_state["role"] = "design"
# ------------------------------


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
        uploaded.seek(0)
        return base64.b64encode(uploaded.read()).decode("utf-8")
    return None

def download_button(file_data: Optional[str], filename: str, order_id: str):
    """Generates a download button for base64 encoded data."""
    if not file_data:
        return
    
    try:
        decoded = base64.b64decode(file_data)
        st.download_button(
            label=f"⬇️ Download {filename}",
            data=decoded,
            file_name=filename,
            key=f"dl_{order_id}_{filename}"
        )
    except Exception as e:
        st.error(f"Error decoding file: {e}")

# ----------------------------------------------------
# 📌 SIDEBAR: FILTER & SELECT ORDER
# ----------------------------------------------------

# --- Filtering ---
st.sidebar.header("Filter & Select Order")

filter_choice = st.sidebar.radio(
    "View",
    ["Pending Orders", "Completed Designs"],
    index=0 # Default to Pending
)

if filter_choice == "Pending Orders":
    show_orders = pending_orders
    st.sidebar.info(f"**{len(show_orders)}** Pending")
    # Sort pending orders by priority and received date
    sorted_items = sorted(
        show_orders.items(),
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(item[1].get("priority", "Medium"), 1), 
            item[1].get("received", "9999-12-31")
        )
    )
else:
    show_orders = completed_orders
    st.sidebar.success(f"**{len(show_orders)}** Completed")
    # Sort completed by completion time (newest first)
    sorted_items = sorted(
        show_orders.items(),
        key=lambda item: item[1].get("design_completed_at", "0000-01-01"),
        reverse=True
    )

order_options = {}
for key, order in sorted_items:
    label = f"#{order.get('order_id')} - {order.get('customer')} ({order.get('priority')})"
    order_options[label] = key

# --- Selection ---
selected_label = st.sidebar.selectbox(
    "Select Order for Details",
    options=["--- Select an Order ---"] + list(order_options.keys())
)

st.sidebar.divider()

selected_order_key = order_options.get(selected_label)
selected_order = orders.get(selected_order_key) if selected_order_key else None

# ----------------------------------------------------
# 📌 MAIN CONTENT: DETAIL VIEW
# ----------------------------------------------------

if not selected_order:
    st.info("Select an order from the sidebar to view details and begin work.")
else:
    # --- Display Header ---
    st.header(f"Order Details: #{selected_order['order_id']}")
    st.subheader(f"{selected_order['item']}")
    
    col_info_1, col_info_2, col_info_3 = st.columns(3)
    
    col_info_1.metric("Customer", selected_order['customer'])
    col_info_2.metric("Product Type", selected_order['product_type'])
    col_info_3.metric("Priority", selected_order['priority'])
    
    st.divider()
    
    order_key = selected_order_key # The Firebase path key

    # ------------------------------------
    # TIME TRACKING (In a dedicated container)
    # ------------------------------------
    with st.container(border=True):
        st.subheader("⏱️ Time Tracking & Status")
        col_start, col_end, col_total, col_status = st.columns(4)

        start_time = selected_order.get("design_start_time")
        end_time = selected_order.get("design_end_time")

        current_stage = selected_order.get("stage", "Design")
        
        # Start/Stop Buttons Logic
        with col_start:
            if current_stage == "Design" and not start_time:
                if st.button(f"▶️ Start Work", key=f"start_{order_key}", type="primary", use_container_width=True):
                    update(f"orders/{order_key}", {"design_start_time": datetime.now().isoformat()})
                    st.rerun()
            elif start_time:
                col_start.success("Work Started")
        
        with col_end:
            if current_stage == "Design" and start_time and not end_time:
                if st.button(f"⏹️ End Work", key=f"end_{order_key}", type="secondary", use_container_width=True):
                    update(f"orders/{order_key}", {"design_end_time": datetime.now().isoformat()})
                    st.rerun()
            elif end_time:
                col_end.success("Work Ended")

        # Status and Total Time Calculation
        with col_status:
            if current_stage == "Design":
                 col_status.warning("STATUS: Pending")
            else:
                 col_status.success(f"STATUS: Moved to {current_stage}")

        with col_total:
            if start_time and end_time:
                try:
                    t1 = datetime.fromisoformat(start_time)
                    t2 = datetime.fromisoformat(end_time)
                    diff = t2 - t1
                    col_total.metric("Time Taken", str(diff).split('.')[0])
                except:
                    col_total.error("Calc Error")
            elif start_time and current_stage == "Design":
                col_total.info("Time Running...")
    
    st.markdown("---")


    # ------------------------------------
    # FILE UPLOADS & DOWNLOADS
    # ------------------------------------
    with st.container(border=True):
        st.subheader("📁 Design Files")
        st.caption("Upload and manage the necessary files for this order.")
        
        design_files: Dict[str, Optional[str]] = selected_order.get("design_files", {})
        
        col_ref, col_temp, col_final = st.columns(3)
        
        # --- Helper function for file section content ---
        def render_file_section(col, type_key, display_name):
            with col:
                st.markdown(f"#### {display_name}")
                
                # File Uploader
                uploaded_file = st.file_uploader(
                    f"Upload New {display_name}",
                    type=["png","jpg","jpeg","pdf","zip","ai","eps","svg"],
                    key=f"upload_{type_key}_{order_key}",
                    label_visibility="collapsed"
                )
                
                # Save Button
                if st.button(f"💾 Save {display_name}", key=f"save_{type_key}_{order_key}", use_container_width=True, disabled=current_stage != "Design"):
                    encoded = encode_file(uploaded_file)
                    if encoded:
                        design_files[type_key] = encoded
                        # Update the specific nested dictionary
                        update(f"orders/{order_key}", {"design_files": design_files}) 
                        st.toast(f"{display_name} saved!")
                        st.rerun()
                
                # Status and Download
                file_data = design_files.get(type_key)
                if file_data:
                    st.success("File Uploaded ✔")
                    download_button(file_data, f"{selected_order['order_id']}_{type_key}.file", selected_order['order_id'])
                else:
                    st.warning("File Missing ❗")

        render_file_section(col_ref, "reference", "Reference Design")
        render_file_section(col_temp, "template", "Drawing Template")
        render_file_section(col_final, "final", "Final Artwork")
        
    st.markdown("---")

    # ------------------------------------
    # INSTRUCTIONS & NOTES
    # ------------------------------------
    with st.container(border=True):
        st.subheader("📝 Instructions & Communication")
        
        col_design_note, col_admin_note = st.columns(2)
        
        # Use st.session_state to manage text area content across reruns for smoother saving
        if f"notes_{order_key}" not in st.session_state:
             st.session_state[f"notes_{order_key}"] = selected_order.get("design_notes", "")
        if f"admin_{order_key}" not in st.session_state:
             st.session_state[f"admin_{order_key}"] = selected_order.get("admin_instructions", "")

        with col_design_note:
            designer_note = st.text_area(
                "Designer Notes (Instructions for Production)",
                value=st.session_state[f"notes_{order_key}"],
                height=150,
                key=f"notes_{order_key}",
                disabled=current_stage != "Design"
            )
        
        with col_admin_note:
            is_admin = st.session_state["role"] == "admin"
            admin_note = st.text_area(
                "Admin/Sales Instructions",
                value=st.session_state[f"admin_{order_key}"],
                height=150,
                key=f"admin_{order_key}",
                disabled=current_stage != "Design" and not is_admin,
            )

        if st.button(f"💾 Save All Notes", key=f"savenotes_{order_key}", type="secondary", disabled=current_stage != "Design"):
            update_data = {
                "design_notes": designer_note
            }
            if is_admin:
                 update_data["admin_instructions"] = admin_note
                 
            update(f"orders/{order_key}", update_data)
            st.toast("Notes updated!")
            st.rerun()

    st.markdown("---")

    # ------------------------------------
    # COMPLETE DESIGN
    # ------------------------------------
    if current_stage == "Design":
        with st.container(border=True):
            next_stage = selected_order.get("next_after_printing", "Assembly")
            
            # Ensure the final file is uploaded before allowing completion
            is_ready = design_files.get("final") is not None
            
            if is_ready:
                if st.button(
                    f"🚀 Mark Design Completed → Move to **{next_stage}**", 
                    key=f"complete_{order_key}", 
                    type="primary", 
                    use_container_width=True
                ):
                    update(f"orders/{order_key}", {
                        "stage": next_stage,
                        "design_completed_at": datetime.now().isoformat()
                    })
                    st.success(f"Design completed! Order **{selected_order['order_id']}** moved to **{next_stage}**")
                    st.balloons()
                    # After success, rerunning will deselect the order and move it to the 'Completed' list
                    st.rerun()
            else:
                st.warning("🚨 **Final Artwork File is required** before moving this order to the next stage. Please upload it in the section above.")
    else:
        st.success(f"Order already completed and moved to the **{current_stage}** stage on {selected_order.get('design_completed_at', 'N/A').split('T')[0]}.")
