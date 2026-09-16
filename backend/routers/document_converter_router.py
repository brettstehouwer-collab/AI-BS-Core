"""
Document Converter & Google Docs to Microsoft Word Gateway Router.
Enables uploading Google Docs / Word files (.docx, .gdoc, .txt, .md, .pdf),
parsing them, editing in the White Page Canvas, and 1-click exporting to Microsoft Word (.docx).
"""

import io
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import Response, JSONResponse, StreamingResponse
from pydantic import BaseModel
import httpx
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

router = APIRouter(prefix="/api/documents", tags=["Document Conversion & Word Gateway"])


class ExportDocxRequest(BaseModel):
    filename: Optional[str] = "Document"
    content: str
    title: Optional[str] = None
    author: Optional[str] = "Brett Stehouwer"


class ImportGDocUrlRequest(BaseModel):
    url: str


@router.post("/export_docx")
async def export_to_microsoft_word(req: ExportDocxRequest):
    """Converts text / markdown document content into a formatted Microsoft Word (.docx) file."""
    try:
        doc = docx.Document()

        # Set standard 1-inch margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Base document title if provided
        if req.title:
            title_p = doc.add_heading(req.title, level=0)
            title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        lines = req.content.splitlines()
        in_code_block = False

        for line in lines:
            trimmed = line.strip()

            if trimmed.startswith("```"):
                in_code_block = not in_code_block
                continue

            if not trimmed:
                doc.add_paragraph("")
                continue

            # Headings
            if trimmed.startswith("# "):
                doc.add_heading(trimmed[2:].strip(), level=1)
            elif trimmed.startswith("## "):
                doc.add_heading(trimmed[3:].strip(), level=2)
            elif trimmed.startswith("### "):
                doc.add_heading(trimmed[4:].strip(), level=3)
            elif trimmed.startswith("#### "):
                doc.add_heading(trimmed[5:].strip(), level=4)
            # Bullet list
            elif trimmed.startswith("- ") or trimmed.startswith("* "):
                bullet_text = trimmed[2:].strip()
                doc.add_paragraph(bullet_text, style="List Bullet")
            # Numbered list
            elif re.match(r"^\d+\.\s", trimmed):
                num_text = re.sub(r"^\d+\.\s", "", trimmed).strip()
                doc.add_paragraph(num_text, style="List Number")
            # Blockquote
            elif trimmed.startswith("> "):
                quote_text = trimmed[2:].strip()
                p = doc.add_paragraph(quote_text, style="Quote")
            # Horizontal rule
            elif trimmed in ["---", "***", "___"]:
                p = doc.add_paragraph()
                p.add_run("____________________________________________________")
            else:
                p = doc.add_paragraph()
                # Simple bold/italic regex parsing
                # Replace **bold** with bold run
                parts = re.split(r"(\*\*.*?\*\*|\*.*?\*)", line)
                for part in parts:
                    if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                        run = p.add_run(part[2:-2])
                        run.bold = True
                    elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
                        run = p.add_run(part[1:-1])
                        run.italic = True
                    else:
                        p.add_run(part)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        safe_filename = req.filename.replace(".docx", "") if req.filename else "Document"
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', safe_filename)

        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}.docx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Word document: {str(e)}")

@router.post("/export_fdx")
async def export_to_fdx(req: ExportDocxRequest):
    """Converts text / fountain document content into a formatted Final Draft (.fdx) file."""
    try:
        from core.matrix_docs import FountainParser
        parser = FountainParser(req.content)
        parser.parse()
        fdx = parser.to_fdx(req.title or "Untitled", req.author or "Unknown")

        safe_filename = req.filename.replace(".fdx", "").replace(".txt", "").replace(".md", "").replace(".fountain", "") if req.filename else "Document"
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', safe_filename)

        return Response(
            content=fdx,
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}.fdx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate FDX document: {str(e)}")



