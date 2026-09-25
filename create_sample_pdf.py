"""Utility script to generate sample domain PDF documents for testing RAG chatbot.
Produces 'documents/company_policy.pdf' and 'documents/sample.pdf'.
"""

import os

def create_pdf(filename: str, pages_text: list):
    """Generates a standard compliant multi-page PDF 1.4 document from raw text strings."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # PDF generation primitives
    objects = []
    
    def add_object(content_bytes: bytes) -> int:
        objects.append(content_bytes)
        return len(objects)

    # 1: Catalog placeholder
    # 2: Pages placeholder
    # We will build objects list
    page_obj_ids = []
    font_obj_id = 3

    # Object 1: Catalog
    # Object 2: Pages
    # Object 3: Font
    content_obj_ids = []

    # Prepare page content streams
    for text in pages_text:
        # Format text lines for PDF stream
        lines = text.strip().split("\n")
        stream_cmds = ["BT", "/F1 11 Tf", "50 750 Td", "16 TL"]
        for line in lines:
            safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if safe_line.startswith("# "):
                # Large header
                stream_cmds.append(f"/F1 16 Tf ({safe_line[2:]}) Tj T* /F1 11 Tf")
            elif safe_line.startswith("## "):
                # Section header
                stream_cmds.append(f"/F1 13 Tf ({safe_line[3:]}) Tj T* /F1 11 Tf")
            elif safe_line.startswith("### "):
                stream_cmds.append(f"/F1 12 Tf ({safe_line[4:]}) Tj T* /F1 11 Tf")
            else:
                stream_cmds.append(f"({safe_line}) Tj T*")
        stream_cmds.append("ET")
        stream_data = "\n".join(stream_cmds).encode("latin-1")
        
        # Content object
        content_obj = f"<< /Length {len(stream_data)} >>\nstream\n".encode("latin-1") + stream_data + b"\nendstream"
        objects.append(content_obj)
        content_id = len(objects) # 1-based index will be assigned later
        content_obj_ids.append((content_id, len(stream_data), stream_data))

    # Re-structure complete PDF object table
    all_objs = []
    # 1: Catalog
    all_objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    
    # 2: Pages
    kids_refs = []
    # Font is 3
    all_objs.append(b"") # placeholder for Pages (index 1 in 0-indexed list)
    all_objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>") # 3

    # Next objects: Page objects and Content objects
    # Page i: 4, 6, 8...
    # Content i: 5, 7, 9...
    curr_id = 4
    page_ids = []
    for stream_data in [c[2] for c in content_obj_ids]:
        p_id = curr_id
        c_id = curr_id + 1
        page_ids.append(p_id)
        page_dict = f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> /MediaBox [0 0 612 792] /Contents {c_id} 0 R >>".encode("ascii")
        all_objs.append(page_dict)
        content_dict = f"<< /Length {len(stream_data)} >>\nstream\n".encode("latin-1") + stream_data + b"\nendstream"
        all_objs.append(content_dict)
        curr_id += 2

    # Now update Pages object (obj 2)
    kids_str = " ".join([f"{pid} 0 R" for pid in page_ids])
    all_objs[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>".encode("ascii")

    # Now assemble file with xref table
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for idx, obj in enumerate(all_objs, start=1):
        offsets.append(len(output))
        output.extend(f"{idx} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(b"xref\n")
    output.extend(f"0 {len(all_objs) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for off in offsets:
        output.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    output.extend(b"trailer\n")
    output.extend(f"<< /Size {len(all_objs) + 1} /Root 1 0 R >>\n".encode("ascii"))
    output.extend(b"startxref\n")
    output.extend(f"{xref_offset}\n".encode("ascii"))
    output.extend(b"%%EOF\n")

    with open(filename, "wb") as f:
        f.write(output)
    print(f"Generated PDF: {filename} ({len(pages_text)} pages, {len(output)} bytes)")

SAMPLE_PAGES = [
    # Page 1
    """# Acme Corporation Employee Policy Handbook
## Section 1: Working Hours & Remote Work
Welcome to Acme Corporation. This handbook outlines operational policies.
1.1 Working Hours
Standard business operations occur Monday through Friday.
Employees must be available during core hours of 10:00 AM to 4:00 PM.
Total mandatory working commitment is 40 hours per calendar week.
Flexible starting times are permitted between 8:00 AM and 10:00 AM.
1.2 Remote Work Policy
Acme Corporation supports a hybrid workplace arrangement.
Employees can work remotely up to 2 days per week with prior manager approval.
Remote workstations must adhere to information security standards.
Employees must log in to the enterprise VPN during all remote hours.""",

    # Page 2
    """# Acme Corporation Employee Policy Handbook
## Section 2: Leave & Time-Off Policy
2.1 Annual Paid Vacation Leave
Full-time employees receive 20 days of paid annual leave per calendar year accrued monthly.
Leave requests exceeding 3 consecutive days must be submitted 14 days in advance.
A maximum of 5 unused annual leave days can be carried forward to the following year.
2.2 Sick Leave & Medical Circumstances
Employees are granted 10 days of paid sick leave annually.
Sick leave exceeding 2 consecutive days requires a certified doctor note.
Unused sick leave expires on December 31st and is not eligible for cash encashment.
2.3 Parental & Maternity Leave
Maternity leave provides 16 weeks of fully paid leave for eligible birth parents.
Paternity leave provides 4 weeks of fully paid leave following childbirth or adoption.""",

    # Page 3
    """# Acme Corporation Employee Policy Handbook
## Section 3: Attendance Calculation & Overtime
3.1 Attendance Calculation Methodology
Attendance is calculated monthly based on biometric badge swipes and portal check-ins requiring at least 8 hours per day.
Grace period for daily arrival is 15 minutes past the agreed schedule.
Accumulating three unexcused tardy instances within a single calendar month incurs formal counseling.
3.2 Overtime Regulations
Overtime beyond 40 weekly hours is paid at 1.5 times the standard hourly rate.
All overtime work requires pre-authorization in writing from the Department Director.
Salaried exempt managerial employees are not eligible for overtime compensation.""",

    # Page 4
    """# Acme Corporation Employee Policy Handbook
## Section 4: Security Badges & Information Governance
4.1 Physical Security Badges
Security access badges must be prominently worn and visible at all times within corporate premises.
Loss must be reported immediately to Facilities within 2 hours; a $20 replacement fee applies.
Employees are strictly prohibited from tailgating or admitting non-badged visitors without front desk escort.
4.2 Data Confidentiality & Device Protection
Company laptops must utilize full-disk BitLocker encryption.
Storing confidential customer records on personal flash drives or unauthorized cloud drives is strictly forbidden.
All intellectual property conceived during tenure remains exclusive corporate property.""",

    # Page 5
    """# Acme Corporation Employee Policy Handbook
## Section 5: Travel Reimbursement & Grievance Protocol
5.1 Business Travel & Per Diem
Official company travel requires managerial pre-approval via Concur.
Employees are eligible for a per diem meal reimbursement of up to $60 per day.
Receipts must be filed within 14 business days of return for audit compliance.
5.2 Grievance Redressal Mechanism
Acme Corporation is committed to a harassment-free and equitable workplace.
Grievances should be submitted in writing to the HR Ethics Officer at ethics@acmecorp.internal.
The investigative committee delivers a binding resolution within 21 calendar days of formal filing."""
]

if __name__ == "__main__":
    create_pdf("documents/company_policy.pdf", SAMPLE_PAGES)
    create_pdf("documents/sample.pdf", SAMPLE_PAGES)
