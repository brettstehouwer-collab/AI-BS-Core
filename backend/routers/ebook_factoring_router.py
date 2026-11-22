"""
eBook Factoring & PDF Stream Router for Stehouwer Publishing LLC
Exposes endpoints for:
- POST /api/v1/publishing/ebook/convert
- POST /api/v1/publishing/pdf/optimize
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.ebook_factoring_engine import EbookFactoringEngine

router = APIRouter(prefix="/api/v1/publishing", tags=["Publishing Factoring"])


class EbookConvertRequest(BaseModel):
    input_text_or_path: str = Field(..., description="Markdown, raw text, or path to HTML/DOCX file")
    to_format: str = Field(default="epub", description="'epub', 'mobi', 'azw3', or 'pdf'")
    title: str = Field(default="Stehouwer Publishing Publication", description="Book/Document Title")
    author: str = Field(default="Brett Stehouwer", description="Author Name")
    device_profile: str = Field(default="kindle_pw", description="'kindle_pw', 'kobo', 'ipad', 'generic_eink'")
    cover_image_path: Optional[str] = Field(default=None, description="Optional path to cover image")
    output_filename: Optional[str] = Field(default=None, description="Optional output filename")


class PdfOptimizeRequest(BaseModel):
    pdf_path: str = Field(..., description="Path to input PDF file on host")
    watermark_text: Optional[str] = Field(default=None, description="Optional watermark text")
    linearize: bool = Field(default=True, description="Enable Fast Web View linearization")
    output_filename: Optional[str] = Field(default=None, description="Optional output filename")


@router.post("/ebook/convert")
async def convert_ebook_endpoint(req: EbookConvertRequest):
    try:
        res = EbookFactoringEngine.convert_ebook(
            input_text_or_path=req.input_text_or_path,
            to_format=req.to_format,
            title=req.title,
            author=req.author,
            device_profile=req.device_profile,
            cover_image_path=req.cover_image_path,
            output_filename=req.output_filename
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf/optimize")
async def optimize_pdf_endpoint(req: PdfOptimizeRequest):
    try:
        res = EbookFactoringEngine.optimize_pdf_stream(
            pdf_path=req.pdf_path,
            watermark_text=req.watermark_text,
            linearize=req.linearize,
            output_filename=req.output_filename
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
