import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

st.set_page_config(page_title="Lamination Department", layout="wide", page_icon="🟦")

# -------------------
# ROLE CHECK
# -------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["lamination", "admin"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🟦 Lamination Department")
st.caption("Upload lamination output, enter lamination details, track time, and move orders to DieCut.")


# -------------------
# LOAD ORDERS
# -------------------
orders = read("orders") or {}
pending, completed = {}, {}

for key, o in orders.items():

    if not isinstance(o, dict):
        continue

    if o.get("product_type") != "Box":
        continue  # Only BOX orders

    if o.get("stage") == "Lamination":
        pending[key] = o
    elif o.get("lamination_completed_at"):
        completed[key] = o


# -------------------
# Download Handler
# -------------------
def download_button(label, b64_data, order_id, fname, prefix):
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
        key=f"{prefix}_{order_id}",
        use_container_width=True
    )


# -------------------
# Preview Handler
# -------------------
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


# -------------------
# PRINT PAGE JS
# -------------------
def print_section(html_id):
    print_js = f"""
    <script>
    var content = document.getElementById('{html_id}').innerHTML;
    var win = window.open("", "", "width=900,height=600");
    win.document.write("<html><head><title>Print</title></head><body>");
    win.document.write(content);
    win.document.write("</body></html>");
    win.document.close();
    win.print();
    </script>
    """
    st.components.v1.html(print_js, height=0)


# -------------------
# TABS
# -------------------
tab1, tab2 = st.tabs([
    f"🛠 Pending Lamination ({len(pending)})",
    f"✔ Completed Lamination ({len(completed)})"
])


# -------------------
# TAB 1 — PENDING
# -------------------
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
            start = o.get("lamination_start")
            end = o.get("lamination_end")

            st.subheader("⏱ Time Tracking")

            if not start:
                if st.button("▶️ Start Lamination", key=f"start_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"lamination_start": datetime.now().isoformat()})
                    st.rerun()

            elif not end:
                if st.button("⏹ End Lamination", key=f"end_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {"lamination_end": datetime.now().isoformat()})
                    st.rerun()
                st.info(f"Started at {start}")

            else:
                st.success("Lamination Completed")
                st.caption(f"Start: {start}")
                st.caption(f"End: {end}")

            st.divider()

            # ---------------- LAMINATION DETAILS ----------------
            st.subheader("📋 Lamination Details")

            lam_type = st.selectbox(
                "Type of Lamination",
                ["Gloss", "Matt", "Velvet", "Thermal", "BOPP Gloss", "BOPP Matt"],
                index=0,
                key=f"type_{order_id}"
            )

            material = st.text_input(
                "Quality / Material",
                value=o.get("lamination_material", ""),
                placeholder="e.g., 18 Micron BOPP",
                key=f"material_{order_id}"
            )

            reel_width = st.number_input(
                "Reel Width (in inches)",
                min_value=1,
                max_value=100,
                value=o.get("lamination_reel_width", 30),
                key=f"width_{order_id}"
            )

            notes = st.text_area(
                "Additional Notes",
                value=o.get("lamination_notes", ""),
                height=80,
                key=f"notes_{order_id}"
            )

            if st.button("💾 Save Lamination Details", key=f"save_details_{order_id}", use_container_width=True):
                update(f"orders/{key}", {
                    "lamination_type": lam_type,
                    "lamination_material": material,
                    "lamination_reel_width": reel_width,
                    "lamination_notes": notes
                })
                st.success("Details Saved!")
                st.rerun()

            st.divider()

            # ---------------- FILE UPLOAD ----------------
            st.subheader("📁 Upload Lamination Output File")

            upload = st.file_uploader(
                "Upload file",
                type=["png", "jpg", "jpeg", "pdf"],
                key=f"up_{order_id}"
            )

            if st.button("💾 Save File", key=f"save_file_{order_id}", use_container_width=True) and upload:
                encoded = base64.b64encode(upload.read()).decode()
                update(f"orders/{key}", {"lamination_file": encoded})
                st.success("File saved!")
                st.rerun()

            if lam_file:
                preview("Lamination Output", lam_file)
                download_button(
                    "⬇️ Download Lamination Output",
                    lam_file,
                    order_id,
                    "lamination",
                    "dl_lam"
                )

            st.divider()

            # ---------------- PRINT BUTTON ----------------
            print_id = f"print_section_{order_id}"
            st.markdown(f"""
            <div id="{print_id}">
                <h2>Lamination Report — {order_id}</h2>
                <p><b>Customer:</b> {o.get('customer')}</p>
                <p><b>Item:</b> {o.get('item')}</p>
                <p><b>Type:</b> {lam_type}</p>
                <p><b>Material:</b> {material}</p>
                <p><b>Reel Width:</b> {reel_width} inches</p>
                <p><b>Notes:</b> {notes}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🖨 Print This Page", key=f"print_{order_id}", use_container_width=True):
                print_section(print_id)

            st.divider()

            # ---------------- MOVE TO DIECUT ----------------
            if lam_file and end:
                if st.button("🚀 Move to DieCut", type="primary", key=f"next_{order_id}", use_container_width=True):
                    update(f"orders/{key}", {
                        "stage": "DieCut",
                        "lamination_completed_at": datetime.now().isoformat()
                    })
                    st.balloons()
                    st.success("Moved to DieCut!")
                    st.rerun()
            else:
                st.warning("Finish lamination & upload file first.")


# -------------------
# TAB 2 — COMPLETED
# -------------------
with tab2:

    if not completed:
        st.info("No completed lamination jobs yet.")
    else:
        for key, o in completed.items():

            order_id = o["order_id"]

            with st.container(border=True):
                st.subheader(f"✔ {order_id} — {o.get('customer')}")
                st.caption(f"Completed at {o.get('lamination_completed_at')}")

                lam_file = o.get("lamination_file")

                if lam_file:
                    preview("Lamination Output", lam_file)
                    download_button(
                        "⬇️ Download Output File",
                        lam_file,
                        order_id,
                        "lamination",
                        "dl_completed"
                    )

                st.divider()
