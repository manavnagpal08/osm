import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

# -----------------------------------------
# PAGE CONFIG
# -----------------------------------------
st.set_page_config(page_title="Assembly Department", layout="wide", page_icon="🟩")

# -----------------------------------------
# ROLE CHECK
# -----------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["assembly", "admin"]:
    st.error("❌ Access Denied")
    st.stop()

st.title("🟩 Assembly Department")
st.caption("Manage assembly work, record output, assign workers & generate job slips.")

# -----------------------------------------
# LOAD ORDERS
# -----------------------------------------
orders = read("orders") or {}

pending = {}
completed = {}

for key, o in orders.items():

    if not isinstance(o, dict):
        continue

    # Bags and Boxes both reach Assembly
    if o.get("stage") == "Assembly":
        pending[key] = o
    elif o.get("assembly_completed_at"):
        completed[key] = o


# -----------------------------------------
# UTILITIES
# -----------------------------------------
def detect_file_type(data):
    raw = base64.b64decode(data)
    head = raw[:10]
    if head.startswith(b"%PDF"):
        return "pdf", "application/pdf", ".pdf"
    if head.startswith(b"\x89PNG"):
        return "png", "image/png", ".png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg", ".jpg"
    return "bin", "application/octet-stream", ".bin"


def preview(label, b64):
    if not b64:
        st.warning(f"{label} missing")
        return
    raw = base64.b64decode(b64)
    if raw.startswith(b"%PDF"):
        st.info("PDF preview not supported — download to view.")
    else:
        st.image(raw, use_container_width=True)


def download_button_ui(label, b64, order_id, fname):
    if not b64:
        return
    raw = base64.b64decode(b64)
    _, mime, ext = detect_file_type(b64)
    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime,
        use_container_width=True
    )


# -----------------------------------------
# PDF — PURE PYTHON
# -----------------------------------------
def generate_assembly_slip(order, assembled_qty, assign_to, notes):

    lines = [
        "ASSEMBLY DEPARTMENT – WORK SLIP",
        "",
        f"Order ID: {order.get('order_id')}",
        f"Customer: {order.get('customer')}",
        f"Item: {order.get('item')}",
        "",
        f"Order Quantity: {order.get('qty')}",
        f"Assembled Quantity: {assembled_qty}",
        f"Remaining: {max(order.get('qty', 0) - assembled_qty, 0)}",
        "",
        f"Assigned To: {assign_to}",
        "",
        "Notes:",
        notes or "-",
        "",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]

    def esc(s): return s.replace("(", "\\(").replace(")", "\\)")

    pdf_text = "BT\n/F1 12 Tf\n50 750 Td\n"
    for ln in lines:
        pdf_text += f"({esc(ln)}) Tj\n0 -18 Td\n"
    pdf_text += "ET"

    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj <<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources << /Font << /F1 5 0 R >> >>
/Contents 4 0 R
>> endobj
4 0 obj << /Length {len(pdf_text)} >> stream
{pdf_text}
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000065 00000 n
0000000134 00000 n
0000000325 00000 n
0000000571 00000 n
trailer << /Root 1 0 R /Size 6 >>
startxref
700
%%EOF
"""
    return pdf.encode("utf-8", errors="ignore")


# -----------------------------------------
# TABS
# -----------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Assembly ({len(pending)})",
    f"✔ Completed Assembly ({len(completed)})"
])


# -----------------------------------------
# TAB: PENDING
# -----------------------------------------
with tab1:

    if not pending:
        st.success("🎉 No pending Assembly work!")

    for key, o in pending.items():

        order_id = o["order_id"]
        file_assembly = o.get("assembly_file")

        with st.container(border=True):

            st.subheader(f"🟩 Order {order_id}")
            st.write(f"**Customer:** {o.get('customer')}  —  **Item:** {o.get('item')}  —  **Qty:** {o.get('qty')}")

            st.divider()

            # ---------------- TIME TRACKING ----------------
            st.subheader("⏱ Time Tracking")

            start = o.get("assembly_start")
            end = o.get("assembly_end")

            if not start:
                if st.button("▶️ Start Assembly", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"assembly_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Assembly", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"assembly_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started at: {start}")

            else:
                st.success("Assembly Completed")
                st.caption(f"Start: {start}")
                st.caption(f"End: {end}")

            st.divider()

            # ---------------- ASSEMBLY DETAILS ----------------
            st.subheader("📋 Assembly Work Details")

            qty = o.get("qty", 1)

            assembled_qty = st.number_input(
                "Assembled Quantity",
                min_value=0,
                max_value=qty,
                value=o.get("assembled_qty", 0),
                key=f"asm_qty_{order_id}"
            )

            assign_to = st.text_input(
                "Assign Worker",
                value=o.get("assembly_assigned_to", ""),
                placeholder="e.g., Manish, Rohan, Salim",
                key=f"asm_assign_{order_id}"
            )

            remaining = max(qty - assembled_qty, 0)
            st.info(f"Remaining: **{remaining} pcs**")

            notes = st.text_area(
                "Notes",
                value=o.get("assembly_notes", ""),
                key=f"asm_notes_{order_id}",
                height=70
            )

            if st.button("💾 Save Assembly Data", key=f"save_asm_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "assembled_qty": assembled_qty,
                    "assembly_assigned_to": assign_to,
                    "assembly_notes": notes
                })
                st.success("Saved!")
                st.rerun()

            st.divider()

            # ---------------- FILE UPLOAD ----------------
            st.subheader("📁 Upload Assembly Output")

            up = st.file_uploader(
                "Upload File",
                type=["png", "jpg", "jpeg", "pdf"],
                key=f"upasm_{order_id}"
            )

            if st.button("💾 Save File", key=f"save_fileasm_{order_id}", use_container_width=True) and up:
                encoded = base64.b64encode(up.read()).decode()
                update(f"orders/{key}", {"assembly_file": encoded})
                st.success("File Uploaded!")
                st.rerun()

            if file_assembly:
                preview("Assembly File", file_assembly)
                download_button_ui("⬇ Download File", file_assembly, order_id, "assembly")

            st.divider()

            # ---------------- PDF SLIP ----------------
            st.subheader("📄 Assembly Slip")

            slip = generate_assembly_slip(o, assembled_qty, assign_to, notes)

            st.download_button(
                "📥 Download Assembly Slip (PDF)",
                data=slip,
                file_name=f"{order_id}_assembly_slip.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.divider()

            # ---------------- MOVE TO NEXT STAGE ----------------
            if file_assembly and end:
                if st.button("🚀 Move to Packing", key=f"next_{order_id}", type="primary", use_container_width=True):
                    update(f"orders/{key}", {
                        "stage": "Packing",
                        "assembly_completed_at": datetime.now().isoformat()
                    })
                    st.balloons()
                    st.success("Moved to Packing!")
                    st.rerun()
            else:
                st.warning("⚠ Complete time & upload file to proceed.")


# -----------------------------------------
# TAB: COMPLETED
# -----------------------------------------
with tab2:

    if not completed:
        st.info("No completed Assembly jobs.")

    for key, o in completed.items():

        st.write(f"### {o['order_id']} — {o['customer']}")
        st.caption(f"Item: {o.get('item')} — Qty: {o.get('qty')}")
        st.caption(f"Completed At: {o.get('assembly_completed_at')}")

        file_assembly = o.get("assembly_file")
        if file_assembly:
            preview("Assembly File", file_assembly)
            download_button_ui("⬇ Download File", file_assembly, o["order_id"], "assembly")

        st.divider()
