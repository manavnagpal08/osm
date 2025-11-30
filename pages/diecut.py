import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="Die-Cut Department", layout="wide", page_icon="✂️")

# ---------------------------------------------------
# ROLE CHECK
# ---------------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["diecut", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("✂️ Die-Cut Department")
st.caption("Manage die-cutting operations, assign workers, upload output files & generate job slips.")

# ---------------------------------------------------
# LOAD ORDERS
# ---------------------------------------------------
orders = read("orders") or {}

pending = {}
completed = {}

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # Only BOX orders reach Die-Cut
    if o.get("product_type") != "Box":
        continue

    if o.get("stage") == "DieCut":
        pending[key] = o
    elif o.get("diecut_completed_at"):
        completed[key] = o


# ---------------------------------------------------
# FILE DOWNLOAD HANDLER
# ---------------------------------------------------
def download_button(label, b64_data, order_id, fname, key_prefix):
    if not b64_data:
        return

    raw = base64.b64decode(b64_data)
    head = raw[:10]

    # Detect type
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
# PREVIEW HANDLER
# ---------------------------------------------------
def preview(label, b64):
    if not b64:
        st.warning(f"{label} not uploaded.")
        return

    raw = base64.b64decode(b64)
    head = raw[:10]

    st.markdown(f"### 📄 {label}")

    if head.startswith(b"%PDF"):
        st.info("PDF cannot be previewed — download to view.")
    else:
        st.image(raw, use_container_width=True)


