import streamlit as st
from firebase import read, update
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

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
    try:
        orders = read("orders") or {}
    except:
        orders = {}

    incoming = {}      # stage = Assembly
    storage = {}       # stage = Storage
    dispatch = {}      # stage = Dispatch
    completed = {}     # stage = Completed

    for key, o in orders.items():
        if not isinstance(o, dict): continue
        s = o.get("stage")

        if s == "Assembly":
            incoming[key] = o
        elif s == "Storage":
            storage[key] = o
        elif s == "Dispatch":
            dispatch[key] = o
        elif s == "Completed":
            completed[key] = o

    return incoming, storage, dispatch, completed


incoming, storage, dispatch, completed = load_orders()
all_orders = {**incoming, **storage, **dispatch, **completed}

# ---------------- UTILS ----------------
def parse_dt(s):
    if not s: return None
    try:
        return datetime.fromisoformat(s)
    except:
        return None

def minutes_ago(t):
    if not t: return "N/A"
    diff = datetime.now(timezone.utc) - t
    return str(diff).split(".")[0]


def dl_qr_ui(b64_data):
    if b64_data:
        raw = base64.b64decode(b64_data + "===")
        st.download_button("⬇ Download QR", raw, "order_qr.png", "image/png", use_container_width=True)


# ---------------- TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Incoming From Assembly",
    "🏬 Storage",
    "🚀 Dispatch Queue",
    "✅ Completed Orders"
])

# =================================================================
# TAB 1: INCOMING FROM ASSEMBLY
# =================================================================
with tab1:

    st.subheader(f"Incoming Orders From Assembly ({len(incoming)})")

    if len(incoming) == 0:
        st.success("🎉 No incoming assembly orders.")
        st.stop()

    # MULTI SELECT AREA
    st.markdown("### ✓ Multi-Select Operations")
    selected = []
    colA, colB = st.columns([0.2, 0.8])

    with colA:
        select_all = st.checkbox("Select All")

    # Dropdown for action
    with colB:
        bulk_action = st.selectbox("Apply Action To Selected Orders:",
                                   ["None", "Move Selected to Storage", "Move Selected to Dispatch"])

    if select_all:
        selected = list(incoming.keys())

    # Apply bulk action
    if bulk_action != "None" and selected:
        now = datetime.now(timezone.utc).isoformat()

        if bulk_action == "Move Selected to Storage":
            for key in selected:
                update(f"orders/{key}", {
                    "stage": "Storage",
                    "storage_started_at": now
                })
            st.success(f"Moved {len(selected)} orders to Storage successfully.")
            st.rerun()

        if bulk_action == "Move Selected to Dispatch":
            for key in selected:
                update(f"orders/{key}", {
                    "stage": "Dispatch",
                    "storage_completed_at": now
                })
            st.success(f"Moved {len(selected)} orders to Dispatch successfully.")
            st.rerun()

    st.markdown("---")

    # LIST ORDERS
    for key, o in incoming.items():

        order_id = o.get("order_id")
        item = o.get("item")
        customer = o.get("customer")
        qty = o.get("qty")
        priority = o.get("priority", "Medium")
        assembly_done = parse_dt(o.get("assembly_completed_at"))

        with st.container(border=True):

            # header
            cols = st.columns([0.1, 2, 1, 1, 2, 2])
            with cols[0]:
                c = st.checkbox("", key=f"sel_{key}")
                if c: selected.append(key)

            cols[1].markdown(f"### {order_id}")
            cols[2].metric("Qty", qty)
            cols[3].metric("Priority", priority)

            with cols[4]:
                st.caption("Time Since Assembly")
                st.info(minutes_ago(assembly_done))

            with cols[5]:
                qr = o.get("order_qr")
                if qr:
                    st.image(base64.b64decode(qr), width=90)

            # BUTTONS
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

        st.markdown("---")


