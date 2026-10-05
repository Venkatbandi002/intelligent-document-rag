from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

DOCS_DIR = Path(__file__).resolve().parent / "sample_docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def create_company_policy_pdf():
    pdf_path = DOCS_DIR / "Company_Policy.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
    )
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2563EB'),
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937'),
    )

    story = []

    # Page 1: Overview & Code of Conduct
    story.append(Paragraph("Enterprise Global Corporation: Company Policy Manual", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Section 1: Corporate Code of Conduct and Ethics", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "All employees are expected to maintain the highest standards of professional integrity, honesty, and legal compliance. "
        "Conflicts of interest must be disclosed in writing to the Compliance Department within 5 business days of occurrence. "
        "Bribery, kickbacks, or inappropriate corporate gifts valued at over $50 USD are strictly prohibited. "
        "Employees must safeguard proprietary data, intellectual property, and customer privacy under strict non-disclosure obligations.",
        body_style
    ))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Section 2: Workplace Inclusivity and Anti-Harassment", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Our company guarantees equal opportunity employment regardless of race, gender, religion, sexual orientation, or disability. "
        "Zero-tolerance harassment policies apply to all physical and digital communications. Violations result in disciplinary action up to termination.",
        body_style
    ))
    story.append(PageBreak())

    # Page 2: Leave Policy & Paid Time Off
    story.append(Paragraph("Section 3: Leave and Absence Guidelines", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Annual Leave: Full-time employees are entitled to 20 days of paid annual leave per calendar year. "
        "Leave requests exceeding 3 consecutive days must be submitted through the HR Portal at least two weeks in advance. "
        "A maximum of 5 unused leave days can be carried over into the following calendar year, expiring on March 31st.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Sick Leave: Employees are provided 10 days of paid medical and sick leave per year. "
        "Absences exceeding 2 consecutive days require a certified medical certificate from a licensed physician upon returning to work.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Parental Leave: Primary caregivers receive 16 weeks of fully paid parental leave, while secondary caregivers receive 6 weeks of fully paid leave.",
        body_style
    ))
    story.append(PageBreak())

    # Page 3: Expense Reimbursement
    story.append(Paragraph("Section 4: Travel and Expense Reimbursement Policy", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Business Travel: Employees traveling on company business must book economy class for domestic flights and business class for flights exceeding 8 continuous hours. "
        "The daily meal allowance is capped at $75 USD per day, with itemized tax receipts required for all expense claims. "
        "Alcoholic beverages are not eligible for company reimbursement unless explicitly pre-approved for client entertainment by a Vice President. "
        "All expense reports must be submitted within 30 days of expense incurrence via the Financial ERP System.",
        body_style
    ))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Section 5: Information Security and Device Usage", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "All company laptops must run full-disk encryption (BitLocker/FileVault) and mandatory endpoint detection agents. "
        "Passwords must be at least 14 characters long and include alphanumeric and special characters. Multi-Factor Authentication (MFA) is strictly mandatory on all accounts.",
        body_style
    ))

    doc.build(story)
    print(f"Generated: {pdf_path}")


def create_employee_handbook_pdf():
    pdf_path = DOCS_DIR / "Employee_Handbook.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#065F46'))
    heading_style = ParagraphStyle('DocHeading', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#059669'))
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#1F2937'))

    story = []

    # Page 1: Working Hours & Remote Work
    story.append(Paragraph("Employee Handbook: Operational Guidelines & Benefits", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Chapter 1: Working Hours and Hybrid Work Policy", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Standard working hours are 40 hours per week, typically from 9:00 AM to 5:00 PM local time, Monday through Friday. "
        "Core collaboration hours are designated between 10:00 AM and 3:00 PM, during which team members are expected to be available for synchronizations. "
        "Employees in eligible technical roles may work remotely up to 3 days per week with manager approval. "
        "A one-time home office equipment stipend of $500 USD is available during onboarding.",
        body_style
    ))
    story.append(PageBreak())

    # Page 2: Compensation & Health Benefits
    story.append(Paragraph("Chapter 2: Health Insurance and Retirement Benefits", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Health Coverage: Comprehensive medical, dental, and vision insurance is provided for all full-time employees and their eligible dependents. "
        "The company covers 90% of monthly health insurance premiums for employees and 75% for dependents. "
        "Coverage begins on the first day of the calendar month following the start date.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "401(k) Retirement Plan: The company matches 100% of employee contributions up to 4% of base salary, and 50% on the next 2%, with immediate 100% vesting from day one. "
        "Employees can enroll or adjust contribution percentages at any time through the payroll portal.",
        body_style
    ))
    story.append(PageBreak())

    # Page 3: Performance & Learning
    story.append(Paragraph("Chapter 3: Performance Evaluations and Professional Development", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Performance Reviews: Formal reviews occur bi-annually in June and December. Ratings range from Unsatisfactory (1) to Consistently Exceeds Expectations (5). "
        "Annual merit increases and performance bonuses are determined based on the year-end evaluation.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Learning and Development: Each full-time employee has access to an annual education stipend of $1,500 USD for technical certifications, conferences, and books. "
        "Prior approval from the department director is required before booking courses.",
        body_style
    ))

    doc.build(story)
    print(f"Generated: {pdf_path}")


def create_product_manual_pdf():
    pdf_path = DOCS_DIR / "Product_Manual.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#7C2D12'))
    heading_style = ParagraphStyle('DocHeading', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#EA580C'))
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#1F2937'))

    story = []

    # Page 1: Architecture & Specs
    story.append(Paragraph("Titan Cloud Gateway: Technical Architecture & Product Manual", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Chapter 1: System Overview and Hardware Specifications", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Titan Cloud Gateway is an enterprise-grade API gateway designed for high-throughput, low-latency microservice orchestration. "
        "Minimum hardware specifications: 4 vCPU cores, 8 GB RAM, and 50 GB NVMe storage. "
        "The gateway operates on Linux kernel 5.15 or newer with eBPF network acceleration enabled. "
        "It supports up to 50,000 concurrent TLS connections with sub-5 millisecond median latency.",
        body_style
    ))
    story.append(PageBreak())

    # Page 2: Security & Authentication
    story.append(Paragraph("Chapter 2: Authentication Protocols and Rate Limiting", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Authentication: Titan Gateway supports OAuth2 with PKCE, JWT validation, mTLS (mutual TLS), and API Key authentication. "
        "Tokens must be signed with RS256 or ES256 algorithms. Symmetric HS256 tokens are rejected by default.",
        body_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Rate Limiting: Uses a distributed Redis-backed sliding window token bucket algorithm. "
        "The default global tier limits traffic to 1,000 requests per minute per IP address. Exceeded limits return HTTP status code 429 Too Many Requests.",
        body_style
    ))
    story.append(PageBreak())

    # Page 3: Troubleshooting & Monitoring
    story.append(Paragraph("Chapter 3: Troubleshooting, Diagnostics, and Health Checks", heading_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Health Endpoint: The gateway exposes `/healthz` for liveness probes (HTTP 200 OK) and `/readyz` for upstream readiness probes. "
        "Metrics: Prometheus metrics are exposed at port 9090 on path `/metrics`. "
        "Common Error Codes: Error 5003 indicates upstream backend socket timeout (default 30 seconds). Error 4001 indicates missing or expired JWT authorization header.",
        body_style
    ))

    doc.build(story)
    print(f"Generated: {pdf_path}")


if __name__ == "__main__":
    create_company_policy_pdf()
    create_employee_handbook_pdf()
    create_product_manual_pdf()
