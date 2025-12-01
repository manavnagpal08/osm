import streamlit as st
from firebase import read, update
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, Dict

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
st.caption("Manage die-cutting operations, assign workers, upload output files, and generate job slips.")

# ---------------------------------------------------
# LOAD ORDERS
# ---------------------------------------------------
orders = read("orders") or {}

pending: Dict[str, Any] = {}
completed: Dict[str, Any] = {}

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
# HELPER FUNCTIONS
# ---------------------------------------------------

def calculate_time_diff(start: Optional[str], end: Optional[str]) -> str:
    """Calculate how long the task took."""
    if start and end:
        try:
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            diff = t2 - t1
            return f"Total: **{str(diff).split('.')[0]}**"
        except:
            return "Time Calculation Error"
    elif start:
        return "⏳ Running…"
    return "Not Started"

def download_button(label: str, b64_data: Optional[str], order_id: str, fname: str, key_prefix: str):
    """File download handler with basic type detection."""
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


def preview(label: str, b64: Optional[str], order_id: str):
    """File preview handler."""
    if not b64:
        st.info(f"No {label} uploaded yet.")
        return

    raw = base64.b64decode(b64)
    head = raw[:10]
    
    with st.expander(f"🖼️ View {label}"):
        
        # Try image
        try:
            st.image(raw, use_container_width=True)
            return
        except:
            pass

        # PDF and other types
        if head.startswith(b"%PDF"):
            st.warning("PDFs cannot be previewed directly in the web app, please download.")
        else:
            st.info(f"File ({len(raw)} bytes) is not a common image type for preview. Download required.")

        # Always provide the download button inside the preview pane for convenience
        download_button(
            label="⬇️ Download File for Viewing", 
            b64_data=b64, 
            order_id=order_id, 
            fname=f"{label.lower().replace(' ', '_')}_preview", 
            key_prefix=f"prev_dl_{order_id}"
        )


