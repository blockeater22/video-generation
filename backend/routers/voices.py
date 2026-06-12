from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from constants import OPENAI_VOICE_FALLBACK
from media_store import MEDIA_ROOT, public_url
from engine.tts import synthesize_speech
from schemas import VoiceCreate

router = APIRouter(prefix="/voices", tags=["voices"])


async def generate_voice_preview(voice: dict) -> str:
    """Generate (and cache) a real TTS preview sample for a voice. Returns public URL."""
    ov = voice.get("openai_voice") or OPENAI_VOICE_FALLBACK.get(voice.get("gender") or "", "alloy")
    path = MEDIA_ROOT / "voice_previews" / f"{voice['id']}.mp3"
    if not path.exists():
        text = f"Hi, I'm {voice['name']}. This is a preview of my voice on Avatar Platform."
        await synthesize_speech(text, voice=ov, out_path=path)
    url = public_url(f"voice_previews/{voice['id']}.mp3")
    await db.voices.update_one({"id": voice["id"]}, {"$set": {"sample_audio_url": url}})
    return url


@router.get("")
async def list_voices(org: dict = Depends(get_current_org)):
    return await db.voices.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("")
async def create_voice(body: VoiceCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {"id": gen_id("vce"), "organization_id": org["id"], "name": body.name, "status": "ready",
           "engine": body.engine, "openai_voice": body.openai_voice,
           "language": body.language, "gender": body.gender,
           "sample_audio_url": body.sample_audio_url, "is_stock": False,
           "created_by": user["id"], "created_at": now_iso()}
    await db.voices.insert_one(doc)
    return clean(doc)


@router.post("/{vid}/preview")
async def preview_voice(vid: str, org: dict = Depends(get_current_org)):
    voice = await db.voices.find_one({"id": vid, "organization_id": org["id"]})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    try:
        url = await generate_voice_preview(voice)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Preview generation failed: {e}")
    return {"sample_audio_url": url}


@router.delete("/{vid}", status_code=204)
async def delete_voice(vid: str, org: dict = Depends(get_current_org)):
    voice = await db.voices.find_one({"id": vid, "organization_id": org["id"]})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    if voice.get("is_stock"):
        raise HTTPException(status_code=400, detail="Stock voices cannot be deleted")
    await db.voices.delete_one({"id": vid})
    return JSONResponse(status_code=204, content=None)
