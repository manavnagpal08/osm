# ============================
# SECTION 1 — IMPORTS + SETUP
# ============================

import streamlit as st
from firebase import read, update
from datetime import datetime
import base64
from typing import Optional
import pytz

# ---------------------------------------------
# PAGE CONFIG
# ---------------------------------------------
st.set_page_config(
    page_title="Design Department",
    layout="wide",
    page_icon="🎨"
)

# ---------------------------------------------
# ROLE CHECK
# ---------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["design", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department Dashboard")
st.caption("Manage artwork, files, notes, and track design time efficiently.")

# ---------------------------------------------
# LOAD ORDERS
# ---------------------------------------------
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


# ========================================================
# TIME HELPERS — IST FORMAT + RAW FORMAT
# ========================================================
IST = pytz.timezone("Asia/Kolkata")

def now_ist_raw():
    """Returns ISO datetime string in IST timezone."""
    return datetime.now(IST).isoformat()

def now_ist_formatted():
    """Returns human-readable format: 01 Dec 2024, 2:22 PM"""
    return datetime.now(IST).strftime("%d %b %Y, %I:%M %p")


def calculate_time_diff(start_raw, end_raw):
    """Calculate IST readable difference."""
    if start_raw and end_raw:
        try:
            s = datetime.fromisoformat(start_raw)
            e = datetime.fromisoformat(end_raw)
            diff = e - s
            return f"Total: **{str(diff).split('.')[0]}**"
        except:
            return "Time error"
    elif start_raw and not end_raw:
        return "⏳ Running…"
    return "Not started"


# ========================================================
# PREVIEW HELPERS (PDF + IMAGE FIXED)
# ========================================================
def preview_file(b64_data: Optional[str], label: str):
    if not b64_data:
        return

    decoded = base64.b64decode(b64_data)

    # Detect file type:
    is_pdf = decoded[:4] == b"%PDF"

    if is_pdf:
        # Large PDF Preview
        st.markdown(
            f"""
            <iframe 
                src="data:application/pdf;base64,{b64_data}" 
                width="100%" 
                height="800px"
                style="border:2px solid #0C7A35;border-radius:12px;margin-top:8px;">
            </iframe>
            """,
            unsafe_allow_html=True
        )
    else:
        # Image preview
        st.image(decoded, caption=f"{label} Preview", use_container_width=True)


# ========================================================
# DOWNLOAD HELPER
# ========================================================
def download_button_ui(b64, filename, label, key):
    if not b64:
        return
    decoded = base64.b64decode(b64)
    st.download_button(
        label=label,
        data=decoded,
        file_name=filename,
        mime="application/octet-stream",
        use_container_width=True,
        key=key
    )


# ========================================================
# FILE CARD — BEAUTIFUL GREEN UI
# ========================================================
def file_card(col, order_id, file_key, label, allowed, firebase_key):

    order = orders[firebase_key]
    design_files = order.get("design_files", {})
    existing_file = design_files.get(file_key)

    with col:

        # Header
        st.markdown(
            f"""
            <div style="
                background:#0C7A35;
                padding:6px 12px;
                border-radius:6px;
                margin-bottom:8px;
                color:white;
                font-weight:600;">
                📁 {label}
            </div>
            """,
            unsafe_allow_html=True
        )

        # File uploader
        upload = st.file_uploader(
            f"Upload {label}",
            type=allowed,
            label_visibility="collapsed",
            key=f"up_{file_key}_{order_id}"
        )

        # Save button
        if st.button(f"💾 Save {label}",
                     key=f"save_{file_key}_{order_id}",
                     disabled=not upload):
            upload.seek(0)
            encoded = base64.b64encode(upload.read()).decode("utf-8")

            design_files[file_key] = encoded
            update(f"orders/{firebase_key}", {"design_files": design_files})

            st.toast(f"{label} saved!")
            st.rerun()

        # Preview Section
        if existing_file:
            preview_file(existing_file, label)

        download_button_ui(
            existing_file,
            f"{order_id}_{file_key}.file",
            f"⬇️ Download {label}",
            f"dl_{file_key}_{order_id}"
        )
# ================================
# SECTION 2 — PENDING DESIGNS
# ================================

tab_pending, tab_completed = st.tabs([
    f"🛠️ Pending Designs ({len(pending_orders)})",
    f"✅ Completed Designs ({len(completed_orders)})"
])


