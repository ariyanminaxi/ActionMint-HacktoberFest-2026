from __future__ import annotations
import hashlib, hmac, re
from fastapi import Header, HTTPException, Request
from app.config import settings
from app.meetings.store import store

async def require_app_token(x_app_token: str | None = Header(default=None)) -> str:
    if not x_app_token or not hmac.compare_digest(x_app_token, settings.app_token):
        raise HTTPException(status_code=401, detail={"code":"unauthorized", "message":"Valid app token required."})
    return x_app_token

async def require_session(request: Request, x_session_token: str | None = Header(default=None), x_app_token: str | None = Header(default=None)):
    if not x_app_token or not hmac.compare_digest(x_app_token, settings.app_token):
        raise HTTPException(status_code=401, detail={"code":"unauthorized", "message":"Valid app token required."})
    meeting_id = request.path_params.get("meeting_id") or request.path_params.get("id")
    if not meeting_id or not x_session_token:
        raise HTTPException(status_code=401, detail={"code":"expired", "message":"Meeting session expired. Start again."})
    if not store.check_token(meeting_id, x_session_token):
        raise HTTPException(status_code=401, detail={"code":"expired", "message":"Meeting session expired. Start again."})
    return meeting_id

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def validate_meeting_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", value):
        raise HTTPException(status_code=422, detail={"code":"bad_request", "message":"Invalid meeting id."})
    return value
