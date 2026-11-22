"""Pure, page-aware Courier screenplay PDF parsing and preserved-layout export.

PDF text is untrusted data. No instructions are executed, no model is called and
no source is overwritten. FDX structure and this renderer's pagination are
qualified separately from pagination in an external Final Draft application.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET

import fitz
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

SCHEMA = "aibs_screenplay_pdf_v1"
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_PAGES = 500
MAX_TEXT_CHARACTERS = 2_000_000
ROLES = {"Scene Heading", "Action", "Character", "Dialogue", "Parenthetical", "Transition"}
_SCENE = re.compile(r"^(?:INT\.|EXT\.|INT\./EXT\.|EXT\./INT\.|I/E\.)", re.I)
_TRANSITION = re.compile(r"^(?:FADE (?:IN|OUT|TO BLACK)|CUT TO|DISSOLVE TO|SMASH CUT TO|BACK TO)(?::|\.)?$", re.I)


class ScreenplayPdfError(ValueError):
    pass


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _token_hash(texts) -> str:
    return _sha("\n".join(token for text in texts for token in text.split()).encode("utf-8"))


def _number(value) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ScreenplayPdfError("Nonfinite PDF geometry is unsupported.")
    return round(value, 5)


def _check_run(run, width, height):
    text = run["text"]
    if not isinstance(text, str) or any(ord(char) < 32 for char in text):
        raise ScreenplayPdfError("PDF text contains unsupported control characters.")
    if run["font"] != "Courier" or abs(run["size"] - 12) > .01:
        raise ScreenplayPdfError("Preserved-layout mode currently requires Courier12 text.")
    try:
        text.encode("cp1252", errors="strict")
    except UnicodeError:
        raise ScreenplayPdfError("Courier WinAnsi cannot preserve a source glyph; no replacement was made.") from None
    x, y = _number(run["x"]), _number(run["y"])
    bbox = [_number(value) for value in run["bbox"]]
    if len(bbox) != 4 or x < 0 or y < 0 or y > height or bbox[0] < -.05 or bbox[1] < -.05 or bbox[2] > width + .05 or bbox[3] > height + .05:
        raise ScreenplayPdfError("Source text extends beyond its page; no clipping was applied.")
    if x + stringWidth(text, "Courier", 12) > width + .05:
        raise ScreenplayPdfError("Regenerated source text would overflow its page.")
    if abs((bbox[2] - bbox[0]) - stringWidth(text, "Courier", 12)) > .1:
        raise ScreenplayPdfError("Source character spacing is unsupported; no reflow was substituted.")


def _role(line):
    x, text = line["x"], line["text"].strip()
    if abs(x - 270.24) < 1:
        return "Character"
    if abs(x - 229.2) < 1:
        return "Parenthetical"
    if abs(x - 186) < 1:
        return "Dialogue"
    if _SCENE.match(text):
        return "Scene Heading"
    if x > 420 and _TRANSITION.fullmatch(text):
        return "Transition"
    return "Action"


def _paragraphs(pages):
    body, titles = [], []
    body_pages = [page["number"] for page in pages if not page["is_title"]]
    first_body = body_pages[0] if body_pages else None
    for page in pages:
        if page["is_title"]:
            for line in page["lines"]:
                titles.append(dict(type="Action", text=line["text"], page=page["number"],
                                   starts_new_page=False, alignment="Center", line_ids=[line["id"]]))
            continue
        current = None
        first_on_page = True
        for line in page["lines"]:
            if line["is_page_number"]:
                continue
            kind = line["role"]
            alignment = "Right" if line["x"] > 420 else "Left"
            can_join = current is not None and alignment == current["alignment"] and (
                (kind == current["type"] and kind in {"Action", "Parenthetical"}
                 and abs(line["y"] - current["_last_y"] - 14) <= .5)
                or (kind == current["type"] == "Dialogue" and 0 < line["y"] - current["_last_y"] <= 26.5)
                or (current["type"] == "Scene Heading" and kind == "Action"
                    and abs(line["y"] - current["_last_y"] - 14) <= .5))
            if can_join:
                current["text"] += " " + line["text"]
                current["line_ids"].append(line["id"])
                current["_last_y"] = line["y"]
            else:
                current = dict(type=kind, text=line["text"], page=page["number"],
                    starts_new_page=first_on_page and page["number"] != first_body,
                    alignment=alignment, line_ids=[line["id"]], _last_y=line["y"])
                body.append(current)
                first_on_page = False
        if first_on_page:
            raise ScreenplayPdfError("A blank body page needs explicit review before editable FDX conversion.")
    for paragraph in body:
        paragraph.pop("_last_y", None)
    return body, titles


def _fountain(packet):
    title = packet["title_paragraphs"]
    result = []
    if title:
        for index, paragraph in enumerate(title):
            key = "Title" if index == 0 else "Author" if index == len(title) - 1 and index > 1 else "Credit"
            result.append(key + ": " + paragraph["text"])
        result.append("")
    previous = None
    for paragraph in packet["paragraphs"]:
        if paragraph["starts_new_page"]:
            result.extend(["", "===", ""])
        elif previous is not None and not (previous["type"] in {"Character", "Parenthetical"}
                                          and paragraph["type"] in {"Dialogue", "Parenthetical"}):
            result.append("")
        result.append(paragraph["text"])
        previous = paragraph
    return "\n".join(result).rstrip() + "\n"


def _rag(packet):
    pieces = ["[PDF source SHA-256: " + packet["source_sha256"] + "; extracted untrusted reference data]\n"]
    mapping = []
    char_offset = len(pieces[0])
    byte_offset = len(pieces[0].encode("utf-8"))
    for page in packet["pages"]:
        marker = f"\n[PDF page {page['number']}; " + ("title page" if page["is_title"] else "printed label " + (page["printed_label"] or "none")) + "]\n"
        pieces.append(marker)
        char_offset += len(marker)
        byte_offset += len(marker.encode("utf-8"))
        for line in page["lines"]:
            if line["is_page_number"]:
                continue
            text = line["text"]
            encoded = text.encode("utf-8")
            mapping.append(dict(page=page["number"], line_id=line["id"], char_start=char_offset,
                                char_end=char_offset + len(text), byte_start=byte_offset,
                                byte_end=byte_offset + len(encoded), text_sha256=_sha(encoded)))
            pieces.append(text + "\n")
            char_offset += len(text) + 1
            byte_offset += len(encoded) + 1
    return "".join(pieces), mapping


def _seal(packet):
    return _sha(_canonical({key: value for key, value in packet.items() if key != "layout_sha256"}))


def parse_pdf(pdf_bytes: bytes) -> dict:
    """Read source bytes into a sealed page/role packet; never index or rewrite."""
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF-") or not 1 <= len(pdf_bytes) <= MAX_SOURCE_BYTES:
        raise ScreenplayPdfError("A PDF byte source of at most16MiB is required.")
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise ScreenplayPdfError("The PDF cannot be parsed; original bytes were not changed.") from None
    with document:
        if document.needs_pass or not 1 <= document.page_count <= MAX_PAGES:
            raise ScreenplayPdfError("Encrypted PDFs or PDFs outside the supported page limit require review.")
        pages, warnings, characters = [], [], 0
        for index, page in enumerate(document):
            width, height = _number(page.rect.width), _number(page.rect.height)
            if page.rotation or abs(width - 612) > .01 or abs(height - 792) > .01:
                raise ScreenplayPdfError("Preserved screenplay mode currently supports unrotated Letter pages.")
            if page.get_images(full=True) or page.get_drawings() or page.first_annot or page.get_links():
                raise ScreenplayPdfError("Images, drawings, annotations or links need a different preservation path.")
            if any(trace.get("type", 0) != 0 or abs(trace.get("opacity", 1) - 1) > .001
                   for trace in page.get_texttrace()):
                raise ScreenplayPdfError("Invisible, stroked or translucent source text requires review.")
            lines = []
            for block in page.get_text("dict", sort=True)["blocks"]:
                for item in block.get("lines", []):
                    if item.get("dir") != (1.0, 0.0) or item.get("wmode", 0):
                        raise ScreenplayPdfError("Rotated or vertical text is unsupported.")
                    runs = []
                    for span in item["spans"]:
                        if not span["text"]:
                            continue
                        run = dict(text=span["text"], x=_number(span["origin"][0]),
                            y=_number(span["origin"][1]), bbox=[_number(v) for v in span["bbox"]],
                            font=span["font"], size=_number(span["size"]))
                        if span.get("color", 0) != 0 or span.get("alpha", 255) != 255:
                            raise ScreenplayPdfError("Nonblack or translucent source text is unsupported in preserved mode.")
                        _check_run(run, width, height)
                        runs.append(run)
                    text = "".join(run["text"] for run in runs)
                    if not text.strip():
                        continue
                    characters += len(text)
                    if characters > MAX_TEXT_CHARACTERS:
                        raise ScreenplayPdfError("The extracted source text exceeds the supported limit.")
                    line = dict(id=f"p{index + 1:03d}l{len(lines) + 1:03d}", text=text,
                        x=runs[0]["x"], y=runs[0]["y"], bbox=[_number(v) for v in item["bbox"]],
                        font="Courier", size=12, runs=runs,
                        is_page_number=bool(runs[0]["y"] <= 45 and re.fullmatch(r"\d{1,4}\.?", text.strip())))
                    line["role"] = _role(line)
                    lines.append(line)
            if not lines:
                raise ScreenplayPdfError("A page has no selectable source text; OCR was not substituted.")
            labels = [line["text"].strip() for line in lines if line["is_page_number"]]
            if len(labels) > 1:
                raise ScreenplayPdfError("Ambiguous page-number labels require review.")
            title = index == 0 and not labels and len(lines) <= 12 and min(line["y"] for line in lines) > 100
            if title:
                for line in lines:
                    line["role"] = "Action"
            for line in lines:
                if not title and len(line["text"].strip()) == 1 and not line["text"].strip().isalnum():
                    warnings.append(dict(page=index + 1, line_id=line["id"], kind="single_punctuation_line_preserved"))
            pages.append(dict(number=index + 1, width=width, height=height, is_title=title,
                              printed_label=labels[0] if labels else "", lines=lines))
        body, titles = _paragraphs(pages)
        full = [line["text"] for page in pages for line in page["lines"]]
        body_text = [line["text"] for page in pages if not page["is_title"]
                     for line in page["lines"] if not line["is_page_number"]]
        packet = dict(schema=SCHEMA, source_sha256=_sha(pdf_bytes), source_bytes=len(pdf_bytes),
            page_count=len(pages), title_page_count=sum(page["is_title"] for page in pages),
            body_page_count=sum(not page["is_title"] for page in pages), pages=pages,
            paragraphs=body, title_paragraphs=titles, hard_page_boundaries=list(range(1, len(pages))),
            body_token_sha256=_token_hash(body_text), full_token_sha256=_token_hash(full),
            body_word_count=sum(len(text.split()) for text in body_text),
            full_word_count=sum(len(text.split()) for text in full), warnings=warnings,
            provenance=dict(parser="pymupdf_selectable_text_v1", source_instructions_trusted=False,
                ocr_used=False, text_rewritten=False, layout_mode="source_geometry",
                external_final_draft_pagination_verified=False))
        packet["rag_text"], packet["rag_lines"] = _rag(packet)
        packet["rag_sha256"] = _sha(packet["rag_text"].encode("utf-8"))
        packet["fountain_text"] = _fountain(packet)
        packet["fountain_sha256"] = _sha(packet["fountain_text"].encode("utf-8"))
        packet["layout_sha256"] = _seal(packet)
        validate_packet(packet)
        return packet


def validate_packet(packet: dict) -> None:
    """Reject changed rendering/derived fields; the server must also verify ownership."""
    try:
        if packet["schema"] != SCHEMA or packet["layout_sha256"] != _seal(packet):
            raise ScreenplayPdfError("The preserved layout fingerprint changed.")
        if not re.fullmatch(r"[a-f0-9]{64}", packet["source_sha256"]):
            raise ScreenplayPdfError("The source fingerprint is invalid.")
        pages = packet["pages"]
        if packet["page_count"] != len(pages) or packet["hard_page_boundaries"] != list(range(1, len(pages))):
            raise ScreenplayPdfError("The source page boundary map changed.")
        if (not 1 <= len(pages) <= MAX_PAGES or packet["title_page_count"] != sum(page["is_title"] for page in pages)
                or packet["body_page_count"] != sum(not page["is_title"] for page in pages)
                or sum(page["is_title"] for page in pages) > 1
                or any(page["is_title"] for page in pages[1:])):
            raise ScreenplayPdfError("Title/script page counts disagree with source geometry.")
        if type(packet["source_bytes"]) is not int or not 1 <= packet["source_bytes"] <= MAX_SOURCE_BYTES:
            raise ScreenplayPdfError("The source byte count is invalid.")
        for index, page in enumerate(pages, 1):
            if page["number"] != index or page["width"] != 612 or page["height"] != 792:
                raise ScreenplayPdfError("The source page geometry changed.")
            for line in page["lines"]:
                if line["text"] != "".join(run["text"] for run in line["runs"]):
                    raise ScreenplayPdfError("Source line/run text disagrees.")
                if (not line["runs"] or line["x"] != line["runs"][0]["x"] or line["y"] != line["runs"][0]["y"]
                        or line["role"] != ("Action" if page["is_title"] else _role(line))
                        or line["is_page_number"] != bool(line["y"] <= 45 and re.fullmatch(r"\d{1,4}\.?", line["text"].strip()))):
                    raise ScreenplayPdfError("Source line identity, role or page-number flags changed.")
                for run in line["runs"]:
                    _check_run(run, page["width"], page["height"])
            labels = [line["text"].strip() for line in page["lines"] if line["is_page_number"]]
            if len(labels) > 1 or page["printed_label"] != (labels[0] if labels else ""):
                raise ScreenplayPdfError("The printed page-label map changed.")
        body, title = _paragraphs(pages)
        if packet["paragraphs"] != body or packet["title_paragraphs"] != title:
            raise ScreenplayPdfError("The logical paragraph map changed.")
        body_text = [line["text"] for page in pages if not page["is_title"]
                     for line in page["lines"] if not line["is_page_number"]]
        if packet["body_token_sha256"] != _token_hash(body_text) or _token_hash(p["text"] for p in body) != packet["body_token_sha256"]:
            raise ScreenplayPdfError("The ordered screenplay words changed.")
        if packet["body_word_count"] != sum(len(text.split()) for text in body_text):
            raise ScreenplayPdfError("The screenplay word count changed.")
        if packet["full_token_sha256"] != _token_hash(line["text"] for page in pages for line in page["lines"]):
            raise ScreenplayPdfError("The complete source word fingerprint changed.")
        if packet["full_word_count"] != sum(len(line["text"].split()) for page in pages for line in page["lines"]):
            raise ScreenplayPdfError("The complete source word count changed.")
        rag_text, rag_lines = _rag(packet)
        if (packet["rag_text"] != rag_text or packet["rag_lines"] != rag_lines
                or packet["rag_sha256"] != _sha(rag_text.encode("utf-8"))
                or packet["fountain_text"] != _fountain(packet)
                or packet["fountain_sha256"] != _sha(packet["fountain_text"].encode("utf-8"))):
            raise ScreenplayPdfError("Derived reference/editable text changed.")
    except (KeyError, TypeError, IndexError, AttributeError, UnicodeError) as error:
        raise ScreenplayPdfError("The preserved screenplay packet is invalid.") from error


def to_fountain(packet: dict) -> str:
    validate_packet(packet)
    return packet["fountain_text"]


def validate_unchanged_fountain(packet: dict, canonical_text: str) -> None:
    """Only unchanged editor content may use the source-layout export mode."""
    validate_packet(packet)
    if (not isinstance(canonical_text, str) or canonical_text != packet["fountain_text"]
            or _sha(canonical_text.encode("utf-8")) != packet["fountain_sha256"]):
        raise ScreenplayPdfError("Edited screenplay requires an explicit reflow export; original source layout remains preserved.")


def to_fdx(packet: dict) -> bytes:
    """Emit standard FDX structure; source geometry stays in the validated sidecar."""
    validate_packet(packet)
    root = ET.Element("FinalDraft", DocumentType="Script", Template="No", Version="1")
    for role in sorted(ROLES):
        setting = ET.SubElement(root, "ElementSettings", Type=role)
        ET.SubElement(setting, "FontSpec", Font="Courier", Size="12", Style="")
        left = {"Character": "3.753333", "Dialogue": "2.583333", "Parenthetical": "3.183333",
                "Transition": "5.5"}.get(role, "1.583333")
        right = {"Dialogue": "6.5", "Parenthetical": "5.5"}.get(role, "7.5")
        ET.SubElement(setting, "ParagraphSpec", Alignment="Right" if role == "Transition" else "Left",
            FirstIndent="0", LeftIndent=left, RightIndent=right,
            SpaceBefore="0" if role in {"Dialogue", "Parenthetical"} else "12",
            Spacing="1", StartsNewPage="No")
        return_key, tab_key = {
            "Scene Heading": ("Action", "Action"), "Action": ("Action", "Character"),
            "Character": ("Dialogue", "Transition"), "Parenthetical": ("Dialogue", "Dialogue"),
            "Dialogue": ("Action", "Parenthetical"), "Transition": ("Scene Heading", "Scene Heading")
        }[role]
        ET.SubElement(setting, "Behavior", PaginateAs=role, ReturnKey=return_key, TabKey=tab_key)
    content = ET.SubElement(root, "Content")
    for paragraph in packet["paragraphs"]:
        attributes = dict(Type=paragraph["type"], Alignment=paragraph["alignment"])
        if paragraph["starts_new_page"]:
            attributes["StartsNewPage"] = "Yes"
        element = ET.SubElement(content, "Paragraph", attributes)
        ET.SubElement(element, "Text", Font="Courier", Size="12").text = paragraph["text"]
    if packet["title_paragraphs"]:
        title = ET.SubElement(ET.SubElement(root, "TitlePage"), "Content")
        for paragraph in packet["title_paragraphs"]:
            element = ET.SubElement(title, "Paragraph", Type="Action", Alignment="Center")
            ET.SubElement(element, "Text", Font="Courier", Size="12").text = paragraph["text"]
    labels = [page["printed_label"] for page in packet["pages"] if not page["is_title"]]
    numbers = [int(label.rstrip(".")) for label in labels if re.fullmatch(r"\d{1,4}\.?", label)]
    contiguous = bool(numbers) and len(numbers) == len(labels) and numbers == list(range(numbers[0], numbers[0] + len(numbers)))
    header = ET.SubElement(root, "HeaderAndFooter", StartingPage=str(numbers[0]) if contiguous else "1",
                           HeaderFirstPage="Yes", HeaderVisible="Yes", FooterFirstPage="Yes", FooterVisible="No")
    paragraph = ET.SubElement(ET.SubElement(header, "Header"), "Paragraph", Alignment="Left",
        FirstIndent="0.00", Leading="Regular", LeftIndent="1.25", OutlineLevel="1",
        RightIndent="-1.00", SpaceBefore="0", Spacing="1", StartsNewPage="No")
    ET.SubElement(paragraph, "Text", Font="Courier", Size="12", Style="").text = "\t"
    ET.SubElement(paragraph, "DynamicLabel", Font="Courier", Size="12", Style="", Type="Page #")
    ET.SubElement(paragraph, "Text", Font="Courier", Size="12", Style="").text = "."
    ET.SubElement(ET.SubElement(paragraph, "Tabstops"), "Tabstop", Position="7.25", Type="Right")
    continueds = ET.SubElement(root, "MoresAndContinueds")
    ET.SubElement(continueds, "FontSpec", Font="Courier", Size="12", Style="")
    ET.SubElement(continueds, "DialogueBreaks", AutomaticCharacterContinueds="No", BottomOfPage="No",
        DialogueBottom="(MORE)", DialogueTop="(CONT'D)", TopOfNext="No")
    ET.SubElement(continueds, "SceneBreaks", ContinuedNumber="No", SceneBottom="(CONTINUED)",
        SceneBottomOfPage="No", SceneTop="CONTINUED:", SceneTopOfNext="No")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def to_preserved_pdf(packet: dict) -> bytes:
    """Regenerate vector text at validated source positions, without source PDF copying."""
    validate_packet(packet)
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792), pageCompression=1, invariant=1)
    canvas.setCreator("AI-BS source-layout screenplay renderer")
    canvas.setTitle("Preserved source-layout screenplay")
    for page in packet["pages"]:
        canvas.setPageSize((page["width"], page["height"]))
        canvas.setFillColorRGB(0, 0, 0)
        for line in page["lines"]:
            for run in line["runs"]:
                canvas.setFont("Courier", run["size"])
                canvas.drawString(run["x"], page["height"] - run["y"], run["text"])
        canvas.showPage()
    canvas.save()
    generated = output.getvalue()
    # Reopen the generated bytes; a write success alone is not qualification.
    recovered = parse_pdf(generated)
    if (recovered["page_count"] != packet["page_count"]
            or recovered["full_token_sha256"] != packet["full_token_sha256"]
            or recovered["body_token_sha256"] != packet["body_token_sha256"]):
        raise ScreenplayPdfError("Regenerated PDF page/text readback did not match.")
    return generated
