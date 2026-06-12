import os
import asyncio
import logging
import random
import json
from pathlib import Path
from typing import List, Optional, Literal

from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from core import (
    now_iso, gen_id, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    make_api_key, hash_api_key, sign_payload,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]

app = FastAPI(title="AvatarPlatform API")
api = APIRouter(prefix="/api")

# ---------------- constants ----------------
PLAN_CREDITS = {"free": 3, "starter": 50, "pro": 300, "enterprise": 1_000_000}
PLAN_PRICES = {"starter": 29.00, "pro": 99.00}

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


# ============================================================
# Seeding helpers
# ============================================================
async def seed_org_stock(org_id: str, user_id: str):
    for a in STOCK_AVATARS:
        await db.avatars.insert_one({
            "id": gen_id("avt"), "organization_id": org_id, "name": a["name"], "status": "ready",
            "source_type": "stock", "thumbnail_url": a["thumbnail_url"],
            "preview_video_url": random.choice(SAMPLE_VIDEOS), "metadata": {"gender": a["gender"]},
            "is_stock": True, "created_by": user_id, "created_at": now_iso(), "updated_at": now_iso(),
        })
    for v in STOCK_VOICES:
        await db.voices.insert_one({
            "id": gen_id("vce"), "organization_id": org_id, "name": v["name"], "status": "ready",
            "engine": v["engine"], "language": v["language"], "gender": v["gender"],
            "sample_audio_url": None, "is_stock": True, "created_by": user_id, "created_at": now_iso(),
        })
    await db.projects.insert_one({
        "id": gen_id("prj"), "organization_id": org_id, "name": "Default Project",
        "description": "Your first project", "created_by": user_id,
        "created_at": now_iso(), "updated_at": now_iso(),
    })


