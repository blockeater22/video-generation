from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_org_from_api_key
from routers.videos import create_video_record
from schemas import VideoCreate

router = APIRouter(prefix="/api/v1", tags=["developer"])


@router.get("/videos")
async def v1_list_videos(org: dict = Depends(get_org_from_api_key)):
    items = await db.videos.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items, "total": len(items)}


@router.post("/videos", status_code=202)
async def v1_create_video(body: VideoCreate, org: dict = Depends(get_org_from_api_key)):
    return await create_video_record(org["id"], org.get("created_by", "api"), body)


@router.get("/videos/{vid}")
async def v1_get_video(vid: str, org: dict = Depends(get_org_from_api_key)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v


@router.get("/avatars")
async def v1_list_avatars(org: dict = Depends(get_org_from_api_key)):
    items = await db.avatars.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}


@router.get("/voices")
async def v1_list_voices(org: dict = Depends(get_org_from_api_key)):
    items = await db.voices.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}
