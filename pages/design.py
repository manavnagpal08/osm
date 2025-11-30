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
st.caption("Manage artwork, uploads, notes, and track time efficiently.")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
orders = read("orders") or {}

pending_orders = {}
completed_orders = {}

# Updated logic:
for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Design":
        pending_orders[key] = o
    else:
        completed_orders[key] = o


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def encode_file(uploaded):
    if uploaded:
        uploaded.seek(0)
        return base64.b64encode(uploaded.read()).decode("utf-8")
    return None


def preview_file(b64_data: Optional[str], label: str):
    """Show preview for image / PDF."""
    if not b64_data:
        return

    try:
        decoded = base64.b64decode(b64_data)

        # Try image preview
        st.image(decoded, caption=f"{label} Preview", use_container_width=True)
    except:
        pass

    # PDF preview
    try:
        b64_pdf = b64_data
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="400px"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except:
        pass


def download_button_ui(file_data: Optional[str], filename: str, label: str, key: str):
    if not file_data:
        return
    decoded = base64.b64decode(file_data)
    st.download_button(
        label=label,
        data=decoded,
        file_name=filename,
        mime="application/octet-stream",
        use_container_width=True,
        key=key,
    )


def calculate_time_diff(start, end):
    if start and end:
        try:
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            diff = t2 - t1
            return f"Total: **{str(diff).split('.')[0]}**"
        except:
            return "Time error."
    elif start and not end:
        return "⏳ Running..."
    return "Not Started"


# ---------------------------------------------------------
# FILE CARD COMPONENT
# ---------------------------------------------------------
def file_card(col, order_id, key_name, label, allowed, order_key):
    with col:
        design_files = orders[order_key].get("design_files", {})
        file_data = design_files.get(key_name)

        status = "✔️" if file_data else "➕"
        st.markdown(f"**{status} {label}**")

        upload = st.file_uploader(
            f"Upload {label}",
            type=allowed,
            key=f"file_{key_name}_{order_id}",
            label_visibility="collapsed"
        )

        if st.button(f"💾 Save {label}", key=f"save_{key_name}_{order_id}", disabled=not upload):
            encoded = encode_file(upload)
            df = orders[order_key].get("design_files", {})
            df[key_name] = encoded
            update(f"orders/{order_key}", {"design_files": df})
            st.toast(f"{label} Saved")
            st.rerun()

        if file_data:
            preview_file(file_data, label)

        download_button_ui(
            file_data,
            f"{order_id}_{key_name}.file",
            "⬇️ Download",
            f"dl_{key_name}_{order_id}"
        )


# ---------------------------------------------------------
# MAIN TABS
# ---------------------------------------------------------
tab_pending, tab_completed = st.tabs([
    f"🛠️ Pending Work ({len(pending_orders)})",
    f"✅ Completed Designs ({len(completed_orders)})"
])


# =========================================================
# TAB 1 — PENDING
# =========================================================
with tab_pending:
    st.header("🛠️ Work in Progress")

    if not pending_orders:
        st.success("No pending work 🎉 All caught up!")

    for key, order in pending_orders.items():
        order_id = order.get("order_id")

        with st.container(border=True):
            st.markdown(f"### **{order_id}** — {order.get('customer')}")
            st.markdown(f"**Item:** {order.get('item')}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Priority", order.get("priority"))
            c2.metric("Qty", order.get("qty"))
            c3.metric("Product", order.get("product_type"))
            c4.metric("Due", order.get("due"))

            st.divider()

            # --- Columns for Time / Files / Notes ---
            tcol, fcol, ncol = st.columns([1.2, 3, 2])

            # 1) TIME
            with tcol:
                st.subheader("⏱️ Time")
                start = order.get("design_start_time")
                end = order.get("design_end_time")

                if not start:
                    if st.button("▶️ Start", key=f"start_{order_id}"):
                        update(f"orders/{key}", {"design_start_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Waiting to start")
                elif not end:
                    if st.button("⏹️ Stop", key=f"stop_{order_id}"):
                        update(f"orders/{key}", {"design_end_time": datetime.now().isoformat()})
                        st.rerun()
                    st.caption(f"Started at: {start.split('T')[1][:5]}")
                else:
                    st.success("Completed")
                    st.caption(calculate_time_diff(start, end))

            # 2) FILE UPLOADS
            with fcol:
                st.subheader("📁 Files")

                colF1, colF2, colF3 = st.columns(3)

                file_card(colF1, order_id, "reference", "Reference", ["png", "jpg", "pdf"], key)
                file_card(colF2, order_id, "template", "Template", ["pdf", "ai", "zip"], key)
                file_card(colF3, order_id, "final", "Final Art", ["pdf", "ai", "zip"], key)

            # 3) NOTES + COMPLETE
            with ncol:
                st.subheader("📝 Notes")

                notes = st.text_area("Designer Notes", value=order.get("design_notes", ""), key=f"notes_{order_id}")

                if st.button("💾 Save Notes", key=f"save_notes_{order_id}"):
                    update(f"orders/{key}", {"design_notes": notes})
                    st.toast("Notes updated")
                    st.rerun()

                st.markdown("---")

                # Complete order
                final_ready = orders[key].get("design_files", {}).get("final") is not None
                next_stage = order.get("next_after_printing", "Assembly")

                if final_ready:
                    if st.button(f"🚀 Move to {next_stage}", key=f"complete_{order_id}", type="primary"):
                        now = datetime.now().isoformat()
                        start = order.get("design_start_time")
                        end = order.get("design_end_time")

                        # auto-end time
                        if start and not end:
                            end = now

                        update(f"orders/{key}", {
                            "stage": next_stage,
                            "design_completed_at": now,
                            "design_end_time": end or now
                        })

                        st.balloons()
                        st.toast("Design Completed!")
                        st.rerun()
                else:
                    st.warning("Final art required to complete order.")

            st.markdown("---")


# =========================================================
# TAB 2 — COMPLETED
# =========================================================
with tab_completed:
    st.header("✅ Completed Designs")

    if not completed_orders:
        st.info("No completed designs yet.")

    for key, order in completed_orders.items():
        order_id = order.get("order_id")

        with st.container(border=True):

            c1, c2, c3 = st.columns([2, 3, 2])

            with c1:
                st.subheader(order_id)
                st.write(order.get("customer"))
                st.caption(f"Completed: {order.get('design_completed_at', '-')[:10]}")

            with c2:
                st.write(f"**Item:** {order.get('item')}")
                st.write(f"**Notes:** {order.get('design_notes', '-')}")
                st.write(calculate_time_diff(order.get("design_start_time"), order.get("design_end_time")))

            with c3:
                st.subheader("📁 Files")
                df = order.get("design_files", {})

                for key_name, label in {
                    "reference": "Reference",
                    "template": "Template",
                    "final": "Final"
                }.items():

                    if df.get(key_name):
                        st.markdown(f"**{label}**")
                        preview_file(df[key_name], label)

                        download_button_ui(
                            df[key_name],
                            f"{order_id}_{key_name}.file",
                            "⬇️ Download",
                            f"dl_comp_{key_name}_{order_id}"
                        )

            st.markdown("---")
