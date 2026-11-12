# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
Unified Upload Route — PiNE AI

Single endpoint that handles:
  - Images  (jpg, png, gif, webp, bmp)  → Gemini Vision analysis
  - Audio   (mp3, wav, webm, ogg, m4a)  → Whisper transcription → fact-check
  - PDF     (pdf)                        → text extraction → fact-check
  - DOCX    (docx)                       → text extraction → fact-check

POST /upload
  multipart/form-data:
    file:     the uploaded file
    claim:    optional claim text to check against (for images)
    language: language hint for audio (default: en)
"""

import os
import io
import base64
import logging
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from app.auth import get_current_user  # sign-in required: these routes spend free-tier quotas
from app.models import User

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)

# ── File type limits ──────────────────────────────────────────
MAX_IMAGE_MB = 10
MAX_AUDIO_MB = 25
MAX_DOC_MB   = 20

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/webm",
               "audio/ogg", "audio/mp4", "audio/x-m4a", "audio/aac"}
PDF_TYPE    = "application/pdf"
DOCX_TYPE   = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
AUDIO_EXTS = {".mp3", ".wav", ".webm", ".ogg", ".m4a", ".aac"}
PDF_EXTS   = {".pdf"}
DOCX_EXTS  = {".docx"}
TXT_EXTS   = {".txt", ".text", ".md"}


def _detect_type(filename: str, content_type: str) -> str:
    """Return 'image', 'audio', 'pdf', 'docx', 'txt', or 'unknown'."""
    ext = os.path.splitext(filename.lower())[1] if filename else ""
    ct  = (content_type or "").lower()

    if ct in IMAGE_TYPES or ext in IMAGE_EXTS:  return "image"
    if ct in AUDIO_TYPES or ext in AUDIO_EXTS:  return "audio"
    if ct == PDF_TYPE    or ext in PDF_EXTS:     return "pdf"
    if ct == DOCX_TYPE   or ext in DOCX_EXTS:   return "docx"
    if ct == "text/plain" or ext in TXT_EXTS:   return "txt"
    return "unknown"


def _size_mb(data: bytes) -> float:
    return len(data) / (1024 * 1024)


# ─────────────────────────────────────────────────────────────
# PDF / DOCX text extraction
# ─────────────────────────────────────────────────────────────

def _extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF bytes. Tries pdfplumber then PyPDF2."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages[:20]]
        text = "\n".join(pages).strip()
        if text:
            return text
    except ImportError:
        pass
    except Exception as e:
        logger.debug("pdfplumber failed: %s", e)

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        pages  = [reader.pages[i].extract_text() or "" for i in range(min(20, len(reader.pages)))]
        return "\n".join(pages).strip()
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF parsing requires pdfplumber or PyPDF2. Run: pip install pdfplumber")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")


def _extract_docx_text(data: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        import docx
        doc  = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text.strip()
    except ImportError:
        raise HTTPException(status_code=500, detail="DOCX parsing requires python-docx. Run: pip install python-docx")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read DOCX: {e}")


def _rename_session_to_file(db, session_id, display_name: str):
    """Rename a session to the uploaded filename (called after upload fact-check)."""
    if not session_id:
        return
    try:
        from app.models import ChatSession
        s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if s:
            s.title = display_name[:60]
            db.commit()
    except Exception as e:
        logger.debug("Session rename failed: %s", e)


# ─────────────────────────────────────────────────────────────
# Main upload endpoint
# ─────────────────────────────────────────────────────────────

@router.post("")
@router.post("/")
async def upload_file(
    file:     UploadFile = File(...),
    claim:    str        = Form(""),
    language: str        = Form("en"),
    db:       Session    = Depends(get_db),
    user:     User = Depends(get_current_user),
):
    """
    Upload an image, audio file, PDF, DOCX, or TXT for fact-checking.
    """
    import asyncio
    from functools import partial

    filename     = file.filename or "upload"
    file_type    = _detect_type(filename, file.content_type or "")
    claim        = (claim or "").strip()
    display_name = filename.rsplit(".", 1)[0] if "." in filename else filename

    # ── Validate Content-Type BEFORE reading full file ────────
    if file_type == "unknown":
        raise HTTPException(400, "Unsupported file type. Upload image, audio, PDF, DOCX, or TXT.")

    # Check Content-Length header before buffering entire file
    content_length = file.headers.get("content-length") if hasattr(file, "headers") else None
    if content_length:
        size_mb_approx = int(content_length) / (1024 * 1024)
        limit = MAX_IMAGE_MB if file_type == "image" else MAX_AUDIO_MB if file_type == "audio" else MAX_DOC_MB
        if size_mb_approx > limit:
            raise HTTPException(400, f"File too large ({size_mb_approx:.1f}MB, max {limit}MB)")

    # Read file into memory (validated size above)
    data    = await file.read()
    size_mb = _size_mb(data)

    logger.info("Upload: filename=%s type=%s size=%.1fMB claim_len=%d",
                filename, file_type, size_mb, len(claim))

    # Helper: run sync verify_message in thread pool (avoids blocking event loop)
    async def _verify(message_text: str, image_url: str = None):
        from app.api import message as verify_message
        from app.schemas import MessageRequest
        req = MessageRequest(message=message_text, image_url=image_url)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(verify_message, req, db, user))

    # ── IMAGE ─────────────────────────────────────────────────
    if file_type == "image":
        if size_mb > MAX_IMAGE_MB:
            raise HTTPException(400, f"Image too large ({size_mb:.1f}MB, max {MAX_IMAGE_MB}MB)")

        mime     = file.content_type or "image/jpeg"
        b64      = base64.b64encode(data).decode()
        data_uri = f"data:{mime};base64,{b64}"

        if not claim:
            from app.analysis.image_check import check_image_consistency
            result = check_image_consistency("Describe what is shown in this image", data_uri)
            return {
                "file_type":   "image",
                "filename":    file.filename,
                "size_mb":     round(size_mb, 2),
                "description": result.get("description", ""),
                "message":     "Image received. Provide a claim to fact-check against this image.",
                "image_url":   data_uri[:100] + "...",
            }

        verification = await _verify(claim, data_uri)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {"file_type": "image", "filename": filename, "size_mb": round(size_mb, 2)}
        return verification

    # ── AUDIO ─────────────────────────────────────────────────
    elif file_type == "audio":
        if size_mb > MAX_AUDIO_MB:
            raise HTTPException(400, f"Audio too large ({size_mb:.1f}MB, max {MAX_AUDIO_MB}MB)")

        from app.analysis.audio_transcription import transcribe_audio, validate_audio_file
        validate_audio_file(data, max_size_mb=MAX_AUDIO_MB)
        transcription = await transcribe_audio(data, language=language, service="auto")
        text = transcription.get("text", "").strip()
        if not text or len(text) < 5:
            raise HTTPException(400, "Transcription returned empty text. Check audio quality.")

        verification = await _verify(text)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type": "audio", "filename": filename, "size_mb": round(size_mb, 2),
            "transcript": text, "language": transcription.get("language", language),
            "confidence": transcription.get("confidence", 0.0),
            "service": transcription.get("service", "unknown"),
            "duration_sec": transcription.get("duration", 0),
        }
        return verification

    # ── PDF ───────────────────────────────────────────────────
    elif file_type == "pdf":
        if size_mb > MAX_DOC_MB:
            raise HTTPException(400, f"PDF too large ({size_mb:.1f}MB, max {MAX_DOC_MB}MB)")
        text = _extract_pdf_text(data)
        if not text or len(text) < 20:
            raise HTTPException(400, "Could not extract text from PDF. Is it a scanned image PDF?")
        claim_text = (claim + " " + text[:1800]).strip() if claim else text[:2000]
        verification = await _verify(claim_text)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type": "pdf", "filename": filename, "size_mb": round(size_mb, 2),
            "extracted_chars": len(text), "text_preview": text[:200],
        }
        return verification

    # ── DOCX ──────────────────────────────────────────────────
    elif file_type == "docx":
        if size_mb > MAX_DOC_MB:
            raise HTTPException(400, f"DOCX too large ({size_mb:.1f}MB, max {MAX_DOC_MB}MB)")
        text = _extract_docx_text(data)
        if not text or len(text) < 20:
            raise HTTPException(400, "Could not extract text from DOCX.")
        claim_text = (claim + " " + text[:1800]).strip() if claim else text[:2000]
        verification = await _verify(claim_text)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type": "docx", "filename": filename, "size_mb": round(size_mb, 2),
            "extracted_chars": len(text), "text_preview": text[:200],
        }
        return verification

    # ── TXT ───────────────────────────────────────────────────
    elif file_type == "txt":
        if size_mb > MAX_DOC_MB:
            raise HTTPException(400, f"Text file too large ({size_mb:.1f}MB, max {MAX_DOC_MB}MB)")
        text = data.decode("utf-8", errors="replace").strip()
        if not text or len(text) < 10:
            raise HTTPException(400, "Text file is empty.")
        claim_text = (claim + " " + text[:1800]).strip() if claim else text[:2000]
        verification = await _verify(claim_text)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type": "txt", "filename": filename, "size_mb": round(size_mb, 2),
            "extracted_chars": len(text),
        }
        return verification

    raise HTTPException(400, "Unsupported file type.")

    # ── IMAGE ─────────────────────────────────────────────────
    if file_type == "image":
        if size_mb > MAX_IMAGE_MB:
            raise HTTPException(400, f"Image too large ({size_mb:.1f}MB, max {MAX_IMAGE_MB}MB)")

        # Convert to base64 data URI
        mime = file.content_type or "image/jpeg"
        b64  = base64.b64encode(data).decode()
        data_uri = f"data:{mime};base64,{b64}"

        # If no claim provided, ask Gemini to describe and generate a claim
        if not claim:
            from app.analysis.image_check import check_image_consistency
            result = check_image_consistency("Describe what is shown in this image", data_uri)
            description = result.get("description", "")
            return {
                "file_type":   "image",
                "filename":    file.filename,
                "size_mb":     round(size_mb, 2),
                "description": description,
                "message":     "Image received. Provide a claim to fact-check against this image.",
                "image_url":   data_uri[:100] + "...",  # truncated for response
            }

        # Fact-check claim against image
        from app.analysis.image_check import check_image_consistency
        image_result = check_image_consistency(claim, data_uri)

        # Run full fact-check pipeline with image
        from app.api import message as verify_message
        from app.schemas import MessageRequest
        req = MessageRequest(message=claim, image_url=data_uri)
        verification = verify_message(req, db, user)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type": "image",
            "filename":  filename,
            "size_mb":   round(size_mb, 2),
        }
        return verification

    # ── AUDIO ─────────────────────────────────────────────────
    elif file_type == "audio":
        if size_mb > MAX_AUDIO_MB:
            raise HTTPException(400, f"Audio too large ({size_mb:.1f}MB, max {MAX_AUDIO_MB}MB)")

        from app.analysis.audio_transcription import transcribe_audio, validate_audio_file
        validate_audio_file(data, max_size_mb=MAX_AUDIO_MB)

        transcription = await transcribe_audio(data, language=language, service="auto")
        text = transcription.get("text", "").strip()

        if not text or len(text) < 5:
            raise HTTPException(400, "Transcription returned empty text. Check audio quality.")

        logger.info("Audio transcribed: %d chars via %s", len(text), transcription.get("service"))

        # Fact-check the transcript
        from app.api import message as verify_message
        from app.schemas import MessageRequest
        req = MessageRequest(message=text)
        verification = verify_message(req, db, user)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type":    "audio",
            "filename":     filename,
            "size_mb":      round(size_mb, 2),
            "transcript":   text,
            "language":     transcription.get("language", language),
            "confidence":   transcription.get("confidence", 0.0),
            "service":      transcription.get("service", "unknown"),
            "duration_sec": transcription.get("duration", 0),
        }
        return verification

    # ── PDF ───────────────────────────────────────────────────
    elif file_type == "pdf":
        if size_mb > MAX_DOC_MB:
            raise HTTPException(400, f"PDF too large ({size_mb:.1f}MB, max {MAX_DOC_MB}MB)")

        text = _extract_pdf_text(data)
        if not text or len(text) < 20:
            raise HTTPException(400, "Could not extract text from PDF. Is it a scanned image PDF?")

        # Truncate to 2000 chars for fact-checking
        claim_text = (claim + " " + text[:1800]).strip() if claim else text[:2000]

        from app.api import message as verify_message
        from app.schemas import MessageRequest
        req = MessageRequest(message=claim_text)
        verification = verify_message(req, db, user)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type":    "pdf",
            "filename":     filename,
            "size_mb":      round(size_mb, 2),
            "extracted_chars": len(text),
            "text_preview": text[:200],
        }
        return verification

    # ── DOCX ──────────────────────────────────────────────────
    elif file_type == "docx":
        if size_mb > MAX_DOC_MB:
            raise HTTPException(400, f"DOCX too large ({size_mb:.1f}MB, max {MAX_DOC_MB}MB)")

        text = _extract_docx_text(data)
        if not text or len(text) < 20:
            raise HTTPException(400, "Could not extract text from DOCX.")

        claim_text = (claim + " " + text[:1800]).strip() if claim else text[:2000]

        from app.api import message as verify_message
        from app.schemas import MessageRequest
        req = MessageRequest(message=claim_text)
        verification = verify_message(req, db, user)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type":    "docx",
            "filename":     filename,
            "size_mb":      round(size_mb, 2),
            "extracted_chars": len(text),
            "text_preview": text[:200],
        }
        return verification

    # ── TXT ───────────────────────────────────────────────────
    elif file_type == "txt":
        if size_mb > MAX_DOC_MB:
            raise HTTPException(400, f"Text file too large ({size_mb:.1f}MB, max {MAX_DOC_MB}MB)")

        try:
            text = data.decode("utf-8", errors="replace").strip()
        except Exception:
            text = data.decode("latin-1", errors="replace").strip()

        if not text or len(text) < 5:
            raise HTTPException(400, "Text file is empty.")

        claim_text = (claim + " " + text[:1800]).strip() if claim else text[:2000]

        from app.api import message as verify_message
        from app.schemas import MessageRequest
        req = MessageRequest(message=claim_text)
        verification = verify_message(req, db, user)
        _rename_session_to_file(db, verification.get("session_id"), display_name)
        verification["upload"] = {
            "file_type":    "txt",
            "filename":     filename,
            "size_mb":      round(size_mb, 2),
            "extracted_chars": len(text),
            "text_preview": text[:200],
        }
        return verification

    else:
        raise HTTPException(
            400,
            f"Unsupported file type: {file.content_type or file.filename}. "
            "Supported: jpg/png/gif/webp (image), mp3/wav/webm/ogg/m4a (audio), pdf, docx, txt"
        )


# ─────────────────────────────────────────────────────────────
# Quick info endpoint
# ─────────────────────────────────────────────────────────────

@router.get("/info")
def upload_info():
    """Return supported file types and size limits."""
    return {
        "supported_types": {
            "image": {"formats": ["jpg", "jpeg", "png", "gif", "webp", "bmp"], "max_mb": MAX_IMAGE_MB},
            "audio": {"formats": ["mp3", "wav", "webm", "ogg", "m4a", "aac"], "max_mb": MAX_AUDIO_MB},
            "pdf":   {"formats": ["pdf"],  "max_mb": MAX_DOC_MB},
            "docx":  {"formats": ["docx"], "max_mb": MAX_DOC_MB},
            "txt":   {"formats": ["txt", "text", "md"], "max_mb": MAX_DOC_MB},
        },
        "usage": "POST /upload with multipart/form-data: file=<file>, claim=<optional claim text>",
    }
