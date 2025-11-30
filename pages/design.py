import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
from typing import Optional, Any, Dict

# ===========================================================
# PAGE CONFIG
# ===========================================================
st.set_page_config(page_title="Design Department", layout="wide", page_icon="🎨")

# ===========================================================
# ROLE CHECK
# ===========================================================
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["design", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department Dashboard")
st.caption("Manage artwork, upload files, track time, and transition orders to the next stage.")

# ===========================================================
# LOAD ORDERS
# ===========================================================
orders = read("orders") or {}

pending_orders: Dict[str, Any] = {}
completed_orders: Dict[str, Any] = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue
    if o.get("stage") == "Design":
        pending_orders[key] = o
    elif o.get("design_completed_at"):
        completed_orders[key] = o

# ===========================================================
# FILE HELPERS
# ===========================================================
def encode_file(file: Optional[Any]) -> Optional[str]:
    """Convert uploaded file to base64."""
    if file:
        file.seek(0)
        return base64.b64encode(file.read()).decode("utf-8")
    return None

def preview_file(file_data: Optional[str], label: str):
    """Preview images or PDFs."""
    if not file_data:
        return
    
    # Use a specific expander just for the preview to save space
    with st.expander(f"🖼️ View {label} Preview"):
        decoded = base64.b64decode(file_data)
        
        # Try image
        try:
            st.image(decoded, use_column_width=True)
            return
        except:
            pass

        # Try PDF
        try:
            st.markdown("**(PDF Preview)**")
            st.download_button(
                label="Click to download PDF for external viewer", 
                data=decoded, 
                file_name=f"Preview_{label}.pdf",
                mime="application/pdf"
            )
            return
        except:
            pass

        st.info("Preview not supported for this file type (e.g., .zip, .ai).")

def download_button_ui(file_data: Optional[str], filename: str, label: str, key: str):
    """Generate Streamlit download button."""
    if not file_data:
        return
    decoded = base64.b64decode(file_data)
    
    # Determine MIME type based on a guess from the filename
    if filename.endswith(".pdf"): mime = "application/pdf"
    elif filename.endswith(".zip"): mime = "application/zip"
    elif filename.endswith(".ai"): mime = "application/postscript" # Adobe Illustrator
    else: mime = "application/octet-stream"

    st.download_button(
        label=label,
        data=decoded,
        file_name=filename,
        key=key,
        mime=mime,
        use_container_width=True
    )

def calculate_time_diff(start: Optional[str], end: Optional[str]) -> str:
    """Calculate how long the design task took."""
    if start and end:
        try:
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            diff = t2 - t1
            return f"Total: **{str(diff).split('.')[0]}**"
        except:
            return "Time Calculation Error"
    elif start:
        return "⏳ Running…"
    return "Not Started"

# ===========================================================
# TABS
# ===========================================================
tab_pending, tab_completed = st.tabs([
    f"🛠️ Pending Workload ({len(pending_orders)})",
    f"✅ Completed Designs ({len(completed_orders)})"
])

# ===========================================================
# TAB: PENDING ORDERS (UPDATED for Preview)
# ===========================================================
with tab_pending:
    st.header("🛠️ Orders Awaiting Design")

    if not pending_orders:
        st.info("No orders pending in design.")
        st.stop()

    # Sort by priority + date
    sorted_pending = sorted(
        pending_orders.items(),
        key=lambda i: (
            {"High": 0, "Medium": 1, "Low": 2}.get(i[1].get("priority", "Medium")),
            i[1].get("received", "9999-12-31")
        )
    )

    for key, order in sorted_pending:

        order_id = order.get("order_id")
        customer = order.get("customer")
        item = order.get("item")

        with st.container(border=True):

            # TOP HEADER
            st.markdown(f"## {order_id} — {customer}")
            st.caption(f"**Item:** {item}")

            colA, colB, colC, colD = st.columns(4)
            colA.metric("Priority", order.get("priority"))
            colB.metric("Product", order.get("product_type"))
            colC.metric("Qty", order.get("qty"))
            colD.metric("Due", order.get("due"))

            st.markdown(
                f"📐 **Specs:** Foil=`{order.get('foil_id','-')}` | SpotUV=`{order.get('spotuv_id','-')}` | Size=`{order.get('size_id','-')}`"
            )

            st.divider()

            # LAYOUT 3 COLUMNS
            col_time, col_files, col_notes = st.columns([1.5, 3, 2.5])

            # ------------------
            # TIME TRACKING
            # ------------------
            with col_time:
                st.subheader("⏱️ Time")

                start = order.get("design_start_time")
                end = order.get("design_end_time")

                if not start:
                    if st.button("▶️ Start", key=f"start_{order_id}", use_container_width=True):
                        update(f"orders/{key}", {"design_start_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Waiting to start")

                elif not end:
                    if st.button("⏹️ End", key=f"end_{order_id}", use_container_width=True):
                        update(f"orders/{key}", {"design_end_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption(f"Started at {start.split('T')[1][:5]}")

                else:
                    st.success("Completed")
                    st.caption(calculate_time_diff(start, end))

            # ------------------
            # FILE SECTION (UPDATED)
            # ------------------
            design_files = order.get("design_files", {})

            with col_files:
                st.subheader("📁 Files")

                col_f1, col_f2, col_f3 = st.columns(3)

                def file_card(container, file_key, label, allowed, required=False):
                    with container:
                        exists_data = design_files.get(file_key)
                        
                        # Use the most common/first file extension as a hint for download
                        ext_hint = allowed[0] if allowed else "file" 

                        icon = "✔️" if exists_data else ("⚠️" if required else "➖")
                        st.markdown(f"**{icon} {label}**")

                        upload = st.file_uploader(
                            f"Upload {label}",
                            type=allowed,
                            key=f"up_{file_key}_{order_id}",
                            label_visibility="collapsed"
                        )

                        if st.button(f"💾 Save {label}", key=f"save_{file_key}_{order_id}", disabled=not upload, use_container_width=True):
                            encoded = encode_file(upload)
                            new = orders[key].get("design_files", {})
                            new[file_key] = encoded
                            update(f"orders/{key}", {"design_files": new})
                            st.toast(f"{label} Saved!")
                            st.rerun()

                        # --- NEW: Show Preview ---
                        if exists_data:
                            preview_file(exists_data, label)
                            
                        # download
                        download_button_ui(
                            exists_data, 
                            f"{order_id}_{file_key}.{ext_hint}", # Use hint for filename
                            f"⬇️ Download {ext_hint.upper()}",
                            key=f"dl_{file_key}_{order_id}"
                        )

                file_card(col_f1, "reference", "Reference", ["png", "jpg", "jpeg", "pdf", "zip"], required=False)
                file_card(col_f2, "template", "Template", ["ai", "eps", "pdf", "zip"], required=False)
                file_card(col_f3, "final", "Final Art", ["ai", "eps", "pdf", "zip"], required=True)

            # ------------------
            # NOTES + COMPLETE
            # ------------------
            with col_notes:
                st.subheader("📝 Notes")

                notes = st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", ""),
                    height=80,
                    key=f"notes_{order_id}",
                    label_visibility="collapsed"
                )

                if st.button("💾 Save Notes", key=f"save_notes_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"design_notes": notes})
                    st.toast("Notes Updated!")
                    st.rerun()

                st.markdown("---")
                
                # Admin Instructions (Read-Only)
                st.caption("Admin Instructions")
                st.info(order.get("admin_instructions", "N/A"))
                st.markdown("---")

                next_stage = order.get("next_after_printing", "Assembly")
                is_ready = design_files.get("final")

                if is_ready:
                    if st.button(
                        f"🚀 Move to {next_stage}",
                        key=f"complete_{order_id}",
                        type="primary",
                        use_container_width=True
                    ):
                        update(f"orders/{key}", {
                            "stage": next_stage,
                            "design_completed_at": datetime.now().isoformat()
                        })
                        st.balloons()
                        st.rerun()
                else:
                    st.warning("Upload Final Art to complete.")

            st.markdown("---")

# ===========================================================
# TAB: COMPLETED DESIGNS (Minor Naming Fix)
# ===========================================================
with tab_completed:
    st.header("✅ Completed Designs")

    if not completed_orders:
        st.info("No completed designs yet.")
        st.stop()

    sorted_completed = sorted(
        completed_orders.items(),
        key=lambda i: i[1].get("design_completed_at", "0000-01-01"),
        reverse=True
    )

    for key, order in sorted_completed:

        order_id = order.get("order_id")
        customer = order.get("customer")
        item = order.get("item")
        design_files = order.get("design_files", {})
        start = order.get("design_start_time")
        end = order.get("design_end_time")

        # Re-using the expander here as it's for static history viewing, not active workflow
        with st.expander(f"{order_id} — {customer} | {item} (Completed: {order.get('design_completed_at', '').split('T')[0]})"):

            # BASIC SUMMARY
            st.subheader("📌 Summary")

            c1, c2, c3 = st.columns(3)
            c1.metric("Customer", customer)
            c2.metric("Product", order.get("product_type"))
            c3.metric("Qty", order.get("qty"))

            c4, c5 = st.columns(2)
            c4.metric("Moved to Stage", order.get("stage", "N/A"))
            c5.markdown(calculate_time_diff(start, end))

            st.divider()

            # FILES (PREVIEW + DOWNLOAD)
            st.subheader("📁 Uploaded Files")

            col_f1, col_f2, col_f3 = st.columns(3)

            def show_file(container, file_key, label, ext_hint):
                with container:
                    fdata = design_files.get(file_key)
                    if not fdata:
                        st.warning(f"No {label} Uploaded")
                        return

                    st.success(f"{label} Available ✔")
                    preview_file(fdata, label) # Show Preview
                    download_button_ui(
                        fdata,
                        f"{order_id}_{file_key}.{ext_hint}", # Use hint for filename
                        f"⬇️ Download {label} ({ext_hint.upper()})",
                        key=f"dlc_{file_key}_{order_id}"
                    )

            show_file(col_f1, "reference", "Reference", "zip")
            show_file(col_f2, "template", "Template", "ai")
            show_file(col_f3, "final", "Final Art", "pdf")

            st.divider()

            # NOTES
            st.subheader("📝 Notes & Instructions")

            c1, c2 = st.columns(2)
            c1.markdown("### Designer Notes")
            c1.info(order.get("design_notes", "No notes"))

            c2.markdown("### Admin Instructions")
            c2.success(order.get("admin_instructions", "No instructions"))

            st.divider()

            # PREVIOUS ORDER THINKING
            st.subheader("🧠 Previous Order Used (Auto-Think)")

            prev = order.get("previous_order_used_for_repeat")
            if prev:
                st.success(f"Repeat of: **{prev.get('order_id')}** — {prev.get('item')}")
                # Display key specs from the previous order used for quick reference
                st.json({
                    "Foil": prev.get("foil_id"),
                    "SpotUV": prev.get("spotuv_id"),
                    "Size": prev.get("size_id"),
                    "Brand Thickness": prev.get("brand_thickness_id"),
                })
            else:
                st.info("This order did not reference a previous job.")