@router.post("/import_docx")
async def import_word_document(file: UploadFile = File(...)):
    """Extracts structured text/markdown from an uploaded Microsoft Word (.docx) file (or Google Docs export)."""
    try:
        content_bytes = await file.read()
        file_stream = io.BytesIO(content_bytes)
        doc = docx.Document(file_stream)

        extracted_lines = []
        for p in doc.paragraphs:
            text = p.text
            if not text.strip():
                extracted_lines.append("")
                continue

            style_name = p.style.name.lower() if p.style else ""
            if "heading 1" in style_name:
                extracted_lines.append(f"# {text}")
            elif "heading 2" in style_name:
                extracted_lines.append(f"## {text}")
            elif "heading 3" in style_name:
                extracted_lines.append(f"### {text}")
            elif "list bullet" in style_name:
                extracted_lines.append(f"- {text}")
            elif "list number" in style_name:
                extracted_lines.append(f"1. {text}")
            elif "quote" in style_name:
                extracted_lines.append(f"> {text}")
            else:
                extracted_lines.append(text)

        full_content = "\n".join(extracted_lines)
        word_count = len(full_content.split())

        return {
            "status": "success",
            "filename": file.filename,
            "content": full_content,
            "word_count": word_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read Word document: {str(e)}")


@router.post("/import_gdoc_url")
async def import_from_google_docs_url(req: ImportGDocUrlRequest):
    """Fetches and parses a Google Doc directly from its sharing link."""
    # Extract Google Doc ID: https://docs.google.com/document/d/<DOC_ID>/...
    match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", req.url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Google Docs URL format. Expected: https://docs.google.com/document/d/<DOC_ID>/...")

    doc_id = match.group(1)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=docx"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            res = await client.get(export_url)
            if res.status_code != 200:
                # Fallback to txt format
                txt_export = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
                txt_res = await client.get(txt_export)
                if txt_res.status_code == 200:
                    text_content = txt_res.text
                    return {
                        "status": "success",
                        "doc_id": doc_id,
                        "filename": f"Google_Doc_{doc_id[:8]}.txt",
                        "content": text_content,
                        "word_count": len(text_content.split())
                    }
                raise HTTPException(
                    status_code=res.status_code,
                    detail="Could not access Google Doc. Please ensure the document is set to 'Anyone with the link can view'."
                )

            # Parse docx stream
            file_stream = io.BytesIO(res.content)
            doc = docx.Document(file_stream)

            extracted_lines = []
            for p in doc.paragraphs:
                text = p.text
                if not text.strip():
                    extracted_lines.append("")
                    continue

                style_name = p.style.name.lower() if p.style else ""
                if "heading 1" in style_name:
                    extracted_lines.append(f"# {text}")
                elif "heading 2" in style_name:
                    extracted_lines.append(f"## {text}")
                elif "heading 3" in style_name:
                    extracted_lines.append(f"### {text}")
                elif "list bullet" in style_name:
                    extracted_lines.append(f"- {text}")
                elif "list number" in style_name:
                    extracted_lines.append(f"1. {text}")
                elif "quote" in style_name:
                    extracted_lines.append(f"> {text}")
                else:
                    extracted_lines.append(text)

            full_content = "\n".join(extracted_lines)
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": f"Google_Doc_{doc_id[:8]}.docx",
                "content": full_content,
                "word_count": len(full_content.split())
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Google Doc: {str(e)}")


class BanquetBeoRequest(BaseModel):
    event_name: str = "Grand Gala & Banquet Celebration"
    client_name: str = "Mr. & Mrs. Anderson"
    contact_email: Optional[str] = "client@example.com"
    contact_phone: Optional[str] = "(616) 555-0199"
    event_date: str = "Saturday, October 24, 2026"
    event_time: str = "5:00 PM - 11:30 PM"
    room_name: str = "Grand Ballroom (Noto's)"
    guest_count: int = 175
    menu_package: str = "Plated Filet Mignon & Chilean Sea Bass"
    bar_service: str = "Premium Open Bar with Cellar Master Reserve Wine Service"
    special_requests: Optional[str] = "Champagne toast upon arrival; 3 vegetarian & 2 gluten-free meals."
    subtotal: float = 14500.00
    service_charge: float = 2900.00
    tax: float = 870.00
    total: float = 18270.00
    deposit_paid: float = 5000.00
    balance_due: float = 13270.00


