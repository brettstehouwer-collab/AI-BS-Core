"""Normalize existing source authority for the private native creative channel.

This is not an owner migration or a new admission path for unfenced projects.
Callers retain the project-store lock and bind the verified owner first.
"""
import re

from fastapi import HTTPException
from core.chat_pdf_sources import require_project_owner, source_project_view, PDFSourceError
from core.fdx_source_documents import fence as fdx_fence, read_project, FDXSourceError


def require_native_creative_source(directory):
    try:
        pdf = require_project_owner(directory)
        fdx = fdx_fence(directory)
        if pdf is not None and fdx is not None:
            raise HTTPException(409, 'Conflicting source ownership records; preserve this project for review.')
        if pdf is not None:
            # Reuse the existing original/packet/export integrity checks.
            source_project_view(directory, pdf['canonical_revision'])
            digest, kind = pdf.get('source_sha256'), 'pdf'
            if pdf['artifact_sha256'].get('original.pdf') != digest:
                raise HTTPException(409, 'The PDF source identity does not match its retained original.')
        elif fdx is not None:
            # read_project checks original bytes and the current retained version.
            current = read_project(directory)
            if current is None or current.get('source') != 'rich_fdx':
                raise HTTPException(403, 'Native rich-source admission requires the preserved FDX project.')
            digest, kind = fdx.get('original_sha256'), 'rich_fdx'
            if current['fdx_document'].get('source_sha256') != digest:
                raise HTTPException(409, 'The retained rich source identity changed.')
        else:
            raise HTTPException(403, 'Native creative admission requires an owned source-backed project.')
        if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
            raise HTTPException(409, 'The retained source identity is invalid.')
        return {'source_sha256': digest, 'source_kind': kind}
    except (PDFSourceError, FDXSourceError) as error:
        raise HTTPException(error.status, str(error)) from None
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise HTTPException(409, 'Retained source evidence is malformed; the project was preserved.') from None
    except OSError:
        raise HTTPException(503, 'Retained source evidence could not be read; the project was preserved.') from None
