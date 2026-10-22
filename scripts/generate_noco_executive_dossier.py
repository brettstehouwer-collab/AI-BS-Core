"""
AI-BS Sovereign Executive Due Diligence Dossier Generator
---------------------------------------------------------
Compiles a publication-grade PDF:
- Project NoCo & "The Living Stage" Master Vision
- Co-Founders: Sean (Kief) Stehouwer & Brett Adam Stehouwer
- 112 Due Diligence Audit Summary
- Nationwide Municipal Defense Matrix (NJ, VT, NY, MI)
- 23-Acre CapEx Schedule ($185k / $85k / $580k / $95k) & ROI
- Trojan Horse Agricultural Zoning Strategy
"""

import os
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = r"C:\AI-BS\saved_data\NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
PUBLIC_PDF_PATH = r"C:\AI-BS\frontend\public\NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
DIST_PDF_PATH = r"C:\AI-BS\frontend\dist\NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
ARTIFACT_PDF_PATH = r"C:\Users\footb\.gemini\antigravity\brain\3e6e6e6c-c306-4bed-9631-db8a9be99846\NoCo_Executive_Due_Diligence_Dossier_2026.pdf"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 755, "PROJECT NOCO & THE LIVING STAGE — EXECUTIVE DUE DILIGENCE DOSSIER")
            self.drawRightString(612 - 54, 755, "CONFIDENTIAL & PROPRIETARY")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 748, 612 - 54, 748)
            
        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.drawString(54, 32, "Co-Founders: Brett Adam Stehouwer & Sean (Kief) Stehouwer • AI-BS Sovereign Intelligence")
        self.drawRightString(612 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_pdf():
    print("=" * 80)
    print(" 📄 COMPILING NOCO EXECUTIVE DUE DILIGENCE DOSSIER PDF")
    print("=" * 80)
    
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=colors.HexColor("#0f172a")
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0284c7")
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#334155")
    )
    
    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#1e293b")
    )
    
    story = []
    
    # -------------------------------------------------------------
    # PAGE 1: TITLE & EXECUTIVE VISION
    # -------------------------------------------------------------
    story.append(Spacer(1, 20))
    story.append(Paragraph("PROJECT NoCo & “THE LIVING STAGE”", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("23-Acre Autonomous Acoustic-Agricultural Enclave • Executive Land Acquisition & Realtor Due Diligence Dossier", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0284c7"), spaceAfter=14))
    
    meta_table_data = [
        [Paragraph("<b>Co-Founders & Principals:</b>", body_style), Paragraph("Brett Adam Stehouwer & Sean (Kief) Stehouwer", body_style)],
        [Paragraph("<b>Primary Target Locus:</b>", body_style), Paragraph("Ithaca & Finger Lakes Region, Tompkins County, NY", body_style)],
        [Paragraph("<b>Nationwide Expansion Ring:</b>", body_style), Paragraph("Hunterdon/Warren Co. NJ • Addison/Windham Co. VT • Ottawa Co. MI", body_style)],
        [Paragraph("<b>Core Dual-Use Architecture:</b>", body_style), Paragraph("High-Pressure Aeroponics (HPA) Greenhouse + Living Amphitheater", body_style)],
        [Paragraph("<b>Governance Protocol:</b>", body_style), Paragraph("The Kief Protocol (Est. August 17, 2025) • Non-Refusal Safety S1/S3/S4", body_style)],
        [Paragraph("<b>Dossier Publication Date:</b>", body_style), Paragraph("October 2026 • Sovereign AI-BS Deployment", body_style)]
    ]
    t_meta = Table(meta_table_data, colWidths=[160, 344])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))
    
    story.append(Paragraph("1. Executive Summary & The 'Trojan Horse' Agricultural Shield", h1_style))
    story.append(Paragraph(
        "Project NoCo resolves the fundamental regulatory and financial dilemma facing independent acoustic theater and cultural sanctuaries: "
        "commercial assembly zoning is vulnerable to speculative sprawl, prohibitive energy mandates, and industrial data center creep. "
        "By structuring the primary performance space as a <b>dual-use 4,000 SF Controlled Environment Agriculture (CEA) polycarbonate greenhouse</b>, "
        "the facility operates under state Right to Farm protections. Under Tompkins County and New York Town Code § 144-202.1(B)(1)(b), "
        "agricultural production structures are explicitly exempt from commercial Net-Zero building energy moratoriums. "
        "This legal foundation shields our unamplified acoustic amphitheater, vertical aeroponic lettuce towers, koi nutrient recovery loop, and off-grid microgrid from municipal obstruction.",
        body_style
    ))
    story.append(Spacer(1, 14))
    
    # -------------------------------------------------------------
    # PAGE 2: NATIONWIDE MUNICIPAL DEFENSE MATRIX
    # -------------------------------------------------------------
    story.append(Paragraph("2. Nationwide Municipality Regulatory & Environmental Defense Matrix", h1_style))
    story.append(Paragraph(
        "Each candidate jurisdiction evaluated by Brett and Sean has been audited for industrial data center bans, water security, acoustic baselines, and donor transit accessibility:",
        body_style
    ))
    story.append(Spacer(1, 8))
    
    muni_data = [
        ["Jurisdiction", "Zoning Shield & Bans", "Water & Acoustic Security", "Cultural & Donor Transit"],
        [
            "Hunterdon & Warren\nCounties, NJ\n(Tier 1 Ag-Preserve)",
            "110+ municipal zoning bans\nagainst hyperscale data centers;\nNJ Right to Farm preserves\nup to 42% of county land.",
            "50-year aquifer security;\nNatural groundwater tables;\nLow ambient industrial noise.",
            "Direct 1.5-hour transit radius\nto Manhattan donor base\nand Broadway patrons."
        ],
        [
            "Addison & Windham\nCounties, VT\n(Tier 1 Ecological)",
            "Vermont Act 250 Land Use\nRegulations prohibit speculative\ncommercial sprawl and data centers.",
            "Abundant glacial springs & streams;\nUltra-quiet acoustic noise floor\n(<30 dBA ambient).",
            "Deep collegiate theater\nintegration via Middlebury College\nDepartment of Theatre."
        ],
        [
            "Tompkins County, NY\n(Ithaca / Finger Lakes\nTier 1 Target Hub)",
            "Town Code § 144-202.1(B)(1)(b)\nexempts agricultural buildings\nfrom stringent IECS mandates.",
            "Cayuga Lake watershed;\nPorous shale & gravel filtration;\nNatural bowl topography.",
            "Direct research nexus with\nCornell CEA program and\nIthaca College Theatre Arts."
        ],
        [
            "Ottawa County, MI\n(Jenison / Grand Haven\nTier 2 Regional Base)",
            "Strong agricultural zoning\npreservation in Georgetown\nand Robinson Townships.",
            "Great Lakes freshwater abundance;\nPrevailing SW winds support vocal\nHuygens-Fresnel propagation.",
            "Home base foundation with\nregional Grand Rapids\ndonor & artisan network."
        ]
    ]
    t_muni = Table(muni_data, colWidths=[110, 134, 130, 130])
    t_muni.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor("#f8fafc")),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_muni)
    story.append(Spacer(1, 14))
    
    # -------------------------------------------------------------
    # PAGE 3: 112-POINT REALTOR DUE DILIGENCE SUMMARY
    # -------------------------------------------------------------
    story.append(Paragraph("3. 112-Point Realtor Due Diligence Questionnaire Audit Summary", h1_style))
    story.append(Paragraph(
        "Candidate parcels are audited across 6 strict operational sections (112 discrete questions) before acquisition approval:",
        body_style
    ))
    story.append(Spacer(1, 8))
    
    audit_sections = [
        ["Audit Domain", "Questions", "Mandatory Pass Criteria & Technical Specifications"],
        ["S1: Zoning & Agritourism", "Q1 – Q18", "By-right agricultural classification; accessory theatrical assembly permitted; zero deed restrictions on seasonal agritourism or artist residencies."],
        ["S2: Hydrology & Aquifers", "Q19 – Q35", "Minimum 15 GPM sustained well flow or surface pond (>0.5 acre); clean water chemistry (pH 6.2–6.8, TDS < 250 ppm) for closed-loop aeroponics."],
        ["S3: Topography & Acoustics", "Q36 – Q52", "Natural south/southeast-facing depression bowl; minimum 8°–12° slope rake; ambient noise floor <35 dBA; minimum 500-ft buffer from multi-lane highways."],
        ["S4: Electrical & Microgrid", "Q53 – Q70", "Utility grid interconnect capacity or by-right 160 kW off-grid bifacial solar PV array + 500 kWh LiFePO4 BESS; isolation transformer ground plane."],
        ["S5: Environmental & Soils", "Q71 – Q90", "Percolation rate supporting gravity subsurface wetland (>1 in/30 min); deep gravelly loam soil; zero adjacent industrial or high-voltage EMF easements."],
        ["S6: Civil & Life Safety", "Q91 – Q112", "Emergency vehicle 20-ft turnaround radius; 350-person peak hydraulic septic compliance; frost-line depth >48 inches for geothermal loops."]
    ]
    t_audit = Table(audit_sections, colWidths=[120, 60, 324])
    t_audit.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284c7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor("#f8fafc")),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_audit)
    story.append(Spacer(1, 14))
    
    # -------------------------------------------------------------
    # PAGE 4: 23-ACRE CAPEX SCHEDULE & FINANCIAL PAYBACK
    # -------------------------------------------------------------
    story.append(Paragraph("4. 23-Acre Master CapEx Schedule & Multi-Stream Revenue Model", h1_style))
    story.append(Paragraph(
        "Capital expenditure for full 23-acre build-out in Ithaca, NY, calibrated against annual energy savings and agricultural/cultural revenues:",
        body_style
    ))
    story.append(Spacer(1, 8))
    
    capex_data = [
        ["System / Infrastructure Asset", "Specification / Capacity", "Budgeted CapEx", "Annual Benefit / Revenue"],
        ["Land Acquisition (23 Acres)", "Natural bowl, road frontage, water rights", "$425,500", "Asset equity, acoustic isolation"],
        ["Living Stage Polycarbonate Greenhouse", "4,000 SF twin-wall, 18 NFT towers, 120 seats", "$580,000", "$81,600/yr (81,600 heads greens)"],
        ["150 kW Solar PV + 10 kW Wind Turbine", "Ground-mount bifacial + 500 kWh BESS bunker", "$185,000", "$32,400/yr utility electric savings"],
        ["10 kW Low-Noise Vertical Wind Array", "Secondary night & winter power generation", "$85,000", "Winter off-grid resilience"],
        ["Ground Source Geothermal Loop (GSHP)", "Radiant floor heating for stage & greenhouse", "$95,000", "$14,500/yr heating fuel savings"],
        ["Livestock Shelter & Paddock Fence", "Valais sheep barn & alpaca fiber station", "$45,000", "$8,975/yr (wool & vicuña fleece)"],
        ["Subsurface Constructed Septic Wetland", "3,000-gal primary tank + gravel reed bed", "$65,000", "Zero municipal sewer fees"],
        ["TOTAL ESTIMATED INITIAL CAPEX", "Autonomous 23-Acre Master Enclave", "$1,480,500", "$377,475/yr Gross Revenue + Utility Savings"]
    ]
    t_capex = Table(capex_data, colWidths=[150, 154, 85, 115])
    t_capex.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(t_capex)
    story.append(Spacer(1, 12))
    
    callout_box = [
        [Paragraph(
            "<b>FINANCIAL VERDICT:</b> With combined annual revenue and utility avoidance of <b>$377,475 per year</b> "
            "(incorporating 8 monthly performances, agritourism dinners, NFT greens harvest, and fleece), "
            "the capital payback period is calculated at <b>3.92 Years</b>, transitioning into an autonomous self-funding endowment.",
            callout_style
        )]
    ]
    t_callout = Table(callout_box, colWidths=[504])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ecfdf5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#10b981")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_callout)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    
    # Copy to public, dist, and artifacts
    import shutil
    shutil.copyfile(PDF_OUTPUT_PATH, PUBLIC_PDF_PATH)
    shutil.copyfile(PDF_OUTPUT_PATH, DIST_PDF_PATH)
    shutil.copyfile(PDF_OUTPUT_PATH, ARTIFACT_PDF_PATH)
    
    print(f"✔ Generated PDF at: {PDF_OUTPUT_PATH} ({os.path.getsize(PDF_OUTPUT_PATH):,} bytes)")
    print(f"✔ Copied to Public: {PUBLIC_PDF_PATH}")
    print(f"✔ Copied to Artifacts: {ARTIFACT_PDF_PATH}")
    print("=" * 80)

if __name__ == "__main__":
    build_pdf()
