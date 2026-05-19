"""
parse.py — PDF and plain-text reading; no LLM calls.

Task 1 of the Day 4 lab (Track A).
Study material reference: §5 Document Parsing
"""

import re
import io
import sys

from pypdf import PdfReader
import streamlit as st


# Résumé text below this character count likely means an image-only PDF.
_MIN_RESUME_CHARS = 200

# JD text below this character count likely means the student forgot to paste content.
_MIN_JD_CHARS = 100

# Rough token estimate: 1 token ≈ 4 chars. Truncate above ~6 000 tokens.
_MAX_RESUME_CHARS = 6000 * 4


def read_resume_pdf(uploaded_file) -> str:
    """
    Extract plain text from a PDF résumé using pypdf.

    Requirements:
    1. Open the file with ``pypdf.PdfReader(path)``.
       Raise ``ValueError`` with a clear message if the file is not found or
       cannot be opened (catch ``FileNotFoundError`` separately from ``Exception``).
    2. If the résumé has more than 2 pages, print a warning to ``sys.stderr``.
       ATS systems typically expect a one-page résumé.
    3. Extract text from each page with ``page.extract_text() or ""``.
       Join page texts with ``"\\n\\n"``.
    4. Collapse runs of 3 or more consecutive blank lines to 2 using ``re.sub``.
    5. Strip leading/trailing whitespace from the full text.
    6. Raise ``ValueError`` if the result is shorter than ``_MIN_RESUME_CHARS``
       characters (likely an image-based / scanned PDF — no text layer).
    7. Truncate to ``_MAX_RESUME_CHARS`` characters if very long, and print a
       warning to ``sys.stderr``.

    Args:
        path: Path to the PDF file.

    Returns:
        Extracted plain text.

    Raises:
        ValueError: If the file is not found, cannot be opened, or is too short.
    """
    # attempt to open file
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
    except Exception as e:
        raise ValueError(f"Cannot read file: \"{uploaded_file.name}\", error: \"{e}\"")

    # warn user if more than 2 pages
    if len(reader.pages) > 2:
        print(f"Warning: Resume has {len(reader.pages)}. ATS systems typically expect a one-page resume.", 
            file=sys.stderr)

    # join page texts    
    page_texts = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n\n".join(page_texts)

    # collapse 3 or more consecutive blank lines to 2 using regex
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    # strip leading and trailing ws
    full_text = full_text.strip()

    if len(full_text) < _MIN_RESUME_CHARS: 
        raise ValueError(f"Extracted text is too short ({len(full_text)} chars). The PDF may be image-based or scanned with no text layer.")
    
    if len(full_text) > _MAX_RESUME_CHARS:
        print(f"Warning: Extracted text exceeds {_MAX_RESUME_CHARS} characters. Truncating.", 
            file=sys.stderr)
        full_text = full_text[:_MAX_RESUME_CHARS]

    return full_text


def read_jd_text(uploaded_file) -> str:
    """
    Read a plain-text job description file (UTF-8).

    Requirements:
    1. Open the file with ``open(path, encoding="utf-8")``.
       Raise ``ValueError`` with a clear message if the file is not found.
       Catch other ``Exception`` types and raise ``ValueError`` with the cause.
    2. Strip the content.
    3. Raise ``ValueError`` if the stripped content has fewer than
       ``_MIN_JD_CHARS`` characters.

    Args:
        path: Path to the plain-text job description file.

    Returns:
        Content of the file as a string.

    Raises:
        ValueError: If the file is not found or the content is too short.
    """
    # open the file
    try: 
        content = uploaded_file.read().decode("utf-8")
    except Exception as e:
        raise ValueError(f"Cannot read job description file: \"{uploaded_file.name}\", error: \"{e}\"")
    
    # strip the content
    content = content.strip()

    # check that it has min content
    if len(content) < _MIN_JD_CHARS:
        raise ValueError(f"Job description is too short ({len(content)} chars). Minimum required: {_MIN_JD_CHARS} characters.")
    
    return content
