import asyncio, json, logging, re, secrets, time
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings
from app.schemas import CreateMeeting, TranscriptBody, MeetingSpec, BotBody, AskBody, SaveBody
from app.security import require_app_token, require_session, validate_meeting_id
from app.meetings.store import store
from app.meetings.normalize import normalize_transcript
from app.meetings.sample import SAMPLE_TRANSCRIPT
from app.meetings.export_md import render_markdown
from app.meetings.meeting_url import UnsupportedPlatform, normalize_meet_url
from app.meetings.extraction import iter_extraction
from app.providers.base import provider_for
from app.stt.media import transcribe_upload
from app.bots.simulated import replay_sample
from app.history import client as history

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("actionmint")
limiter=Limiter(key_func=get_remote_address, default_limits=[])
app=FastAPI(title="ActionMint — Meeting-to-Action Workspace", version="1.0.0", docs_url="/docs" if settings.env=="dev" else None, redoc_url=None)
app.state.limiter=limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),allow_credentials=False,allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],allow_headers=["Content-Type","X-App-Token","X-Session-Token"],expose_headers=["Content-Disposition"])

@app.middleware("http")
async def security_headers(request: Request, call_next):
    length=request.headers.get("content-length")
    if length and request.url.path.startswith("/api/") and request.url.path.endswith("/media") and int(length)>settings.max_media_mb*1024*1024+1024*1024:
        return JSONResponse(status_code=413,content={"detail":{"code":"too_long","message":"Upload exceeds the configured size limit."}})
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="no-referrer"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"): response.headers["Cache-Control"]="no-store"
    return response

@app.on_event("startup")
async def check_config():
    if settings.env!="dev" and (not settings.app_token or settings.app_token=="dev-token-change-me"):
        raise RuntimeError("APP_TOKEN must be configured outside development.")

@app.get("/health")
async def health():
    providers=[]
    for name in settings.provider_chain:
        p=provider_for(name)
        if p is None:
            # Unconfigured providers are reported honestly instead of being shown as ready.
            providers.append({"name":name,"ok":False,"latency_ms":None,"configured":False}); continue
        ok,latency=await p.check()
        providers.append({"name":name,"ok":bool(ok),"latency_ms":latency,"configured":True})
    ready=next((p["name"] for p in providers if p["ok"] and p["name"]!="mock"),"mock")
    return {"status":"ok","providers":providers,"default_provider":ready,"model":settings.model_for(ready),"history":{"configured":history.configured()},"bot":{"backend":settings.bot_backend,"worker_configured":bool(settings.bot_worker_url)}}

@app.post("/api/meetings",status_code=201)
@limiter.limit("10/minute")
async def create_meeting(request: Request, body: CreateMeeting, _: str=Depends(require_app_token)):
    text=body.text or ""
    if text and len(text)>settings.max_transcript_chars: raise HTTPException(413,detail={"code":"too_long","message":"Transcript exceeds 60,000 characters."})
    meeting_date=body.meeting_date or date.today().isoformat()
    try: date.fromisoformat(meeting_date)
    except ValueError: raise HTTPException(422,detail={"code":"bad_request","message":"meeting_date must use YYYY-MM-DD."})
    title=(body.title or "Meeting notes").strip() or "Meeting notes"
    item,token=store.create(body.source,title,meeting_date,text)
    if text: item.segments=normalize_transcript(text)
    log.info("meeting created id=%s source=%s",item.meeting_id[:8],body.source)
    return {"meeting_id":item.meeting_id,"session_token":token,"expires_at":item.expires_at,"state":item.state,"demo_mode":not bool(settings.gemini_api_key or settings.groq_api_key)}

