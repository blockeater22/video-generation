from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from schemas import VoiceCreate

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("")
async def list_voices(org: dict = Depends(get_current_org)):
    return await db.voices.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("")
async def create_voice(body: VoiceCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {"id": gen_id("vce"), "organization_id": org["id"], "name": body.name, "status": "ready",
           "engine": body.engine, "language": body.language, "gender": body.gender,
           "sample_audio_url": body.sample_audio_url, "is_stock": False,
           "created_by": user["id"], "created_at": now_iso()}
    await db.voices.insert_one(doc)
    return clean(doc)


@router.delete("/{vid}", status_code=204)
async def delete_voice(vid: str, org: dict = Depends(get_current_org)):
    voice = await db.voices.find_one({"id": vid, "organization_id": org["id"]})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    if voice.get("is_stock"):
        raise HTTPException(status_code=400, detail="Stock voices cannot be deleted")
    await db.voices.delete_one({"id": vid})
    return JSONResponse(status_code=204, content=None)