async def create_user_with_org(email: str, password: str, full_name: str, is_superadmin=False):
    email = email.lower().strip()
    uid = gen_id("usr")
    oid = gen_id("org")
    slug = (full_name or email.split("@")[0]).lower().replace(" ", "-")[:40] + "-" + uid[-4:]
    user = {
        "id": uid, "email": email, "full_name": full_name or email.split("@")[0],
        "hashed_password": hash_password(password), "email_verified": True,
        "is_active": True, "is_superadmin": is_superadmin, "org_id": oid,
        "avatar_url": None, "created_at": now_iso(), "updated_at": now_iso(),
    }
    org = {
        "id": oid, "name": (full_name.split(" ")[0] + "'s Studio") if full_name else "My Studio",
        "slug": slug, "logo_url": None, "plan": "free", "subscription_status": "trialing",
        "stripe_customer_id": None, "stripe_subscription_id": None, "current_period_end": None,
        "credits_used": 0, "credits_limit": PLAN_CREDITS["free"], "created_by": uid,
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.users.insert_one(user)
    await db.organizations.insert_one(org)
    await db.organization_members.insert_one({
        "id": gen_id("mem"), "organization_id": oid, "user_id": uid, "role": "owner",
        "invited_by": None, "joined_at": now_iso(),
    })
    await seed_org_stock(oid, uid)
    return user, org


async def seed_admin():
    email = os.environ.get("ADMIN_EMAIL", "admin@avatarplatform.io").lower()
    password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    existing = await db.users.find_one({"email": email})
    if not existing:
        await create_user_with_org(email, password, "Admin", is_superadmin=True)
        logger.info("Seeded admin user")
    elif not verify_password(password, existing.get("hashed_password", "")):
        await db.users.update_one({"email": email}, {"$set": {"hashed_password": hash_password(password)}})


def clean(doc):
    if doc and "_id" in doc:
        doc.pop("_id")
    return doc


def public_user(u: dict) -> dict:
    u = dict(u)
    u.pop("_id", None)
    u.pop("hashed_password", None)
    return u


# ============================================================
# Dependencies
# ============================================================
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return public_user(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


import jwt  # noqa: E402  (for exception classes above)


async def get_current_org(user: dict = Depends(get_current_user)) -> dict:
    org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def get_org_from_api_key(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    key = auth[7:]
    rec = await db.api_keys.find_one({"key_hash": hash_api_key(key), "is_active": True})
    if not rec:
        raise HTTPException(status_code=401, detail="Invalid API key")
    await db.api_keys.update_one({"id": rec["id"]}, {"$set": {"last_used_at": now_iso()}})
    org = await db.organizations.find_one({"id": rec["organization_id"]}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=401, detail="Organization not found")
    return org


# ============================================================
# Schemas
# ============================================================
class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class ForgotReq(BaseModel):
    email: EmailStr


class ResetReq(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


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


class ApiKeyCreate(BaseModel):
    name: str
    environment: Literal["live", "test"] = "live"


class WebhookCreate(BaseModel):
    url: str
    events: List[str] = Field(default_factory=lambda: ["video.completed", "video.failed"])


class InviteCreate(BaseModel):
    email: EmailStr
    role: Literal["admin", "member", "viewer"] = "member"


class CheckoutReq(BaseModel):
    plan: Literal["starter", "pro"]
    origin_url: str


class OrgUpdate(BaseModel):
    name: Optional[str] = None


# ============================================================
# Webhook delivery
# ============================================================
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


# ============================================================
# Simulated generation pipeline
# ============================================================
async def process_video_job(video_id: str, org_id: str):
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


# ============================================================
# AUTH ROUTES
# ============================================================
def set_auth_cookies(resp: Response, access: str, refresh: str):
    resp.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=ACCESS_MIN * 60, path="/")
    resp.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=REFRESH_DAYS * 86400, path="/")


from core import ACCESS_MIN, REFRESH_DAYS  # noqa: E402


@api.post("/auth/register", status_code=201)
async def register(body: RegisterReq, response: Response):
    if await db.users.find_one({"email": body.email.lower().strip()}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user, org = await create_user_with_org(body.email, body.password, body.full_name or "")
    access = create_access_token(user["id"], user["email"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return {"user": public_user(user), "access_token": access, "refresh_token": refresh}


@api.post("/auth/login")
async def login(body: LoginReq, response: Response):
    user = await db.users.find_one({"email": body.email.lower().strip()})
    if not user or not verify_password(body.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_iso()}})
    access = create_access_token(user["id"], user["email"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return {"user": public_user(user), "access_token": access, "refresh_token": refresh}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0})
    return {"user": user, "org": org}


@api.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        body = None
        try:
            body = await request.json()
        except Exception:
            pass
        token = (body or {}).get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["id"], user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none",
                            max_age=ACCESS_MIN * 60, path="/")
        return {"access_token": access}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotReq):
    user = await db.users.find_one({"email": body.email.lower().strip()})
    if user:
        import secrets as _s
        token = _s.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "id": gen_id("prt"), "user_id": user["id"], "token": token,
            "expires_at": now_iso(), "used": False, "created_at": now_iso(),
        })
        logger.info(f"[PASSWORD RESET] link token for {user['email']}: {token}")
    return {"message": "If that email exists, a reset link has been sent"}


@api.post("/auth/reset-password")
async def reset_password(body: ResetReq):
    rec = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"hashed_password": hash_password(body.new_password)}})
    await db.password_reset_tokens.update_one({"id": rec["id"]}, {"$set": {"used": True}})
    return {"message": "Password updated"}


# ============================================================
# ORG / DASHBOARD / TEAM
# ============================================================
@api.get("/org")
async def read_org(org: dict = Depends(get_current_org)):
    return org


@api.patch("/org")
async def update_org(body: OrgUpdate, org: dict = Depends(get_current_org)):
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    await db.organizations.update_one({"id": org["id"]}, {"$set": upd})
    return await db.organizations.find_one({"id": org["id"]}, {"_id": 0})


@api.get("/dashboard/stats")
async def dashboard_stats(org: dict = Depends(get_current_org)):
    from datetime import datetime as dt, timezone as tz, timedelta as td
    videos = await db.videos.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    recent = videos[:5]
    today = dt.now(tz.utc).date()
    buckets = {(today - td(days=i)).isoformat(): 0 for i in range(29, -1, -1)}
    for v in videos:
        try:
            d = dt.fromisoformat(v["created_at"]).date().isoformat()
            if d in buckets:
                buckets[d] += 1
        except Exception:
            pass
    usage = [{"date": k, "count": v} for k, v in buckets.items()]
    counts = {"total": len(videos), "completed": 0, "processing": 0, "queued": 0, "failed": 0}
    for v in videos:
        s = v.get("status", "queued")
        counts[s] = counts.get(s, 0) + 1
    avatars = await db.avatars.count_documents({"organization_id": org["id"]})
    voices = await db.voices.count_documents({"organization_id": org["id"]})
    return {"org": org, "recent_videos": recent, "usage_last_30_days": usage, "counts": counts,
            "totals": {"avatars": avatars, "voices": voices, "videos": len(videos)}}


