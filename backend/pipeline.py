"""Real video generation pipeline.

Job flow: queued -> processing (tts -> render -> compose) -> completed | failed.
Priority queue by plan (enterprise > pro > starter > free), N async workers,
real OpenAI TTS + ffmpeg avatar animation render, webhook delivery with
exponential-backoff retries.
"""
import asyncio
import json
import logging

import httpx

from db import db
from core import now_iso, gen_id, sign_payload
from constants import OPENAI_VOICE_FALLBACK
from media_store import MEDIA_ROOT, public_url
from engine.tts import synthesize_speech
from engine.renderer import render_video

logger = logging.getLogger(__name__)

PLAN_PRIORITY = {"enterprise": 0, "pro": 1, "starter": 2, "free": 3}
WORKERS = 2
WEBHOOK_RETRY_DELAYS = [30, 120, 600, 1800]  # seconds between retries (max 5 attempts)

_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
_seq = 0
_workers_started = False


class PipelineError(Exception):
    """User-facing pipeline failure."""


# ---------------- Webhooks (with retry/backoff) ----------------
async def _attempt_delivery(hook: dict, payload: dict, attempt: int, next_retry_in) -> bool:
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
        "id": gen_id("whd"), "webhook_id": hook["id"], "event_type": payload["type"],
        "payload": payload, "response_status": status_code, "response_body": resp_body,
        "delivered_at": now_iso(), "attempt_count": attempt, "success": success,
        "next_retry_at": None if (success or next_retry_in is None) else f"in {next_retry_in}s",
    })
    await db.webhooks.update_one({"id": hook["id"]}, {
        "$set": {"last_triggered_at": now_iso()},
        "$inc": {"failure_count": 0 if success else 1},
    })
    return success


async def _deliver_with_retry(hook: dict, payload: dict):
    max_attempts = len(WEBHOOK_RETRY_DELAYS) + 1
    for attempt in range(1, max_attempts + 1):
        delay = WEBHOOK_RETRY_DELAYS[attempt - 1] if attempt < max_attempts else None
        ok = await _attempt_delivery(hook, payload, attempt, delay)
        if ok or delay is None:
            return
        await asyncio.sleep(delay)


async def deliver_webhooks(org_id: str, event_type: str, data: dict):
    hooks = await db.webhooks.find({"organization_id": org_id, "is_active": True}).to_list(100)
    for hook in hooks:
        if event_type not in hook.get("events", []):
            continue
        payload = {"id": gen_id("evt"), "type": event_type, "created_at": now_iso(), "data": data}
        asyncio.create_task(_deliver_with_retry(hook, payload))


# ---------------- Job queue ----------------
def ensure_workers():
    global _workers_started
    if not _workers_started:
        for _ in range(WORKERS):
            asyncio.create_task(_worker())
        _workers_started = True
        logger.info(f"Started {WORKERS} pipeline workers")


async def process_video_job(video_id: str, org_id: str):
    """Enqueue a video generation job, prioritized by plan."""
    global _seq
    ensure_workers()
    org = await db.organizations.find_one({"id": org_id})
    prio = PLAN_PRIORITY.get((org or {}).get("plan", "free"), 3)
    _seq += 1
    await db.videos.update_one({"id": video_id}, {"$set": {
        "status": "queued", "pipeline_stage": "queued", "progress": 0, "updated_at": now_iso()}})
    await _queue.put((prio, _seq, video_id, org_id))


async def _worker():
    while True:
        _, _, vid, org_id = await _queue.get()
        try:
            await _run_job(vid, org_id)
        except Exception:
            logger.exception(f"Worker crashed on video {vid}")
        finally:
            _queue.task_done()


async def _set(vid: str, **fields):
    fields["updated_at"] = now_iso()
    await db.videos.update_one({"id": vid}, {"$set": fields})


async def _download_audio(url: str, path) -> str:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as cx:
        r = await cx.get(url)
        r.raise_for_status()
        if not r.content:
            raise PipelineError("Input audio file is empty")
    with open(path, "wb") as f:
        f.write(r.content)
    return str(path)


