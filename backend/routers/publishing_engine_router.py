import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.typst_pandoc_engine import TypstPandocEngine, OUTPUT_DIR

router = APIRouter(prefix="/api/v1/publishing", tags=["Stehouwer Publishing"])


class TypstCompileRequest(BaseModel):
    markup_text: str = Field(..., description="Typst markup text or raw manuscript content")
    title: Optional[str] = Field("Stehouwer Publishing Contract", description="Document title")
    author: Optional[str] = Field("Brett Stehouwer", description="Author or publisher name")
    trim_size: Optional[str] = Field("6x9", description="KDP trim size: '6x9', '8.5x11', '5.5x8.5', 'a4'")
    output_filename: Optional[str] = Field(None, description="Optional custom output filename")


class KdpManuscriptRequest(BaseModel):
    title: str
    author: str
    chapters: List[Dict[str, str]]
    subtitle: Optional[str] = None
    trim_size: Optional[str] = "6x9"
    isbn: Optional[str] = None


class PandocConvertRequest(BaseModel):
    input_text: str
    from_format: str = "markdown"
    to_format: str = "typst"


@router.post("/typst/compile")
async def compile_typst_endpoint(req: TypstCompileRequest):
    """
    Sub-50ms Typst PDF compilation endpoint for Stehouwer Publishing LLC.
    """
    try:
        out_path = os.path.join(OUTPUT_DIR, req.output_filename) if req.output_filename else None
        res = TypstPandocEngine.compile_typst(
            markup_text=req.markup_text,
            output_pdf_path=out_path,
            title=req.title,
            author=req.author,
            trim_size=req.trim_size
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kdp-manuscript")
async def generate_kdp_endpoint(req: KdpManuscriptRequest):
    """
    Formats structured manuscript chapters into a publication-ready KDP interior PDF.
    """
    try:
        res = TypstPandocEngine.generate_kdp_manuscript(
            title=req.title,
            author=req.author,
            chapters=req.chapters,
            subtitle=req.subtitle,
            trim_size=req.trim_size,
            isbn=req.isbn
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pandoc/convert")
async def convert_pandoc_endpoint(req: PandocConvertRequest):
    """
    Converts raw text/markdown to Typst/LaTeX/Docx/HTML via Pandoc.
    """
    try:
        res = TypstPandocEngine.convert_pandoc(
            input_text=req.input_text,
            from_format=req.from_format,
            to_format=req.to_format
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_published_pdf(filename: str):
    """
    Serves generated publication PDFs directly.
    """
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Publication file not found.")
    return FileResponse(file_path, media_type="application/pdf", filename=safe_name)


@router.get("/templates")
async def list_publishing_templates():
    """
    Returns available KDP trim sizes and publication presets.
    """
    return {
        "presets": [
            {"name": "Trade Paperback (6x9)", "trim": "6x9", "margins": "0.75in inside, 0.5in outside", "use": "Novels, Non-Fiction"},
            {"name": "Workbook / Manual (8.5x11)", "trim": "8.5x11", "margins": "0.8in inside, 0.6in outside", "use": "Technical Manuals, Guides"},
            {"name": "Digest Pocket (5.5x8.5)", "trim": "5.5x8.5", "margins": "0.7in inside, 0.5in outside", "use": "Pocket Books, Short Works"},
            {"name": "International Standard (A4)", "trim": "a4", "margins": "2cm inside, 1.5cm outside", "use": "Corporate Reports, NDAs"}
        ]
    }
