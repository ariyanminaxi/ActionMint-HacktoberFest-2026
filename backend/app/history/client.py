from __future__ import annotations
import httpx
from app.config import settings

class HistoryUnavailable(Exception): pass

def configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_key)

async def request(method: str, path: str, *, params=None, json=None):
    if not configured(): raise HistoryUnavailable("Cloud history is not configured on this server.")
    headers={"apikey":settings.supabase_service_key,"Authorization":f"Bearer {settings.supabase_service_key}","Content-Type":"application/json"}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response=await client.request(method,settings.supabase_url.rstrip("/")+"/rest/v1/"+path,headers=headers,params=params,json=json)
            response.raise_for_status(); return response
    except Exception as exc: raise HistoryUnavailable("Cloud history is temporarily unavailable.") from exc
