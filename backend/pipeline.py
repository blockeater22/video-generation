import asyncio
import json
import random
import logging

import httpx

from db import db
from core import now_iso, gen_id, sign_payload
from constants import SAMPLE_VIDEOS

logger = logging.getLogger(__name__)


async def deliver_webhooks(org_id: str, event_type: str, data: dict):
    hooks = await db.webhooks.find({"organization_id": org_id, "is_active": True}).to_list(100)
    for hook in hooks:
        if event_type not in hook.get("events", []):
            continue
        payload = {"id": gen_id("evt"), "type": event_type, "created_at": now_iso(), "data": data}
        body = json.dumps(payload).encode()
        status_code, resp_body, success = None, None, False
        try:
            async with httpx.AsyncClient(timeout=8) as cx:
                r = await cx.post(hook["url"], content=body, headers={
                    "Content-Type": "application/json",
                    "X-AvatarPlatform-Signature": sign_payload(body, hook["secret"]),
                })
                status_code, resp_body = r.status_code, r.text[:500]
                success = 200 <= r.status_code < 300
        except Exception as e:
            resp_body = str(e)[:500]
        await db.webhook_deliveries.insert_one({
            "id": gen_id("whd"), "webhook_id": hook["id"], "event_type": event_type,
            "payload": payload, "response_status": status_code, "response_body": resp_body,
            "delivered_at": now_iso(), "attempt_count": 1, "success": success,
        })
        await db.webhooks.update_one({"id": hook["id"]}, {"$set": {"last_triggered_at": now_iso()},
                                     "$inc": {"failure_count": 0 if success else 1}})


async def process_video_job(video_id: str, org_id: str):
    """Simulated generation pipeline: queued -> processing -> completed (TTS->LipSync->Compose)."""
    try:
        await asyncio.sleep(3)
        await db.videos.update_one({"id": video_id}, {"$set": {
            "status": "processing", "processing_started_at": now_iso(), "updated_at": now_iso()}})
        await asyncio.sleep(6)
        video = await db.videos.find_one({"id": video_id})
        if not video:
            return
        avatar = await db.avatars.find_one({"id": video.get("avatar_id")})
        thumb = avatar.get("thumbnail_url") if avatar else None
        duration = round(random.uniform(15, 60), 1)
        output_url = random.choice(SAMPLE_VIDEOS)
        await db.videos.update_one({"id": video_id}, {"$set": {
            "status": "completed", "output_url": output_url, "thumbnail_url": thumb,
            "duration_seconds": duration, "processing_completed_at": now_iso(), "updated_at": now_iso()}})
        await db.organizations.update_one({"id": org_id}, {"$inc": {"credits_used": 1}})
        await deliver_webhooks(org_id, "video.completed", {"video": {
            "id": video_id, "status": "completed", "output_url": output_url, "duration_seconds": duration}})
        logger.info(f"Video {video_id} completed")
    except Exception as e:
        logger.error(f"Video {video_id} failed: {e}")
        await db.videos.update_one({"id": video_id}, {"$set": {
            "status": "failed", "error_message": str(e), "updated_at": now_iso()}})
        await deliver_webhooks(org_id, "video.failed", {"video": {"id": video_id, "status": "failed"}})
