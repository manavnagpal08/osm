import base64
from datetime import datetime
import pytz

# Using IST timezone for consistency
IST = pytz.timezone("Asia/Kolkata")

def generate_delivery_summary_pdf(order: dict) -> bytes:
    """
    Generates a comprehensive Delivery Note and Job Summary PDF
    using pure Python/PDF format.
    
    Args:
        order: The dictionary containing all order data.
        
    Returns:
        The PDF content as bytes.
    """
    
    # --- 1. EXTRACT DATA ---
    order_id = order.get('order_id', 'N/A')
    customer = order.get('customer', 'N/A')
    item = order.get('item', 'N/A')
    qty = order.get('qty', 'N/A')
    
    # Critical fields requested by the user:
    delivery_date = order.get('due', 'TBD') # Assuming 'due' field is used as Delivery Date
    product_description = order.get('product_type', 'N/A') # Using product_type as the main description
    admin_notes = order.get('admin_notes', 'No special instructions.')
    
    # Additional Production Details
    printing_specs = order.get('printing_specs', {})
    paper_quality = printing_specs.get('paper_quality', 'N/A')
    
    # --- 2. BUILD TEXT CONTENT ---
    
    # Function to format time consistently
    def now_ist_formatted():
        return datetime.now(IST).strftime("%d %b %Y, %I:%M %p")

    lines = [
        "*** FINAL DELIVERY NOTE & JOB SUMMARY ***",
        "",
        f"Order ID: {order_id}",
        f"Customer: {customer}",
        f"Item Name: {item}",
        f"Quantity: {qty}",
        "",
        "--- DELIVERY DETAILS ---",
        f"REQUIRED DELIVERY DATE: {delivery_date}",
        "",
        "--- PRODUCT DESCRIPTION & SPECS ---",
        f"Product Type: {product_description}",
        f"Material Used: {paper_quality}",
        "",
        "--- ADMINISTRATION NOTES ---",
        admin_notes or "No special instructions.",
        "",
        "",
        "*** IMPORTANT: PLEASE CONFIRM QUANTITY UPON RECEIPT ***",
        "",
        f"Generated On: {now_ist_formatted()}"
    ]

    # --- 3. ASSEMBLE PDF ---

    # Escape PDF special characters
    def esc(s):
        return s.replace("(", "\\(").replace(")", "\\)")

    # Build PDF text block: set font, move to position (50, 750), then print lines
    pdf_text = "BT\n/F1 12 Tf\n50 750 Td\n"
    for i, line in enumerate(lines):
        # Use bold font for titles and large font for important notes
        if line.startswith('***') or line.startswith('---'):
             pdf_text += "/F1 14 Tf\n" # Larger font for headers
        else:
             pdf_text += "/F1 12 Tf\n"
        
        pdf_text += f"({esc(line)}) Tj\n0 -20 Td\n" # Move down 20 units (points)
    pdf_text += "ET"

    # Assemble the PDF structure (Unchanged boilerplate PDF code)
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
<< /Type /Font
   /Subtype /Type1
   /BaseFont /Courier
>>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000075 00000 n 
0000000144 00000 n 
0000000334 00000 n 
0000000580 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
700
%%EOF
"""

    return pdf.encode("utf-8", errors="ignore")

# Example usage (for testing):
# order_data = read("orders").get('some_key')
# pdf_bytes = generate_delivery_summary_pdf(order_data)
# st.download_button(..., data=pdf_bytes, ...)
