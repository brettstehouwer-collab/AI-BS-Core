import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_border(cell, **kwargs):
    """
    Set cell borders
    kwargs: top, bottom, left, right
    values: dict(sz=12, val='single', color='FF0000', space='0')
    """
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders')
        tcPr.append(tcBorders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = tcBorders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tcBorders.append(element)
            for key, val in edge_data.items():
                element.set(qn('w:{}'.format(key)), str(val))

def create_docx(output_path):
    doc = docx.Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        
        # Header
        header = section.header
        hp = header.paragraphs[0]
        hp.text = "STEHOUWER PUBLISHING, LLC  |  MASTER CONFIDENTIALITY & IP AGREEMENT"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.style.font.name = "Calibri"
        hp.style.font.size = Pt(8.5)
        hp.style.font.color.rgb = RGBColor(113, 128, 150)
        
        # Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.text = "CONFIDENTIAL & PROPRIETARY — STEHOUWER PUBLISHING, LLC"
        fp.style.font.name = "Calibri"
        fp.style.font.size = Pt(8.5)
        fp.style.font.color.rgb = RGBColor(113, 128, 150)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = p_title.add_run("MASTER SERVICES, CONFIDENTIALITY,\nINTELLECTUAL PROPERTY, AND SECURITY AGREEMENT")
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(16)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(26, 54, 93)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Stehouwer Publishing, LLC • Proprietary System & Technical Collaboration Protection")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(10)
    run_sub.font.color.rgb = RGBColor(74, 85, 104)

    # Parties Table
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell_left = table.cell(0, 0)
    cell_left.width = Inches(3.4)
    p_left = cell_left.paragraphs[0]
    p_left.paragraph_format.space_after = Pt(2)
    r1 = p_left.add_run("COMPANY:\n")
    r1.bold = True
    r1.font.color.rgb = RGBColor(26, 54, 93)
    p_left.add_run("Stehouwer Publishing, LLC\n1481 Rosewood St.\nJenison, Michigan 49428\nExecutive: Julie A. Stehouwer (CEO)\nTechnical: Brett Adam Stehouwer (VP / CTO)")

    cell_right = table.cell(0, 1)
    cell_right.width = Inches(3.4)
    p_right = cell_right.paragraphs[0]
    p_right.paragraph_format.space_after = Pt(2)
    r2 = p_right.add_run("COLLABORATOR / RECIPIENT:\n")
    r2.bold = True
    r2.font.color.rgb = RGBColor(26, 54, 93)
    p_right.add_run("Robert Costner\nAddress: _______________________________\nEmail: _________________________________\nPhone: _________________________________\nCapacity: Technical Evaluation / Collaborator")

    # Shading and borders
    shading_elm = parse_xml(r'<w:shd {} w:fill="F7FAFC"/>'.format(nsdecls('w')))
    cell_left._tc.get_or_add_tcPr().append(shading_elm)
    shading_elm2 = parse_xml(r'<w:shd {} w:fill="F7FAFC"/>'.format(nsdecls('w')))
    cell_right._tc.get_or_add_tcPr().append(shading_elm2)

    doc.add_paragraph()

    # Effective Date Callout
    p_eff = doc.add_paragraph()
    r_eff = p_eff.add_run("EFFECTIVE DATE: This Agreement is entered into and deemed effective as of: ________________________, 2026 (the \"Effective Date\") by and between the Company and Collaborator named above (collectively, the \"Parties\").")
    r_eff.font.italic = True
    r_eff.font.color.rgb = RGBColor(43, 108, 176)

    # Recitals
    p_rec_h = doc.add_paragraph()
    p_rec_h.paragraph_format.space_before = Pt(8)
    p_rec_h.paragraph_format.space_after = Pt(4)
    r_rh = p_rec_h.add_run("RECITALS")
    r_rh.bold = True
    r_rh.font.color.rgb = RGBColor(43, 108, 176)

    doc.add_paragraph("WHEREAS, the Company is actively engaged in commercial publishing, software systems development, artificial intelligence research, and digital media architecture;", style='List Bullet')
    doc.add_paragraph("WHEREAS, the Collaborator provides professional consulting, creative development, technical engineering, strategic evaluation, or advisory services; and", style='List Bullet')
    doc.add_paragraph("WHEREAS, the Parties wish to establish a contractual framework to govern their professional relationship, protect proprietary and confidential information, preserve trade secrets, and define the exclusive ownership of intellectual property created or shared during their collaboration.", style='List Bullet')

    doc.add_paragraph("NOW, THEREFORE, in consideration of the mutual covenants, premises, and representations contained herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:")

    # Read the full markdown text of the agreement
    sections = [
        ("SECTION I: MASTER SERVICES AGREEMENT (MSA)", [
            ("1. Purpose & Scope of Services", [
                "1.1 Scope. This Agreement establishes the master terms and conditions governing all collaboration, consulting, creative development, technical development, evaluation, licensing discussions, and other professional services performed by the Collaborator for or with the Company. The scope of activities may include, but is not limited to: (a) Publishing projects, manuscripts, and creative works; (b) Software systems, infrastructure, and digital media; (c) Artificial intelligence systems, training pipelines, and automation workflows; (d) Research, development, and business strategy; and (e) Technical architecture and system evaluation.",
                "1.2 Precedence. This Agreement shall apply to all Company-related collaboration and services unless expressly superseded by a separate, subsequent written agreement signed by authorized representatives of both Parties."
            ]),
            ("2. Company Authority & Governance", [
                "2.1 Corporate Authority. Stehouwer Publishing, LLC retains absolute, exclusive authority over all business operations, commercial decisions, contract negotiations, intellectual property strategies, publication decisions, licensing, and brand representation.",
                "2.2 Key Representatives. Julie A. Stehouwer serves as the authorized executive authority for Company operations, corporate decisions, and financial executions. Brett Adam Stehouwer serves as the Vice President, Chief Technology Officer (CTO), and Technical Architecture Lead, managing technical architecture, engineering systems, and the technical integrity of Company Proprietary Technology.",
                "2.3 No Transfer of Authority. Nothing in this Agreement shall be construed to transfer any corporate ownership, operational authority, or commercial decision-making power of the Company to the Collaborator."
            ]),
            ("3. Services, Statements of Work, and Compensation", [
                "3.1 SOW Requirement. All paid services performed by the Collaborator must be defined in writing prior to performance through a mutually executed Statement of Work (\"SOW\"), Purchase Order, or documented written/electronic authorization from an authorized representative of the Company.",
                "3.2 Consulting Fee Rule. Compensation terms must be finalized and approved in writing before any paid work begins. Unauthorized work, or work performed outside the scope of an active SOW, does not create any payment obligation for the Company. All executed SOWs shall incorporate the terms of this Agreement by reference."
            ]),
            ("4. Term, Termination, and Survival", [
                "4.1 Term. This Agreement shall commence on the Effective Date and shall remain in effect until terminated in accordance with Section 4.2.",
                "4.2 Termination. Either Party may terminate active services or this Agreement for convenience upon thirty (30) days' written notice to the other Party. Notwithstanding the foregoing, the Company reserves the right to terminate active services and this Agreement immediately, without prior notice, for \"Cause\" (including, but not limited to, a security breach, unauthorized data or code exfiltration, breach of confidentiality, or violation of applicable data protection laws).",
                "4.3 Consequences of Termination. Upon termination or expiration of this Agreement for any reason: (a) All intellectual property, deliverables, and Work Product developed up to termination shall immediately and exclusively vest with the Company; (b) Collaborator shall immediately cease all use of Company systems, networks, and applications; (c) Collaborator shall, within five (5) business days, return or permanently destroy all physical and digital Confidential Information in its possession, custody, or control, and provide written certification of such destruction to the Company's CTO.",
                "4.4 Survival. The rights and obligations of the Parties under Section II (Confidentiality), Section III (Intellectual Property), Section IV (Security and Compliance), Section V (Brand & Business Protection), and Section VI (Governance & Disputes) shall survive the expiration or termination of this Agreement in perpetuity."
            ])
        ]),
        ("SECTION II: CONFIDENTIALITY & NON-DISCLOSURE", [
            ("5. Definition of Confidential Information", [
                "\"Confidential Information\" means any and all non-public, proprietary, or business-sensitive information disclosed by or on behalf of the Company to the Collaborator, whether disclosed orally, visually, in writing, or via electronic access, and whether or not marked as \"confidential.\" Confidential Information includes, without limitation:",
                "5.1 Creative Assets: Manuscripts, drafts, poetry, publications, outlines, story concepts, characters, plot structures, artwork, and unreleased materials.",
                "5.2 Business Information: Business plans, partnership agreements, financial reports, client lists, marketing strategies, pricing structures, and internal communications.",
                "5.3 Technical Information: Source code, object code, software architecture, infrastructure designs, database schemas, prompt engineering structures, algorithms, workflows, and technical system configurations.",
                "5.4 Proprietary Systems: Company Proprietary Technology (as defined in Exhibit A), reasoning frameworks, validation systems, memory architectures, automation pipelines, and proprietary methodologies."
            ]),
            ("6. Specific Confidentiality & Security Obligations", [
                "6.1 Duty of Confidentiality. Maintain all Confidential Information in strict confidence and prevent its unauthorized disclosure, publication, or dissemination to any third party (domestic or international) without the prior express written consent of the Company.",
                "6.2 Standard of Care. Protect Confidential Information with at least the same degree of care as Collaborator uses to protect their own highly sensitive confidential information, but in no event less than a reasonable standard of care, including active encryption at rest and in transit.",
                "6.3 Permitted Use. Use the Confidential Information solely for the performance of authorized services for the Company.",
                "6.4 Non-Replication. Not copy, reverse-engineer, decompile, duplicate, or commercialize any Confidential Information or materials derived therefrom.",
                "6.5 Perpetual Duration. Notwithstanding any other provisions of this Agreement, the confidentiality obligations with respect to trade secrets and Company Proprietary Technology shall survive indefinitely. For other general business information, these obligations shall survive for a period of no less than five (5) years post-termination.",
                "6.6 Immediate Breach Reporting. The Collaborator shall notify the Company's representatives (Brett Adam Stehouwer and Julie A. Stehouwer) in writing immediately, and in no event later than twenty-four (24) hours, upon discovering any actual, suspected, or potential unauthorized access, exposure, leak, or breach of Confidential Information."
            ]),
            ("7. Exclusions & Whistleblower Immunity", [
                "7.1 Exclusions. Confidential Information does not include information that: (a) Is or becomes publicly known through no breach of this Agreement by the Collaborator; (b) Was already in the Collaborator's lawful possession prior to disclosure by the Company; (c) Is lawfully obtained from a third party without restriction on disclosure; or (d) Is independently developed by the Collaborator without reference to or reliance upon the Company's Confidential Information.",
                "7.2 Defend Trade Secrets Act (DTSA) Immunity Notice. Pursuant to 18 U.S.C. § 1833(b), an individual shall not be held criminally or civilly liable under any Federal or State trade secret law for the disclosure of a trade secret that is made in confidence to a Federal, State, or local government official, or to an attorney, solely for the purpose of reporting or investigating a suspected violation of law, or is made in a complaint or other document filed in a lawsuit or other proceeding, if such filing is made under seal."
            ])
        ]),
        ("SECTION III: INTELLECTUAL PROPERTY ASSIGNMENT", [
            ("8. Ownership of Work Product", [
                "The Collaborator agrees that all deliverables, written content, software, source code, documentation, designs, concepts, technical solutions, algorithms, and creative materials developed specifically for or on behalf of the Company (collectively, the \"Work Product\") shall belong exclusively to the Company upon creation."
            ]),
            ("9. Work Made for Hire & Assignment", [
                "9.1 Work Made for Hire. To the maximum extent permitted under the United States Copyright Act (17 U.S.C. § 101 et seq.), all eligible parts of the Work Product shall be considered a \"work made for hire\" for the sole and exclusive benefit of the Company.",
                "9.2 Universal Assignment. To the extent that any Work Product does not qualify as a \"work made for hire\" under applicable law, or where international intellectual property treaties apply, the Collaborator hereby irrevocably, globally, and unconditionally assigns, transfers, and conveys to the Company all right, title, and interest in and to the Work Product. This assignment includes all copyrights, patents, trade secrets, trademarks, derivative rights, modification rights, licensing rights, and commercialization rights.",
                "9.3 Restrictions on Transfer. The Collaborator has no right to assign, license, sublicense, or transfer any Company intellectual property, Work Product, or derivative works to any third party without the express, digitally timestamped written consent of Julie A. Stehouwer or Brett Adam Stehouwer."
            ]),
            ("10. Proprietary Technology Ownership", [
                "The Company's Proprietary Technology (including all architectural systems, prompt systems, reasoning frameworks, agent workflows, memory systems, databases, automation logic, and training methodologies as defined in Exhibit A) represents strictly proprietary Trade Secrets of the Company. Any and all Company-directed modifications, enhancements, improvements, or derivative works of the Proprietary Technology shall remain the sole and exclusive property of the Company."
            ]),
            ("11. Collaborator Representations", [
                "The Collaborator represents and warrants that: (a) They have full authority to execute this Agreement and perform the services; (b) All materials and contributions delivered to the Company do not infringe upon, misappropriate, or violate the intellectual property rights, privacy rights, or proprietary rights of any third party; and (c) They will immediately disclose to the Company in writing any pre-existing intellectual property or third-party open-source components proposed to be integrated into any Work Product."
            ])
        ]),
        ("SECTION IV: SECURITY, ACCESS, AND DATA COMPLIANCE", [
            ("12. System Access & CTO Authorization", [
                "Any access granted to the Collaborator to the Company's internal systems, networks, repositories, software development environments, or servers is strictly limited, revocable at will, and purpose-specific. Use of Company systems must conform strictly to the instructions and pathways authorized directly by the CTO (Brett Adam Stehouwer). Any unauthorized access, navigation of unapproved pathways, or bypass of technical restrictions constitutes a material breach of this Agreement."
            ]),
            ("13. Technical Security Controls", [
                "The Collaborator shall not: (a) Attempt to bypass, disable, or circumvent any security controls, user authentications, or firewalls; (b) Copy, clone, or extract restricted database contents, models, or source files onto unauthorized physical or cloud-based storage; (c) Circumvent environment isolation or sandbox restrictions; or (d) Deploy unauthorized diagnostic, network monitoring, or penetration testing tools against Company infrastructure."
            ]),
            ("14. Technical Environment Protection & Export Controls", [
                "14.1 Sandbox Integrity. Where access is provided to Company Proprietary Technology environments (including staging or sandboxed systems), the Collaborator shall strictly respect all infrastructure isolation, memory boundaries, and database protections. Unauthorized extraction, replication, or reverse-engineering of the sandbox or the systems running within it is strictly prohibited.",
                "14.2 Export Control Compliance. The Collaborator shall comply with all applicable United States and international export and re-export control laws and regulations, including the Export Administration Regulations (EAR) maintained by the U.S. Department of Commerce and trade sanctions maintained by the U.S. Department of the Treasury's Office of Foreign Assets Control (OFAC). The Collaborator shall not export or transfer any Company Proprietary Technology, software, or technical data to restricted nations, entities, or individuals without proper government authorization."
            ]),
            ("15. Data Protection Compliance & Indemnity", [
                "15.1 Regulatory Compliance. The Collaborator agrees to comply strictly with all applicable domestic and international data protection and privacy regulations, including GDPR, HIPAA, and CCPA where applicable.",
                "15.2 Liability for Non-Compliance. Any regulatory fines, statutory penalties, litigation costs, damages, or legal fees incurred by the Company as a direct result of the Collaborator's failure to comply with applicable data protection laws or security protocols shall be the sole financial and legal responsibility of the Collaborator."
            ])
        ]),
        ("SECTION V: BRAND & BUSINESS PROTECTION", [
            ("16. Non-Circumvention", [
                "The Collaborator agrees that during their collaboration with the Company and for a period of five (5) years following the termination or expiration of this Agreement, the Collaborator shall not, directly or indirectly, circumvent the Company by exploiting confidential business opportunities, bypassing Company relationships, or establishing competing business entities or models using the Company's Confidential Information."
            ]),
            ("17. Non-Solicitation", [
                "For a period of three (3) years following the termination of this Agreement, the Collaborator shall not, directly or indirectly, solicit, recruit, or attempt to hire or contract any employee, consultant, independent contractor, or active client of the Company with whom the Collaborator had contact or about whom the Collaborator gained knowledge of during the performance of services under this Agreement."
            ]),
            ("18. Brand and Affiliation Restrictions", [
                "The Collaborator shall not: (a) Represent themselves as an employee, officer, partner, or authorized spokesperson of the Company unless explicitly authorized in writing by the CEO; (b) Use the Company's trademarks, trade names, logos, or brand marks without prior written authorization; or (c) Publish, post, or share internal company communications, slack messages, emails, or drafts on any public forum or social media platform."
            ])
        ]),
        ("SECTION VI: LEGAL GOVERNANCE, DISPUTES, & INDEMNIFICATION", [
            ("19. Dispute Resolution Mechanism", [
                "19.1 Executive Escalation & Mediation. The Parties shall first attempt to resolve disputes in good faith through direct consultation. If unresolved, the dispute shall be submitted to confidential, non-binding mediation before a mutually agreed mediator in Kent County, Michigan, costs shared equally.",
                "19.2 Binding Arbitration. If mediation fails within thirty (30) days, the dispute shall be settled by binding arbitration administered by the American Arbitration Association (AAA) under Commercial Arbitration Rules in Kent County, Michigan, governed by the Federal Arbitration Act (9 U.S.C. §§ 1-16). Awards may be confirmed and enforced globally under the New York Convention.",
                "19.3 Litigation & Injunctions. Venue for any non-arbitrable litigation shall be exclusively in Kent County, Michigan. Notwithstanding arbitration, the Company retains the right to seek immediate injunctive or equitable relief in any court of competent jurisdiction to protect intellectual property, trade secrets, or network security."
            ]),
            ("20. Remedies", [
                "Collaborator acknowledges that any breach of Section II, III, or IV causes immediate, irreparable harm for which monetary damages alone are inadequate. The Company is entitled to seek injunctive relief, specific performance, and other equitable remedies without prejudice to other rights."
            ]),
            ("21. Indemnification", [
                "Collaborator agrees to indemnify, defend, and hold harmless Stehouwer Publishing, LLC, its officers, members, and affiliates from all claims, damages, liabilities, losses, statutory penalties, and legal fees arising from unauthorized system access, confidentiality breach, IP infringement, or data compliance failure."
            ]),
            ("22. Amendments and Reviews", [
                "Amendments or updates to this Agreement must be executed in a written instrument signed by authorized representatives of both Parties."
            ])
        ]),
        ("SECTION VII: MISCELLANEOUS PROVISIONS", [
            ("23. Governing Law", ["Governed by and construed in accordance with the laws of the State of Michigan and applicable United States Federal Law."]),
            ("24. International Exclusions", ["The United Nations Convention on Contracts for the International Sale of Goods (CISG) is expressly excluded."]),
            ("25. Entire Agreement", ["Constitutes the entire agreement between the Parties regarding its subject matter and supersedes all prior agreements or representations."]),
            ("26. Severability", ["If any provision is held invalid, remaining provisions remain in full effect."]),
            ("27. Counterparts & Electronic Signatures", ["May be executed in counterparts. Digital, scanned, or electronic signatures (PDF, DocuSign, etc.) are deemed originals."])
        ]),
        ("EXHIBIT A: TECHNICAL SCOPE & DEFINITIONS", [
            ("Definition of Company Proprietary Technology", [
                "\"Company Proprietary Technology\" refers to all proprietary systems, software, tools, and technical architectures developed, owned, or licensed by the Company, including but not limited to:",
                "• The AI-BS (Autonomous Intelligence & Build System);",
                "• Proprietary Reasoning Frameworks, AIBSTensor autograd define-by-run graphs, and logical verification models;",
                "• Validation systems, AST syntax verification engines, and multi-agent memory architectures;",
                "• Automation pipelines, prompt systems, and agent orchestration workflows;",
                "• Associated database architectures, 18-port collision matrix, and technical infrastructure; and",
                "• Any proprietary methodologies, hallucination mitigation pipelines, and training datasets used to operate, enhance, or run these systems."
            ])
        ])
    ]

    for sec_title, subsecs in sections:
        p_sec = doc.add_paragraph()
        p_sec.paragraph_format.space_before = Pt(14)
        p_sec.paragraph_format.space_after = Pt(4)
        r_s = p_sec.add_run(sec_title)
        r_s.bold = True
        r_s.font.size = Pt(11)
        r_s.font.color.rgb = RGBColor(26, 54, 93)

        for sub_title, paras in subsecs:
            p_sub = doc.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(8)
            p_sub.paragraph_format.space_after = Pt(2)
            r_sb = p_sub.add_run(sub_title)
            r_sb.bold = True
            r_sb.font.size = Pt(10)
            r_sb.font.color.rgb = RGBColor(43, 108, 176)

            for p_text in paras:
                p_body = doc.add_paragraph(p_text)
                p_body.paragraph_format.space_after = Pt(4)
                p_body.style.font.name = "Calibri"
                p_body.style.font.size = Pt(9.5)

    # Signatures
    p_sig_head = doc.add_paragraph()
    p_sig_head.paragraph_format.space_before = Pt(16)
    p_sig_head.paragraph_format.space_after = Pt(4)
    r_sh = p_sig_head.add_run("EXECUTION & SIGNATURES")
    r_sh.bold = True
    r_sh.font.size = Pt(11)
    r_sh.font.color.rgb = RGBColor(26, 54, 93)

    doc.add_paragraph("IN WITNESS WHEREOF, the Parties hereto have caused this Master Services, Confidentiality, Intellectual Property, and Security Agreement to be executed by their duly authorized representatives as of the Effective Date.")

    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False

    s_left = sig_table.cell(0, 0)
    s_left.width = Inches(3.4)
    p_sleft = s_left.paragraphs[0]
    p_sleft.add_run("STEHOUWER PUBLISHING, LLC\n\nSignature: _____________________________________\nJulie A. Stehouwer\nCEO / Authorized Representative\nDate: _________________________________________\n\nSignature: _____________________________________\nBrett Adam Stehouwer\nVP / CTO / Technical Architecture Lead\nDate: _________________________________________")

    s_right = sig_table.cell(0, 1)
    s_right.width = Inches(3.4)
    p_sright = s_right.paragraphs[0]
    p_sright.add_run("COLLABORATOR / RECIPIENT\n\nSignature: _____________________________________\nRobert Costner\nTitle: _________________________________________\nCompany / Org: _________________________________\nAddress: _______________________________________\nEmail: _________________________________________\nDate: _________________________________________")

    shading_s1 = parse_xml(r'<w:shd {} w:fill="F7FAFC"/>'.format(nsdecls('w')))
    s_left._tc.get_or_add_tcPr().append(shading_s1)
    shading_s2 = parse_xml(r'<w:shd {} w:fill="F7FAFC"/>'.format(nsdecls('w')))
    s_right._tc.get_or_add_tcPr().append(shading_s2)

    doc.save(output_path)
    print(f"DOCX successfully generated at: {output_path}")

if __name__ == "__main__":
    out_docx = r"C:\AI-BS\Documents\Stehouwer_Publishing_Robert_Costner_Master_NDA_Agreement.docx"
    create_docx(out_docx)
