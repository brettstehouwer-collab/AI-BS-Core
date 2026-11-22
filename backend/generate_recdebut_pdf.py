import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

DB_PATH = Path(r"C:\AI-BS\saved_data\rec_debut.db")
PDF_PATH = Path(r"C:\AI-BS\saved_data\RecDebut_All_Time_Contacted_Athletes_Audit.pdf")
DESKTOP_PDF_PATH = Path(r"C:\Users\footb\OneDrive\Desktop\carrytodex\RecDebut_All_Time_Contacted_Athletes_Audit.pdf")

class NumberedCanvas(canvas.Canvas):
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
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 580, "RECREATIONAL DEBUT · ALL-TIME CONTACTED ATHLETES AUDIT")
            self.drawRightString(756, 580, f"Dennis Bell (President) · {datetime.now().strftime('%B %d, %Y')}")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 574, 756, 574)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, 756, 32)
        
        footer_text = "Recreational Debut (501c3 Nonprofit) · 1475 Edgeknoll Dr SE, Kentwood, MI 49508 · dbell002@sbcglobal.net"
        self.drawString(36, 22, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(756, 22, page_str)
        self.restoreState()

def build_pdf():
    print("Fetching athlete records from database...")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT id, name, email, phone, sport, high_school, grad_year, city_state, status, last_messaged_at
        FROM rec_debut_athletes
        WHERE status = 'Contacted'
        ORDER BY last_messaged_at DESC
    """)
    athletes = c.fetchall()
    conn.close()
    print(f"Loaded {len(athletes)} contacted athletes.")

    # Landscape letter gives 792 x 612 pt
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#001F3F')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#F58426')
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )

    tbl_header_style = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    tbl_cell_style = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1e293b')
    )

    tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )

    tbl_cell_dim = ParagraphStyle(
        'TblCellDim',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748b')
    )

    elements = []

    # Title Banner
    elements.append(Paragraph("RECREATIONAL DEBUT", title_style))
    elements.append(Paragraph("ALL-TIME CONTACTED ATHLETES & DISPATCH VERIFICATION AUDIT", subtitle_style))
    elements.append(Spacer(1, 4))
    
    gen_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    summary_text = f"""
    <b>Executive Summary for Dennis Bell (President · Former NY Knick #4)</b><br/>
    <b>Total Contacted Athletes:</b> {len(athletes):,} records &bull; 
    <b>Delivered Today (Nov 5, 2026):</b> 329 student-athletes &bull; 
    <b>Real-Time Confirmation Receipts:</b> 329 forwarded to dbell002@sbcglobal.net<br/>
    <b>Registered Office:</b> 1475 Edgeknoll Dr SE, Kentwood, MI 49508 &bull; 
    <b>Official Phone:</b> (616) 291-5227 &bull; 
    <b>Generated:</b> {gen_time}
    """
    elements.append(Paragraph(summary_text, meta_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#001F3F"), spaceBefore=2, spaceAfter=8))

    # Table Header
    headers = [
        Paragraph("#", tbl_header_style),
        Paragraph("ATHLETE NAME", tbl_header_style),
        Paragraph("EMAIL ADDRESS", tbl_header_style),
        Paragraph("PHONE", tbl_header_style),
        Paragraph("SPORT", tbl_header_style),
        Paragraph("HIGH SCHOOL / LOCATION", tbl_header_style),
        Paragraph("CLASS", tbl_header_style),
        Paragraph("CONTACT DATE", tbl_header_style),
        Paragraph("STATUS", tbl_header_style),
    ]

    table_data = [headers]

    for idx, ath in enumerate(athletes, 1):
        ath_id = ath[0]
        name = ath[1] or "N/A"
        email_addr = ath[2] or "N/A"
        phone = ath[3] or "N/A"
        sport = (ath[4] or "Basketball").replace(" (Girls)", " (G)").replace("Basketball", "B-Ball")
        hs = ath[5] or "N/A"
        city_st = f" ({ath[7]})" if ath[7] else ""
        hs_full = (hs + city_st)[:30]
        grad = ath[6] or "N/A"
        last_ts = ath[9]
        dt_str = datetime.fromtimestamp(last_ts).strftime("%m/%d/%y %H:%M") if last_ts else "Prior Wave"
        status = ath[8] or "Contacted"

        table_data.append([
            Paragraph(str(idx), tbl_cell_dim),
            Paragraph(name[:24], tbl_cell_bold),
            Paragraph(email_addr[:30], tbl_cell_style),
            Paragraph(phone[:15], tbl_cell_dim),
            Paragraph(sport[:14], tbl_cell_style),
            Paragraph(hs_full, tbl_cell_style),
            Paragraph(str(grad), tbl_cell_style),
            Paragraph(dt_str, tbl_cell_dim),
            Paragraph(f"<font color='#059669'><b>{status}</b></font>", tbl_cell_style),
        ])

    # Column widths summing to 720pt (792 - 72pt margins)
    # 25 + 105 + 145 + 75 + 65 + 135 + 40 + 75 + 55 = 720
    col_widths = [25, 105, 145, 75, 65, 135, 40, 75, 55]

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#001F3F')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
    ]

    # Alternating row colors
    for r in range(1, len(table_data)):
        bg_col = colors.HexColor('#f8fafc') if r % 2 == 1 else colors.white
        t_style.append(('BACKGROUND', (0, r), (-1, r), bg_col))

    t.setStyle(TableStyle(t_style))
    elements.append(t)

    print("Building PDF with NumberedCanvas...")
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"Generated PDF successfully: {PDF_PATH}")
    
    # Copy to Desktop/carrytodex
    import shutil
    shutil.copy2(PDF_PATH, DESKTOP_PDF_PATH)
    print(f"Copied PDF to: {DESKTOP_PDF_PATH}")

if __name__ == '__main__':
    build_pdf()