@api.get("/members")
async def list_members(org: dict = Depends(get_current_org)):
    mems = await db.organization_members.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    out = []
    for m in mems:
        u = await db.users.find_one({"id": m["user_id"]}, {"_id": 0, "hashed_password": 0})
        if u:
            out.append({"role": m["role"], "joined_at": m["joined_at"],
                        "email": u["email"], "full_name": u.get("full_name"), "user_id": u["id"]})
    return out


@api.get("/invitations")
async def list_invitations(org: dict = Depends(get_current_org)):
    return await db.invitations.find({"organization_id": org["id"], "accepted_at": None}, {"_id": 0}).to_list(200)


@api.post("/invitations")
async def create_invitation(body: InviteCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    import secrets as _s
    doc = {
        "id": gen_id("inv"), "organization_id": org["id"], "email": body.email.lower(),
        "role": body.role, "token": _s.token_urlsafe(24), "invited_by": user["id"],
        "accepted_at": None, "created_at": now_iso(),
    }
    await db.invitations.insert_one(doc)
    logger.info(f"[INVITE] {body.email} to org {org['id']} token={doc['token']}")
    return clean(doc)


@api.delete("/invitations/{inv_id}", status_code=204)
async def delete_invitation(inv_id: str, org: dict = Depends(get_current_org)):
    await db.invitations.delete_one({"id": inv_id, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)


# ============================================================
# PROJECTS
# ============================================================
@api.get("/projects")
async def list_projects(org: dict = Depends(get_current_org)):
    return await db.projects.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/projects")
async def create_project(body: ProjectCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {"id": gen_id("prj"), "organization_id": org["id"], "name": body.name,
           "description": body.description, "created_by": user["id"],
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.projects.insert_one(doc)
    return clean(doc)


@api.delete("/projects/{pid}", status_code=204)
async def delete_project(pid: str, org: dict = Depends(get_current_org)):
    await db.projects.delete_one({"id": pid, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)


# ============================================================
# AVATARS
# ============================================================
@api.get("/avatars")
async def list_avatars(org: dict = Depends(get_current_org)):
    return await db.avatars.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/avatars")
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


@api.delete("/avatars/{aid}")
async def delete_avatar(aid: str, org: dict = Depends(get_current_org)):
    avatar = await db.avatars.find_one({"id": aid, "organization_id": org["id"]})
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if avatar.get("is_stock"):
        raise HTTPException(status_code=400, detail="Stock avatars cannot be deleted")
    await db.avatars.delete_one({"id": aid})
    return {"message": "deleted"}


# ============================================================
# VOICES
# ============================================================
@api.get("/voices")
async def list_voices(org: dict = Depends(get_current_org)):
    return await db.voices.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/voices")
async def create_voice(body: VoiceCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {"id": gen_id("vce"), "organization_id": org["id"], "name": body.name, "status": "ready",
           "engine": body.engine, "language": body.language, "gender": body.gender,
           "sample_audio_url": body.sample_audio_url, "is_stock": False,
           "created_by": user["id"], "created_at": now_iso()}
    await db.voices.insert_one(doc)
    return clean(doc)


@api.delete("/voices/{vid}")
async def delete_voice(vid: str, org: dict = Depends(get_current_org)):
    voice = await db.voices.find_one({"id": vid, "organization_id": org["id"]})
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    if voice.get("is_stock"):
        raise HTTPException(status_code=400, detail="Stock voices cannot be deleted")
    await db.voices.delete_one({"id": vid})
    return {"message": "deleted"}


# ============================================================
# VIDEOS
# ============================================================
async def _create_video(org_id: str, user_id: str, body: VideoCreate):
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


@api.get("/videos")
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


@api.post("/videos", status_code=202)
async def create_video(body: VideoCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    return await _create_video(org["id"], user["id"], body)


@api.get("/videos/{vid}")
async def get_video(vid: str, org: dict = Depends(get_current_org)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v


@api.patch("/videos/{vid}")
async def update_video(vid: str, body: VideoPatch, org: dict = Depends(get_current_org)):
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    await db.videos.update_one({"id": vid, "organization_id": org["id"]}, {"$set": upd})
    return await get_video(vid, org)


@api.delete("/videos/{vid}", status_code=204)
async def delete_video(vid: str, org: dict = Depends(get_current_org)):
    await db.videos.delete_one({"id": vid, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)


@api.post("/videos/{vid}/retry")
async def retry_video(vid: str, org: dict = Depends(get_current_org)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.videos.update_one({"id": vid}, {"$set": {"status": "queued", "error_message": None,
                               "output_url": None, "updated_at": now_iso()}})
    asyncio.create_task(process_video_job(vid, org["id"]))
    return await get_video(vid, org)


# ============================================================
# API KEYS
# ============================================================
@api.get("/api-keys")
async def list_api_keys(org: dict = Depends(get_current_org)):
    keys = await db.api_keys.find({"organization_id": org["id"]}, {"_id": 0, "key_hash": 0}).sort("created_at", -1).to_list(200)
    return keys


@api.post("/api-keys", status_code=201)
async def create_api_key(body: ApiKeyCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    raw = make_api_key(test=body.environment == "test")
    doc = {"id": gen_id("key"), "organization_id": org["id"], "name": body.name,
           "key_hash": hash_api_key(raw), "key_prefix": raw[:12],
           "scopes": ["video:read", "video:write", "avatar:read", "voice:read"],
           "last_used_at": None, "created_by": user["id"], "is_active": True, "created_at": now_iso()}
    await db.api_keys.insert_one(doc)
    out = clean(dict(doc))
    out.pop("key_hash", None)
    out["key"] = raw  # plaintext returned ONCE
    return out


@api.delete("/api-keys/{kid}", status_code=204)
async def delete_api_key(kid: str, org: dict = Depends(get_current_org)):
    await db.api_keys.delete_one({"id": kid, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)


# ============================================================
# WEBHOOKS
# ============================================================
@api.get("/webhooks")
async def list_webhooks(org: dict = Depends(get_current_org)):
    return await db.webhooks.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.post("/webhooks", status_code=201)
async def create_webhook(body: WebhookCreate, org: dict = Depends(get_current_org)):
    import secrets as _s
    doc = {"id": gen_id("whk"), "organization_id": org["id"], "url": body.url, "events": body.events,
           "secret": "whsec_" + _s.token_hex(24), "is_active": True, "last_triggered_at": None,
           "failure_count": 0, "created_at": now_iso()}
    await db.webhooks.insert_one(doc)
    return clean(doc)


@api.delete("/webhooks/{wid}", status_code=204)
async def delete_webhook(wid: str, org: dict = Depends(get_current_org)):
    await db.webhooks.delete_one({"id": wid, "organization_id": org["id"]})
    await db.webhook_deliveries.delete_many({"webhook_id": wid})
    return JSONResponse(status_code=204, content=None)


@api.get("/webhooks/{wid}/deliveries")
async def webhook_deliveries(wid: str, org: dict = Depends(get_current_org)):
    hook = await db.webhooks.find_one({"id": wid, "organization_id": org["id"]})
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return await db.webhook_deliveries.find({"webhook_id": wid}, {"_id": 0}).sort("delivered_at", -1).to_list(100)


@api.post("/webhooks/{wid}/test")
async def test_webhook(wid: str, org: dict = Depends(get_current_org)):
    hook = await db.webhooks.find_one({"id": wid, "organization_id": org["id"]})
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await deliver_webhooks(org["id"], "video.completed", {"video": {"id": "vid_test", "status": "completed",
                           "output_url": SAMPLE_VIDEOS[0], "duration_seconds": 12.3}})
    return {"message": "Test event dispatched"}


# ============================================================
# DEVELOPER API (/api/v1, API key auth)
# ============================================================
v1 = APIRouter(prefix="/api/v1", tags=["developer"])


@v1.get("/videos")
async def v1_list_videos(org: dict = Depends(get_org_from_api_key)):
    items = await db.videos.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items, "total": len(items)}


@v1.post("/videos", status_code=202)
async def v1_create_video(body: VideoCreate, org: dict = Depends(get_org_from_api_key)):
    return await _create_video(org["id"], org.get("created_by", "api"), body)


@v1.get("/videos/{vid}")
async def v1_get_video(vid: str, org: dict = Depends(get_org_from_api_key)):
    v = await db.videos.find_one({"id": vid, "organization_id": org["id"]}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v


@v1.get("/avatars")
async def v1_list_avatars(org: dict = Depends(get_org_from_api_key)):
    items = await db.avatars.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}


@v1.get("/voices")
async def v1_list_voices(org: dict = Depends(get_org_from_api_key)):
    items = await db.voices.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    return {"items": items}


# ============================================================
# BILLING (Stripe)
# ============================================================
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest  # noqa: E402


@api.get("/billing/plans")
async def billing_plans():
    return {
        "plans": [
            {"id": "free", "name": "Free", "price": 0, "credits": PLAN_CREDITS["free"], "resolution": "720p", "api": False, "members": 1},
            {"id": "starter", "name": "Starter", "price": 29, "credits": PLAN_CREDITS["starter"], "resolution": "1080p", "api": True, "members": 3},
            {"id": "pro", "name": "Pro", "price": 99, "credits": PLAN_CREDITS["pro"], "resolution": "1080p + 4K", "api": True, "members": 10},
            {"id": "enterprise", "name": "Enterprise", "price": None, "credits": "Unlimited", "resolution": "4K", "api": True, "members": "Unlimited"},
        ]
    }


@api.post("/billing/checkout")
async def billing_checkout(body: CheckoutReq, request: Request, org: dict = Depends(get_current_org)):
    amount = PLAN_PRICES[body.plan]
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)
    success_url = f"{body.origin_url}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{body.origin_url}/billing"
    req = CheckoutSessionRequest(amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url,
                                 metadata={"org_id": org["id"], "plan": body.plan})
    session = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": gen_id("pay"), "session_id": session.session_id, "organization_id": org["id"],
        "plan": body.plan, "amount": amount, "currency": "usd", "payment_status": "initiated",
        "status": "open", "processed": False, "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api.get("/billing/status/{session_id}")
async def billing_status(session_id: str, request: Request, org: dict = Depends(get_current_org)):
    host_url = str(request.base_url)
    stripe = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=f"{host_url}api/webhook/stripe")
    status = await stripe.get_checkout_status(session_id)
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if tx and status.payment_status == "paid" and not tx.get("processed"):
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
            "payment_status": status.payment_status, "status": status.status, "processed": True}})
        plan = tx["plan"]
        await db.organizations.update_one({"id": tx["organization_id"]}, {"$set": {
            "plan": plan, "subscription_status": "active", "credits_limit": PLAN_CREDITS[plan], "updated_at": now_iso()}})
    elif tx:
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
            "payment_status": status.payment_status, "status": status.status}})
    return {"payment_status": status.payment_status, "status": status.status, "plan": tx["plan"] if tx else None}


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    host_url = str(request.base_url)
    stripe = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=f"{host_url}api/webhook/stripe")
    try:
        resp = await stripe.handle_webhook(body, request.headers.get("Stripe-Signature"))
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"received": False}
    if resp.payment_status == "paid" and resp.metadata:
        oid = resp.metadata.get("org_id")
        plan = resp.metadata.get("plan")
        tx = await db.payment_transactions.find_one({"session_id": resp.session_id})
        if oid and plan and tx and not tx.get("processed"):
            await db.payment_transactions.update_one({"session_id": resp.session_id}, {"$set": {
                "payment_status": "paid", "status": "complete", "processed": True}})
            await db.organizations.update_one({"id": oid}, {"$set": {
                "plan": plan, "subscription_status": "active", "credits_limit": PLAN_CREDITS[plan], "updated_at": now_iso()}})
    return {"received": True}


# ============================================================
# Mount + lifecycle
# ============================================================
@api.get("/")
async def root():
    return {"message": "AvatarPlatform API", "status": "ok"}


app.include_router(api)
app.include_router(v1)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await seed_admin()
    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown():
    client.close()
