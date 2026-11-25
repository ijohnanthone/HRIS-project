import io
import os
import datetime
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from apps.requests.models import RequestType

def generate_coe_pdf(coe_request, template=None):
    """
    Renders an official Certificate of Employment (COE) PDF in memory.
    Embeds the company logo, employee details, verification seal, and HR signature.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    corporate_blue = colors.HexColor("#174F91")
    sky_blue = colors.HexColor("#36A6D6")
    dark_slate = colors.HexColor("#1E293B")
    muted_slate = colors.HexColor("#64748B")

    company_title_style = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=corporate_blue,
        alignment=0  # Left
    )
    company_sub_style = ParagraphStyle(
        'CompanySub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=muted_slate,
        alignment=0
    )
    cert_title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=26,
        textColor=corporate_blue,
        alignment=1,  # Center
        spaceAfter=25
    )
    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=20,
        textColor=dark_slate,
        alignment=4,  # Justified
        spaceAfter=15
    )
    meta_style = ParagraphStyle(
        'CertMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=dark_slate,
        spaceAfter=10
    )

    # 1. Header with Logo & Brand
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'brand', 'logo.png')
    header_data = []

    logo_cell = ""
    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=55, height=55)
            logo_cell = logo_img
        except Exception:
            logo_cell = ""

    company_text = [
        Paragraph("<b>HREQUEST HRIS CORPORATION</b>", company_title_style),
        Paragraph("Human Resources Operations & People Management Department<br/>100 Corporate Plaza, Suite 400 &bull; www.hrequest.com", company_sub_style)
    ]

    header_table = Table([[logo_cell, company_text]], colWidths=[65, 435])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=corporate_blue, spaceAfter=25, spaceBefore=5))

    # 2. Date of Issuance & Reference
    issue_date = datetime.date.today().strftime('%B %d, %Y')
    story.append(Paragraph(f"<b>Date of Issue:</b> {issue_date}", meta_style))
    story.append(Paragraph(f"<b>Reference Ticket:</b> {coe_request.ticket_number}", meta_style))
    story.append(Spacer(1, 15))

    # 3. Document Title
    header_title = template.header_title if template else "CERTIFICATE OF EMPLOYMENT"
    story.append(Paragraph(header_title, cert_title_style))

    # 4. Certification Body
    emp = coe_request.employee
    hire_date_str = emp.hire_date.strftime('%B %d, %Y')
    emp_name = f"<b>{emp.full_name}</b>"
    pos_title = f"<b>{emp.position.title}</b>"
    raw_dept = emp.department.name.strip()
    dept_label = raw_dept if 'department' in raw_dept.lower() else f"{raw_dept} Department"
    dept_name = f"<b>{dept_label}</b>"
    loc_display = emp.get_work_location_display() if hasattr(emp, 'get_work_location_display') else emp.work_location
    if loc_display:
        if 'remote' in loc_display.lower():
            location_clause = f", working under <b>{loc_display}</b> arrangement"
        else:
            location_clause = f", assigned at our <b>{loc_display}</b>"
    else:
        location_clause = ""

    p1 = (
        f"TO WHOM IT MAY CONCERN:<br/><br/>"
        f"This is to certify that {emp_name} (Employee ID: {emp.employee_id_number}) is an official, bona fide employee "
        f"of HRequest Corporation, currently holding the position of {pos_title} under the {dept_name}{location_clause}. "
        f"The employee commenced active employment with the company on {hire_date_str} and holds "
        f"{emp.get_employment_type_display().lower()} employment status."
    )
    story.append(Paragraph(p1, body_style))

    # Compensation Paragraph if applicable
    if coe_request.request_type == RequestType.COE_WITH_COMPENSATION:
        p_comp = (
            f"This further certifies that as of {issue_date}, the employee receives a gross monthly compensation "
            f"commensurate with the company's designated grade classification."
        )
        story.append(Paragraph(p_comp, body_style))

    p2 = (
        f"This certification is being issued upon the formal request of {emp_name} for the explicit purpose of "
        f"<b>{coe_request.purpose}</b>, and for whatever legal and administrative intent it may serve."
    )
    story.append(Paragraph(p2, body_style))

    story.append(Spacer(1, 35))

    # 5. Signatory Block
    sig_name = template.signatory_name if template else "Paula Mora"
    sig_title = template.signatory_title if template else "Human Resources Manager"

    sig_data = [
        [
            Paragraph(f"Certified True and Correct:<br/><br/><br/><b>{sig_name}</b><br/>{sig_title}<br/><i>HRequest Corporation</i>", body_style),
            Paragraph("<br/><br/>[ OFFICIAL SEAL ]<br/><b>HREQUEST VERIFIED</b>", ParagraphStyle('Seal', parent=styles['Normal'], alignment=1, textColor=sky_blue, fontSize=11, fontName='Helvetica-Bold'))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[300, 200])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
