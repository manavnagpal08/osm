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
st.caption("Centralized hub for managing artwork, tracking time, and transitioning orders.")

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
    # A design is considered 'completed' if it has a completion timestamp AND is not still pending
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

def download_button_ui(file_data: Optional[str], filename: str, label: str, key: str):
    """Generates a download button."""
    if not file_data:
        return
    decoded = base64.b64decode(file_data)

    st.download_button(
        label=label,
        data=decoded,
        file_name=filename,
        key=key,
        mime="application/octet-stream",
        use_container_width=True
    )

def calculate_time_diff(start: Optional[str], end: Optional[str]) -> str:
    """Calculates and formats the time difference."""
    if start and end:
        try:
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            diff = t2 - t1
            # Format to drop milliseconds
            return f"Total: **{str(diff).split('.')[0]}**" 
        except:
            return "Time calc error."
    elif start and not end:
        return "Time Running..."
    return "Not Started."

# ----------------------------------------------------
# 📌 MAIN VIEW: TABS
# ----------------------------------------------------

tab_pending, tab_completed = st.tabs([
    f"🛠️ Pending Workload ({len(pending_orders)})", 
    f"✅ Completed Designs ({len(completed_orders)})"
])

# ----------------------------------------------------
# TAB 1: PENDING WORKLOAD (UNCHANGED)
# ----------------------------------------------------
with tab_pending:
    st.header(f"Orders Awaiting Design ({len(pending_orders)})")
    
    if not pending_orders:
        st.info("No orders are currently in the Design stage. Great work!")
    
    # Sort pending orders by priority and received date
    sorted_pending = sorted(
        pending_orders.items(),
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(item[1].get("priority", "Medium"), 1), 
            item[1].get("received", "9999-12-31")
        )
    )

    for key, order in sorted_pending:
        order_id = order.get("order_id", "Unknown")
        
        # Use a container for each order card instead of expander
        with st.container(border=True):
            
            # --- CARD HEADER: ID, Customer, Item ---
            st.markdown(f"## **{order_id}** — {order.get('customer')}")
            st.markdown(f"**Item:** *{order.get('item', 'No description')}*")
            
            # --- METRICS & SPECS ---
            col_specs_1, col_specs_2, col_specs_3, col_specs_4 = st.columns(4)
            
            col_specs_1.metric("Priority", order.get('priority', 'Medium'))
            col_specs_2.metric("Product", order.get('product_type', 'N/A'))
            col_specs_3.metric("Qty", order.get('qty', 'N/A'))
            col_specs_4.metric("Due Date", order.get('due', 'N/A'))
            
            st.markdown(f"**Required Specs:** Foil=`{order.get('foil_id', '-')}`, SpotUV=`{order.get('spotuv_id', '-')}`, Size=`{order.get('size_id', '-')}`")

            st.divider()
            
            # --- WORKFLOW AREA (Time, Files, Notes) ---
            
            col_time, col_files, col_notes = st.columns([1.5, 3, 2.5])
            
            # 1. TIME TRACKING
            with col_time:
                st.subheader("⏱️ Tracking")
                start = order.get("design_start_time")
                end = order.get("design_end_time")

                if not start:
                    if st.button(f"▶️ Start Work", key=f"start_{order_id}", use_container_width=True, type="primary"):
                        update(f"orders/{key}", {"design_start_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Status: Waiting to Start")
                elif not end:
                    if st.button(f"⏹️ End Work", key=f"end_{order_id}", use_container_width=True, type="secondary"):
                        update(f"orders/{key}", {"design_end_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption(f"Started: {datetime.fromisoformat(start).strftime('%H:%M')}")
                else:
                    st.success("Work Completed")
                    st.caption(calculate_time_diff(start, end))

            # 2. FILE UPLOADS/DOWNLOADS
            design_files = order.get("design_files", {})
            with col_files:
                st.subheader("📁 Files")
                col_file_ref, col_file_temp, col_file_final = st.columns(3)

                # --- Helper for File Actions ---
                def render_file_card(c, file_key, label, type_list, is_required=False):
                    with c:
                        status_icon = "✔️" if design_files.get(file_key) else ("⚠️" if is_required else "➖")
                        st.markdown(f"**{status_icon} {label}**")
                        
                        uploaded_file = st.file_uploader(
                            f"Upload {label}",
                            type=type_list,
                            key=f"up_{file_key}_{order_id}",
                            label_visibility="collapsed"
                        )
                        
                        # Save action
                        if st.button(f"💾 Save {label}", key=f"save_{file_key}_{order_id}", use_container_width=True, disabled=not uploaded_file):
                            encoded = encode_file(uploaded_file)
                            if encoded:
                                update_path = f"orders/{key}"
                                current_files = orders.get(key, {}).get("design_files", {})
                                current_files[file_key] = encoded
                                update(update_path, {"design_files": current_files})
                                st.toast(f"{label} saved!")
                                st.rerun()

                        # Download button
                        download_button_ui(
                            design_files.get(file_key), 
                            f"{order_id}_{file_key}.file", 
                            "⬇️ Download", 
                            f"dl_{file_key}_{order_id}"
                        )

                render_file_card(col_file_ref, "reference", "Reference", ["png", "jpg", "pdf", "zip"])
                render_file_card(col_file_temp, "template", "Template", ["ai", "eps", "pdf", "zip"])
                render_file_card(col_file_final, "final", "Final Art", ["ai", "eps", "pdf", "zip"], is_required=True)
            
            # 3. NOTES & ACTIONS
            with col_notes:
                st.subheader("📝 Actions")
                
                # Notes Area (read-only for non-admin on admin_instructions)
                is_admin = st.session_state["role"] == "admin"
                
                designer_note = st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", ""),
                    height=70,
                    key=f"notes_{order_id}",
                    label_visibility="collapsed"
                )
                
                # Save notes button
                if st.button("💾 Save Notes", key=f"save_notes_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"design_notes": designer_note})
                    st.toast("Notes updated!")
                    st.rerun()
                
                st.markdown("---")
                
                # Completion Action
                next_stage = order.get("next_after_printing", "Assembly")
                is_ready = design_files.get("final") is not None
                
                if is_ready:
                    if st.button(
                        f"🚀 Move to {next_stage}", 
                        key=f"done_{order_id}", 
                        type="primary", 
                        use_container_width=True
                    ):
                        update(f"orders/{key}", {
                            "stage": next_stage,
                            "design_completed_at": datetime.now().isoformat()
                        })
                        st.balloons()
                        st.toast(f"Order moved to {next_stage}!")
                        st.rerun()
                else:
                    st.warning("Final Art is required to complete this order.")
                
            st.markdown("---")

# ----------------------------------------------------
# TAB 2: COMPLETED DESIGNS (ENHANCED)
# ----------------------------------------------------
with tab_completed:
    st.header(f"Design History ({len(completed_orders)})")
    
    if not completed_orders:
        st.info("No designs have been completed yet.")
        
    sorted_completed = sorted(
        completed_orders.items(),
        key=lambda item: item[1].get("design_completed_at", "0000-01-01"),
        reverse=True
    )
    
    # Display completed orders using containers for detailed viewing
    for key, order in sorted_completed:
        order_id = order.get("order_id", "Unknown")
        
        with st.container(border=True):
            
            # --- CARD HEADER: ID, Customer, Item ---
            st.markdown(f"## ✅ **{order_id}** — {order.get('customer')}")
            st.markdown(f"**Item:** *{order.get('item', 'No description')}*")

            # --- METRICS & SPECS ---
            col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
            
            completion_time = order.get("design_completed_at", "N/A")
            
            col_c1.metric("Priority", order.get('priority', 'Medium'))
            col_c2.metric("Product", order.get('product_type', 'N/A'))
            col_c3.metric("Qty", order.get('qty', 'N/A'))
            col_c4.metric("Completed On", completion_time.split('T')[0] if completion_time != 'N/A' else 'N/A')
            col_c5.metric("Time Taken", calculate_time_diff(order.get("design_start_time"), order.get("design_end_time")).replace("Total: ", ""))
            
            st.divider()

            # --- ADDED: FILES, NOTES, and PREVIOUS ORDER DATA ---
            col_files_comp, col_notes_comp = st.columns([4, 3])
            
            design_files = order.get("design_files", {})
            
            # 1. FILES (PREVIEW + DOWNLOAD)
            with col_files_comp:
                st.subheader("📁 Final Files (For Reference/Reprint)")
                
                file_keys = [("reference", "Ref"), ("template", "Template"), ("final", "Final")]
                
                # Dynamic columns based on file availability
                file_cols = st.columns(len(file_keys))
                
                for i, (file_key, label) in enumerate(file_keys):
                    file_data = design_files.get(file_key)
                    
                    with file_cols[i]:
                        st.markdown(f"**{label}**")
                        if file_data:
                            st.success("File Exists ✔")
                            # Download button for completed tab
                            download_button_ui(
                                file_data, 
                                f"{order_id}_{file_key}_FINAL.file", 
                                f"⬇️ Download {label}", 
                                f"comp_dl_{file_key}_{order_id}"
                            )
                        else:
                            st.warning("File Missing ❗")

            # 2. NOTES (DESIGNER + ADMIN)
            with col_notes_comp:
                st.subheader("📝 Design Notes")
                
                st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", "No notes recorded."),
                    height=100,
                    disabled=True,
                    key=f"comp_notes_{order_id}"
                )
                
                st.text_area(
                    "Admin Instructions",
                    value=order.get("admin_instructions", "No instructions recorded."),
                    height=100,
                    disabled=True,
                    key=f"comp_admin_{order_id}"
                )
            
            st.markdown("---")
