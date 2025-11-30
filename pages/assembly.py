import streamlit as st
from firebase import read, update
import base64
from datetime import datetime, timedelta

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
st.caption("Manage assembly work, record output, assign workers, monitor deadlines & generate slips.")

# -----------------------------------------
# LOAD ORDERS
# -----------------------------------------
orders = read("orders") or {}

pending, completed = {}, {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("stage") == "Assembly":
        pending[key] = o
    elif o.get("assembly_completed_at"):
        completed[key] = o


# -----------------------------------------
# UTILITIES
# -----------------------------------------
def detect_file_type(data):
    raw = base64.b64decode(data)
    header = raw[:10]
    if header.startswith(b"%PDF"): return "pdf", "application/pdf", ".pdf"
    if header.startswith(b"\x89PNG"): return "png", "image/png", ".png"
    if header[:3] == b"\xff\xd8\xff": return "jpg", "image/jpeg", ".jpg"
    return "bin", "application/octet-stream", ".bin"


def preview(label, b64):
    if not b64:
        st.warning(f"{label} missing")
        return
    raw = base64.b64decode(b64)
    if raw.startswith(b"%PDF"):
        st.info("PDF preview not supported → Download to view.")
    else:
        st.image(raw, use_container_width=True)


def download_button_ui(label, b64, order_id, fname):
    if not b64: 
        return
    raw = base64.b64decode(b64)
    _, mime, ext = detect_file_type(b64)

    st.markdown(
        f"""
        <style>
        .download-btn-{order_id} {{
            background: linear-gradient(90deg,#4CAF50,#0A7B32);
            color: white;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime,
        key=f"dl_{fname}_{order_id}",
        use_container_width=True
    )


# -----------------------------------------
# PURE PYTHON PDF SLIP
# -----------------------------------------
def generate_slip(order, assembled_qty, assign_to, material, notes):

    lines = [
        "ASSEMBLY DEPARTMENT – WORK SLIP",
        "",
        f"Order ID: {order.get('order_id')}",
        f"Customer: {order.get('customer')}",
        "",
        f"Item: {order.get('item')}",
        f"Order Quantity: {order.get('qty')}",
        f"Assembled Quantity: {assembled_qty}",
        f"Remaining: {max(order.get('qty', 0) - assembled_qty, 0)}",
        "",
        f"Material Used: {material}",
        f"Assigned To: {assign_to}",
        "",
        "Notes:",
        notes or "-",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]

    def esc(t): return t.replace("(", "\\(").replace(")", "\\)")

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
0000000130 00000 n
0000000305 00000 n
0000000550 00000 n
trailer << /Root 1 0 R /Size 6 >>
startxref
700
%%EOF"""
    return pdf.encode("latin-1", errors="ignore")


# -----------------------------------------
# TABS
# -----------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Assembly ({len(pending)})",
    f"✔ Completed Assembly ({len(completed)})"
])