async def _run_job(video_id: str, org_id: str):
    video = await db.videos.find_one({"id": video_id})
    if not video or video.get("status") != "queued":
        return
    org = await db.organizations.find_one({"id": org_id})
    try:
        if org and org.get("credits_used", 0) >= org.get("credits_limit", 0):
            raise PipelineError("Monthly credit limit reached. Upgrade your plan to generate more videos.")

        avatar = await db.avatars.find_one({"id": video.get("avatar_id")})
        voice = await db.voices.find_one({"id": video.get("voice_id")})
        avatar_src = (avatar or {}).get("source_asset_path") or (avatar or {}).get("thumbnail_url")
        if not avatar_src:
            raise PipelineError("Avatar has no source image")

        # --- Stage 1: TTS (real speech) ---
        await _set(video_id, status="processing", pipeline_stage="tts", progress=10,
                   processing_started_at=now_iso(), error_message=None)
        audio_path = MEDIA_ROOT / "audio" / f"{video_id}.mp3"
        settings = video.get("settings") or {}
        try:
            speed = min(2.0, max(0.5, float(settings.get("speed", 1.0) or 1.0)))
        except (TypeError, ValueError):
            speed = 1.0

        if video.get("input_type") == "audio" and video.get("input_audio_url"):
            await _download_audio(video["input_audio_url"], audio_path)
        else:
            script = (video.get("script") or "").strip()
            if not script:
                raise PipelineError("Script is empty — write something for your avatar to say.")
            openai_voice = (voice or {}).get("openai_voice") or \
                OPENAI_VOICE_FALLBACK.get((voice or {}).get("gender") or "", "alloy")
            await synthesize_speech(script, voice=openai_voice, speed=speed, out_path=audio_path)

        # --- Stage 2: Render (lip-animated avatar + background + captions) ---
        await _set(video_id, pipeline_stage="render", progress=40)
        out_path = MEDIA_ROOT / "videos" / f"{video_id}.mp4"
        thumb_path = MEDIA_ROOT / "thumbnails" / f"{video_id}.jpg"
        watermark = (org or {}).get("plan", "free") == "free"
        meta = await asyncio.to_thread(
            render_video, avatar_src, str(audio_path), str(out_path), str(thumb_path),
            resolution=video.get("resolution", "1080p"),
            aspect_ratio=video.get("aspect_ratio", "16:9"),
            background_type=video.get("background_type", "solid"),
            background_value=video.get("background_value") or "#0A0A0A",
            captions_enabled=bool(settings.get("caption_enabled", True)),
            script=video.get("script") or "",
            watermark=watermark,
        )

        # --- Stage 3: Publish ---
        await _set(video_id, pipeline_stage="compose", progress=90)
        output_url = public_url(f"videos/{video_id}.mp4")
        thumb_url = public_url(f"thumbnails/{video_id}.jpg")
        await _set(video_id, status="completed", pipeline_stage="done", progress=100,
                   output_url=output_url, thumbnail_url=thumb_url,
                   duration_seconds=meta["duration_seconds"],
                   processing_completed_at=now_iso(), error_message=None)
        await db.organizations.update_one({"id": org_id}, {"$inc": {"credits_used": 1}})
        await deliver_webhooks(org_id, "video.completed", {"video": {
            "id": video_id, "status": "completed", "output_url": output_url,
            "duration_seconds": meta["duration_seconds"]}})
        logger.info(f"Video {video_id} completed ({meta['duration_seconds']}s)")
    except Exception as e:
        msg = str(e) if isinstance(e, PipelineError) else f"Generation failed: {e}"
        logger.error(f"Video {video_id} failed: {msg}")
        await _set(video_id, status="failed", pipeline_stage="failed", error_message=msg[:500])
        await deliver_webhooks(org_id, "video.failed", {"video": {
            "id": video_id, "status": "failed", "error": msg[:300]}})
