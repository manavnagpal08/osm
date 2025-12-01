import streamlit as st
from firebase import read, update
import base64
from datetime import datetime, timezone, timedelta


st.set_page_config(page_title="Logistics Department", page_icon="🚚", layout="wide")

# ---------------- ROLE CHECK ----------------
if "role" not in st.session_state:
    st.session_state["role"] = "admin"
    st.session_state["username"] = "AdminUser"

if st.session_state["role"] not in ["admin", "dispatch", "packaging"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

USER = st.session_state["username"]


# ---------------- LOAD ORDERS ----------------
@st.cache_data(ttl=1)
def load_orders():
    orders = read("orders") or {}

    incoming = {}       # from assembly (stage = Assembly)
    storage = {}         # stage = Storage
    dispatch = {}        # stage = Dispatch
    completed = {}       # stage = Completed

    for key, o in orders.items():
        if not isinstance(o, dict):
            continue

        stage = o.get("stage", "")

        if stage == "Assembly":
            incoming[key] = o
        elif stage == "Storage":
            storage[key] = o
        elif stage == "Dispatch":
            dispatch[key] = o
        elif stage == "Completed":
            completed[key] = o

    return incoming, storage, dispatch, completed


incoming, storage, dispatch, completed = load_orders()


# ---------------- UTILS (REFACTORED) ----------------
def parse_dt(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return None


def get_qr_raw_data(b64_data):
    """Safely decode base64 QR data and return raw bytes."""
    if not b64_data:
        return None
    try:
        # The '===' padding is added for robustness
        return base64.b64decode(b64_data + "===")
    except:
        return None


def show_qr_inline(raw_data, width=110):
    """Show QR image from raw bytes."""
    if raw_data:
        st.image(raw_data, width=width)
    else:
        st.warning("QR not available")


def dl_qr(raw_data):
    """Provide download button for QR from raw bytes."""
    if raw_data:
        st.download_button("⬇ Download QR", raw_data, "order_qr.png", "image/png", use_container_width=True)
    # No warning if data is missing, just no button


# ---------------- TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Incoming From Assembly",
    "🏬 Storage",
    "🚀 Dispatch Queue",
    "✅ Completed Orders"
])

# ============================================================
# TAB 1 → INCOMING (Modified QR display)
# ============================================================
with tab1:

    st.subheader(f"Incoming Orders From Assembly ({len(incoming)})")

    if len(incoming) == 0:
        st.success("🎉 No incoming assembly orders.")
        st.markdown("---")

    selected = []
    colA, colB = st.columns([0.2, 0.8])

    with colA:
        select_all = st.checkbox("Select All")

    with colB:
        bulk_action = st.selectbox(
            "Apply Action:",
            ["None", "Move Selected to Storage", "Move Selected to Dispatch"]
        )

    if select_all:
        selected = list(incoming.keys())

    # BULK ACTION
    if bulk_action != "None" and selected:
        now = datetime.now(timezone.utc).isoformat()

        for k in selected:
            if bulk_action == "Move Selected to Storage":
                update(f"orders/{k}", {"stage": "Storage", "storage_started_at": now})

            if bulk_action == "Move Selected to Dispatch":
                update(f"orders/{k}", {"stage": "Dispatch", "storage_completed_at": now})

        st.success(f"{len(selected)} orders updated.")
        st.rerun()

    # ORDER LIST
    for key, o in incoming.items():

        order_id = o.get("order_id")
        item = o.get("item")
        customer = o.get("customer")
        qty = o.get("qty")
        priority = o.get("priority", "Medium")
        qr = o.get("order_qr")
        qr_raw = get_qr_raw_data(qr) # NEW: Decode QR once

        assembly_done = parse_dt(o.get("assembly_completed_at"))

        with st.container(border=True):
            cols = st.columns([0.1, 3, 1, 1, 2, 1])

            # Select checkbox
            with cols[0]:
                if st.checkbox("", key=f"sel_{key}"):
                    selected.append(key)

            cols[1].markdown(f"### {order_id} — {item}")
            cols[1].caption(f"Customer: {customer}")

            cols[2].metric("Qty", qty)
            cols[3].metric("Priority", priority)

            with cols[4]:
                if assembly_done:
                    diff = datetime.now(timezone.utc) - assembly_done
                    st.info(str(diff).split(".")[0])
                else:
                    st.warning("N/A")

            with cols[5]:
                show_qr_inline(qr_raw) # CHANGED

            b1, b2 = st.columns(2)

            if b1.button("🏬 Move to Storage", key=f"to_store_{key}", use_container_width=True):
                update(f"orders/{key}", {
                    "stage": "Storage",
                    "storage_started_at": datetime.now(timezone.utc).isoformat()
                })
                st.rerun()

            if b2.button("🚀 Move to Dispatch", key=f"to_disp_{key}", use_container_width=True):
                update(f"orders/{key}", {
                    "stage": "Dispatch",
                    "storage_completed_at": datetime.now(timezone.utc).isoformat()
                })
                st.rerun()