# -----------------------------------------
# PENDING
# -----------------------------------------
with tab1:

    if not pending:
        st.success("🎉 All assembly jobs completed!")

    for key, o in pending.items():

        order_id = o["order_id"]
        file_asm = o.get("assembly_file")

        with st.container(border=True):

            st.subheader(f"🟩 Order {order_id}")
            st.write(f"**Customer:** {o.get('customer')}  |  **Item:** {o.get('item')}  |  **Qty:** {o.get('qty')}")

            # ---------------- DEADLINE WATCH ----------------
            st.markdown("### ⏳ Deadline Monitoring")

            start_design_out = o.get("printing_completed_at") or o.get("diecut_completed_at")
            if start_design_out:
                start_time = datetime.fromisoformat(start_design_out)
                deadline = start_time + timedelta(hours=36)

                now = datetime.now()

                if now > deadline:
                    st.error(f"⛔ OVERDUE by {(now - deadline)}")
                else:
                    remaining = deadline - now
                    st.success(f"🟢 Time Remaining: {remaining}")

            st.divider()

            # ---------------- TIME TRACKING ----------------
            st.markdown("### 🕒 Time Tracking")

            start = o.get("assembly_start")
            end = o.get("assembly_end")

            if not start:
                if st.button("▶ Start Assembly", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"assembly_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Assembly", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"assembly_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started at: {start}")

            else:
                st.success("✔ Assembly Completed")
                st.caption(f"Start: {start} | End: {end}")

            st.divider()

            # ---------------- DETAILS FORM ----------------
            st.markdown("### 🧾 Assembly Details")

            qty = o.get("qty", 1)

            assembled_qty = st.number_input(
                "Assembled Quantity",
                min_value=0,
                max_value=qty,
                value=o.get("assembled_qty", 0),
                key=f"asmqty_{order_id}"
            )

            assign_to = st.text_input(
                "Assign Worker",
                o.get("assembly_assigned_to", ""),
                key=f"assign_{order_id}",
                placeholder="e.g., Rohan / Sameer"
            )

            material = st.text_input(
                "Material Used",
                o.get("assembly_material", ""),
                placeholder="e.g., White Glue, 180 GSM Board",
                key=f"mat_{order_id}"
            )

            notes = st.text_area(
                "Notes",
                o.get("assembly_notes", ""),
                key=f"notes_{order_id}",
                height=80
            )

            remaining = qty - assembled_qty
            st.info(f"Remaining Quantity: **{remaining} pcs**")

            if st.button("💾 Save Data", key=f"save_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "assembled_qty": assembled_qty,
                    "assembly_assigned_to": assign_to,
                    "assembly_material": material,
                    "assembly_notes": notes
                })
                st.success("Saved!")
                st.rerun()

            st.divider()

            # ---------------- FILE UPLOAD ----------------
            st.markdown("### 📁 Assembly Output File")

            upload = st.file_uploader(
                "Upload File (JPG, PNG, PDF)",
                type=["png", "jpg", "jpeg", "pdf"],
                key=f"upasm_{order_id}"
            )

            if st.button("💾 Save File", key=f"svf_{order_id}", use_container_width=True) and upload:
                encoded = base64.b64encode(upload.read()).decode()
                update(f"orders/{key}", {"assembly_file": encoded})
                st.success("File uploaded!")
                st.rerun()

            if file_asm:
                preview("Assembly Output", file_asm)
                download_button_ui("⬇ Download Assembly File", file_asm, order_id, "assembly")

            st.divider()

            # ---------------- SLIP DOWNLOAD ----------------
            st.markdown("### 📄 Assembly Slip")

            slip = generate_slip(o, assembled_qty, assign_to, material, notes)

            st.download_button(
                "📥 Download Slip (PDF)",
                data=slip,
                file_name=f"{order_id}_assembly_slip.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.divider()

            # ---------------- MOVE TO NEXT STAGE ----------------
            if file_asm and end:
                if st.button("🚀 Move to Packing", key=f"next_{order_id}", type="primary", use_container_width=True):
                    update(f"orders/{key}", {
                        "stage": "Packing",
                        "assembly_completed_at": datetime.now().isoformat()
                    })
                    st.balloons()
                    st.success("Moved to Packing!")
                    st.rerun()
            else:
                st.warning("⚠ Complete all steps (time + file) to continue.")


# -----------------------------------------
# COMPLETED TAB
# -----------------------------------------
with tab2:
    if not completed:
        st.info("No completed Assembly work")

    for key, o in completed.items():
        st.subheader(f"{o['order_id']} — {o['customer']}")
        st.caption(f"Completed At: {o.get('assembly_completed_at')}")

        file_asm = o.get("assembly_file")
        if file_asm:
            preview("Assembly File", file_asm)
            download_button_ui("⬇ Download Assembly File", file_asm, o['order_id'], "assembly")

        st.divider()
