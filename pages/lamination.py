import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Lamination Department",
    layout="wide",
    page_icon="🟦"
)

# ---------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["lamination", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🟦 Lamination Department")
st.caption("Manage lamination process, upload files, assign operator & download job slips.")

# ---------------------------------------------------
# LOAD ORDERS
# ---------------------------------------------------
orders = read("orders") or {}

pending = {}
completed = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    if o.get("product_type") != "Box":
        continue  # Lamination only for Box

    if o.get("stage") == "Lamination":
        pending[key] = o
    elif o.get("lamination_completed_at"):
        completed[key] = o

# ---------------------------------------------------
# FILE DOWNLOAD HANDLER (Auto-detect file type)
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
        st.info("PDF detected — Please download to view.")
    else:
        st.image(raw, use_container_width=True)

# ---------------------------------------------------
# PURE PYTHON PDF SLIP GENERATOR
# ---------------------------------------------------
def generate_lamination_slip(order, lam_type, material, reel, assign_to, notes):
    # Clean multi-line text inside PDF safely
    def pdf_escape(text):
        return text.replace("(", "\\(").replace(")", "\\)")

    content = f"""
LAMINATION DEPARTMENT – JOB SLIP

Order ID: {order.get('order_id')}
Customer: {order.get('customer')}
Item: {order.get('item')}

Lamination Type: {lam_type}
Material Quality: {material}
Reel Width: {reel} inches
Assigned To: {assign_to}

Notes:
{notes or '-'}

Generated At: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

    # Escape PDF characters
    safe = pdf_escape(content)

    pdf_bytes = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
  /Font << /F1 5 0 R >>
>>
>>
endobj
4 0 obj
<< /Length {len(safe) + 200} >>
stream
BT
/F1 12 Tf
50 750 Td
({safe}) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font
   /Subtype /Type1
   /BaseFont /Courier
>>
endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000178 00000 n
0000000379 00000 n
0000000565 00000 n
trailer
<< /Root 1 0 R /Size 6 >>
startxref
640
%%EOF
"""

    return pdf_bytes.encode("utf-8", errors="ignore")


# ---------------------------------------------------
# TABS
# ---------------------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Lamination ({len(pending)})",
    f"✔ Completed Lamination ({len(completed)})"
])

# ---------------------------------------------------
# TAB 1 — PENDING JOBS
# ---------------------------------------------------
with tab1:
    if not pending:
        st.success("🎉 No pending lamination work!")
    
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
                if st.button("▶ Start Lamination", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"lamination_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Lamination", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"lamination_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started: {start}")

            else:
                st.success("Lamination Time Completed")
                st.caption(f"Start: {start}")
                st.caption(f"End: {end}")

            st.divider()

            # ---------------- DETAILS ----------------
            st.subheader("📋 Lamination Details")

            lam_type = st.selectbox(
                "Lamination Type", 
                ["Gloss", "Matt", "Velvet", "Thermal", "BOPP Gloss", "BOPP Matt"],
                key=f"type_{order_id}"
            )

            material = st.text_input(
                "Material Quality",
                value=o.get("lamination_material", ""),
                placeholder="e.g., BOPP 20 Micron",
                key=f"material_{order_id}"
            )

            reel = st.number_input(
                "Reel Width (Inches)",
                min_value=1, max_value=100, value=30,
                key=f"reel_{order_id}"
            )

            assign_to = st.text_input(
                "Assign Work To",
                value=o.get("lamination_assigned_to", ""),
                placeholder="e.g., Rajesh",
                key=f"assign_{order_id}"
            )

            notes = st.text_area(
                "Notes",
                value=o.get("lamination_notes", ""),
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
            st.subheader("📁 Upload Lamination Output")

            up = st.file_uploader(
                "Upload File",
                type=["pdf", "png", "jpg"],
                key=f"upl_{order_id}"
            )

            if st.button("💾 Save File", key=f"save_file_{order_id}", use_container_width=True) and up:
                encoded = base64.b64encode(up.read()).decode()
                update(f"orders/{key}", {"lamination_file": encoded})
                st.success("File Uploaded!")
                st.rerun()

            if lam_file:
                preview("Lamination File", lam_file)
                download_button("⬇ Download", lam_file, order_id, "lamination", "dl")

            st.divider()

            # ---------------- PDF SLIP ----------------
            st.subheader("📄 Download Lamination Slip")

            slip_bytes = generate_lamination_slip(
                o, lam_type, material, reel, assign_to, notes
            )

            st.download_button(
                label="⬇ Download Lamination Slip (PDF)",
                data=slip_bytes,
                file_name=f"{order_id}_lamination_slip.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            # ---------------- COMPLETE & MOVE TO NEXT ----------------
            if st.button("🚀 Move to DieCut", key=f"move_{order_id}", type="primary", use_container_width=True):
                now = datetime.now().isoformat()
                update(f"orders/{key}", {
                    "stage": "DieCut",
                    "lamination_completed_at": now,
                    "lamination_end": o.get("lamination_end") or now
                })
                st.success("Moved to DieCut Stage!")
                st.balloons()
                st.rerun()

# ---------------------------------------------------
# TAB 2 — COMPLETED JOBS
# ---------------------------------------------------
with tab2:
    st.header("✔ Completed Lamination")

    for key, o in completed.items():
        with st.container(border=True):
            st.write(f"### {o.get('order_id')} — {o.get('customer')}")
            st.caption(f"Completed At: {o.get('lamination_completed_at')}")

            if o.get("lamination_file"):
                download_button("⬇ Download Lamination File", o["lamination_file"], o["order_id"], "lamination", "dl2")

            st.markdown("---")