@app.post("/api/meetings/{meeting_id}/transcript")
@limiter.limit("10/minute")
async def add_transcript(request: Request, meeting_id: str, body: TranscriptBody, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    if len(body.text)>settings.max_transcript_chars: raise HTTPException(413,detail={"code":"too_long","message":"Transcript is too long."})
    item.raw_text=body.text; item.segments=normalize_transcript(body.text); item.state="created"; store.extend(meeting_id)
    return {"ok":True,"segments":len(item.segments)}

@app.post("/api/meetings/{meeting_id}/media",status_code=202)
@limiter.limit("3/minute")
async def upload_media(request: Request, meeting_id: str, file: UploadFile=File(...), _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    payload=await file.read(settings.max_media_mb*1024*1024+1)
    text,duration,provider=await transcribe_upload(file.filename or "recording.wav",payload)
    item.raw_text=text; item.segments=normalize_transcript(text); item.state="created"; item.source="upload"; item.duration_s=duration; item.stt_provider=provider
    store.extend(meeting_id)
    return {"ok":True,"segments":len(item.segments),"duration_s":duration,"stt_provider":provider,"demo_mode":provider=="mock"}

@app.post("/api/meetings/{meeting_id}/bot")
@limiter.limit("3/minute")
async def start_bot(request: Request, meeting_id: str, body: BotBody, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    if body.consent is not True: raise HTTPException(422,detail={"code":"bad_request","message":"Consent is required before a bot can start."})
    # Amendment C.24: Google Meet only, enforced with the shared parser-based validator.
    try: meeting_url=normalize_meet_url(body.meeting_url)
    except UnsupportedPlatform as exc: raise HTTPException(422,detail={"code":exc.code,"message":str(exc)})
    item.source="link"; item.state="live"; item.bot_id="sim_"+secrets.token_hex(5); item.meeting_url=meeting_url
    # The simulated adapter makes the workflow demonstrable without pretending to join a real call.
    async def replay():
        segments=[]
        async def on_segment(segment):
            segment["id"]=f"S{len(segments)+1}"; segments.append(segment); item.segments=list(segments); item.raw_text="\n".join(s["text"] for s in segments)
        await replay_sample(on_segment)
        item.state="processing"
    asyncio.create_task(replay())
    return {"bot_id":item.bot_id,"state":"live","backend":"simulated","label":"Simulated bot — does not join a real meeting"}

@app.post("/api/meetings/{meeting_id}/finalize")
# This endpoint is also the client's "is the capture finished?" poll, so the limit is
# sized for polling (every ~1 s for a minute), not for a one-shot action.
@limiter.limit("30/minute")
async def finalize(request: Request, meeting_id: str, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    # A live capture has no transcript to finalize yet. Answering 200 with state=live is
    # honest and keeps the poll out of the error path (it used to 422 on every poll).
    if item.state=="live": return {"meeting_id":meeting_id,"state":"live"}
    if not item.raw_text and not item.segments: raise HTTPException(422,detail={"code":"bad_request","message":"Add a transcript or recording before processing."})
    if item.state not in {"live","ready"}: item.state="processing"
    return {"meeting_id":meeting_id,"state":item.state}

@app.get("/api/meetings/{meeting_id}/events")
async def meeting_events(request: Request, meeting_id: str, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    if item.state=="live": raise HTTPException(409,detail={"code":"bad_request","message":"The simulated meeting is still in progress; connect to events again shortly."})
    if item.state not in {"processing","ready"}: item.state="processing"
    async def emit(event: str, data: dict):
        return f"event: {event}\ndata: {json.dumps(data,ensure_ascii=False,separators=(',',':'))}\n\n"
    async def stream():
        if item.state=="ready" and item.spec:
            yield await emit("status",{"state":"ready","label":"Meeting ready"})
            yield await emit("spec",{"section":"all","data":item.spec})
            yield await emit("done",{"meeting_id":meeting_id}); return
        if not item.segments:
            item.segments=normalize_transcript(item.raw_text or "")
        yield await emit("status",{"state":"transcribing","label":"Preparing transcript"})
        for segment in item.segments:
            if await request.is_disconnected(): return
            yield await emit("segment",{**segment,"final":True})
        yield await emit("status",{"state":"extracting","label":"Finding decisions and commitments"})
        try:
            spec=None; provider="mock"
            # C.4: four calls, and a question/spec event as each category finishes.
            async for kind,payload in iter_extraction(item.segments,{"meeting_id":item.meeting_id,"title":item.title,"meeting_date":item.meeting_date,"source":item.source}):
                if kind=="section": yield await emit("spec",payload)
                elif kind=="question": yield await emit("question",payload)
                elif kind=="result": spec,provider=payload["spec"],payload["provider"]
            if spec is None: raise RuntimeError("extraction produced no result")
            item.spec=MeetingSpec.model_validate(spec).model_dump(mode="json"); item.provider=provider
            item.state="ready"; store.extend(meeting_id,1800)
            yield await emit("status",{"state":"ready","label":"Review your notes"})
            yield await emit("done",{"meeting_id":meeting_id})
            log.info("meeting processed id=%s provider=%s segments=%s",meeting_id[:8],provider,len(item.segments))
        except Exception as exc:
            item.state="created"
            yield await emit("error",{"code":"internal","message":"Processing failed. Your transcript is still in this session; you can retry."})
            log.warning("meeting processing failed id=%s kind=%s",meeting_id[:8],type(exc).__name__)
    return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache, no-store","X-Accel-Buffering":"no","Connection":"keep-alive"})

@app.get("/api/meetings/{meeting_id}/result")
async def get_result(request: Request, meeting_id: str, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    if item.state!="ready" or not item.spec: raise HTTPException(409,detail={"code":"bad_request","message":"Meeting is still processing."})
    return {"spec":item.spec,"segments":item.segments,"md":render_markdown(item.spec),"provider":item.provider}

@app.put("/api/meetings/{meeting_id}/result")
async def put_result(request: Request, meeting_id: str, body: MeetingSpec, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    if body.meeting_id!=meeting_id: raise HTTPException(422,detail={"code":"bad_request","message":"meeting_id mismatch."})
    spec=body.model_dump(mode="json"); spec["edited"]=True
    item.spec=spec; store.extend(meeting_id)
    return {"ok":True,"md":render_markdown(spec)}

@app.post("/api/meetings/{meeting_id}/ask")
@limiter.limit("20/minute")
async def ask_meeting(request: Request, meeting_id: str, body: AskBody, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); item=store.get(meeting_id)
    question_terms={t.lower() for t in re.findall(r"[\w]+",body.question) if len(t)>2}
    selected=sorted(item.segments,key=lambda s:len(question_terms & {t.lower() for t in re.findall(r"[\w]+",s["text"])}),reverse=True)[:4]
    answer="I couldn't find a relevant passage in this meeting." if not selected or not question_terms else "Relevant meeting passages: " + " ".join(f'[{s["id"]}] {s["text"]}' for s in selected)
    async def stream():
        yield f"event: retrieval\ndata: {json.dumps({'chunks':[{'id':s['id'],'source':'Transcript '+s['id'],'score':0.5,'preview':s['text'][:160]} for s in selected]})}\n\n"
        for part in re.findall(r".{1,90}(?:\s|$)",answer): yield f"event: token\ndata: {json.dumps({'text':part})}\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(request: Request, meeting_id: str, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id); store.delete(meeting_id); return {"ok":True}

@app.post("/api/meetings/{meeting_id}/save")
async def save_history(request: Request, meeting_id: str, body: SaveBody, _: str=Depends(require_session)):
    meeting_id=validate_meeting_id(meeting_id)
    if not history.configured(): raise HTTPException(404,detail={"code":"history_unavailable","message":"Cloud history is not configured on this server."})
    data=body.spec.model_dump(mode="json")
    encoded=json.dumps(data,ensure_ascii=False)
    if len(encoded.encode())>65536: raise HTTPException(413,detail={"code":"too_long","message":"Meeting summary exceeds the 64 KB history limit."})
    try:
        await history.request("POST","meetings_saved",params={"on_conflict":"meeting_id"},json={"meeting_id":meeting_id,"title":data["title"],"meeting_date":data["meeting_date"],"spec":data},)
        return {"saved":True,"meeting_id":meeting_id}
    except history.HistoryUnavailable as exc: raise HTTPException(503,detail={"code":"history_unavailable","message":str(exc)})

@app.get("/api/history")
@limiter.limit("20/minute")
async def get_history(request: Request, limit: int=20, _: str=Depends(require_app_token)):
    if not history.configured(): raise HTTPException(404,detail={"code":"history_unavailable","message":"Cloud history is not configured on this server."})
    try:
        r=await history.request("GET","meetings_saved",params={"select":"id,meeting_id,title,meeting_date,created_at,updated_at","order":"created_at.desc","limit":max(1,min(limit,50))})
        return {"items":r.json()}
    except history.HistoryUnavailable as exc: raise HTTPException(503,detail={"code":"history_unavailable","message":str(exc)})

@app.get("/api/history/{meeting_id}")
async def get_saved(request: Request, meeting_id: str, _: str=Depends(require_app_token)):
    meeting_id=validate_meeting_id(meeting_id)
    try:
        r=await history.request("GET","meetings_saved",params={"meeting_id":f"eq.{meeting_id}","select":"*"})
        rows=r.json()
        if not rows: raise HTTPException(404,detail={"code":"bad_request","message":"Saved meeting not found."})
        return rows[0]
    except history.HistoryUnavailable as exc: raise HTTPException(503,detail={"code":"history_unavailable","message":str(exc)})

@app.delete("/api/history/{meeting_id}")
async def delete_saved(request: Request, meeting_id: str, _: str=Depends(require_app_token)):
    meeting_id=validate_meeting_id(meeting_id)
    try:
        await history.request("DELETE","meetings_saved",params={"meeting_id":f"eq.{meeting_id}"})
        return {"deleted":True}
    except history.HistoryUnavailable as exc: raise HTTPException(503,detail={"code":"history_unavailable","message":str(exc)})
