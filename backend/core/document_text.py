"""Ordered DOCX text traversal shared by document import and adaptation."""
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph


def iter_docx_paragraphs(document):
    """Include table-cell paragraphs at their body position without editing XML.

    This extracts text only; drawings, tracked-deletion text and embedded objects
    require a separate fidelity workflow. The source package is never rewritten.
    """
    for element in document.element.body.iter(qn('w:p')):
        yield Paragraph(element, document)
