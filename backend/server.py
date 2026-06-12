from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
import logging
import random
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="AvatarPlatform API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Single-tenant default org (auth deferred per user request)
DEFAULT_ORG_ID = "org_default"

SAMPLE_VIDEOS = [
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
]

STOCK_AVATARS = [
    {"name": "Sofia (Professional)", "thumbnail_url": "https://images.unsplash.com/photo-1573497161161-c3e73707e25c?w=600&q=80", "gender": "female"},
    {"name": "Marcus (Corporate)", "thumbnail_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=600&q=80", "gender": "male"},
    {"name": "Aria (Presenter)", "thumbnail_url": "https://images.unsplash.com/photo-1685760259914-ee8d2c92d2e0?w=600&q=80", "gender": "female"},
    {"name": "Lena (Cinematic)", "thumbnail_url": "https://images.unsplash.com/photo-1532171875345-9712d9d4f65a?w=600&q=80", "gender": "female"},
    {"name": "David (Newsdesk)", "thumbnail_url": "https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=600&q=80", "gender": "male"},
    {"name": "Maya (Educator)", "thumbnail_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600&q=80", "gender": "female"},
]

STOCK_VOICES = [
    {"name": "Emma", "language": "en", "gender": "female", "engine": "xtts"},
    {"name": "James", "language": "en", "gender": "male", "engine": "xtts"},
    {"name": "Sophie", "language": "en", "gender": "female", "engine": "f5-tts"},
    {"name": "Carlos", "language": "es", "gender": "male", "engine": "xtts"},
    {"name": "Yuki", "language": "ja", "gender": "female", "engine": "xtts"},
    {"name": "Liam", "language": "en", "gender": "male", "engine": "f5-tts"},
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---------------------- Models ----------------------
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AvatarCreate(BaseModel):
    name: str
    source_type: Literal["image", "video", "stock"] = "image"
    source_asset_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class VoiceCreate(BaseModel):
    name: str
    language: str = "en"
    gender: Optional[str] = None
    engine: Literal["xtts", "f5-tts", "elevenlabs"] = "xtts"
    sample_audio_url: Optional[str] = None


class VideoCreate(BaseModel):
    avatar_id: str
    voice_id: str
    title: Optional[str] = None
    project_id: Optional[str] = None
    input_type: Literal["text", "audio"] = "text"
    script: Optional[str] = Field(None, max_length=10000)
    input_audio_url: Optional[str] = None
    resolution: Literal["720p", "1080p", "4k"] = "1080p"
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    background_type: Literal["solid", "image", "video", "transparent"] = "solid"
    background_value: Optional[str] = "#0A0A0A"
    settings: dict = Field(default_factory=dict)


class VideoPatch(BaseModel):
    title: Optional[str] = None


# ---------------------- Seed ----------------------
async def seed():
    org = await db.organizations.find_one({"id": DEFAULT_ORG_ID})
    if not org:
        await db.organizations.insert_one({
            "id": DEFAULT_ORG_ID,
            "name": "My Studio",
            "slug": "my-studio",
            "plan": "pro",
            "subscription_status": "active",
            "credits_used": 0,
            "credits_limit": 300,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        logger.info("Seeded default organization")

    if await db.avatars.count_documents({"organization_id": DEFAULT_ORG_ID}) == 0:
        for a in STOCK_AVATARS:
            await db.avatars.insert_one({
                "id": gen_id("avt"),
                "organization_id": DEFAULT_ORG_ID,
                "name": a["name"],
                "status": "ready",
                "source_type": "stock",
                "thumbnail_url": a["thumbnail_url"],
                "preview_video_url": random.choice(SAMPLE_VIDEOS),
                "metadata": {"gender": a["gender"]},
                "is_stock": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            })
        logger.info("Seeded stock avatars")

    if await db.voices.count_documents({"organization_id": DEFAULT_ORG_ID}) == 0:
        for v in STOCK_VOICES:
            await db.voices.insert_one({
                "id": gen_id("vce"),
                "organization_id": DEFAULT_ORG_ID,
                "name": v["name"],
                "status": "ready",
                "engine": v["engine"],
                "language": v["language"],
                "gender": v["gender"],
                "sample_audio_url": None,
                "is_stock": True,
                "created_at": now_iso(),
            })
        logger.info("Seeded stock voices")

    if await db.projects.count_documents({"organization_id": DEFAULT_ORG_ID}) == 0:
        await db.projects.insert_one({
            "id": gen_id("prj"),
            "organization_id": DEFAULT_ORG_ID,
            "name": "Default Project",
            "description": "Your first project",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })


def clean(doc):
    if doc and "_id" in doc:
        doc.pop("_id")
    return doc


async def get_org():
    org = await db.organizations.find_one({"id": DEFAULT_ORG_ID}, {"_id": 0})
    if not org:
        await seed()
        org = await db.organizations.find_one({"id": DEFAULT_ORG_ID}, {"_id": 0})
    return org


# ---------------------- Simulated generation pipeline ----------------------
async def process_video_job(video_id: str):
    try:
        await asyncio.sleep(3)
        await db.videos.update_one(
            {"id": video_id},
            {"$set": {"status": "processing", "processing_started_at": now_iso(), "updated_at": now_iso()}},
        )
        # Simulate ML pipeline (TTS -> LipSync -> Compose)
        await asyncio.sleep(6)
        video = await db.videos.find_one({"id": video_id})
        if not video:
            return
        avatar = await db.avatars.find_one({"id": video.get("avatar_id")})
        thumb = avatar.get("thumbnail_url") if avatar else None
        duration = round(random.uniform(15, 60), 1)
        output_url = random.choice(SAMPLE_VIDEOS)
        await db.videos.update_one(
            {"id": video_id},
            {"$set": {
                "status": "completed",
                "output_url": output_url,
                "thumbnail_url": thumb,
                "duration_seconds": duration,
                "processing_completed_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )
        await db.organizations.update_one({"id": DEFAULT_ORG_ID}, {"$inc": {"credits_used": 1}})
        logger.info(f"Video {video_id} completed")
    except Exception as e:
        logger.error(f"Video job {video_id} failed: {e}")
        await db.videos.update_one(
            {"id": video_id},
            {"$set": {"status": "failed", "error_message": str(e), "updated_at": now_iso()}},
        )


# ---------------------- Routes ----------------------
@api_router.get("/")
async def root():
    return {"message": "AvatarPlatform API", "status": "ok"}


@api_router.get("/org")
async def read_org():
    return await get_org()


@api_router.get("/dashboard/stats")
async def dashboard_stats():
    org = await get_org()
    videos = await db.videos.find({"organization_id": DEFAULT_ORG_ID}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    recent = videos[:5]

    # usage over last 30 days
    today = datetime.now(timezone.utc).date()
    buckets = {(today - timedelta(days=i)).isoformat(): 0 for i in range(29, -1, -1)}
    for v in videos:
        try:
            d = datetime.fromisoformat(v["created_at"]).date().isoformat()
            if d in buckets:
                buckets[d] += 1
        except Exception:
            pass
    usage = [{"date": k, "count": v} for k, v in buckets.items()]

    counts = {"total": len(videos), "completed": 0, "processing": 0, "queued": 0, "failed": 0}
    for v in videos:
        s = v.get("status", "queued")
        counts[s] = counts.get(s, 0) + 1

    avatars = await db.avatars.count_documents({"organization_id": DEFAULT_ORG_ID})
    voices = await db.voices.count_documents({"organization_id": DEFAULT_ORG_ID})

    return {
        "org": org,
        "recent_videos": recent,
        "usage_last_30_days": usage,
        "counts": counts,
        "totals": {"avatars": avatars, "voices": voices, "videos": len(videos)},
    }


# Projects
@api_router.get("/projects")
async def list_projects():
    return await db.projects.find({"organization_id": DEFAULT_ORG_ID}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/projects")
async def create_project(body: ProjectCreate):
    doc = {
        "id": gen_id("prj"),
        "organization_id": DEFAULT_ORG_ID,
        "name": body.name,
        "description": body.description,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.projects.insert_one(doc)
    return clean(doc)


@api_router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str):
    await db.projects.delete_one({"id": project_id, "organization_id": DEFAULT_ORG_ID})
    return JSONResponse(status_code=204, content=None)


# Avatars
@api_router.get("/avatars")
async def list_avatars():
    return await db.avatars.find({"organization_id": DEFAULT_ORG_ID}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/avatars")
async def create_avatar(body: AvatarCreate):
    doc = {
        "id": gen_id("avt"),
        "organization_id": DEFAULT_ORG_ID,
        "name": body.name,
        "status": "processing",
        "source_type": body.source_type,
        "source_asset_url": body.source_asset_url,
        "thumbnail_url": body.thumbnail_url or random.choice(STOCK_AVATARS)["thumbnail_url"],
        "preview_video_url": random.choice(SAMPLE_VIDEOS),
        "metadata": {},
        "is_stock": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.avatars.insert_one(doc)

    async def finish_avatar(aid):
        await asyncio.sleep(5)
        await db.avatars.update_one({"id": aid}, {"$set": {"status": "ready", "updated_at": now_iso()}})

    asyncio.create_task(finish_avatar(doc["id"]))
    return clean(doc)


@api_router.delete("/avatars/{avatar_id}", status_code=204)
async def delete_avatar(avatar_id: str):
    await db.avatars.delete_one({"id": avatar_id, "organization_id": DEFAULT_ORG_ID, "is_stock": False})
    return JSONResponse(status_code=204, content=None)


# Voices
@api_router.get("/voices")
async def list_voices():
    return await db.voices.find({"organization_id": DEFAULT_ORG_ID}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/voices")
async def create_voice(body: VoiceCreate):
    doc = {
        "id": gen_id("vce"),
        "organization_id": DEFAULT_ORG_ID,
        "name": body.name,
        "status": "ready",
        "engine": body.engine,
        "language": body.language,
        "gender": body.gender,
        "sample_audio_url": body.sample_audio_url,
        "is_stock": False,
        "created_at": now_iso(),
    }
    await db.voices.insert_one(doc)
    return clean(doc)


@api_router.delete("/voices/{voice_id}", status_code=204)
async def delete_voice(voice_id: str):
    await db.voices.delete_one({"id": voice_id, "organization_id": DEFAULT_ORG_ID, "is_stock": False})
    return JSONResponse(status_code=204, content=None)


# Videos
@api_router.get("/videos")
async def list_videos(project_id: Optional[str] = None, status: Optional[str] = None,
                      page: int = 1, per_page: int = 50):
    q = {"organization_id": DEFAULT_ORG_ID}
    if project_id:
        q["project_id"] = project_id
    if status:
        q["status"] = status
    total = await db.videos.count_documents(q)
    skip = (page - 1) * per_page
    items = await db.videos.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)
    return {"items": items, "total": total, "page": page, "per_page": per_page,
            "has_more": skip + len(items) < total}


@api_router.post("/videos", status_code=202)
async def create_video(body: VideoCreate):
    avatar = await db.avatars.find_one({"id": body.avatar_id, "organization_id": DEFAULT_ORG_ID})
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    voice = await db.voices.find_one({"id": body.voice_id, "organization_id": DEFAULT_ORG_ID})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    doc = {
        "id": gen_id("vid"),
        "organization_id": DEFAULT_ORG_ID,
        "project_id": body.project_id,
        "title": body.title or "Untitled Video",
        "status": "queued",
        "avatar_id": body.avatar_id,
        "voice_id": body.voice_id,
        "script": body.script,
        "input_type": body.input_type,
        "input_audio_url": body.input_audio_url,
        "output_url": None,
        "thumbnail_url": avatar.get("thumbnail_url"),
        "duration_seconds": None,
        "resolution": body.resolution,
        "aspect_ratio": body.aspect_ratio,
        "background_type": body.background_type,
        "background_value": body.background_value,
        "settings": body.settings,
        "error_message": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.videos.insert_one(doc)
    asyncio.create_task(process_video_job(doc["id"]))
    return clean(doc)


@api_router.get("/videos/{video_id}")
async def get_video(video_id: str):
    v = await db.videos.find_one({"id": video_id, "organization_id": DEFAULT_ORG_ID}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v


@api_router.patch("/videos/{video_id}")
async def update_video(video_id: str, body: VideoPatch):
    update = {k: val for k, val in body.model_dump(exclude_none=True).items()}
    update["updated_at"] = now_iso()
    await db.videos.update_one({"id": video_id, "organization_id": DEFAULT_ORG_ID}, {"$set": update})
    return await get_video(video_id)


@api_router.delete("/videos/{video_id}", status_code=204)
async def delete_video(video_id: str):
    await db.videos.delete_one({"id": video_id, "organization_id": DEFAULT_ORG_ID})
    return JSONResponse(status_code=204, content=None)


@api_router.post("/videos/{video_id}/retry")
async def retry_video(video_id: str):
    v = await db.videos.find_one({"id": video_id, "organization_id": DEFAULT_ORG_ID})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.videos.update_one(
        {"id": video_id},
        {"$set": {"status": "queued", "error_message": None, "output_url": None, "updated_at": now_iso()}},
    )
    asyncio.create_task(process_video_job(video_id))
    return await get_video(video_id)


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await seed()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
