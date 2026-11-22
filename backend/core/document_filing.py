"""Persist a PDF copy of editor text, optionally with a drawn signature mark.

This module does not apply a certificate or authenticate a signer's identity.
"""

import base64
import hashlib
import io
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

from fastapi import HTTPException

_FONT_LOCK = threading.Lock()


def _signature_png(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith('data:image/png;base64,'):
        raise HTTPException(400, 'Signature must be a PNG image.')
    if len(value) > 3_000_000:
        raise HTTPException(413, 'Signature image is too large.')
    try:
        from PIL import Image
        raw = base64.b64decode(value.split(',', 1)[1], validate=True)
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != 'PNG' or max(image.size) > 2048:
                raise ValueError('Invalid signature dimensions or format')
            image = image.convert('RGBA')
            alpha = image.getchannel('A')
            bounds = alpha.getbbox()
            if bounds is None:
                raise ValueError('Empty signature')
            # Normalize legacy light canvas ink for legibility on the white PDF.
            ink = Image.new('RGBA', image.size, (0, 0, 0, 0))
            ink.putalpha(alpha)
            ink = ink.crop(bounds)
            result = io.BytesIO()
            ink.save(result, format='PNG')
            return result.getvalue()
    except Exception:
        raise HTTPException(422, 'Draw a signature first, or choose File without signature.')


def _document_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    name = 'AIBSDocumentArial'
    with _FONT_LOCK:
        if name not in pdfmetrics.getRegisteredFontNames():
            candidates = [Path('C:/Windows/Fonts/arial.ttf'),
                          Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
            font_path = next((p for p in candidates if p.is_file()), None)
            if font_path is None:
                raise HTTPException(503, 'A Unicode document font must be installed before filing PDFs.')
            pdfmetrics.registerFont(TTFont(name, str(font_path)))
    return name


def file_document_pdf(root: Path, filename: str, content: str, signature_image=None):
    if (not isinstance(filename, str) or not filename.strip() or len(filename) > 240
            or any(c in filename for c in '<>:"/\\|?*') or any(ord(c) < 32 for c in filename)):
        raise HTTPException(400, 'A document filename without directory components is required.')
    if not isinstance(content, str):
        raise HTTPException(400, 'Document content must be text.')
    if len(content) > 1_000_000:
        raise HTTPException(413, 'Document is too large to file in one request.')
    signature = _signature_png(signature_image)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether

    font = _document_font()
    supported = pdfmetrics.getFont(font).face.charToGlyph
    if any(ord(c) not in supported and c not in '\n\r\t' for c in content + filename):
        raise HTTPException(422, 'The document contains characters unsupported by the installed PDF font. The original is unchanged.')
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    style = ParagraphStyle('DocumentText', fontName=font, fontSize=11, leading=15,
                           spaceAfter=6, splitLongWords=True)
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=(612, 792), leftMargin=54, rightMargin=54,
                            topMargin=54, bottomMargin=54, title=filename,
                            author='AI-BS document export')
    story = []
    for line in content.expandtabs(4).splitlines():
        story.append(Paragraph(escape(line) if line.strip() else '&#160;', style))
    receipt = [Spacer(1, 16), Paragraph(f'Filed at {timestamp}', style),
               Paragraph('Drawn signature mark attached.' if signature else 'Filed without a signature.', style),
               Paragraph('Certificate-based digital signature: not applied', style)]
    if signature:
        mark = Image(io.BytesIO(signature))
        scale = min(220 / mark.imageWidth, 100 / mark.imageHeight, 1)
        mark.drawWidth = mark.imageWidth * scale
        mark.drawHeight = mark.imageHeight * scale
        mark.hAlign = 'LEFT'
        receipt.append(mark)
    story.append(KeepTogether(receipt))
    pdf.build(story)
    data = buffer.getvalue()

    root = Path(root).resolve()
    directory = (root / 'Documents' / 'Filed').resolve()
    if not directory.is_relative_to(root):
        raise HTTPException(403, 'Filed documents must stay inside the shared drive.')
    directory.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem.strip(' .')[:80] or 'document'
    target = directory / f'{stem}_filed_{uuid4().hex}.pdf'
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.document-', suffix='.tmp', delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
        # Create-only publication keeps an existing file intact even on a name collision.
        os.link(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {'status': 'success', 'path': str(target), 'filename': target.name,
            'media_type': 'application/pdf', 'sha256': hashlib.sha256(data).hexdigest(),
            'filed_at': timestamp, 'signature_type': 'drawn_mark' if signature else 'none',
            'cryptographically_signed': False}
