import asyncio
import random
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from constants import STOCK_AVATARS, SAMPLE_VIDEOS
from schemas import AvatarCreate

router = APIRouter(prefix="/avatars", tags=["avatars"])


@router.get("")
async def list_avatars(org: dict = Depends(get_current_org)):
    return await db.avatars.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("")
async def create_avatar(body: AvatarCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {"id": gen_id("avt"), "organization_id": org["id"], "name": body.name, "status": "processing",
           "source_type": body.source_type, "source_asset_url": body.source_asset_url,
           "thumbnail_url": body.thumbnail_url or random.choice(STOCK_AVATARS)["thumbnail_url"],
           "preview_video_url": random.choice(SAMPLE_VIDEOS), "metadata": {}, "is_stock": False,
           "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.avatars.insert_one(doc)

    async def finish(aid):
        await asyncio.sleep(5)
        await db.avatars.update_one({"id": aid}, {"$set": {"status": "ready", "updated_at": now_iso()}})

    asyncio.create_task(finish(doc["id"]))
    return clean(doc)


@router.delete("/{aid}", status_code=204)
async def delete_avatar(aid: str, org: dict = Depends(get_current_org)):
    avatar = await db.avatars.find_one({"id": aid, "organization_id": org["id"]})
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if avatar.get("is_stock"):
        raise HTTPException(status_code=400, detail="Stock avatars cannot be deleted")
    await db.avatars.delete_one({"id": aid})
    return JSONResponse(status_code=204, content=None)