# ============================================================
# TAB 2 → STORAGE (Modified QR display)
# ============================================================
with tab2:

    st.subheader(f"Orders in Storage ({len(storage)})")

    if len(storage) == 0:
        st.info("No orders in storage.")
        st.markdown("---")

    for key, o in storage.items():

        order_id = o.get("order_id")
        item = o.get("item")
        qty = o.get("qty")
        priority = o.get("priority", "Medium")
        qr = o.get("order_qr")
        qr_raw = get_qr_raw_data(qr) # NEW: Decode QR once

        started = parse_dt(o.get("storage_started_at"))
        time_in_storage = "N/A"

        if started:
            diff = datetime.now(timezone.utc) - started
            time_in_storage = str(diff).split(".")[0]

        with st.container(border=True):

            cols = st.columns([3, 1, 1, 2, 1])

            cols[0].markdown(f"### {order_id} — {item}")
            cols[1].metric("Qty", qty)
            cols[2].metric("Priority", priority)
            cols[3].metric("Time in Storage", time_in_storage)

            with cols[4]:
                show_qr_inline(qr_raw) # CHANGED

            if st.button("🚀 Move to Dispatch", key=f"s2d_{key}", use_container_width=True):
                update(f"orders/{key}", {
                    "stage": "Dispatch",
                    "storage_completed_at": datetime.now(timezone.utc).isoformat()
                })
                st.rerun()


# ============================================================
# TAB 3 → DISPATCH (Modified QR display)
# ============================================================
with tab3:

    st.subheader(f"Pending Dispatch ({len(dispatch)})")

    if len(dispatch) == 0:
        st.info("No orders waiting for dispatch.")
        st.markdown("---")

    for key, o in dispatch.items():

        order_id = o.get("order_id")
        item = o.get("item")
        qty = o.get("qty")
        priority = o.get("priority", "Medium")
        qr = o.get("order_qr")
        qr_raw = get_qr_raw_data(qr) # NEW: Decode QR once

        with st.container(border=True):
            cols = st.columns([3, 1, 1, 2])

            cols[0].markdown(f"### {order_id} — {item}")
            cols[1].metric("Qty", qty)
            cols[2].metric("Priority", priority)

            with cols[3]:
                show_qr_inline(qr_raw) # CHANGED

            st.markdown("#### Dispatch Details")

            courier = st.text_input("Courier", o.get("courier", ""), key=f"courier_{key}")
            tracking = st.text_input("Tracking No.", o.get("tracking_number", ""), key=f"track_{key}")
            notes = st.text_area("Notes", o.get("dispatch_notes", ""), key=f"notes_{key}")

            c1, c2 = st.columns(2)

            if c1.button("💾 Save", key=f"save_{key}", use_container_width=True):
                update(f"orders/{key}", {
                    "courier": courier,
                    "tracking_number": tracking,
                    "dispatch_notes": notes
                })
                st.success("Saved")
                st.rerun()

            if c2.button("🎉 Mark Completed", key=f"done_{key}", use_container_width=True):
                now = datetime.now(timezone.utc).isoformat()
                update(f"orders/{key}", {
                    "stage": "Completed",
                    "completed_at": now,
                    "dispatch_completed_at": now,
                    "dispatch_completed_by": USER
                })
                st.balloons()
                st.rerun()


# ============================================================
# TAB 4 → COMPLETED (Modified QR display/download)
# ============================================================
with tab4:

    st.subheader(f"Completed Orders ({len(completed)})")

    if len(completed) == 0:
        st.info("No completed orders.")
        st.markdown("---")

    for key, o in completed.items():

        order_id = o.get("order_id")
        item = o.get("item")
        courier = o.get("courier", "N/A")
        tracking = o.get("tracking_number", "N/A")
        notes = o.get("dispatch_notes", "N/A")
        qr = o.get("order_qr")
        qr_raw = get_qr_raw_data(qr) # NEW: Decode QR once

        completed_dt = parse_dt(o.get("completed_at"))
        completed_txt = completed_dt.strftime("%Y-%m-%d %H:%M") if completed_dt else "N/A"

        with st.expander(f"✅ {order_id} — {item}"):
            st.markdown(f"**Courier:** {courier}")
            st.markdown(f"**Tracking No:** {tracking}")
            st.markdown(f"**Completed At:** {completed_txt}")
            st.markdown(f"**Notes:** {notes}")

            if qr_raw: # CHANGED: Check decoded data for presence
                # Use columns to neatly separate the QR image and download button
                c_qr, c_dl = st.columns([1, 4])
                with c_qr:
                    show_qr_inline(qr_raw, width=150) # CHANGED: Use raw data
                with c_dl:
                    st.markdown("<br>", unsafe_allow_html=True) # Add spacing
                    dl_qr(qr_raw)                           # CHANGED: Use raw data
            else:
                st.warning("QR not available for this order.")
