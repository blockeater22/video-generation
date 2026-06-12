"""Developer REST API (v1) — API-key authenticated, Phase 2 surface."""
import asyncio
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_org_from_api_key, clean
from pipeline import process_video_job, deliver_webhooks
from routers.videos import create_video_record
from routers.voices import generate_voice_preview
from schemas import VideoCreate, WebhookCreate

router = APIRouter(prefix="/api/v1", tags=["developer"])


# ---------------- Videos ----------------
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


@router.delete("/videos/{vid}", status_code=204)
async def v1_delete_video(vid: str, org: dict = Depends(get_org_from_api_key)):
    res = await db.videos.delete_one({"id": vid, "organization_id": org["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    return JSONResponse(status_code=204, content=None)


@router.post("/videos/{vid}/retry", status_code=202)
async def v1_retry_video(vid: str, org: dict = Depends(get_org_from_api_key)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.videos.update_one({"id": vid}, {"$set": {"status": "queued", "error_message": None,
                               "output_url": None, "updated_at": now_iso()}})
    asyncio.create_task(process_video_job(vid, org["id"]))
    return await db.videos.find_one({"id": vid}, {"_id": 0})


# ---------------- Avatars / Voices ----------------
@router.get("/avatars")
async def v1_list_avatars(org: dict = Depends(get_org_from_api_key)):
    items = await db.avatars.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}


@router.get("/voices")
async def v1_list_voices(org: dict = Depends(get_org_from_api_key)):
    items = await db.voices.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}


@router.post("/voices/{vid}/preview")
async def v1_preview_voice(vid: str, org: dict = Depends(get_org_from_api_key)):
    voice = await db.voices.find_one({"id": vid, "organization_id": org["id"]})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    try:
        url = await generate_voice_preview(voice)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Preview generation failed: {e}")
    return {"sample_audio_url": url}


# ---------------- Webhooks ----------------
@router.get("/webhooks")
async def v1_list_webhooks(org: dict = Depends(get_org_from_api_key)):
    items = await db.webhooks.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}


@router.post("/webhooks", status_code=201)
async def v1_create_webhook(body: WebhookCreate, org: dict = Depends(get_org_from_api_key)):
    doc = {"id": gen_id("whk"), "organization_id": org["id"], "url": body.url, "events": body.events,
           "secret": "whsec_" + secrets.token_hex(24), "is_active": True, "last_triggered_at": None,
           "failure_count": 0, "created_at": now_iso()}
    await db.webhooks.insert_one(doc)
    return clean(doc)


@router.delete("/webhooks/{wid}", status_code=204)
async def v1_delete_webhook(wid: str, org: dict = Depends(get_org_from_api_key)):
    res = await db.webhooks.delete_one({"id": wid, "organization_id": org["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.webhook_deliveries.delete_many({"webhook_id": wid})
    return JSONResponse(status_code=204, content=None)


@router.get("/webhooks/{wid}/deliveries")
async def v1_webhook_deliveries(wid: str, org: dict = Depends(get_org_from_api_key)):
    hook = await db.webhooks.find_one({"id": wid, "organization_id": org["id"]})
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    items = await db.webhook_deliveries.find({"webhook_id": wid}, {"_id": 0}).sort("delivered_at", -1).to_list(100)
    return {"items": items}


@router.post("/webhooks/{wid}/test")
async def v1_test_webhook(wid: str, org: dict = Depends(get_org_from_api_key)):
    hook = await db.webhooks.find_one({"id": wid, "organization_id": org["id"]})
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await deliver_webhooks(org["id"], "video.completed", {"video": {"id": "vid_test", "status": "completed",
                           "output_url": "https://example.com/videos/vid_test.mp4", "duration_seconds": 12.3}})
    return {"message": "Test event dispatched"}
