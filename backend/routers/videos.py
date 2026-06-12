import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from pipeline import process_video_job
from schemas import VideoCreate, VideoPatch

router = APIRouter(prefix="/videos", tags=["videos"])


async def create_video_record(org_id: str, user_id: str, body: VideoCreate):
    avatar = await db.avatars.find_one({"id": body.avatar_id, "organization_id": org_id})
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    voice = await db.voices.find_one({"id": body.voice_id, "organization_id": org_id})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    doc = {"id": gen_id("vid"), "organization_id": org_id, "project_id": body.project_id,
           "title": body.title or "Untitled Video", "status": "queued", "avatar_id": body.avatar_id,
           "voice_id": body.voice_id, "script": body.script, "input_type": body.input_type,
           "input_audio_url": body.input_audio_url, "output_url": None,
           "thumbnail_url": avatar.get("thumbnail_url"), "duration_seconds": None,
           "resolution": body.resolution, "aspect_ratio": body.aspect_ratio,
           "background_type": body.background_type, "background_value": body.background_value,
           "settings": body.settings, "error_message": None, "created_by": user_id,
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.videos.insert_one(doc)
    asyncio.create_task(process_video_job(doc["id"], org_id))
    return clean(doc)


@router.get("")
async def list_videos(project_id: Optional[str] = None, status: Optional[str] = None,
                      page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=100),
                      org: dict = Depends(get_current_org)):
    q = {"organization_id": org["id"]}
    if project_id:
        q["project_id"] = project_id
    if status:
        q["status"] = status
    total = await db.videos.count_documents(q)
    skip = (page - 1) * per_page
    items = await db.videos.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)
    return {"items": items, "total": total, "page": page, "per_page": per_page, "has_more": skip + len(items) < total}


@router.post("", status_code=202)
async def create_video(body: VideoCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    return await create_video_record(org["id"], user["id"], body)


@router.get("/{vid}")
async def get_video(vid: str, org: dict = Depends(get_current_org)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v


@router.patch("/{vid}")
async def update_video(vid: str, body: VideoPatch, org: dict = Depends(get_current_org)):
    upd = body.model_dump(exclude_none=True)
    upd["updated_at"] = now_iso()
    await db.videos.update_one({"id": vid, "organization_id": org["id"]}, {"$set": upd})
    return await get_video(vid, org)


@router.delete("/{vid}", status_code=204)
async def delete_video(vid: str, org: dict = Depends(get_current_org)):
    await db.videos.delete_one({"id": vid, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)


@router.post("/{vid}/retry")
async def retry_video(vid: str, org: dict = Depends(get_current_org)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.videos.update_one({"id": vid}, {"$set": {"status": "queued", "error_message": None,
                               "output_url": None, "updated_at": now_iso()}})
    asyncio.create_task(process_video_job(vid, org["id"]))
    return await get_video(vid, org)