# =================================================================
# TAB 2: STORAGE
# =================================================================
with tab2:

    st.subheader(f"Orders in Storage ({len(storage)})")

    if len(storage) == 0:
        st.info("No orders in storage.")
    else:
        for key, o in storage.items():

            order_id = o.get("order_id")
            item = o.get("item")
            customer = o.get("customer")
            qty = o.get("qty")
            priority = o.get("priority", "Medium")
            storage_at = parse_dt(o.get("storage_started_at"))

            with st.container(border=True):

                cols = st.columns([2, 1, 1, 2, 1])
                cols[0].markdown(f"### {order_id} – {item}")
                cols[1].metric("Qty", qty)
                cols[2].metric("Priority", priority)
                cols[3].metric("Time in Storage", minutes_ago(storage_at))

                # Button
                with cols[4]:
                    if st.button("🚀 Move to Dispatch", key=f"store_to_disp_{key}", use_container_width=True):
                        update(f"orders/{key}", {
                            "stage": "Dispatch",
                            "storage_completed_at": datetime.now(timezone.utc).isoformat()
                        })
                        st.rerun()

            st.markdown("---")


# =================================================================
# TAB 3: DISPATCH QUEUE
# =================================================================
with tab3:

    st.subheader(f"Pending Dispatch ({len(dispatch)})")

    if len(dispatch) == 0:
        st.info("No orders waiting for dispatch.")
    else:
        for key, o in dispatch.items():

            order_id = o.get("order_id")
            item = o.get("item")
            customer = o.get("customer")
            qty = o.get("qty")
            priority = o.get("priority", "Medium")
            qr = o.get("order_qr")

            with st.container(border=True):

                cols = st.columns([2, 1, 1, 2])
                cols[0].markdown(f"### {order_id} – {item}")
                cols[1].metric("Qty", qty)
                cols[2].metric("Priority", priority)

                with cols[3]:
                    if qr:
                        st.image(base64.b64decode(qr), width=100)

                st.markdown("#### Dispatch Details")

                courier = st.text_input("Courier", o.get("courier", ""), key=f"c_{key}")
                tracking = st.text_input("Tracking No.", o.get("tracking_number", ""), key=f"t_{key}")
                notes = st.text_area("Notes", o.get("dispatch_notes", ""), key=f"n_{key}")

                save_col, done_col = st.columns([1, 1])

                if save_col.button("💾 Save", key=f"save_{key}", use_container_width=True):
                    update(f"orders/{key}", {
                        "courier": courier,
                        "tracking_number": tracking,
                        "dispatch_notes": notes
                    })
                    st.success("Saved.")
                    st.rerun()

                if done_col.button("🎉 Mark Completed", key=f"done_{key}", use_container_width=True):
                    now = datetime.now(timezone.utc).isoformat()
                    update(f"orders/{key}", {
                        "stage": "Completed",
                        "completed_at": now,
                        "dispatch_completed_at": now,
                        "dispatch_completed_by": USER
                    })
                    st.success("Order Completed!")
                    st.balloons()
                    st.rerun()

            st.markdown("---")


# =================================================================
# TAB 4: COMPLETED
# =================================================================
with tab4:

    st.subheader(f"Completed Orders ({len(completed)})")

    if len(completed) == 0:
        st.info("No completed orders.")
    else:
        for key, o in completed.items():

            order_id = o.get("order_id")
            item = o.get("item")
            courier = o.get("courier", "N/A")
            tracking = o.get("tracking_number", "N/A")
            notes = o.get("dispatch_notes", "N/A")
            qr = o.get("order_qr")
            completed_at = parse_dt(o.get("completed_at"))

            with st.expander(f"✅ {order_id} – {item}"):
                st.markdown(f"**Courier:** {courier}")
                st.markdown(f"**Tracking:** {tracking}")
                st.markdown(f"**Notes:** {notes}")
                st.markdown(f"**Completed At:** {completed_at}")

                if qr:
                    st.image(base64.b64decode(qr), width=120)
                    dl_qr_ui(qr)

            st.markdown("---")
