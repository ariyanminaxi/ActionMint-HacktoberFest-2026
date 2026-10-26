from __future__ import annotations
import os, tempfile, subprocess
from pathlib import Path
from fastapi import HTTPException
from app.config import settings
from app.meetings.sample import SAMPLE_TRANSCRIPT

ALLOWED={".mp3",".wav",".m4a",".mp4",".webm",".mkv"}
def check_magic(ext: str, data: bytes) -> bool:
    if ext==".wav": return data[:4]==b"RIFF" and data[8:12]==b"WAVE"
    if ext==".mp3": return data[:3]==b"ID3" or (len(data)>1 and data[0]==0xff and data[1]&0xe0==0xe0)
    if ext in {".m4a",".mp4"}: return b"ftyp" in data[:16]
    if ext in {".webm",".mkv"}: return data[:4]==bytes.fromhex("1a45dfa3")
    return False

async def transcribe_upload(filename: str, payload: bytes) -> tuple[str,float|None,str]:
    ext=Path(filename).suffix.lower()
    if ext not in ALLOWED or not check_magic(ext,payload[:64]):
        raise HTTPException(status_code=415,detail={"code":"bad_media","message":"Unsupported media file or invalid file signature."})
    if len(payload)>settings.max_media_mb*1024*1024:
        raise HTTPException(status_code=413,detail={"code":"too_long","message":"Upload exceeds the configured size limit."})
    if settings.stt_backend=="mock":
        return SAMPLE_TRANSCRIPT, 170.0, "mock"
    try:
        from faster_whisper import WhisperModel
        import imageio_ffmpeg
        with tempfile.TemporaryDirectory(prefix="actionmint-") as td:
            src=Path(td)/("input"+ext); wav=Path(td)/"audio.wav"; src.write_bytes(payload)
            ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
            proc=subprocess.run([ffmpeg,"-y","-i",str(src),"-ac","1","-ar","16000","-vn",str(wav)],capture_output=True,timeout=120,check=False)
            if proc.returncode!=0 or not wav.exists():
                raise ValueError("Audio conversion failed. Try a WAV or paste a transcript instead.")
            model=WhisperModel(settings.stt_model,device="cpu",compute_type="int8")
            segments,info=model.transcribe(str(wav),vad_filter=True,beam_size=3)
            if info.duration>settings.max_media_min*60: raise ValueError("Recording is longer than the configured duration limit.")
            text="\n".join(f"[{int(s.start//3600):02d}:{int(s.start%3600//60):02d}:{int(s.start%60):02d}] {s.text.strip()}" for s in segments)
            return text,float(info.duration),"faster-whisper"
    except HTTPException: raise
    except Exception as exc:
        raise HTTPException(status_code=422,detail={"code":"bad_media","message":str(exc)[:240] or "Transcription failed. Paste a transcript instead."}) from exc
