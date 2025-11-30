import streamlit as st
from firebase import read, update
import base64
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="Lamination Department", layout="wide", page_icon="🟦")

# ---------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["lamination", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🟦 Lamination Department")
st.caption("Manage lamination process, upload output files, enter lamination details & generate job slips.")

# ---------------------------------------------------
# LOAD ORDERS
# ---------------------------------------------------
orders = read("orders") or {}

pending = {}
completed = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # Only BOX orders go to Lamination
    if o.get("product_type") != "Box":
        continue

    if o.get("stage") == "Lamination":
        pending[key] = o
    elif o.get("lamination_completed_at"):
        completed[key] = o


# ---------------------------------------------------
# FILE DOWNLOAD HANDLER
# ---------------------------------------------------
def download_button(label, b64_data, order_id, fname, key_prefix):
    if not b64_data:
        return
    
    raw = base64.b64decode(b64_data)
    head = raw[:10]

    if head.startswith(b"%PDF"):
        ext, mime = ".pdf", "application/pdf"
    elif head.startswith(b"\x89PNG"):
        ext, mime = ".png", "image/png"
    elif head[:3] == b"\xff\xd8\xff":
        ext, mime = ".jpg", "image/jpeg"
    else:
        ext, mime = ".bin", "application/octet-stream"

    st.download_button(
        label=label,
        data=raw,
        file_name=f"{order_id}_{fname}{ext}",
        mime=mime,
        key=f"{key_prefix}_{order_id}",
        use_container_width=True
    )


# ---------------------------------------------------
# FILE PREVIEW
# ---------------------------------------------------
def preview(label, b64):
    if not b64:
        st.warning(f"{label} missing.")
        return

    raw = base64.b64decode(b64)
    head = raw[:10]

    st.markdown(f"#### 📄 {label} Preview")

    if head.startswith(b"%PDF"):
        st.info("PDF detected — download to view.")
    else:
        st.image(raw, use_column_width=True)


# ---------------------------------------------------
# GENERATE LAMINATION SLIP PDF
# ---------------------------------------------------
def generate_lamination_slip(o, lam_type, material, reel, assign_to, notes):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    t = c.beginText(40, 800)
    t.setFont("Helvetica", 12)

    t.textLine("LAMINATION DEPARTMENT – JOB SLIP")
    t.textLine("-------------------------------------------")
    t.textLine(f"Order ID: {o.get('order_id')}")
    t.textLine(f"Customer: {o.get('customer')}")
    t.textLine(f"Item: {o.get('item')}")
    t.textLine("")
    t.textLine(f"Lamination Type: {lam_type}")
    t.textLine(f"Material: {material}")
    t.textLine(f"Reel Width: {reel} inches")
    t.textLine(f"Assigned To: {assign_to}")
    t.textLine("")
    t.textLine("NOTES:")
    t.textLines(notes or "—")

    c.drawText(t)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------
# TABS UI
# ---------------------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Lamination ({len(pending)})",
    f"✔ Completed Lamination ({len(completed)})"
])


# ---------------------------------------------------
# TAB 1: PENDING LAMINATION
# ---------------------------------------------------
with tab1:

    if not pending:
        st.success("🎉 No pending lamination jobs!")

    for key, o in pending.items():
        order_id = o["order_id"]
        lam_file = o.get("lamination_file")

        with st.container(border=True):

            st.subheader(f"🟦 Order {order_id}")
            st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")
            st.divider()

            # ---------------- TIME TRACKING ----------------
            st.subheader("⏱ Time Tracking")

            start = o.get("lamination_start")
            end = o.get("lamination_end")

            if not start:
                if st.button("▶️ Start Lamination", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"lamination_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Lamination", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"lamination_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started at: {start}")

            else:
                st.success("Lamination Completed")
                st.caption(f"Start: {start}")
                st.caption(f"End: {end}")

            st.divider()

            # ---------------- LAMINATION DETAILS ----------------
            st.subheader("📋 Lamination Details")

            lam_type = st.selectbox(
                "Lamination Type",
                ["Gloss", "Matt", "Velvet", "Thermal", "BOPP Gloss", "BOPP Matt"],
                key=f"type_{order_id}"
            )

            material = st.text_input(
                "Quality / Material",
                value=o.get("lamination_material", ""),
                placeholder="e.g., BOPP 18 Micron",
                key=f"material_{order_id}"
            )

            reel = st.number_input(
                "Reel Width (inches)",
                min_value=1, max_value=100,
                value=o.get("lamination_reel_width", 30),
                key=f"reel_{order_id}"
            )

            assign_to = st.text_input(
                "Assign Work To",
                value=o.get("lamination_assigned_to", ""),
                placeholder="e.g., Rahul, Sameer",
                key=f"assign_{order_id}"
            )

            notes = st.text_area(
                "Notes",
                value=o.get("lamination_notes", ""),
                height=60,
                key=f"notes_{order_id}"
            )

            if st.button("💾 Save Details", key=f"save_details_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "lamination_type": lam_type,
                    "lamination_material": material,
                    "lamination_reel_width": reel,
                    "lamination_assigned_to": assign_to,
                    "lamination_notes": notes
                })
                st.success("Details Saved!")
                st.rerun()

            st.divider()

            # ---------------- FILE UPLOAD ----------------
            st.subheader("📁 Lamination Output File")

            up = st.file_uploader(
                "Upload Lamination File",
                type=["png", "jpg", "jpeg", "pdf"],
                key=f"upl_{order_id}"
            )

            if st.button("💾 Save File", key=f"save_file_{order_id}", use_container_width=True) and up:
                encoded = base64.b64encode(up.read()).decode()
                update(f"orders/{key}", {"lamination_file": encoded})
                st.success("File Uploaded!")
                st.rerun()

            if lam_file:
                preview("Lamination Output", lam_file)
                download_button("⬇ Download File", lam_file, order_id, "lamination", "dl_lam")

            st.divider()

            # ---------------- PDF SLIP DOWNLOAD ----------------
            st.subheader("📄 Download Lamination Slip")

            slip_pdf = generate_lamination_slip(
                o, lam_type, material, reel, assign_to, notes
            )

            st.download_button(
                label="📥 Download PDF Slip",
                data=slip_pdf,
                file_name=f"{order_id}_lamination_slip.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.divider()

            # ---------------- MOVE TO DIECUT ----------------
            if lam_file and end:
                if st.button("🚀 Move to DieCut", type="primary", key=f"next_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {
                        "stage": "DieCut",
                        "lamination_completed_at": datetime.now().isoformat()
                    })
                    st.balloons()
                    st.rerun()
            else:
                st.warning("Finish lamination + upload file to continue.")


# ---------------------------------------------------
# TAB 2: COMPLETED LAMINATION
# ---------------------------------------------------
with tab2:
    if not completed:
        st.info("No completed lamination jobs yet.")
    else:
        for key, o in completed.items():
            order_id = o["order_id"]

            with st.container(border=True):
                st.subheader(f"✔ {order_id} — {o.get('customer')}")
                st.caption(f"Completed at: {o.get('lamination_completed_at')}")

                lam_file = o.get("lamination_file")

                if lam_file:
                    preview("Lamination Output", lam_file)
                    download_button("⬇ Download File", lam_file, order_id, "lamination", "dl_completed")

                st.divider()
