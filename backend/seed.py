import os
import random
import logging

from db import db
from core import now_iso, gen_id, hash_password, verify_password
from constants import STOCK_AVATARS, STOCK_VOICES, SAMPLE_VIDEOS, PLAN_CREDITS

logger = logging.getLogger(__name__)


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
