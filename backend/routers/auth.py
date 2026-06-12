import os
import jwt
import secrets
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Response

from db import db
from core import (
    now_iso, gen_id, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    ACCESS_MIN, REFRESH_DAYS,
)
from deps import get_current_user, public_user
from seed import create_user_with_org
from schemas import RegisterReq, LoginReq, ForgotReq, ResetReq

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL_HOURS = 1


def set_auth_cookies(resp: Response, access: str, refresh: str):
    resp.set_cookie("access_token", access, httponly=True, secure=True, samesite="none",
                    max_age=ACCESS_MIN * 60, path="/")
    resp.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none",
                    max_age=REFRESH_DAYS * 86400, path="/")


@router.post("/register", status_code=201)
async def register(body: RegisterReq, response: Response):
    if await db.users.find_one({"email": body.email.lower().strip()}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user, org = await create_user_with_org(body.email, body.password, body.full_name or "")
    access = create_access_token(user["id"], user["email"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return {"user": public_user(user), "access_token": access, "refresh_token": refresh}


@router.post("/login")
async def login(body: LoginReq, response: Response):
    user = await db.users.find_one({"email": body.email.lower().strip()})
    if not user or not verify_password(body.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_iso()}})
    access = create_access_token(user["id"], user["email"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return {"user": public_user(user), "access_token": access, "refresh_token": refresh}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0})
    return {"user": user, "org": org}


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        try:
            body = await request.json()
        except Exception:
            body = None
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


@router.post("/forgot-password")
async def forgot_password(body: ForgotReq):
    user = await db.users.find_one({"email": body.email.lower().strip()})
    if user:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)).isoformat()
        await db.password_reset_tokens.insert_one({
            "id": gen_id("prt"), "user_id": user["id"], "token": token,
            "expires_at": expires_at, "used": False, "created_at": now_iso(),
        })
        logger.info(f"[PASSWORD RESET] token for {user['email']}: {token} (expires {expires_at})")
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(body: ResetReq):
    rec = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    try:
        expires = datetime.fromisoformat(rec["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    except Exception:
        expires = datetime.now(timezone.utc)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"hashed_password": hash_password(body.new_password)}})
    await db.password_reset_tokens.update_one({"id": rec["id"]}, {"$set": {"used": True}})
    return {"message": "Password updated"}