with tab_pending:

    st.header("🛠️ Design Work In Progress")

    if not pending_orders:
        st.success("No pending work 🎉")

    # Loop orders
    for firebase_key, order in pending_orders.items():

        order_id = order.get("order_id")
        customer = order.get("customer")
        item = order.get("item")

        with st.container(border=True):

            # ----------------------------------------------------
            # ORDER HEADER
            # ----------------------------------------------------
            st.markdown(
                f"""
                <h3 style="margin-bottom:2px;">{order_id} — {customer}</h3>
                <div style="color:#444;margin-bottom:10px;">{item}</div>
                """,
                unsafe_allow_html=True
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Priority", order.get("priority"))
            c2.metric("Qty", order.get("qty"))
            c3.metric("Type", order.get("product_type"))
            c4.metric("Due", order.get("due"))

            st.divider()

            # ----------------------------------------------------
            # 3 Columns — Time, Files, Notes
            # ----------------------------------------------------
            tcol, fcol, ncol = st.columns([1.1, 3, 2])

            # ====================================================
            # TIME TRACKING (LEFT COLUMN)
            # ====================================================
            with tcol:
                st.subheader("⏱️ Time")

                start_raw = order.get("design_start_time_raw")
                end_raw   = order.get("design_end_time_raw")

                # START BUTTON
                if not start_raw:
                    if st.button("▶️ Start", key=f"start_{order_id}"):
                        update(f"orders/{firebase_key}", {
                            "design_start_time_raw": now_ist_raw(),
                            "design_start_time": now_ist_formatted()
                        })
                        st.rerun()
                    st.caption("Waiting to start")

                # STOP BUTTON
                elif not end_raw:
                    if st.button("⏹️ Stop", key=f"stop_{order_id}"):
                        update(f"orders/{firebase_key}", {
                            "design_end_time_raw": now_ist_raw(),
                            "design_end_time": now_ist_formatted()
                        })
                        st.rerun()
                    st.caption(f"Started: {order.get('design_start_time')}")

                # COMPLETED TIME
                else:
                    st.success("Completed")
                    st.caption(calculate_time_diff(start_raw, end_raw))


            # ====================================================
            # FILES (MIDDLE COLUMN)
            # ====================================================
            with fcol:
                st.subheader("📁 Files")
                f1, f2, f3 = st.columns(3)

                file_card(f1, order_id, "reference", "Reference", ["png", "jpg", "pdf"], firebase_key)
                file_card(f2, order_id, "template", "Template", ["pdf", "ai", "zip"], firebase_key)
                file_card(f3, order_id, "final", "Final Art", ["pdf", "ai", "zip"], firebase_key)


            # ====================================================
            # NOTES + COMPLETE BUTTON (RIGHT COLUMN)
            # ====================================================
            with ncol:

                st.subheader("📝 Notes")

                notes = st.text_area(
                    "Designer Notes",
                    value=order.get("design_notes", ""),
                    key=f"notes_{order_id}"
                )

                if st.button("💾 Save Notes", key=f"save_notes_{order_id}"):
                    update(f"orders/{firebase_key}", {"design_notes": notes})
                    st.toast("Notes saved successfully!", icon="💾")
                    st.rerun()

                st.markdown("---")

                # CHECK IF FINAL ART EXISTS
                final_art_exists = order.get("design_files", {}).get("final")

                if final_art_exists:

                    if st.button("🚀 Move to PRINTING", type="primary", key=f"complete_{order_id}"):

                        end_raw_final = order.get("design_end_time_raw") or now_ist_raw()
                        end_fmt_final = order.get("design_end_time") or now_ist_formatted()

                        update(f"orders/{firebase_key}", {
                            "stage": "Printing",
                            "design_completed_at_raw": end_raw_final,
                            "design_completed_at": end_fmt_final,
                            "design_end_time_raw": end_raw_final,
                            "design_end_time": end_fmt_final
                        })

                        st.balloons()
                        st.toast("Design Completed → Sent to PRINTING", icon="🚀")
                        st.rerun()

                else:
                    st.warning("Upload Final Art to complete order.")

            st.markdown("---")
# ================================
# SECTION 3 — COMPLETED DESIGNS
# ================================

with tab_completed:

    st.header("✅ Completed Designs")

    if not completed_orders:
        st.info("No completed designs yet.")

    for firebase_key, order in completed_orders.items():

        order_id = order.get("order_id")
        customer = order.get("customer")
        item = order.get("item")

        with st.container(border=True):

            # ----------------------------------------------------
            # HEADER
            # ----------------------------------------------------
            st.markdown(
                f"""
                <h3 style="margin-bottom:4px;">{order_id} — {customer}</h3>
                <div style="color:#444;margin-bottom:10px;">{item}</div>
                """,
                unsafe_allow_html=True
            )

            left, mid, right = st.columns([2, 3, 2])

            # ====================================================
            # LEFT COLUMN — BASIC INFO
            # ====================================================
            with left:
                st.subheader("📄 Details")

                st.write(f"**Customer:** {customer}")
                st.write(f"**Item:** {item}")

                completed_at = order.get("design_completed_at", "-")
                st.write(f"**Completed:** {completed_at}")

                st.write(
                    f"**Duration:** {calculate_time_diff(order.get('design_start_time_raw'), order.get('design_end_time_raw'))}"
                )


            # ====================================================
            # MIDDLE COLUMN — NOTES + TIMINGS
            # ====================================================
            with mid:
                st.subheader("📝 Notes")

                notes = order.get("design_notes", "-")
                st.write(notes if notes.strip() else "No notes added.")

                st.markdown("---")

                st.subheader("⏱️ Timing")

                start_fmt = order.get("design_start_time", "-")
                end_fmt = order.get("design_end_time", "-")

                st.write(f"**Started:** {start_fmt}")
                st.write(f"**Ended:** {end_fmt}")


            # ====================================================
            # RIGHT COLUMN — FILE PREVIEWS
            # ====================================================
            with right:
                st.subheader("📁 Files")

                df = order.get("design_files", {})

                for fk, label in {
                    "reference": "Reference",
                    "template": "Template",
                    "final": "Final Art"
                }.items():

                    file_b64 = df.get(fk)

                    if file_b64:
                        # Label header
                        st.markdown(
                            f"""
                            <div style="
                                background:#0C7A35;
                                padding:6px 12px;
                                border-radius:6px;
                                margin-top:5px;
                                margin-bottom:5px;
                                color:white;
                                font-weight:600;">
                                📄 {label}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Preview
                        preview_file(file_b64, label)

                        # Download button
                        download_button_ui(
                            file_b64,
                            f"{order_id}_{fk}.file",
                            f"⬇️ Download {label}",
                            f"dl_c_{fk}_{order_id}"
                        )

            st.markdown("---")
