"""Separate, deterministic US spec-screenplay reflow; never changes archival output.

Input text is untrusted data, not instructions. This profile uses public Courier
and inspected FD13 template positions, not proprietary fonts or a claimed XSD.
Internal PDF and Final Draft pagination are independently qualified.
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

from core.screenplay_pdf import validate_packet

PROFILE_ID = "us-spec-courier12-v1"
RENDERER_ID = "aibs_professional_courier12_v1"
FDX_RENDERER_ID = "aibs_professional_fdx_v1"
PDF_RENDERER_ID = "aibs_reportlab_professional_pdf_v1"
# Left/right are absolute inch positions; FirstIndent is relative to LeftIndent.
_STYLES = {
    "Scene Heading": ("1.50", "7.50", "0.00", "24", "Left", "Action", "Action"),
    "Action": ("1.50", "7.50", "0.00", "12", "Left", "Action", "Character"),
    "Character": ("3.50", "7.25", "0.00", "12", "Left", "Dialogue", "Transition"),
    "Parenthetical": ("3.00", "5.50", "-0.10", "0", "Left", "Dialogue", "Dialogue"),
    "Dialogue": ("2.50", "6.00", "0.00", "0", "Left", "Action", "Parenthetical"),
    "Transition": ("5.50", "7.10", "0.00", "12", "Right", "Scene Heading", "Scene Heading"),
}
_LEADING = 12.0
_FIRST_BASELINE = 84.0
_LAST_BASELINE = 708.0
_MAX_OUTPUT_PAGES = 1000


class ProfessionalScreenplayError(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _tokens_hash(rows):
    return _sha("\n".join(word for row in rows for word in row.split()).encode("utf-8"))


def _role_hash(paragraphs):
    pairs = [[row["type"], word] for row in paragraphs for word in row["text"].split()]
    return _sha(json.dumps(pairs, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _logical_paragraphs(packet):
    """Join only adjacent same-role physical-boundary fragments with evidence.

    This is an explicit inference, retained in diagnostics. A speaker cannot be
    inherited through Action, a scene, a transition or a different Character.
    """
    by_id = {line["id"]: line for page in packet["pages"] for line in page["lines"]}
    result, diagnostics = [], []
    speaker = None
    previous = None
    joins = 0
    for index, source in enumerate(packet["paragraphs"]):
        role = source["type"]
        if role == "Character":
            speaker = index
        elif role not in {"Dialogue", "Parenthetical"}:
            speaker = None
        row = dict(type=role, text=source["text"], source_indices=[index],
                   source_pages=[source["page"]], line_ids=list(source["line_ids"]),
                   speaker_index=speaker if role in {"Dialogue", "Parenthetical"} else None)
        if role == "Dialogue" and speaker is None:
            diagnostics.append(dict(kind="dialogue_speaker_unresolved", source_indices=[index],
                                    source_pages=[source["page"]], decision="retain_without_inventing_character"))
        compatible = (previous is not None and source["starts_new_page"]
                      and source["page"] == previous["page"] + 1
                      and previous["type"] == role and role in {"Action", "Dialogue", "Parenthetical"})
        if compatible:
            last = by_id[previous["line_ids"][-1]]
            first = by_id[source["line_ids"][0]]
            first_alpha = next((char for char in source["text"] if char.isalpha()), "")
            geometry = last["y"] >= 672 and first["y"] <= 100 and abs(last["x"]-first["x"]) <= 1
            continuity = not re.search(r"[.!?;:][\"')\]]*$", previous["text"].rstrip()) and first_alpha.islower()
            speaker_evidence = role == "Action" or (speaker is not None and result[-1]["speaker_index"] == speaker)
            if geometry and continuity and speaker_evidence:
                target = result[-1]
                target["text"] += " " + row["text"]
                target["source_indices"].append(index)
                target["source_pages"].append(source["page"])
                target["line_ids"].extend(row["line_ids"])
                joins += 1
                diagnostics.append(dict(kind="pdf_boundary_join_inferred", role=role,
                    source_indices=[index-1, index], source_pages=[previous["page"], source["page"]],
                    line_ids=[last["id"], first["id"]],
                    evidence=["adjacent_same_role", "bottom_top_geometry", "same_column",
                              "nonterminal_then_lowercase"] + ([] if role == "Action" else ["direct_character_context"])))
                previous = source
                continue
            diagnostics.append(dict(kind="ambiguous_pdf_boundary_retained", role=role,
                source_indices=[index-1, index], source_pages=[previous["page"], source["page"]],
                line_ids=[last["id"], first["id"]], decision="retain_separate_paragraphs",
                geometry_evidence=geometry, continuation_evidence=continuity, speaker_evidence=speaker_evidence))
        result.append(row)
        previous = source
    if not result:
        raise ProfessionalScreenplayError("Professional export needs authored body text.")
    if (_tokens_hash(row["text"] for row in result) != packet["body_token_sha256"]
            or _role_hash(result) != _role_hash(packet["paragraphs"])):
        raise ProfessionalScreenplayError("Professional reconstruction changed authored words or roles.")
    return result, diagnostics, joins


def _wrap(text, role):
    """Whitespace-only wrapping; never dehyphenate, rewrite or split a word."""
    left, right, indent, *_ = _STYLES[role]
    left, right, indent = float(left)*72, float(right)*72, float(indent)*72
    result, words = [], text.split()
    current = ""
    for word in words:
        x = left + (indent if not result else 0)
        width = right-x
        candidate = current + " " + word if current else word
        if stringWidth(candidate, "Courier", 12) <= width + .01:
            current = candidate
            continue
        if current:
            result.append((current, x))
            current = ""
            x, width = left, right-left
        if stringWidth(word, "Courier", 12) > width + .01:
            raise ProfessionalScreenplayError("A source token exceeds the professional column; no clipping or rewriting was used.")
        current = word
    if current:
        result.append((current, left + (indent if not result else 0)))
    if not result:
        raise ProfessionalScreenplayError("An empty source paragraph cannot be silently removed.")
    if _STYLES[role][4] == "Right":
        result = [(line, right-stringWidth(line, "Courier", 12)) for line, _ in result]
    return result


def _plan_pdf(packet, paragraphs):
    pages = []
    if packet["title_paragraphs"]:
        title = dict(is_title=True, body_number=None, lines=[])
        y = 288.0
        for index, row in enumerate(packet["title_paragraphs"]):
            if index == 1:
                y = max(y, 384.0)
            for text, _ in _wrap(row["text"], "Action"):
                if y > _LAST_BASELINE:
                    raise ProfessionalScreenplayError("Title content exceeds one title page; explicit title-layout review is needed.")
                title["lines"].append(dict(text=text, x=(612-stringWidth(text, "Courier", 12))/2,
                    y=y, role="Title", kind="authored", source_indices=[index]))
                y += _LEADING
        pages.append(title)
    page, y, number = None, _FIRST_BASELINE, 0

    def new_page():
        nonlocal page, y, number
        if len(pages) >= _MAX_OUTPUT_PAGES:
            raise ProfessionalScreenplayError("Professional PDF exceeds the bounded page limit.")
        number += 1
        page = dict(is_title=False, body_number=number, lines=[])
        if number > 1:
            text = str(number) + "."
            page["lines"].append(dict(text=text, x=522-stringWidth(text, "Courier", 12), y=36.0,
                role="Header", kind="page_header", source_indices=[]))
        pages.append(page)
        y = _FIRST_BASELINE

    def add_line(text, x, role, kind, source_indices):
        nonlocal y
        if y > _LAST_BASELINE + .01:
            raise ProfessionalScreenplayError("Professional layout overflow was stopped before drawing.")
        page["lines"].append(dict(text=text, x=x, y=y, role=role, kind=kind,
                                  source_indices=source_indices))
        y += _LEADING

    def continued_cue(source_index):
        speaker = packet["paragraphs"][source_index]["text"]
        label = speaker if re.search(r"\(CONT['’]?D\)", speaker, re.I) else speaker + " (CONT'D)"
        for text, x in _wrap(label, "Character"):
            add_line(text, x, "Character", "dialogue_continued", [source_index])

    wrapped = [_wrap(row["text"], row["type"]) for row in paragraphs]
    new_page()
    for index, row in enumerate(paragraphs):
        role, lines = row["type"], wrapped[index]
        before = float(_STYLES[role][3]) if y > _FIRST_BASELINE else 0
        minimum = 1
        if role in {"Character", "Parenthetical", "Scene Heading"}:
            minimum = len(lines)
            for nxt in range(index+1, min(index+4, len(paragraphs))):
                next_role = paragraphs[nxt]["type"]
                if role == "Scene Heading":
                    if next_role == "Action": minimum += 1 + min(2, len(wrapped[nxt]))
                    break
                if next_role == "Parenthetical":
                    minimum += len(wrapped[nxt])
                elif next_role == "Dialogue":
                    minimum += min(3, len(wrapped[nxt]))
                    break
                else:
                    break
        if y + before + (minimum-1)*_LEADING > _LAST_BASELINE and y > _FIRST_BASELINE:
            new_page()
            before = 0
        y += before
        remaining = list(lines)
        if role == "Dialogue" and row["speaker_index"] is not None:
            while remaining:
                capacity = math.floor((_LAST_BASELINE-y)/_LEADING) + 1
                if len(remaining) <= capacity:
                    for text, x in remaining: add_line(text, x, role, "authored", row["source_indices"])
                    remaining = []
                elif capacity < 3:
                    new_page()
                    continued_cue(row["speaker_index"])
                else:
                    for text, x in remaining[:capacity-1]: add_line(text, x, role, "authored", row["source_indices"])
                    remaining = remaining[capacity-1:]
                    add_line("(MORE)", 252.0, "Character", "dialogue_more", row["source_indices"])
                    new_page()
                    continued_cue(row["speaker_index"])
        else:
            for text, x in remaining:
                if y > _LAST_BASELINE: new_page()
                add_line(text, x, role, "authored", row["source_indices"])
    return pages


def _prepare(packet):
    validate_packet(packet)
    paragraphs, diagnostics, joins = _logical_paragraphs(packet)
    pages = _plan_pdf(packet, paragraphs)
    return paragraphs, diagnostics, joins, pages


def _header(root):
    hf = ET.SubElement(root, "HeaderAndFooter", StartingPage="1", HeaderFirstPage="No",
                       HeaderVisible="Yes", FooterFirstPage="No", FooterVisible="No")
    paragraph = ET.SubElement(ET.SubElement(hf, "Header"), "Paragraph", Alignment="Left",
        FirstIndent="0.00", Leading="Regular", LeftIndent="1.25", RightIndent="-1.00",
        SpaceBefore="0", Spacing="1", StartsNewPage="No")
    ET.SubElement(paragraph, "Text", Font="Courier", Size="12").text = "\t"
    ET.SubElement(paragraph, "DynamicLabel", Font="Courier", Size="12", Type="Page #")
    ET.SubElement(paragraph, "Text", Font="Courier", Size="12").text = "."
    ET.SubElement(ET.SubElement(paragraph, "Tabstops"), "Tabstop", Position="7.25", Type="Right")


def to_professional_fdx(packet: dict) -> bytes:
    paragraphs, _, _, _ = _prepare(packet)
    root = ET.Element("FinalDraft", DocumentType="Script", Template="No", Version="1")
    content = ET.SubElement(root, "Content")
    for row in paragraphs:
        paragraph = ET.SubElement(content, "Paragraph", Type=row["type"], Alignment=_STYLES[row["type"]][4])
        ET.SubElement(paragraph, "Text", Font="Courier", Size="12").text = row["text"]
    page = ET.SubElement(root, "PageLayout", TopMargin="72", BottomMargin="72", HeaderMargin="36",
        FooterMargin="36", DocumentLeading="Normal", BreakDialogueAndActionAtSentences="Yes")
    ET.SubElement(page, "PageSize", Width="8.50", Height="11.00")
    for role, (left, right, indent, space, align, return_key, tab_key) in _STYLES.items():
        setting = ET.SubElement(root, "ElementSettings", Type=role)
        ET.SubElement(setting, "FontSpec", Font="Courier", Size="12", Style="")
        ET.SubElement(setting, "ParagraphSpec", Type=role, Alignment=align, FirstIndent=indent,
            LeftIndent=left, RightIndent=right, SpaceBefore=space, Spacing="1", Leading="Regular", StartsNewPage="No")
        ET.SubElement(setting, "Behavior", PaginateAs=role, ReturnKey=return_key, TabKey=tab_key)
    _header(root)
    if packet["title_paragraphs"]:
        title = ET.SubElement(ET.SubElement(root, "TitlePage"), "Content")
        for row in packet["title_paragraphs"]:
            paragraph = ET.SubElement(title, "Paragraph", Type="Action", Alignment="Center")
            ET.SubElement(paragraph, "Text", Font="Courier", Size="12").text = row["text"]
    continueds = ET.SubElement(root, "MoresAndContinueds")
    ET.SubElement(continueds, "FontSpec", Font="Courier", Size="12", Style="")
    ET.SubElement(continueds, "DialogueBreaks", AutomaticCharacterContinueds="No", BottomOfPage="Yes",
        DialogueBottom="(MORE)", DialogueTop="(CONT'D)", TopOfNext="Yes")
    ET.SubElement(continueds, "SceneBreaks", ContinuedNumber="No", SceneBottom="(CONTINUED)",
        SceneBottomOfPage="No", SceneTop="CONTINUED:", SceneTopOfNext="No")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def to_professional_pdf(packet: dict) -> bytes:
    _, _, _, pages = _prepare(packet)
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792), pageCompression=1, invariant=1)
    canvas.setCreator(PDF_RENDERER_ID)
    canvas.setTitle("Professional screenplay")
    for page in pages:
        canvas.setFont("Courier", 12)
        for line in page["lines"]:
            canvas.drawString(line["x"], 792-line["y"], line["text"])
        canvas.showPage()
    canvas.save()
    raw = output.getvalue()
    with fitz.open(stream=raw, filetype="pdf") as document:
        if len(document) != len(pages):
            raise ProfessionalScreenplayError("Professional PDF page readback disagrees with its layout plan.")
        for expected, page in zip(pages, document):
            # Exact token comparison: no punctuation fallback, dehyphenation or
            # blanket removal of whitespace to conceal a word-boundary change.
            if page.get_text().split() != [word for line in expected["lines"] for word in line["text"].split()]:
                raise ProfessionalScreenplayError("Professional PDF text readback changed a word boundary or glyph.")
    return raw


def professional_profile_receipt(packet: dict) -> dict:
    paragraphs, diagnostics, joins, pages = _prepare(packet)
    annotations = [dict(kind=line["kind"], page=number, x=line["x"], y=line["y"],
                        text_sha256=_sha(line["text"].encode("utf-8")), source_indices=line["source_indices"])
                   for number, page in enumerate(pages, 1) for line in page["lines"] if line["kind"] != "authored"]
    title_count = sum(page["is_title"] for page in pages)
    return dict(schema="aibs_screenplay_professional_receipt_v1", profile_id=PROFILE_ID,
        renderer_id=RENDERER_ID, fdx_renderer_id=FDX_RENDERER_ID, pdf_renderer_id=PDF_RENDERER_ID,
        source_sha256=packet["source_sha256"], source_page_count=packet["page_count"],
        source_title_page_count=packet["title_page_count"], source_body_page_count=packet["body_page_count"],
        authored_body_token_sha256=packet["body_token_sha256"], authored_role_token_sha256=_role_hash(paragraphs),
        authored_title_token_sha256=_tokens_hash(row["text"] for row in packet["title_paragraphs"]),
        source_paragraph_count=len(packet["paragraphs"]), logical_paragraph_count=len(paragraphs),
        merged_pdf_boundary_count=joins, source_hard_breaks_removed=sum(row["starts_new_page"] for row in packet["paragraphs"]),
        diagnostics=diagnostics, source_warning_count=len(packet.get("warnings", [])),
        generated_annotations=annotations, generated_annotation_count=len(annotations),
        internal_pdf_planned_page_count=len(pages), internal_pdf_planned_title_page_count=title_count,
        internal_pdf_planned_body_page_count=len(pages)-title_count,
        fdx_page_count=None, external_final_draft_verified=False, source_layout_preserved=False, vendor_certified=False,
        settings=dict(paper="US Letter", font="Courier", font_size=12, document_leading="Normal",
            internal_baseline_leading_pt=12, automatic_character_continueds=False,
            dialogue_page_continuations=True, scene_continuations=False, first_body_page_number=1,
            header_on_first_body_page=False),
        warnings=["Source physical page boundaries are removed; paragraph joins are conservative recorded inferences.",
                  "Internal PDF and Final Draft pagination are separate; no source page count or runtime is promised.",
                  "Authored case and punctuation are retained; no proprietary font or vendor certification is used."])
