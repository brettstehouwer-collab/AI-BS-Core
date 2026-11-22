"""Explicit typed FDX professional reflow; never infer roles from plain text.

Source XML remains authoritative and untouched. This profile replaces source
page/template geometry with the existing Courier12 professional layout. Unknown
visible structures/styles reject instead of disappearing from the export.
"""
import io
import re

import fitz
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from core.fdx_source_documents import parse_fdx, _document, _children
from core.screenplay_professional import _plan_pdf, _STYLES

PROFILE_ID = 'typed-fdx-professional-courier12-v1'
RENDERER_ID = 'aibs_typed_fdx_pdf_v1'
_SECTIONS = {'Content', 'TitlePage', 'ElementSettings', 'HeaderAndFooter',
             'MoresAndContinueds', 'PageLayout'}
_PARAGRAPH_ATTRIBUTES = {'Type', 'Alignment', 'StartsNewPage', 'FirstIndent',
                         'LeftIndent', 'RightIndent', 'SpaceBefore', 'Spacing', 'Leading'}


class TypedFdxPdfError(ValueError):
    pass


def _style(attributes):
    if set(attributes)-{'Font', 'Size', 'Style'}:
        raise TypedFdxPdfError('Unsupported text attributes; original FDX retained.')
    if attributes.get('Font', 'Courier') not in {'Courier', 'Courier New', 'Courier Prime'}:
        raise TypedFdxPdfError('The typed professional profile requires a Courier-family source font.')
    if attributes.get('Size', '12') not in {'12', '12.0', '12.00'}:
        raise TypedFdxPdfError('Unsupported text size; original FDX retained.')
    styles = set(filter(None, attributes.get('Style', '').split('+')))
    if styles-{'Bold', 'Italic', 'Underline'}:
        raise TypedFdxPdfError('Unsupported text styling; original FDX retained.')
    font = ('Courier-BoldOblique' if {'Bold', 'Italic'} <= styles else
            'Courier-Bold' if 'Bold' in styles else
            'Courier-Oblique' if 'Italic' in styles else 'Courier')
    return font, 'Underline' in styles


def _words(block):
    spans = []
    position = 0
    for run in block['runs']:
        font, underline = _style(run['attributes'])
        end = position+len(run['text'])
        spans.append((position, end, font, underline))
        position = end
    words = []
    cursor = 0
    for match in re.finditer(r'\S+', block['text']):
        while cursor < len(spans) and spans[cursor][1] <= match.start():
            cursor += 1
        fragments = []
        index = cursor
        while index < len(spans) and spans[index][0] < match.end():
            start, end, font, underline = spans[index]
            text = block['text'][max(start, match.start()):min(end, match.end())]
            if text:
                fragments.append({'text':text, 'font':font, 'underline':underline})
            index += 1
        if ''.join(fragment['text'] for fragment in fragments) != match.group():
            raise TypedFdxPdfError('Text run coverage is incomplete; no export produced.')
        words.append((match.group(), fragments))
    return words


