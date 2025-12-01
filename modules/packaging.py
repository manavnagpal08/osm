import streamlit as st
from firebase import read, update
import base64
from datetime import datetime, timedelta, timezone


st.set_page_config(page_title="Logistics Department (DEBUG MODE)", page_icon="🚚", layout="wide")

# ---------------- ROLE CHECK ----------------
if "role" not in st.session_state:
    st.session_state["role"] = "admin"
    st.session_state["username"] = "AdminUser"

if st.session_state["role"] not in ["admin", "dispatch", "packaging"]:
    st.error("❌ You do not have permission to access this page.")


USER = st.session_state["username"]


# ---------------- DEBUG READ FROM FIREBASE ----------------
st.header("🟡 DEBUG: RAW FIREBASE ORDERS")
try:
    raw_orders = read("orders") or {}
    st.json(raw_orders)
except Exception as e:
    st.error(f"❌ ERROR reading Firebase: {e}")
    raw_orders = {}

st.markdown("---")

# ---------------- LOAD ORDERS ----------------
def load_orders_debug():
    st.subheader("🟡 DEBUG: STAGE GROUPING")

    incoming = {}
    storage = {}
    dispatch = {}
    completed = {}

    for k, o in raw_orders.items():
        s = o.get("stage")
        st.write(f"Order {k} → Stage = {s}")

        if s == "Assembly":
            incoming[k] = o
        elif s == "Storage":
            storage[k] = o
        elif s == "Dispatch":
            dispatch[k] = o
        elif s == "Completed":
            completed[k] = o
        else:
            st.warning(f"⚠️ UNKNOWN STAGE: {s} for {k}")

    st.markdown("### 🟢 Incoming Keys:")
    st.code(list(incoming.keys()))

    st.markdown("### 🟣 Storage Keys:")
    st.code(list(storage.keys()))

    st.markdown("### 🔵 Dispatch Keys:")
    st.code(list(dispatch.keys()))

    st.markdown("### 🟢 Completed Keys:")
    st.code(list(completed.keys()))

    return incoming, storage, dispatch, completed


incoming, storage, dispatch, completed = load_orders_debug()
st.markdown("---")


# ---------------- UTILS ----------------
def parse_dt(s):
    if not s:
        st.warning("parse_dt() received EMPTY")
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception as e:
        st.error(f"❌ parse_dt ERROR: '{s}' → {e}")
        return None


def dl_qr_ui(b64):
    if not b64:
        return
    try:
        raw = base64.b64decode(b64 + "===")
        st.download_button("⬇ Download QR", raw, "order_qr.png", "image/png")
    except Exception as e:
        st.error(f"QR decode failed: {e}")


# ---------------- TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Incoming",
    "🏬 Storage",
    "🚀 Dispatch Queue",
    "✅ Completed"
])

# ============================================================
# TAB 1 → INCOMING
# ============================================================
with tab1:

    st.subheader("📥 DEBUG: Incoming From Assembly")
    st.code(incoming)

    if len(incoming) == 0:
        st.error("❌ No incoming orders found. Check stages in Firebase above.")
        st.stop()

    for key, o in incoming.items():

        st.markdown(f"### 🟡 DEBUG ORDER {key}")
        st.json(o)

        order_id = o.get("order_id")
        assembly_done = parse_dt(o.get("assembly_completed_at"))

        with st.container(border=True):
            st.write(f"Order ID: {order_id}")
            st.write(f"Stage: {o.get('stage')}")
            st.write(f"assembly_completed_at: {o.get('assembly_completed_at')}")
            st.write(f"parsed time: {assembly_done}")

            col1, col2 = st.columns(2)

            if col1.button(f"Move {order_id} to Storage", key=f"m_s_{key}"):
                update(f"orders/{key}", {
                    "stage": "Storage",
                    "storage_started_at": datetime.now(timezone.utc).isoformat()
                })
                st.success(f"{order_id} moved to STORAGE")
                st.rerun()

            if col2.button(f"Move {order_id} to Dispatch", key=f"m_d_{key}"):
                update(f"orders/{key}", {
                    "stage": "Dispatch",
                    "storage_completed_at": datetime.now(timezone.utc).isoformat()
                })
                st.success(f"{order_id} moved to DISPATCH")
                st.rerun()

# ============================================================
# TAB 2 → STORAGE
# ============================================================
with tab2:

    st.subheader("🏬 DEBUG: STORAGE ITEMS")
    st.code(storage)

    if len(storage) == 0:
        st.warning("Storage empty.")
        st.stop()

    for key, o in storage.items():

        st.markdown(f"### 🟣 DEBUG STORAGE ORDER {key}")
        st.json(o)

        order_id = o.get("order_id")
        started = parse_dt(o.get("storage_started_at"))

        with st.container(border=True):
            st.write(f"Storage Started: {o.get('storage_started_at')}")
            st.write(f"parsed: {started}")

            if st.button(f"Move {order_id} to Dispatch", key=f"s2d_{key}"):
                update(f"orders/{key}", {
                    "stage": "Dispatch",
                    "storage_completed_at": datetime.now(timezone.utc).isoformat()
                })
                st.success("Moved to Dispatch")
                st.rerun()


# ============================================================
# TAB 3 → DISPATCH
# ============================================================
with tab3:

    st.subheader("🚀 DEBUG: DISPATCH QUEUE")
    st.code(dispatch)

    if len(dispatch) == 0:
        st.warning("Dispatch queue empty.")
        

    for key, o in dispatch.items():

        st.markdown(f"### 🔵 DEBUG DISPATCH ORDER {key}")
        st.json(o)

        courier = st.text_input("Courier", o.get("courier", ""), key=f"c_{key}")
        tracking = st.text_input("Tracking", o.get("tracking_number", ""), key=f"t_{key}")

        if st.button(f"Save {key}", key=f"sav_{key}"):
            update(f"orders/{key}", {
                "courier": courier,
                "tracking_number": tracking
            })
            st.success("Saved.")
            st.rerun()

        if st.button(f"Complete {key}", key=f"comp_{key}"):
            now = datetime.now(timezone.utc).isoformat()
            update(f"orders/{key}", {
                "stage": "Completed",
                "completed_at": now
            })
            st.success("Completed.")
            st.rerun()


# ============================================================
# TAB 4 → COMPLETED
# ============================================================
with tab4:

    st.subheader("🏁 DEBUG: COMPLETED ORDERS")
    st.code(completed)

    if len(completed) == 0:
        st.warning("No completed orders.")
       

    for key, o in completed.items():
        st.json(o)
        st.write(f"Completed at: {o.get('completed_at')}")
