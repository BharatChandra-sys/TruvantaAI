# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
Audio routes for voice-based fact-checking
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import logging

from database import get_db
from app.auth import get_current_user  # sign-in required: these routes spend free-tier quotas
from app.models import User
from app.analysis.audio_transcription import transcribe_audio, validate_audio_file

router = APIRouter(prefix="/audio", tags=["audio"])
logger = logging.getLogger(__name__)


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    auto_detect_claim: bool = Form(True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Transcribe audio file to text with smart claim detection
    
    Supports: mp3, wav, webm, ogg, m4a
    Max size: 25MB
    
    Returns transcription with claim_detected flag
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Validate
        validate_audio_file(audio_data, max_size_mb=25)
        
        # Transcribe
        result = await transcribe_audio(
            audio_data=audio_data,
            language=language,
            service="auto"
        )
        
        text = result["text"]
        
        # Smart claim detection
        claim_detected = False
        if auto_detect_claim and text:
            claim_detected = detect_claim_intent(text)
        
        logger.info(f"Audio transcribed: {len(text)} chars, claim={claim_detected}, service={result['service']}")
        
        return {
            "success": True,
            "text": text,
            "language": result.get("language", language),
            "confidence": result.get("confidence", 0.0),
            "service": result.get("service", "unknown"),
            "duration": result.get("duration", 0),
            "claim_detected": claim_detected
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


def detect_claim_intent(text: str) -> bool:
    """
    Detect if text is likely a factual claim vs a question/chat
    
    Uses heuristics:
    - Contains factual statements (is/are/was/were + noun)
    - Contains numbers, dates, statistics
    - Contains absolute words (always, never, all, none)
    - NOT a question (doesn't start with who/what/when/where/why/how)
    - NOT a greeting or casual chat
    """
    text_lower = text.lower().strip()
    
    # Questions are usually chat, not claims (unless rhetorical)
    question_starters = ['what is', 'what are', 'who is', 'when did', 'where is', 'why did', 'how does', 'can you', 'could you', 'would you', 'tell me', 'explain']
    if any(text_lower.startswith(qw) for qw in question_starters):
        # Check if it's a rhetorical question (claim in question form)
        if not any(word in text_lower for word in ['really', 'actually', 'truly']):
            return False
    
    # Greetings are chat
    greetings = ['hello', 'hi ', 'hey ', 'thanks', 'thank you', 'please help']
    if any(text_lower.startswith(g) for g in greetings):
        return False
    
    # Strong claim indicators
    import re
    
    # Factual statements with "is/are/was/were"
    has_factual_verb = bool(re.search(r'\b(is|are|was|were|will be|has been|have been|contains?|includes?)\b', text_lower))
    
    # Numbers and statistics
    has_numbers = bool(re.search(r'\d+\s*(percent|%|million|billion|thousand|people|cases)', text_lower))
    
    # Absolute claims
    has_absolutes = bool(re.search(r'\b(always|never|all|none|every|no one|everyone|completely|totally)\b', text_lower))
    
    # Causation
    has_causation = bool(re.search(r'\b(causes?|leads? to|results? in|due to|because of|makes?|creates?)\b', text_lower))
    
    # Scientific/medical/political claims
    has_authority = bool(re.search(r'\b(study|studies|research|scientists?|doctors?|experts?|government|officials?)\b', text_lower))
    
    # Conspiracy/controversial topics
    has_controversial = bool(re.search(r'\b(vaccine|covid|election|climate|conspiracy|hoax|fake|lie|truth|cover.?up)\b', text_lower))
    
    # Count indicators
    score = sum([
        has_factual_verb * 2,  # Strong indicator
        has_numbers,
        has_absolutes,
        has_causation,
        has_authority,
        has_controversial * 2  # Strong indicator
    ])
    
    # If 2+ indicators, likely a claim
    return score >= 2


@router.post("/verify")
async def verify_audio_claim(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Transcribe audio and verify the claim
    
    This endpoint combines transcription + fact-checking
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Validate
        validate_audio_file(audio_data, max_size_mb=25)
        
        # Transcribe
        transcription = await transcribe_audio(
            audio_data=audio_data,
            language=language,
            service="auto"
        )

        text = transcription["text"]
        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Transcription too short or empty")

        # Fact-check in thread pool — verify_message is sync and blocks the event loop
        import asyncio
        from functools import partial
        from app.api import message as verify_message
        from app.schemas import MessageRequest

        req = MessageRequest(message=text, history=[], session_id=None, image_url=None)
        loop = asyncio.get_event_loop()
        verification_result = await loop.run_in_executor(
            None, partial(verify_message, req, db, user)
        )

        verification_result["transcription"] = {
            "text":       text,
            "language":   transcription.get("language", language),
            "confidence": transcription.get("confidence", 0.0),
            "service":    transcription.get("service", "unknown"),
            "duration":   transcription.get("duration", 0),
        }

        logger.info("Audio claim verified: verdict=%s", verification_result.get("verdict"))
        return verification_result
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Audio verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Audio verification failed: {str(e)}"
        )
