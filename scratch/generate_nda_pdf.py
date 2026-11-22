import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4a5568"))

        # Top running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "STEHOUWER PUBLISHING, LLC  |  MASTER CONFIDENTIALITY & IP AGREEMENT")
            self.drawRightString(612 - 54, 750, "COLLABORATOR: ROBERT COSTNER")
            self.setStrokeColor(colors.HexColor("#cbd5e0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)

        # Bottom running footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 38, "CONFIDENTIAL & PROPRIETARY — STEHOUWER PUBLISHING, LLC")
        self.drawRightString(612 - 54, 38, page_text)
        self.setStrokeColor(colors.HexColor("#cbd5e0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 612 - 54, 48)

        self.restoreState()

def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        alignment=1, # Center
        textColor=colors.HexColor("#1a202c"),
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1a365d"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2b6cb0"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#2d3748"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#2d3748"),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2c5282")
    )

    parties_header_style = ParagraphStyle(
        'PartyHead',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1a365d")
    )

    parties_body_style = ParagraphStyle(
        'PartyBody',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2d3748")
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("MASTER SERVICES, CONFIDENTIALITY,<br/>INTELLECTUAL PROPERTY, AND SECURITY AGREEMENT", title_style))
    story.append(Paragraph("<b>Stehouwer Publishing, LLC</b> &bull; Proprietary System & Technical Collaboration Protection", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2b6cb0"), spaceAfter=14))

    # Parties Box Table
    party_company = Paragraph(
        "<b>COMPANY:</b><br/>"
        "<b>Stehouwer Publishing, LLC</b><br/>"
        "1481 Rosewood St.<br/>"
        "Jenison, Michigan 49428<br/>"
        "<i>Executive:</i> Julie A. Stehouwer (CEO)<br/>"
        "<i>Technical:</i> Brett Adam Stehouwer (VP / CTO)",
        parties_body_style
    )

    party_collaborator = Paragraph(
        "<b>COLLABORATOR / RECIPIENT:</b><br/>"
        "<b>Robert Costner</b><br/>"
        "Address: _______________________________<br/>"
        "Email: _________________________________<br/>"
        "Phone: _________________________________<br/>"
        "<i>Capacity:</i> Technical Evaluation / Collaborator",
        parties_body_style
    )

    parties_table = Table([[party_company, party_collaborator]], colWidths=[245, 259])
    parties_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f7fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 10))

    # Effective Date Callout
    eff_box = Table([[
        Paragraph("<b>EFFECTIVE DATE:</b> This Agreement is entered into and deemed effective as of: <b>________________________, 2026</b> (the \"Effective Date\") by and between the Company and Collaborator named above (collectively, the \"Parties\").", callout_style)
    ]], colWidths=[504])
    eff_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ebf8ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#bee3f8")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(eff_box)
    story.append(Spacer(1, 10))

    # Recitals
    story.append(Paragraph("RECITALS", h2_style))
    story.append(Paragraph("<b>WHEREAS</b>, the Company is actively engaged in commercial publishing, software systems development, artificial intelligence research, and digital media architecture;", bullet_style))
    story.append(Paragraph("<b>WHEREAS</b>, the Collaborator provides professional consulting, creative development, technical engineering, strategic evaluation, or advisory services; and", bullet_style))
    story.append(Paragraph("<b>WHEREAS</b>, the Parties wish to establish a contractual framework to govern their professional relationship, protect proprietary and confidential information, preserve trade secrets, and define the exclusive ownership of intellectual property created or shared during their collaboration.", bullet_style))
    story.append(Paragraph("<b>NOW, THEREFORE</b>, in consideration of the mutual covenants, premises, and representations contained herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:", body_style))
    story.append(Spacer(1, 8))

    # SECTION I
    story.append(Paragraph("SECTION I: MASTER SERVICES AGREEMENT (MSA)", h1_style))
    story.append(Paragraph("1. Purpose & Scope of Services", h2_style))
    story.append(Paragraph("<b>1.1 Scope.</b> This Agreement establishes the master terms and conditions governing all collaboration, consulting, creative development, technical development, evaluation, licensing discussions, and other professional services performed by the Collaborator for or with the Company. The scope of activities may include, but is not limited to: (a) Publishing projects, manuscripts, and creative works; (b) Software systems, infrastructure, and digital media; (c) Artificial intelligence systems, training pipelines, and automation workflows; (d) Research, development, and business strategy; and (e) Technical architecture and system evaluation.", body_style))
    story.append(Paragraph("<b>1.2 Precedence.</b> This Agreement shall apply to all Company-related collaboration and services unless expressly superseded by a separate, subsequent written agreement signed by authorized representatives of both Parties.", body_style))

    story.append(Paragraph("2. Company Authority & Governance", h2_style))
    story.append(Paragraph("<b>2.1 Corporate Authority.</b> Stehouwer Publishing, LLC retains absolute, exclusive authority over all business operations, commercial decisions, contract negotiations, intellectual property strategies, publication decisions, licensing, and brand representation.", body_style))
    story.append(Paragraph("<b>2.2 Key Representatives.</b><br/>"
                           "&bull; <b>Julie A. Stehouwer</b> serves as the authorized executive authority for Company operations, corporate decisions, and financial executions.<br/>"
                           "&bull; <b>Brett Adam Stehouwer</b> serves as the Vice President, Chief Technology Officer (CTO), and Technical Architecture Lead, managing technical architecture, engineering systems, and the technical integrity of Company Proprietary Technology.", body_style))
    story.append(Paragraph("<b>2.3 No Transfer of Authority.</b> Nothing in this Agreement shall be construed to transfer any corporate ownership, operational authority, or commercial decision-making power of the Company to the Collaborator.", body_style))

    story.append(Paragraph("3. Services, Statements of Work, and Compensation", h2_style))
    story.append(Paragraph("<b>3.1 SOW Requirement.</b> All paid services performed by the Collaborator must be defined in writing prior to performance through a mutually executed Statement of Work (\"SOW\"), Purchase Order, or documented written/electronic authorization from an authorized representative of the Company.", body_style))
    story.append(Paragraph("<b>3.2 Consulting Fee Rule.</b> Compensation terms must be finalized and approved in writing before any paid work begins. Unauthorized work, or work performed outside the scope of an active SOW, does not create any payment obligation for the Company. All executed SOWs shall incorporate the terms of this Agreement by reference.", body_style))

    story.append(Paragraph("4. Term, Termination, and Survival", h2_style))
    story.append(Paragraph("<b>4.1 Term.</b> This Agreement shall commence on the Effective Date and shall remain in effect until terminated in accordance with Section 4.2.", body_style))
    story.append(Paragraph("<b>4.2 Termination.</b> Either Party may terminate active services or this Agreement for convenience upon thirty (30) days' written notice to the other Party. Notwithstanding the foregoing, the Company reserves the right to terminate active services and this Agreement immediately, without prior notice, for \"Cause\" (including, but not limited to, a security breach, unauthorized data or code exfiltration, breach of confidentiality, or violation of applicable data protection laws).", body_style))
    story.append(Paragraph("<b>4.3 Consequences of Termination.</b> Upon termination or expiration of this Agreement for any reason: (a) All intellectual property, deliverables, and Work Product developed up to termination shall immediately and exclusively vest with the Company; (b) Collaborator shall immediately cease all use of Company systems, networks, and applications; (c) Collaborator shall, within five (5) business days, return or permanently destroy all physical and digital Confidential Information in its possession, custody, or control, and provide written certification of such destruction to the Company's CTO.", body_style))
    story.append(Paragraph("<b>4.4 Survival.</b> The rights and obligations of the Parties under Section II (Confidentiality), Section III (Intellectual Property), Section IV (Security and Compliance), Section V (Brand & Business Protection), and Section VI (Governance & Disputes) shall survive the expiration or termination of this Agreement in perpetuity.", body_style))
    story.append(Spacer(1, 8))

    # SECTION II
    story.append(Paragraph("SECTION II: CONFIDENTIALITY & NON-DISCLOSURE", h1_style))
    story.append(Paragraph("5. Definition of Confidential Information", h2_style))
    story.append(Paragraph("\"Confidential Information\" means any and all non-public, proprietary, or business-sensitive information disclosed by or on behalf of the Company to the Collaborator, whether disclosed orally, visually, in writing, or via electronic access, and whether or not marked as \"confidential.\" Confidential Information includes, without limitation:", body_style))
    story.append(Paragraph("&bull; <b>5.1 Creative Assets:</b> Manuscripts, drafts, poetry, publications, outlines, story concepts, characters, plot structures, artwork, and unreleased materials.", bullet_style))
    story.append(Paragraph("&bull; <b>5.2 Business Information:</b> Business plans, partnership agreements, financial reports, client lists, marketing strategies, pricing structures, and internal communications.", bullet_style))
    story.append(Paragraph("&bull; <b>5.3 Technical Information:</b> Source code, object code, software architecture, infrastructure designs, database schemas, prompt engineering structures, algorithms, workflows, and technical system configurations.", bullet_style))
    story.append(Paragraph("&bull; <b>5.4 Proprietary Systems:</b> Company Proprietary Technology (as defined in Exhibit A), reasoning frameworks, validation systems, memory architectures, automation pipelines, and proprietary methodologies.", bullet_style))

    story.append(Paragraph("6. Specific Confidentiality & Security Obligations", h2_style))
    story.append(Paragraph("<b>6.1 Duty of Confidentiality.</b> Maintain all Confidential Information in strict confidence and prevent its unauthorized disclosure, publication, or dissemination to any third party (domestic or international) without the prior express written consent of the Company.", body_style))
    story.append(Paragraph("<b>6.2 Standard of Care.</b> Protect Confidential Information with at least the same degree of care as Collaborator uses to protect their own highly sensitive confidential information, but in no event less than a reasonable standard of care, including active encryption at rest and in transit.", body_style))
    story.append(Paragraph("<b>6.3 Permitted Use.</b> Use the Confidential Information solely for the performance of authorized services for the Company.", body_style))
    story.append(Paragraph("<b>6.4 Non-Replication.</b> Not copy, reverse-engineer, decompile, duplicate, or commercialize any Confidential Information or materials derived therefrom.", body_style))
    story.append(Paragraph("<b>6.5 Perpetual Duration.</b> Notwithstanding any other provisions of this Agreement, the confidentiality obligations with respect to trade secrets and Company Proprietary Technology shall survive indefinitely. For other general business information, these obligations shall survive for a period of no less than five (5) years post-termination.", body_style))
    story.append(Paragraph("<b>6.6 Immediate Breach Reporting.</b> The Collaborator shall notify the Company's representatives (Brett Adam Stehouwer and Julie A. Stehouwer) in writing immediately, and in no event later than twenty-four (24) hours, upon discovering any actual, suspected, or potential unauthorized access, exposure, leak, or breach of Confidential Information.", body_style))

    story.append(Paragraph("7. Exclusions & Whistleblower Immunity", h2_style))
    story.append(Paragraph("<b>7.1 Exclusions.</b> Confidential Information does not include information that: (a) Is or becomes publicly known through no breach of this Agreement by the Collaborator; (b) Was already in the Collaborator's lawful possession prior to disclosure by the Company; (c) Is lawfully obtained from a third party without restriction on disclosure; or (d) Is independently developed by the Collaborator without reference to or reliance upon the Company's Confidential Information.", body_style))
    story.append(Paragraph("<b>7.2 Defend Trade Secrets Act (DTSA) Immunity Notice.</b> Pursuant to 18 U.S.C. &sect; 1833(b), an individual shall not be held criminally or civilly liable under any Federal or State trade secret law for the disclosure of a trade secret that is made in confidence to a Federal, State, or local government official, or to an attorney, solely for the purpose of reporting or investigating a suspected violation of law, or is made in a complaint or other document filed in a lawsuit or other proceeding, if such filing is made under seal.", body_style))
    story.append(Spacer(1, 8))

    # SECTION III
    story.append(Paragraph("SECTION III: INTELLECTUAL PROPERTY ASSIGNMENT", h1_style))
    story.append(Paragraph("8. Ownership of Work Product", h2_style))
    story.append(Paragraph("The Collaborator agrees that all deliverables, written content, software, source code, documentation, designs, concepts, technical solutions, algorithms, and creative materials developed specifically for or on behalf of the Company (collectively, the \"Work Product\") shall belong exclusively to the Company upon creation.", body_style))

    story.append(Paragraph("9. Work Made for Hire & Assignment", h2_style))
    story.append(Paragraph("<b>9.1 Work Made for Hire.</b> To the maximum extent permitted under the United States Copyright Act (17 U.S.C. &sect; 101 et seq.), all eligible parts of the Work Product shall be considered a \"work made for hire\" for the sole and exclusive benefit of the Company.", body_style))
    story.append(Paragraph("<b>9.2 Universal Assignment.</b> To the extent that any Work Product does not qualify as a \"work made for hire\" under applicable law, or where international intellectual property treaties apply, the Collaborator hereby irrevocably, globally, and unconditionally assigns, transfers, and conveys to the Company all right, title, and interest in and to the Work Product. This assignment includes all copyrights, patents, trade secrets, trademarks, derivative rights, modification rights, licensing rights, and commercialization rights.", body_style))
    story.append(Paragraph("<b>9.3 Restrictions on Transfer.</b> The Collaborator has no right to assign, license, sublicense, or transfer any Company intellectual property, Work Product, or derivative works to any third party without the express, digitally timestamped written consent of Julie A. Stehouwer or Brett Adam Stehouwer.", body_style))

    story.append(Paragraph("10. Proprietary Technology Ownership", h2_style))
    story.append(Paragraph("The Company's Proprietary Technology (including all architectural systems, prompt systems, reasoning frameworks, agent workflows, memory systems, databases, automation logic, and training methodologies as defined in Exhibit A) represents strictly proprietary Trade Secrets of the Company. Any and all Company-directed modifications, enhancements, improvements, or derivative works of the Proprietary Technology shall remain the sole and exclusive property of the Company.", body_style))

    story.append(Paragraph("11. Collaborator Representations", h2_style))
    story.append(Paragraph("The Collaborator represents and warrants that: (a) They have full authority to execute this Agreement and perform the services; (b) All materials and contributions delivered to the Company do not infringe upon, misappropriate, or violate the intellectual property rights, privacy rights, or proprietary rights of any third party; and (c) They will immediately disclose to the Company in writing any pre-existing intellectual property or third-party open-source components proposed to be integrated into any Work Product.", body_style))
    story.append(Spacer(1, 8))

    # SECTION IV
    story.append(Paragraph("SECTION IV: SECURITY, ACCESS, AND DATA COMPLIANCE", h1_style))
    story.append(Paragraph("12. System Access & CTO Authorization", h2_style))
    story.append(Paragraph("Any access granted to the Collaborator to the Company's internal systems, networks, repositories, software development environments, or servers is strictly limited, revocable at will, and purpose-specific. Use of Company systems must conform strictly to the instructions and pathways authorized directly by the CTO (Brett Adam Stehouwer). Any unauthorized access, navigation of unapproved pathways, or bypass of technical restrictions constitutes a material breach of this Agreement.", body_style))

    story.append(Paragraph("13. Technical Security Controls", h2_style))
    story.append(Paragraph("The Collaborator shall not: (a) Attempt to bypass, disable, or circumvent any security controls, user authentications, or firewalls; (b) Copy, clone, or extract restricted database contents, models, or source files onto unauthorized physical or cloud-based storage; (c) Circumvent environment isolation or sandbox restrictions; or (d) Deploy unauthorized diagnostic, network monitoring, or penetration testing tools against Company infrastructure.", body_style))

    story.append(Paragraph("14. Technical Environment Protection & Export Controls", h2_style))
    story.append(Paragraph("<b>14.1 Sandbox Integrity.</b> Where access is provided to Company Proprietary Technology environments (including staging or sandboxed systems), the Collaborator shall strictly respect all infrastructure isolation, memory boundaries, and database protections. Unauthorized extraction, replication, or reverse-engineering of the sandbox or the systems running within it is strictly prohibited.", body_style))
    story.append(Paragraph("<b>14.2 Export Control Compliance.</b> The Collaborator shall comply with all applicable United States and international export and re-export control laws and regulations, including the Export Administration Regulations (EAR) maintained by the U.S. Department of Commerce and trade sanctions maintained by the U.S. Department of the Treasury's Office of Foreign Assets Control (OFAC). The Collaborator shall not export or transfer any Company Proprietary Technology, software, or technical data to restricted nations, entities, or individuals without proper government authorization.", body_style))

    story.append(Paragraph("15. Data Protection Compliance & Indemnity", h2_style))
    story.append(Paragraph("<b>15.1 Regulatory Compliance.</b> The Collaborator agrees to comply strictly with all applicable domestic and international data protection and privacy regulations, including GDPR, HIPAA, and CCPA where applicable.", body_style))
    story.append(Paragraph("<b>15.2 Liability for Non-Compliance.</b> Any regulatory fines, statutory penalties, litigation costs, damages, or legal fees incurred by the Company as a direct result of the Collaborator's failure to comply with applicable data protection laws or security protocols shall be the sole financial and legal responsibility of the Collaborator.", body_style))
    story.append(Spacer(1, 8))

    # SECTION V
    story.append(Paragraph("SECTION V: BRAND & BUSINESS PROTECTION", h1_style))
    story.append(Paragraph("16. Non-Circumvention", h2_style))
    story.append(Paragraph("The Collaborator agrees that during their collaboration with the Company and for a period of five (5) years following the termination or expiration of this Agreement, the Collaborator shall not, directly or indirectly, circumvent the Company by exploiting confidential business opportunities, bypassing Company relationships, or establishing competing business entities or models using the Company's Confidential Information.", body_style))

    story.append(Paragraph("17. Non-Solicitation", h2_style))
    story.append(Paragraph("For a period of three (3) years following the termination of this Agreement, the Collaborator shall not, directly or indirectly, solicit, recruit, or attempt to hire or contract any employee, consultant, independent contractor, or active client of the Company with whom the Collaborator had contact or about whom the Collaborator gained knowledge of during the performance of services under this Agreement.", body_style))

    story.append(Paragraph("18. Brand and Affiliation Restrictions", h2_style))
    story.append(Paragraph("The Collaborator shall not: (a) Represent themselves as an employee, officer, partner, or authorized spokesperson of the Company unless explicitly authorized in writing by the CEO; (b) Use the Company's trademarks, trade names, logos, or brand marks without prior written authorization; or (c) Publish, post, or share internal company communications, slack messages, emails, or drafts on any public forum or social media platform.", body_style))
    story.append(Spacer(1, 8))

    # SECTION VI
    story.append(Paragraph("SECTION VI: LEGAL GOVERNANCE, DISPUTES, & INDEMNIFICATION", h1_style))
    story.append(Paragraph("19. Dispute Resolution Mechanism", h2_style))
    story.append(Paragraph("<b>19.1 Executive Escalation & Mediation.</b> The Parties shall first attempt to resolve disputes in good faith through direct consultation. If unresolved, the dispute shall be submitted to confidential, non-binding mediation before a mutually agreed mediator in Kent County, Michigan, costs shared equally.", body_style))
    story.append(Paragraph("<b>19.2 Binding Arbitration.</b> If mediation fails within thirty (30) days, the dispute shall be settled by binding arbitration administered by the American Arbitration Association (AAA) under Commercial Arbitration Rules in Kent County, Michigan, governed by the Federal Arbitration Act (9 U.S.C. &sect;&sect; 1-16). Awards may be confirmed and enforced globally under the New York Convention.", body_style))
    story.append(Paragraph("<b>19.3 Litigation & Injunctions.</b> Venue for any non-arbitrable litigation shall be exclusively in Kent County, Michigan. Notwithstanding arbitration, the Company retains the right to seek immediate injunctive or equitable relief in any court of competent jurisdiction to protect intellectual property, trade secrets, or network security.", body_style))

    story.append(Paragraph("20. Remedies", h2_style))
    story.append(Paragraph("Collaborator acknowledges that any breach of Section II, III, or IV causes immediate, irreparable harm for which monetary damages alone are inadequate. The Company is entitled to seek injunctive relief, specific performance, and other equitable remedies without prejudice to other rights.", body_style))

    story.append(Paragraph("21. Indemnification", h2_style))
    story.append(Paragraph("Collaborator agrees to indemnify, defend, and hold harmless Stehouwer Publishing, LLC, its officers, members, and affiliates from all claims, damages, liabilities, losses, statutory penalties, and legal fees arising from unauthorized system access, confidentiality breach, IP infringement, or data compliance failure.", body_style))

    story.append(Paragraph("22. Amendments and Reviews", h2_style))
    story.append(Paragraph("Amendments or updates to this Agreement must be executed in a written instrument signed by authorized representatives of both Parties.", body_style))
    story.append(Spacer(1, 8))

    # SECTION VII
    story.append(Paragraph("SECTION VII: MISCELLANEOUS PROVISIONS", h1_style))
    story.append(Paragraph("<b>23. Governing Law.</b> Governed by and construed in accordance with the laws of the State of Michigan and applicable United States Federal Law.", body_style))
    story.append(Paragraph("<b>24. International Exclusions.</b> The United Nations Convention on Contracts for the International Sale of Goods (CISG) is expressly excluded.", body_style))
    story.append(Paragraph("<b>25. Entire Agreement.</b> Constitutes the entire agreement between the Parties regarding its subject matter and supersedes all prior agreements or representations.", body_style))
    story.append(Paragraph("<b>26. Severability.</b> If any provision is held invalid, remaining provisions remain in full effect.", body_style))
    story.append(Paragraph("<b>27. Counterparts & Electronic Signatures.</b> May be executed in counterparts. Digital, scanned, or electronic signatures (PDF, DocuSign, etc.) are deemed originals.", body_style))
    story.append(Spacer(1, 14))

    # EXHIBIT A
    story.append(Paragraph("EXHIBIT A: TECHNICAL SCOPE & DEFINITIONS", h1_style))
    story.append(Paragraph("<b>Definition of Company Proprietary Technology</b><br/>"
                           "\"Company Proprietary Technology\" refers to all proprietary systems, software, tools, and technical architectures developed, owned, or licensed by the Company, including but not limited to:<br/>"
                           "&bull; <b>The AI-BS (Autonomous Intelligence & Build System)</b>;<br/>"
                           "&bull; Proprietary Reasoning Frameworks, AIBSTensor autograd define-by-run graphs, and logical verification models;<br/>"
                           "&bull; Validation systems, AST syntax verification engines, and multi-agent memory architectures;<br/>"
                           "&bull; Automation pipelines, prompt systems, and agent orchestration workflows;<br/>"
                           "&bull; Associated database architectures, 18-port collision matrix, and technical infrastructure; and<br/>"
                           "&bull; Any proprietary methodologies, hallucination mitigation pipelines, and training datasets used to operate, enhance, or run these systems.", body_style))
    story.append(Spacer(1, 18))

    # SIGNATURE BLOCK (KeepTogether)
    sig_company = Paragraph(
        "<b>STEHOUWER PUBLISHING, LLC</b><br/><br/>"
        "Signature: _________________________________________<br/>"
        "<b>Julie A. Stehouwer</b><br/>"
        "CEO / Authorized Representative<br/>"
        "Date: ____________________________________________<br/><br/>"
        "Signature: _________________________________________<br/>"
        "<b>Brett Adam Stehouwer</b><br/>"
        "VP / CTO / Technical Architecture Lead<br/>"
        "Date: ____________________________________________",
        parties_body_style
    )

    sig_collaborator = Paragraph(
        "<b>COLLABORATOR / RECIPIENT</b><br/><br/>"
        "Signature: _________________________________________<br/>"
        "<b>Robert Costner</b><br/>"
        "Title: ____________________________________________<br/>"
        "Company / Org: ____________________________________<br/>"
        "Address: __________________________________________<br/>"
        "Email: ____________________________________________<br/>"
        "Date: ____________________________________________",
        parties_body_style
    )

    sig_table = Table([[sig_company, sig_collaborator]], colWidths=[245, 259])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f7fafc")),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor("#2b6cb0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))

    story.append(KeepTogether([
        Paragraph("EXECUTION & SIGNATURES", h1_style),
        Paragraph("IN WITNESS WHEREOF, the Parties hereto have caused this Master Services, Confidentiality, Intellectual Property, and Security Agreement to be executed by their duly authorized representatives as of the Effective Date.", body_style),
        Spacer(1, 8),
        sig_table
    ]))

    # Build PDF with dynamic numbering
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    out = r"C:\AI-BS\Documents\Stehouwer_Publishing_Robert_Costner_Master_NDA_Agreement.pdf"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_pdf(out)