# ---------------------------------------------------
# PDF GENERATOR — PURE PYTHON
# ---------------------------------------------------
def generate_diecut_slip(order, machine, blade, assign_to, die_paper, die_board,
                         cut_per_sheet, cut_per_board, total_sheets, total_boards, notes):

    lines = [
        "DIE-CUT DEPARTMENT – JOB SLIP",
        "",
        f"Order ID: {order.get('order_id')}",
        f"Customer: {order.get('customer')}",
        f"Item: {order.get('item')}",
        "",
        f"Machine: {machine}",
        f"Blade Type: {blade}",
        f"Assigned To: {assign_to}",
        "",
        f"Die Number (Paper): {die_paper}",
        f"Die Number (Board): {die_board}",
        "",
        f"Paper Cut Per Sheet: {cut_per_sheet}",
        f"Board Cut Per Die: {cut_per_board}",
        "",
        f"Total Paper Sheets Needed: {total_sheets}",
        f"Total Boards Needed: {total_boards}",
        "",
        "Notes:",
        notes or "-",
        "",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]

    def esc(s):  # Escape brackets
        return s.replace("(", "\\(").replace(")", "\\)")

    # PDF text assembly
    pdf_text = "BT\n/F1 12 Tf\n50 750 Td\n"
    for ln in lines:
        pdf_text += f"({esc(ln)}) Tj\n0 -18 Td\n"
    pdf_text += "ET"

    # PDF Structure
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources << /Font << /F1 5 0 R >> >>
/Contents 4 0 R
>>
endobj
4 0 obj
<< /Length {len(pdf_text)} >>
stream
{pdf_text}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>
endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000078 00000 n
0000000147 00000 n
0000000331 00000 n
0000000577 00000 n
trailer << /Root 1 0 R /Size 6 >>
startxref
700
%%EOF
"""

    return pdf.encode("utf-8", errors="ignore")


# ---------------------------------------------------
# TABS
# ---------------------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Die-Cut ({len(pending)})",
    f"✔ Completed Die-Cut ({len(completed)})"
])


# ---------------------------------------------------
# TAB 1 — PENDING
# ---------------------------------------------------
with tab1:

    if not pending:
        st.success("🎉 No pending die-cut jobs!")

    for key, o in pending.items():

        order_id = o["order_id"]
        file_dc = o.get("diecut_file")

        with st.container(border=True):

            st.subheader(f"✂️ Order {order_id}")
            st.markdown(f"**Customer:** {o.get('customer')} — **Item:** {o.get('item')}")
            st.divider()

            # -------- TIME TRACKING --------
            st.subheader("⏱ Time Tracking")

            start = o.get("diecut_start")
            end = o.get("diecut_end")

            if not start:
                if st.button("▶️ Start Die-Cut", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"diecut_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Die-Cut", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"diecut_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started at: {start}")

            else:
                st.success("Completed")
                st.caption(f"Start: {start}")
                st.caption(f"End: {end}")

            st.divider()

            # -------- DIE CUT DETAILS --------
            st.subheader("📋 Die-Cut Details")

            qty = o.get("qty", 1)

            machine = st.text_input(
                "Machine Used",
                value=o.get("diecut_machine", ""),
                placeholder="e.g., Heidelberg SORM",
                key=f"mc_{order_id}"
            )

            blade = st.text_input(
                "Blade Type",
                value=o.get("diecut_blade", ""),
                placeholder="e.g., Sharp 23T",
                key=f"blade_{order_id}"
            )

            assign_to = st.text_input(
                "Assign To",
                value=o.get("diecut_assigned_to", ""),
                placeholder="e.g., Ramesh, Anil",
                key=f"assign_{order_id}"
            )

            die_paper = st.text_input(
                "Die Number (Paper)",
                value=o.get("diecut_die_paper", ""),
                placeholder="e.g., DIE-P-102",
                key=f"die_paper_{order_id}"
            )

            die_board = st.text_input(
                "Die Number (Board)",
                value=o.get("diecut_die_board", ""),
                placeholder="e.g., DIE-B-77",
                key=f"die_board_{order_id}"
            )

            cut_per_sheet = st.number_input(
                "Paper Cut Per Sheet",
                min_value=1,
                value=o.get("diecut_cut_per_sheet", 1),
                key=f"cut_sheet_{order_id}"
            )

            cut_per_board = st.number_input(
                "Board Cut Per Die",
                min_value=1,
                value=o.get("diecut_cut_per_board", 1),
                key=f"cut_board_{order_id}"
            )

            total_sheets = (qty + cut_per_sheet - 1) // cut_per_sheet
            total_boards = (qty + cut_per_board - 1) // cut_per_board

            st.info(f"📄 Total Paper Sheets Needed: **{total_sheets}**")
            st.info(f"🟫 Total Boards Needed: **{total_boards}**")

            notes = st.text_area(
                "Notes",
                value=o.get("diecut_notes", ""),
                height=80,
                key=f"notes_{order_id}"
            )

            if st.button("💾 Save Details", key=f"save_dc_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "diecut_machine": machine,
                    "diecut_blade": blade,
                    "diecut_assigned_to": assign_to,
                    "diecut_die_paper": die_paper,
                    "diecut_die_board": die_board,
                    "diecut_cut_per_sheet": cut_per_sheet,
                    "diecut_cut_per_board": cut_per_board,
                    "diecut_total_sheets": total_sheets,
                    "diecut_total_boards": total_boards,
                    "diecut_notes": notes
                })
                st.success("Details Saved!")
                st.rerun()

            st.divider()

            # -------- FILE UPLOAD --------
            st.subheader("📁 Upload Die-Cut Output File")

            up = st.file_uploader(
                "Upload File",
                type=["png", "jpg", "jpeg", "pdf"],
                key=f"up_{order_id}"
            )

            if st.button("💾 Save File", key=f"save_file_{order_id}", use_container_width=True) and up:
                encoded = base64.b64encode(up.read()).decode()
                update(f"orders/{key}", {"diecut_file": encoded})
                st.success("File uploaded!")
                st.rerun()

            if file_dc:
                preview("Die-Cut File", file_dc)
                download_button("⬇ Download File", file_dc, order_id, "diecut", "dl_dc")

            st.divider()

            # -------- PDF SLIP --------
            st.subheader("📄 Die-Cut Slip")

            slip = generate_diecut_slip(
                o, machine, blade, assign_to, die_paper, die_board,
                cut_per_sheet, cut_per_board, total_sheets, total_boards, notes
            )

            st.download_button(
                "📥 Download Die-Cut Slip (PDF)",
                data=slip,
                file_name=f"{order_id}_diecut_slip.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.divider()

            # -------- MOVE TO LAMINATION --------
            if file_dc and end:
                if st.button("🚀 Move to Lamination", key=f"move_{order_id}", type="primary", use_container_width=True):
                    update(f"orders/{key}", {
                        "stage": "Lamination",
                        "diecut_completed_at": datetime.now().isoformat()
                    })
                    st.balloons()
                    st.success("Moved to Lamination!")
                    st.rerun()
            else:
                st.warning("⚠ Complete time & upload file to proceed.")


# ---------------------------------------------------
# TAB 2 — COMPLETED JOBS
# ---------------------------------------------------
with tab2:

    if not completed:
        st.info("No completed die-cut jobs.")

    for key, o in completed.items():

        st.write(f"### {o['order_id']} — {o['customer']}")
        st.caption(f"Item: {o.get('item')}")
        st.caption(f"Completed At: {o.get('diecut_completed_at')}")

        file_dc = o.get("diecut_file")
        if file_dc:
            preview("Die-Cut File", file_dc)
            download_button("⬇ Download File", file_dc, o["order_id"], "diecut", f"dl_dc_completed_{o['order_id']}")

        st.divider()
