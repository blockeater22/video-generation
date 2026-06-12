import jwt
from fastapi import Request, HTTPException, Depends

from db import db
from core import decode_token, hash_api_key, now_iso


def clean(doc):
    if doc and "_id" in doc:
        doc.pop("_id")
    return doc


def public_user(u: dict) -> dict:
    u = dict(u)
    u.pop("_id", None)
    u.pop("hashed_password", None)
    return u


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