@router.post("/banquet/generate_beo")
async def generate_banquet_beo(req: BanquetBeoRequest):
    """Generates an official, styled Microsoft Word (.docx) Banquet Event Order (BEO) & Venue Contract."""
    try:
        doc = docx.Document()

        # Set 1-inch margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Header Title
        title_p = doc.add_heading("NOTO'S RESTAURANT & BANQUET CENTER", level=0)
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub_p = doc.add_paragraph("OFFICIAL BANQUET EVENT ORDER (BEO) & VENUE CONTRACT")
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_p.runs[0].bold = True

        address_p = doc.add_paragraph("6600 28th St SE, Grand Rapids, MI 49546 • Phone: (616) 493-6686 • www.notosoldworld.com")
        address_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph("______________________________________________________________________")

        # Section 1: Event & Client Details
        doc.add_heading("1. Event & Client Specifications", level=1)
        t1 = doc.add_table(rows=4, cols=2)
        t1.style = "Table Grid"
        
        t1.cell(0, 0).text = f"Event Name: {req.event_name}"
        t1.cell(0, 1).text = f"Client / Host: {req.client_name}"
        t1.cell(1, 0).text = f"Event Date: {req.event_date}"
        t1.cell(1, 1).text = f"Event Time: {req.event_time}"
        t1.cell(2, 0).text = f"Assigned Venue Space: {req.room_name}"
        t1.cell(2, 1).text = f"Guaranteed Guest Count: {req.guest_count} Guests"
        t1.cell(3, 0).text = f"Contact Email: {req.contact_email or 'N/A'}"
        t1.cell(3, 1).text = f"Contact Phone: {req.contact_phone or 'N/A'}"

        doc.add_paragraph("")

        # Section 2: Food, Beverage & Wine Program
        doc.add_heading("2. Culinary & Beverage Program", level=1)
        doc.add_paragraph(f"• Selected Menu Package: {req.menu_package}")
        doc.add_paragraph(f"• Beverage & Bar Service: {req.bar_service}")
        if req.special_requests:
            doc.add_paragraph(f"• Dietary & Special Instructions: {req.special_requests}")

        doc.add_paragraph("")

        # Section 3: Financial Summary & Billing Schedule
        doc.add_heading("3. Financial Summary & Deposit Schedule", level=1)
        t2 = doc.add_table(rows=7, cols=2)
        t2.style = "Table Grid"
        
        t2.cell(0, 0).text = "Itemized Description"
        t2.cell(0, 1).text = "Amount (USD)"
        t2.cell(1, 0).text = "Food & Beverage Subtotal"
        t2.cell(1, 1).text = f"${req.subtotal:,.2f}"
        t2.cell(2, 0).text = "Service Charge / Gratuity (20%)"
        t2.cell(2, 1).text = f"${req.service_charge:,.2f}"
        t2.cell(3, 0).text = "Applicable State Tax (6%)"
        t2.cell(3, 1).text = f"${req.tax:,.2f}"
        t2.cell(4, 0).text = "Total Estimated Master Contract"
        t2.cell(4, 1).text = f"${req.total:,.2f}"
        t2.cell(5, 0).text = "Deposit Received & Confirmed"
        t2.cell(5, 1).text = f"-${req.deposit_paid:,.2f}"
        t2.cell(6, 0).text = "Remaining Balance Due Prior to Event"
        t2.cell(6, 1).text = f"${req.balance_due:,.2f}"

        doc.add_paragraph("")

        # Section 4: Terms & Signatures
        doc.add_heading("4. Contract Authorization & Signature", level=1)
        doc.add_paragraph(
            "By signing below, the Client agrees to the room configuration, menu selections, and payment schedule outlined in this BEO. "
            "Guaranteed guest counts must be finalized 72 hours prior to the event date. Cancellations within 30 days are subject to standard venue policy."
        )

        doc.add_paragraph("\n\n____________________________________                ____________________________________")
        doc.add_paragraph("Client Signature (Authorized)                          Noto's Banquet Director Signature")
        doc.add_paragraph("Date: ________________________                         Date: ________________________")

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        clean_title = re.sub(r'[^\w\-_\. ]', '_', req.event_name)

        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="BEO_{clean_title}.docx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate BEO document: {str(e)}")

