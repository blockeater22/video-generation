from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id, make_api_key, hash_api_key
from deps import get_current_org, get_current_user, clean
from schemas import ApiKeyCreate

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("")
async def list_api_keys(org: dict = Depends(get_current_org)):
    return await db.api_keys.find({"organization_id": org["id"]}, {"_id": 0, "key_hash": 0}).sort("created_at", -1).to_list(200)


@router.post("", status_code=201)
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


@router.delete("/{kid}", status_code=204)
async def delete_api_key(kid: str, org: dict = Depends(get_current_org)):
    await db.api_keys.delete_one({"id": kid, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)