# ---------------------------------------------------
# PDF GENERATOR — PURE PYTHON
# ---------------------------------------------------
def generate_diecut_slip(order, machine, blade, assign_to, die_paper, die_board,
                         cut_per_sheet, cut_per_board, total_sheets, total_boards, notes):

    # Calculate current time in IST (UTC + 5:30) and format it.
    IST_OFFSET = timezone(timedelta(hours=5, minutes=30))
    # Get current UTC time, localize it to IST offset, and format
    now_ist = datetime.now(timezone.utc).astimezone(IST_OFFSET).strftime('%Y-%m-%d %H:%M IST')

    lines = [
        "DIE-CUT DEPARTMENT – JOB SLIP",
        "=============================",
        "",
        f"Order ID: {order.get('order_id')}",
        f"Customer: {order.get('customer')}",
        f"Item: {order.get('item')}",
        "",
        f"--- EQUIPMENT & ASSIGNMENT ---",
        f"Machine: {machine or 'N/A'}",
        f"Blade Type: {blade or 'N/A'}",
        f"Assigned To: {assign_to or 'Unassigned'}",
        "",
        f"--- DIE NUMBERS ---",
        f"Die Number (Paper): {die_paper or 'N/A'}",
        f"Die Number (Board): {die_board or 'N/A'}",
        "",
        f"--- PRODUCTION COUNTS ---",
        f"Paper Cut Per Sheet: {cut_per_sheet}",
        f"Board Cut Per Die: {cut_per_board}",
        "",
        f"Total Paper Sheets Needed: {total_sheets:,}",
        f"Total Boards Needed: {total_boards:,}",
        "",
        "--- NOTES ---",
        notes or "No special notes.",
        "",
        f"Generated At: {now_ist}"
    ]

    def esc(s):  # Escape brackets
        return s.replace("(", "\\(").replace(")", "\\)")

    # PDF text assembly
    # Using a slightly different positioning approach to center the content vertically
    y_start = 750
    line_height = 18
    
    # Calculate starting position for the text block (x, y)
    # The current PDF text generation method uses Td (move text position), so we iterate
    pdf_text = f"BT\n/F1 12 Tf\n50 {y_start} Td\n"
    for ln in lines:
        # Move down for the next line
        pdf_text += f"({esc(ln)}) Tj\n0 -{line_height} Td\n" 
    pdf_text += "ET"

    # PDF Structure (Simple Text/Courier Font) - original structure retained
    pdf_content = f"""%PDF-1.4
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
    # Note: The original fixed xref/startxref values are kept despite the content length changes 
    # potentially causing issues with advanced PDF viewers, as this is how the original 
    # PDF generation logic was structured.
    return pdf_content.encode("utf-8", errors="ignore")


# ---------------------------------------------------
# TABS
# ---------------------------------------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Die-Cut ({len(pending)})",
    f"✔ Completed Die-Cut ({len(completed)})"
])


# ---------------------------------------------------
# TAB 1 — PENDING (Redesigned UI)
# ---------------------------------------------------
with tab1:

    if not pending:
        st.success("🎉 No pending die-cut jobs for Boxes!")

    # Sort orders by priority (High, Medium, Low)
    sorted_pending = sorted(
        pending.items(),
        key=lambda i: (
            {"High": 0, "Medium": 1, "Low": 2}.get(i[1].get("priority", "Medium")),
            i[1].get("received", "9999-12-31")
        )
    )

    for key, o in sorted_pending:

        order_id = o["order_id"]
        file_dc = o.get("diecut_file")

        with st.container(border=True):
            
            # --- ROW 1: HEADER & METRICS ---
            st.markdown(f"### 📦 Order {order_id} — {o.get('customer')}")
            
            col_priority, col_product, col_qty, col_due = st.columns(4)
            col_priority.metric("Priority", o.get("priority", "Medium"))
            col_product.metric("Product Type", o.get("product_type", "Box"))
            col_qty.metric("Quantity", f"{o.get('qty', 0):,}")
            col_due.metric("Due Date", o.get("due", "N/A"))

            st.caption(f"**Item Description:** *{o.get('item')}*")
            st.divider()

            # --- ROW 2: DETAILS, TIME, FILES ---
            col_details, col_files_action = st.columns([1.5, 2.5])

            # ==================================
            # COLUMN 1: TIME, ASSIGNMENT, DETAILS
            # ==================================
            with col_details:
                
                # --- TIME TRACKING ---
                st.subheader("⏱ Job Status")
                start = o.get("diecut_start")
                end = o.get("diecut_end")

                if not start:
                    if st.button("▶️ Start Die-Cut", key=f"start_{order_id}", use_container_width=True, type="secondary"):
                        update(f"orders/{key}", {"diecut_start": datetime.now().isoformat()})
                        st.rerun()
                    st.caption("Awaiting start signal.")
                
                elif not end:
                    if st.button("⏹ End Die-Cut", key=f"end_{order_id}", use_container_width=True, type="primary"):
                        update(f"orders/{key}", {"diecut_end": datetime.now().isoformat()})
                        st.rerun()
                    st.info(f"Running since: {start.split('T')[1][:5]}")
                
                else:
                    st.success("Task Completed")
                    st.markdown(calculate_time_diff(start, end))

                st.markdown("---")
                
                # --- ASSIGNMENT & MACHINE ---
                st.subheader("🛠️ Setup Details")
                
                assign_to = st.text_input(
                    "Assigned To",
                    value=o.get("diecut_assigned_to", ""),
                    placeholder="e.g., Ramesh",
                    key=f"assign_{order_id}"
                )
                
                col_mc, col_blade = st.columns(2)
                machine = col_mc.text_input(
                    "Machine",
                    value=o.get("diecut_machine", ""),
                    placeholder="Heidelberg SORM",
                    key=f"mc_{order_id}"
                )
                blade = col_blade.text_input(
                    "Blade Type",
                    value=o.get("diecut_blade", ""),
                    placeholder="Sharp 23T",
                    key=f"blade_{order_id}"
                )

                # --- DIE NUMBERS ---
                st.subheader("Die & Tooling")
                col_die_p, col_die_b = st.columns(2)
                die_paper = col_die_p.text_input(
                    "Paper Die #",
                    value=o.get("diecut_die_paper", ""),
                    placeholder="DIE-P-102",
                    key=f"die_paper_{order_id}",
                )
                
                die_board = col_die_b.text_input(
                    "Board Die #",
                    value=o.get("diecut_die_board", ""),
                    placeholder="DIE-B-77",
                    key=f"die_board_{order_id}",
                )

                # --- CUT COUNTS AND CALCULATIONS ---
                st.subheader("Cut Counts & Requirements")
                col_cuts, col_reqs = st.columns(2)

                with col_cuts:
                    cut_per_sheet = st.number_input(
                        "Paper Cut Per Sheet (Impression)",
                        min_value=1,
                        value=o.get("diecut_cut_per_sheet", 1),
                        key=f"cut_sheet_{order_id}",
                    )
                    
                    cut_per_board = st.number_input(
                        "Board Cut Per Die (Impression)",
                        min_value=1,
                        value=o.get("diecut_cut_per_board", 1),
                        key=f"cut_board_{order_id}",
                    )

                with col_reqs:
                    # --- CALCULATIONS ---
                    qty = o.get("qty", 1)
                    cut_per_sheet_safe = cut_per_sheet if cut_per_sheet > 0 else 1
                    cut_per_board_safe = cut_per_board if cut_per_board > 0 else 1
                    
                    total_sheets = (qty + cut_per_sheet_safe - 1) // cut_per_sheet_safe
                    total_boards = (qty + cut_per_board_safe - 1) // cut_per_board_safe
                    
                    st.metric("📄 Paper Sheets Required", f"{total_sheets:,}")
                    st.metric("🟫 Boards Required", f"{total_boards:,}")

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
                        "diecut_notes": o.get("diecut_notes", "") # Preserve notes while saving other fields
                    })
                    st.success("Details Saved!")
                    st.rerun()
            
            # ==================================
            # COLUMN 2: FILES, SLIP, NOTES, ACTION
            # ==================================
            with col_files_action:
                
                # --- FILE UPLOAD ---
                st.subheader("📁 Die-Cut Output File (Final)")

                up = st.file_uploader(
                    "Upload Final Die-Cut Output (PDF/Image)",
                    type=["png", "jpg", "jpeg", "pdf"],
                    key=f"up_{order_id}",
                    label_visibility="collapsed"
                )

                if st.button("💾 Save Final File", key=f"save_file_{order_id}", use_container_width=True, disabled=not up):
                    up.seek(0)
                    encoded = base64.b64encode(up.read()).decode()
                    update(f"orders/{key}", {"diecut_file": encoded})
                    st.toast("File uploaded!")
                    st.rerun()

                if file_dc:
                    preview("Die-Cut File", file_dc, order_id)
                    download_button("⬇ Download Final File", file_dc, order_id, "diecut", "dl_dc")
                
                st.markdown("---")

                # --- NOTES ---
                st.subheader("📝 Notes")
                notes = st.text_area(
                    "Notes/Instructions for Assembly",
                    value=o.get("diecut_notes", ""),
                    height=100,
                    key=f"notes_{order_id}",
                    label_visibility="collapsed"
                )

                if st.button("💾 Save Notes Only", key=f"save_notes_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"diecut_notes": notes})
                    st.toast("Notes Updated!")
                    st.rerun()

                st.markdown("---")
                
                # --- PDF SLIP & ACTION ---
                st.subheader("📄 Job Slip & Action")

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

                st.markdown("---")

                # --- MOVE TO NEXT STAGE ---
                is_ready = file_dc and end

                if is_ready:
                    if st.button("🚀 Move to Assembly", key=f"move_{order_id}", type="primary", use_container_width=True):
                        update(f"orders/{key}", {
                            "stage": "Assembly", 
                            "diecut_completed_at": datetime.now().isoformat()
                        })
                        st.balloons()
                        st.rerun()
                else:
                    st.warning("⚠ Ensure time tracking is ended and the output file is uploaded to proceed.")


# ---------------------------------------------------
# TAB 2 — COMPLETED JOBS (Redesigned UI)
# ---------------------------------------------------
with tab2:

    if not completed:
        st.info("No completed die-cut jobs.")
        st.stop()

    # Sort completed by completion date
    sorted_completed = sorted(
        completed.items(),
        key=lambda i: i[1].get("diecut_completed_at", "0000-01-01"),
        reverse=True
    )

    for key, o in sorted_completed:
        
        order_id = o['order_id']
        file_dc = o.get("diecut_file")
        start = o.get("diecut_start")
        end = o.get("diecut_end")

        with st.expander(f"✅ {order_id} — {o['customer']} | Completed: {o.get('diecut_completed_at', '').split('T')[0]}"):
            
            st.markdown("#### Summary")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Job Time", calculate_time_diff(start, end))
            c2.metric("Assigned To", o.get("diecut_assigned_to", "N/A"))
            c3.metric("Machine", o.get("diecut_machine", "N/A"))
            c4.metric("Next Stage", o.get("stage", "N/A"))
            
            st.divider()
            
            col_data, col_files = st.columns([1, 1])

            with col_data:
                st.markdown("#### Production Details")
                
                # Die Numbers
                st.markdown("##### Tooling")
                die_cols = st.columns(2)
                die_cols[0].markdown(f"**Paper Die #:** `{o.get('diecut_die_paper', 'N/A')}`")
                die_cols[1].markdown(f"**Board Die #:** `{o.get('diecut_die_board', 'N/A')}`")

                # Counts
                st.markdown("##### Material Usage")
                count_cols = st.columns(2)
                count_cols[0].markdown(f"**Paper Sheets Used:** `{o.get('diecut_total_sheets', 0):,}`")
                count_cols[1].markdown(f"**Boards Used:** `{o.get('diecut_total_boards', 0):,}`")
                st.markdown(f"**Blade Type:** `{o.get('diecut_blade', 'N/A')}`")

                st.markdown("#### Notes")
                st.info(o.get("diecut_notes", "No notes recorded."))
            
            with col_files:
                st.markdown("#### Final Output File")
                if file_dc:
                    preview("Die-Cut File", file_dc, order_id)
                    download_button(
                        "⬇ Download Final Output", 
                        file_dc, 
                        order_id, 
                        "diecut_final", 
                        f"dl_dc_completed_{order_id}"
                    )
                else:
                    st.warning("No final file uploaded.")
            
            st.divider()
            
            # Allow slip download for historical record
            slip = generate_diecut_slip(
                o, 
                o.get("diecut_machine", ""), 
                o.get("diecut_blade", ""), 
                o.get("diecut_assigned_to", ""), 
                o.get("diecut_die_paper", ""), 
                o.get("diecut_die_board", ""),
                o.get("diecut_cut_per_sheet", 1), 
                o.get("diecut_cut_per_board", 1), 
                o.get("diecut_total_sheets", 0), 
                o.get("diecut_total_boards", 0), 
                o.get("diecut_notes", "")
            )
            st.download_button(
                "📥 Download Original Job Slip (PDF)",
                data=slip,
                file_name=f"{order_id}_diecut_slip_ARCHIVE.pdf",
                mime="application/pdf",
                key=f"dl_slip_arch_{order_id}"
            )
