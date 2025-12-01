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
orders = read("orders") or {}

pending_orders = {}
completed_orders = {}

# Correct design pipeline logic:
for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # PENDING = stage = DESIGN
    if o.get("stage") == "Design":
        pending_orders[key] = o

    # COMPLETED DESIGN = design_completed_at exists
    elif o.get("design_completed_at"):
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
    """Displays image + large PDF preview."""
    if not b64_data:
        return

    decoded = base64.b64decode(b64_data)

    # IMAGE preview
    try:
        st.image(decoded, caption=f"{label} Preview", use_container_width=True)
    except:
        pass

    # PDF preview (large)
    try:
        pdf_iframe = f"""
        <iframe 
            src="data:application/pdf;base64,{b64_data}" 
            width="100%" 
            height="900px" 
            style="border:2px solid #ccc; border-radius:12px; margin-top:10px;"
        ></iframe>
        """
        st.markdown(pdf_iframe, unsafe_allow_html=True)
    except:
        pass


def download_button_ui(file_data, filename, label, key):
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
    if start and end:
        try:
            s = datetime.fromisoformat(start)
            e = datetime.fromisoformat(end)
            diff = e - s
            return f"Total: **{str(diff).split('.')[0]}**"
        except:
            return "Time error"
    elif start and not end:
        return "⏳ Running…"
    return "Not started"


# ---------------------------------------------------------
# FILE CARD
# ---------------------------------------------------------
def file_card(col, order_id, file_key, label, allowed, db_key):
    with col:
        files = orders[db_key].get("design_files", {})
        exists = files.get(file_key)

        st.markdown(f"**{'✔️' if exists else '➕'} {label}**")

        upload = st.file_uploader(
            f"Upload {label}",
            type=allowed,
            label_visibility="collapsed",
            key=f"up_{file_key}_{order_id}"
        )

        if st.button(f"💾 Save {label}", key=f"save_{file_key}_{order_id}", disabled=not upload):
            encoded = encode_file(upload)
            df = orders[db_key].get("design_files", {})
            df[file_key] = encoded
            update(f"orders/{db_key}", {"design_files": df})
            st.toast(f"{label} saved!")
            st.rerun()

        # Preview
        if exists:
            preview_file(exists, label)

        # Download
        download_button_ui(
            exists,
            f"{order_id}_{file_key}.file",
            f"⬇️ Download {label}",
            f"dl_{file_key}_{order_id}"
        )


# ---------------------------------------------------------
# MAIN TABS
# ---------------------------------------------------------
tab_pending, tab_completed = st.tabs([
    f"🛠️ Pending Designs ({len(pending_orders)})",
    f"✅ Completed Designs ({len(completed_orders)})"
])


# =========================================================
# TAB 1 — PENDING
# =========================================================
with tab_pending:
    st.header("🛠️ Design Work In Progress")

    if not pending_orders:
        st.success("No pending work 🎉")

    for key, order in pending_orders.items():
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

            # 3 columns: TIME / FILES / NOTES
            tcol, fcol, ncol = st.columns([1.2, 3, 2])

            # TIME TRACKING
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
                    st.caption(f"Started: {start.split('T')[1][:5]}")

                else:
                    st.success("Completed")
                    st.caption(calculate_time_diff(start, end))

            # FILES
            with fcol:
                st.subheader("📁 Files")
                f1, f2, f3 = st.columns(3)

                file_card(f1, order_id, "reference", "Reference", ["png", "jpg", "pdf"], key)
                file_card(f2, order_id, "template", "Template", ["pdf", "ai", "zip"], key)
                file_card(f3, order_id, "final", "Final Art", ["pdf", "ai", "zip"], key)

            # NOTES + COMPLETE
            with ncol:
                st.subheader("📝 Notes")

                notes = st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", ""),
                    key=f"notes_{order_id}"
                )

                if st.button("💾 Save Notes", key=f"save_notes_{order_id}"):
                    update(f"orders/{key}", {"design_notes": notes})
                    st.toast("Notes saved")
                    st.rerun()

                st.markdown("---")

                # ✔ CORRECT FIX — move to PRINTING next
                final_exists = orders[key].get("design_files", {}).get("final")

                if final_exists:
                    if st.button(f"🚀 Move to PRINTING", type="primary", key=f"complete_{order_id}"):
                        now = datetime.now().isoformat()
                        start = order.get("design_start_time")
                        end = order.get("design_end_time")

                        if start and not end:   # auto-stop time
                            end = now

                        update(f"orders/{key}", {
                            "stage": "Printing",      # 🔥 FIXED
                            "design_completed_at": now,
                            "design_end_time": end or now,
                        })

                        st.balloons()
                        st.toast("Design Completed → Sent to PRINTING")
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

    for key, order in completed_orders.items():
        order_id = order.get("order_id")

        with st.container(border=True):
            left, mid, right = st.columns([2, 3, 2])

            # LEFT INFO
            with left:
                st.subheader(order_id)
                st.write(order.get("customer"))
                st.caption(f"Completed: {order.get('design_completed_at', '-')[:10]}")

            # NOTES + TIME
            with mid:
                st.write(f"**Item:** {order.get('item')}")
                st.write(f"**Notes:** {order.get('design_notes', '-')}")
                st.caption(calculate_time_diff(order.get("design_start_time"), order.get("design_end_time")))

            # FILES
            with right:
                st.subheader("📁 Files")
                df = order.get("design_files", {})

                for fk, label in {
                    "reference": "Reference",
                    "template": "Template",
                    "final": "Final Art"
                }.items():
                    if df.get(fk):
                        st.markdown(f"**{label}**")
                        preview_file(df[fk], label)
                        download_button_ui(
                            df[fk],
                            f"{order_id}_{fk}.file",
                            "⬇️ Download",
                            f"dl_c_{fk}_{order_id}"
                        )

            st.markdown("---")
