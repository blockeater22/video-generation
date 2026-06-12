import logging
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from schemas import OrgUpdate, InviteCreate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["organization"])


@router.get("/org")
async def read_org(org: dict = Depends(get_current_org)):
    return org


@router.patch("/org")
async def update_org(body: OrgUpdate, org: dict = Depends(get_current_org)):
    upd = body.model_dump(exclude_none=True)
    upd["updated_at"] = now_iso()
    await db.organizations.update_one({"id": org["id"]}, {"$set": upd})
    return await db.organizations.find_one({"id": org["id"]}, {"_id": 0})


@router.get("/dashboard/stats")
async def dashboard_stats(org: dict = Depends(get_current_org)):
    videos = await db.videos.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    recent = videos[:5]
    today = datetime.now(timezone.utc).date()
    buckets = {(today - timedelta(days=i)).isoformat(): 0 for i in range(29, -1, -1)}
    counts = {"total": len(videos), "completed": 0, "processing": 0, "queued": 0, "failed": 0}
    for v in videos:
        try:
            d = datetime.fromisoformat(v["created_at"]).date().isoformat()
            if d in buckets:
                buckets[d] += 1
        except Exception:
            pass
        s = v.get("status", "queued")
        counts[s] = counts.get(s, 0) + 1
    usage = [{"date": k, "count": v} for k, v in buckets.items()]
    avatars = await db.avatars.count_documents({"organization_id": org["id"]})
    voices = await db.voices.count_documents({"organization_id": org["id"]})
    return {"org": org, "recent_videos": recent, "usage_last_30_days": usage, "counts": counts,
            "totals": {"avatars": avatars, "voices": voices, "videos": len(videos)}}


@router.get("/members")
async def list_members(org: dict = Depends(get_current_org)):
    mems = await db.organization_members.find({"organization_id": org["id"]}, {"_id": 0}).to_list(200)
    out = []
    for m in mems:
        u = await db.users.find_one({"id": m["user_id"]}, {"_id": 0, "hashed_password": 0})
        if u:
            out.append({"role": m["role"], "joined_at": m["joined_at"],
                        "email": u["email"], "full_name": u.get("full_name"), "user_id": u["id"]})
    return out


@router.get("/invitations")
async def list_invitations(org: dict = Depends(get_current_org)):
    return await db.invitations.find({"organization_id": org["id"], "accepted_at": None}, {"_id": 0}).to_list(200)


@router.post("/invitations")
async def create_invitation(body: InviteCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {
        "id": gen_id("inv"), "organization_id": org["id"], "email": body.email.lower(),
        "role": body.role, "token": secrets.token_urlsafe(24), "invited_by": user["id"],
        "accepted_at": None, "created_at": now_iso(),
    }
    await db.invitations.insert_one(doc)
    logger.info(f"[INVITE] {body.email} to org {org['id']} token={doc['token']}")
    return clean(doc)


@router.delete("/invitations/{inv_id}", status_code=204)
async def delete_invitation(inv_id: str, org: dict = Depends(get_current_org)):
    await db.invitations.delete_one({"id": inv_id, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)
