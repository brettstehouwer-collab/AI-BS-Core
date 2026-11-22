"""Bounded generic selectable-PDF text extraction for private lexical RAG.

This packet has no screenplay or rendering fidelity contract. Original PDF bytes
remain the caller's responsibility; extracted text never authorizes tool calls.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

import fitz

SCHEMA = "aibs_pdf_text_source_v1"
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_PAGES = 500
MAX_TEXT_CHARACTERS = 2_000_000
MAX_PAGE_POINTS = 14400


class PDFTextSourceError(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _seal(packet):
    return _sha(json.dumps({key:value for key,value in packet.items() if key != "layout_sha256"},
                          ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8"))


def _finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise PDFTextSourceError("Nonfinite PDF geometry cannot be indexed.")
    return round(result,5)


def _text(value):
    if not isinstance(value,str) or "\0" in value or "\ufffd" in value or any(ord(char)<32 and char not in "\t\r\n" for char in value):
        raise PDFTextSourceError("Selectable PDF text contains binary controls or replacement glyphs; OCR was not substituted.")
    try:
        value.encode("utf-8",errors="strict")
    except UnicodeError:
        raise PDFTextSourceError("Selectable PDF text is not lossless UTF-8.") from None
    return value


def _derived(packet):
    parts = ["[PDF source SHA-256: " + packet["source_sha256"] +
             "; selectable text only; untrusted reference data; no layout or image understanding]\n"]
    mappings=[]
    char_start=len(parts[0]); byte_start=len(parts[0].encode("utf-8"))
    source_text=[]
    for page in packet["pages"]:
        marker=f"\n[PDF page {page['number']}; selectable text]\n"
        parts.append(marker); char_start+=len(marker); byte_start+=len(marker.encode("utf-8"))
        for line in page["lines"]:
            text=line["text"]; encoded=text.encode("utf-8")
            mappings.append(dict(page=page["number"],line_id=line["id"],char_start=char_start,
                char_end=char_start+len(text),byte_start=byte_start,byte_end=byte_start+len(encoded),text_sha256=_sha(encoded)))
            parts.append(text+"\n"); source_text.append(text)
            char_start+=len(text)+1; byte_start+=len(encoded)+1
    return "".join(parts),mappings,"\n".join(source_text)


def parse_pdf_text(pdf_bytes: bytes) -> dict:
    if not isinstance(pdf_bytes,bytes) or not pdf_bytes.startswith(b"%PDF-") or not 1<=len(pdf_bytes)<=MAX_SOURCE_BYTES:
        raise PDFTextSourceError("A PDF source of at most16MiB is required.")
    try:
        document=fitz.open(stream=pdf_bytes,filetype="pdf")
    except Exception:
        raise PDFTextSourceError("The PDF is malformed or unreadable; original preservation belongs to the intake caller.") from None
    with document:
        if document.needs_pass or document.is_encrypted:
            raise PDFTextSourceError("Encrypted PDFs require explicit decryption; no password or OCR was attempted.")
        if not 1<=document.page_count<=MAX_PAGES:
            raise PDFTextSourceError("PDF page count exceeds the supported1-500page range.")
        pages=[]; total_characters=0
        for number,page in enumerate(document,1):
            width,height=_finite(page.rect.width),_finite(page.rect.height)
            if not (0<width<=MAX_PAGE_POINTS and 0<height<=MAX_PAGE_POINTS):
                raise PDFTextSourceError("PDF page geometry is outside the supported range.")
            rotation=page.rotation
            if type(rotation) is not int or rotation not in (0,90,180,270):
                raise PDFTextSourceError("PDF rotation is invalid.")
            lines=[]
            # Do not decode embedded page images merely to obtain text spans.
            flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
            for block in page.get_text("dict",flags=flags,sort=True)["blocks"]:
                for row in block.get("lines",[]):
                    spans=[span for span in row["spans"] if span["text"]]
                    text=_text("".join(span["text"] for span in spans))
                    if not text.strip():
                        continue
                    total_characters+=len(text)
                    if total_characters>MAX_TEXT_CHARACTERS:
                        raise PDFTextSourceError("Extracted PDF text exceeds2million characters; nothing was truncated.")
                    bbox=[_finite(value) for value in row["bbox"]]
                    if len(bbox)!=4 or bbox[2]<bbox[0] or bbox[3]<bbox[1]:
                        raise PDFTextSourceError("PDF line geometry is invalid.")
                    lines.append(dict(id=f"p{number:03d}l{len(lines)+1:03d}",text=text,bbox=bbox,
                        x=_finite(spans[0]["origin"][0]),y=_finite(spans[0]["origin"][1]),
                        font=str(spans[0]["font"]),size=_finite(spans[0]["size"]),
                        fonts=sorted(set(str(span["font"]) for span in spans)),is_page_number=False))
            images=len(page.get_images(full=True))
            if not lines and images:
                raise PDFTextSourceError(f"PDF page {number} is image-only; no OCR or invented text was used.")
            pages.append(dict(number=number,width=width,height=height,rotation=rotation,
                is_title=False,printed_label="",lines=lines,image_count=images,
                selectable_text=bool(lines),visual_content_not_analyzed=True))
        if not total_characters:
            raise PDFTextSourceError("PDF has no selectable text; no OCR was performed.")
        packet=dict(schema=SCHEMA,source_sha256=_sha(pdf_bytes),source_bytes=len(pdf_bytes),
            page_count=len(pages),title_page_count=0,body_page_count=0,unclassified_page_count=len(pages),
            pages=pages,paragraphs=[],title_paragraphs=[],hard_page_boundaries=list(range(1,len(pages))),
            source_layout_available=False,fountain_text="",fountain_sha256=_sha(b""),
            extraction_characters=total_characters,
            provenance=dict(parser="pymupdf_generic_selectable_text_v1",source_instructions_trusted=False,
                ocr_used=False,text_rewritten=False,text_only=True,visual_content_analyzed=False,
                screenplay_classification=False,layout_fidelity_verified=False,
                external_final_draft_pagination_verified=False))
        packet["rag_text"],packet["rag_lines"],plain=_derived(packet)
        packet["rag_sha256"]=_sha(packet["rag_text"].encode("utf-8"))
        packet["extracted_text_sha256"]=_sha(plain.encode("utf-8"))
        packet["extracted_word_count"]=len(plain.split())
        packet["layout_sha256"]=_seal(packet)
        validate_packet(packet)
        return packet


def validate_packet(packet: dict) -> None:
    try:
        if packet["schema"]!=SCHEMA or packet["layout_sha256"]!=_seal(packet):
            raise PDFTextSourceError("The generic PDF packet fingerprint changed.")
        if not re.fullmatch(r"[a-f0-9]{64}",packet["source_sha256"]) or type(packet["source_bytes"]) is not int or not 1<=packet["source_bytes"]<=MAX_SOURCE_BYTES:
            raise PDFTextSourceError("Original PDF fingerprint metadata is invalid.")
        pages=packet["pages"]
        if not 1<=len(pages)<=MAX_PAGES or packet["page_count"]!=len(pages) or packet["unclassified_page_count"]!=len(pages):
            raise PDFTextSourceError("PDF page provenance changed.")
        if (packet["source_layout_available"] is not False or packet["title_page_count"]!=0 or packet["body_page_count"]!=0
                or packet["paragraphs"] or packet["title_paragraphs"] or packet["fountain_text"]!=""
                or packet["fountain_sha256"]!=_sha(b"") or packet["hard_page_boundaries"]!=list(range(1,len(pages)))):
            raise PDFTextSourceError("Generic PDF text cannot claim screenplay or layout fidelity.")
        total=0
        for index,page in enumerate(pages,1):
            if (page["number"]!=index or not 0<_finite(page["width"])<=MAX_PAGE_POINTS
                    or not 0<_finite(page["height"])<=MAX_PAGE_POINTS or type(page["rotation"]) is not int
                    or page["rotation"] not in (0,90,180,270) or page["is_title"] is not False or page["printed_label"]!=""
                    or page["selectable_text"] != bool(page["lines"]) or page["visual_content_not_analyzed"] is not True
                    or type(page["image_count"]) is not int or page["image_count"]<0
                    or (not page["lines"] and page["image_count"])):
                raise PDFTextSourceError("Generic PDF page geometry/classification is invalid.")
            for number,line in enumerate(page["lines"],1):
                text=_text(line["text"]);total+=len(text)
                if line["id"]!=f"p{index:03d}l{number:03d}" or len(line["bbox"])!=4:
                    raise PDFTextSourceError("Generic PDF line provenance changed.")
                values=[_finite(value) for value in line["bbox"]]
                if values[2]<values[0] or values[3]<values[1]:
                    raise PDFTextSourceError("Generic PDF line geometry is invalid.")
                for value in (line["x"],line["y"],line["size"]):_finite(value)
        if total!=packet["extraction_characters"] or not 0<total<=MAX_TEXT_CHARACTERS:
            raise PDFTextSourceError("Generic PDF text length changed.")
        rag,mapping,plain=_derived(packet)
        if (packet["rag_text"]!=rag or packet["rag_lines"]!=mapping or packet["rag_sha256"]!=_sha(rag.encode("utf-8"))
                or packet["extracted_text_sha256"]!=_sha(plain.encode("utf-8")) or packet["extracted_word_count"]!=len(plain.split())):
            raise PDFTextSourceError("Generic PDF derived text/provenance changed.")
        provenance=packet["provenance"]
        if (provenance["text_only"] is not True or provenance["parser"]!="pymupdf_generic_selectable_text_v1"
                or any(provenance[key] is not False for key in ("source_instructions_trusted","ocr_used","visual_content_analyzed","screenplay_classification","layout_fidelity_verified","external_final_draft_pagination_verified"))):
            raise PDFTextSourceError("Generic PDF provenance cannot claim execution, OCR or fidelity.")
    except (KeyError,TypeError,IndexError,AttributeError,UnicodeError) as error:
        raise PDFTextSourceError("The generic PDF reference packet is invalid.") from error