def plan_typed_fdx_pdf(raw):
    """Private layout plan with authored text; callers must not log the plan."""
    try:
        xml = _document(raw)
        if any(node.tagName not in _SECTIONS for node in _children(xml.documentElement)):
            raise TypedFdxPdfError('Unsupported FDX section; original document retained.')
        for title in _children(xml.documentElement, 'TitlePage'):
            contents = _children(title, 'Content')
            if len(contents) != 1 or len(_children(title)) != 1:
                raise TypedFdxPdfError('Unsupported title-page structure.')
            if any(node.tagName != 'Paragraph' for node in _children(contents[0])):
                raise TypedFdxPdfError('Unsupported title-page content.')
        document = parse_fdx(raw)
        if document['warnings'] or not document['blocks']:
            raise TypedFdxPdfError('Unsupported or empty typed document; no export produced.')
        blocks, titles = document['blocks'], document['title_page']
        if sum(len(block['runs']) for block in blocks+titles) > 100000:
            raise TypedFdxPdfError('Typed run count exceeds the bounded profile.')
        for block in blocks+titles:
            if block['notes'] or block['dualGroup'] or not block['editable']:
                raise TypedFdxPdfError('Notes, dual dialogue or nested content require a separate renderer.')
            if set(block['attributes'])-_PARAGRAPH_ATTRIBUTES:
                raise TypedFdxPdfError('Unsupported paragraph attributes; original FDX retained.')
        paragraphs = []
        speaker = None
        for index, block in enumerate(blocks):
            role = block['type']
            if role not in _STYLES:
                raise TypedFdxPdfError('Unsupported typed paragraph role; no role was guessed.')
            if role == 'Character':
                speaker = index
            elif role not in {'Dialogue', 'Parenthetical'}:
                speaker = None
            paragraphs.append({'type':role, 'text':block['text'], 'source_indices':[index],
                               'speaker_index':speaker if role in {'Dialogue', 'Parenthetical'} else None})
        queues = [[_words(block) for block in group] for group in (blocks, titles)]
        if sum(len(words) for group in queues for words in group) > 200000:
            raise TypedFdxPdfError('Typed word count exceeds the bounded profile.')
        pointers = [[0]*len(group) for group in (blocks, titles)]
        pages = _plan_pdf({'paragraphs':paragraphs, 'title_paragraphs':titles}, paragraphs)
        for page in pages:
            group = 1 if page['is_title'] else 0
            for line in page['lines']:
                if line['kind'] != 'authored':
                    line['segments'] = [{'text':line['text'], 'font':'Courier', 'underline':False}]
                    continue
                index = line['source_indices'][0]
                segments = []
                for word in line['text'].split():
                    position = pointers[group][index]
                    expected, fragments = queues[group][index][position]
                    if word != expected:
                        raise TypedFdxPdfError('Typed layout changed authored word order.')
                    if segments:
                        segments.append({'text':' ', 'font':'Courier', 'underline':False})
                    segments.extend(fragments)
                    pointers[group][index] += 1
                line['segments'] = segments
        if any(pointer != len(words) for group, positions in zip(queues, pointers)
               for words, pointer in zip(group, positions)):
            raise TypedFdxPdfError('Typed layout did not consume every authored word.')
        return {'profile_id':PROFILE_ID, 'renderer_id':RENDERER_ID, 'pages':pages,
                'paragraph_roles':[row['type'] for row in paragraphs],
                'source_layout_preserved':False, 'source_style_subset':['Bold', 'Italic', 'Underline'],
                'warnings':['Explicit professional reflow replaces source template, page breaks, headers and title geometry.',
                            'Courier-family fonts use standard PDF Courier variants; source font metrics are not retained.',
                            'Paragraph whitespace reflows; original FDX bytes remain separate.']}
    except TypedFdxPdfError:
        raise
    except Exception:
        raise TypedFdxPdfError('Typed professional layout could not be established; original FDX retained.') from None


def render_typed_fdx_pdf(raw):
    """Return readback-checked PDF bytes; no filesystem, source writes or routing."""
    plan = plan_typed_fdx_pdf(raw)
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792), pageCompression=1, invariant=1)
    canvas.setCreator(RENDERER_ID)
    canvas.setTitle('Typed professional screenplay')
    for page in plan['pages']:
        for line in page['lines']:
            x, baseline = line['x'], 792-line['y']
            for segment in line['segments']:
                canvas.setFont(segment['font'], 12)
                canvas.drawString(x, baseline, segment['text'])
                width = stringWidth(segment['text'], segment['font'], 12)
                if segment['underline']:
                    canvas.setLineWidth(.5)
                    canvas.line(x, baseline-1.5, x+width, baseline-1.5)
                x += width
        canvas.showPage()
    canvas.save()
    result = output.getvalue()
    with fitz.open(stream=result, filetype='pdf') as pdf:
        if len(pdf) != len(plan['pages']):
            raise TypedFdxPdfError('Typed PDF page readback disagrees with its plan.')
        for actual, expected in zip(pdf, plan['pages']):
            if actual.get_text().split() != [word for line in expected['lines'] for word in line['text'].split()]:
                raise TypedFdxPdfError('Typed PDF text readback changed authored words or glyphs.')
    return result
