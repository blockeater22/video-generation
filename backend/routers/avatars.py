import random
from io import BytesIO

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from constants import STOCK_AVATARS
from media_store import MEDIA_ROOT, public_url
from engine.renderer import detect_face
from schemas import AvatarCreate

router = APIRouter(prefix="/avatars", tags=["avatars"])

MAX_DIM = 1280
MAX_UPLOAD = 15 * 1024 * 1024


def process_image_bytes(data: bytes, aid: str) -> dict:
    """Validate + normalize an avatar source image, detect face, save locally."""
    try:
        img = Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="File is not a valid image")
    if img.width < 256 or img.height < 256:
        raise HTTPException(status_code=400, detail="Image too small — minimum 256x256 pixels")
    if max(img.size) > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    face = detect_face(img)
    path = MEDIA_ROOT / "avatars" / f"{aid}.jpg"
    img.save(path, quality=90)
    return {"path": str(path), "url": public_url(f"avatars/{aid}.jpg"),
            "face_detected": face is not None, "width": img.width, "height": img.height}


@router.get("")
async def list_avatars(org: dict = Depends(get_current_org)):
    return await db.avatars.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("")
async def create_avatar(body: AvatarCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    """Create avatar from an image URL. Downloads + processes the source when reachable."""
    aid = gen_id("avt")
    src = body.source_asset_url or body.thumbnail_url
    thumb, local_path, face_detected = body.thumbnail_url, None, None
    if src and src.startswith("http"):
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as cx:
                r = await cx.get(src, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
            info = process_image_bytes(r.content, aid)
            local_path, thumb, face_detected = info["path"], info["url"], info["face_detected"]
        except Exception:
            pass  # keep the remote URL as-is; renderer will fetch at generation time
    if not thumb:
        thumb = random.choice(STOCK_AVATARS)["thumbnail_url"]
    doc = {"id": aid, "organization_id": org["id"], "name": body.name, "status": "ready",
           "source_type": body.source_type, "source_asset_url": body.source_asset_url,
           "source_asset_path": local_path, "thumbnail_url": thumb, "preview_video_url": None,
           "metadata": {"face_detected": face_detected}, "is_stock": False,
           "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.avatars.insert_one(doc)
    return clean(doc)


@router.post("/upload", status_code=201)
async def upload_avatar(name: str = Form(...), file: UploadFile = File(...),
                        org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    """Create a custom avatar from an uploaded photo (validated + face-detected)."""
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="Image must be under 15MB")
    aid = gen_id("avt")
    info = process_image_bytes(data, aid)
    doc = {"id": aid, "organization_id": org["id"], "name": name, "status": "ready",
           "source_type": "image", "source_asset_url": None, "source_asset_path": info["path"],
           "thumbnail_url": info["url"], "preview_video_url": None,
           "metadata": {"face_detected": info["face_detected"], "width": info["width"], "height": info["height"]},
           "is_stock": False, "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.avatars.insert_one(doc)
    return clean(doc)


@router.delete("/{aid}", status_code=204)
async def delete_avatar(aid: str, org: dict = Depends(get_current_org)):
    avatar = await db.avatars.find_one({"id": aid, "organization_id": org["id"]})
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if avatar.get("is_stock"):
        raise HTTPException(status_code=400, detail="Stock avatars cannot be deleted")
    await db.avatars.delete_one({"id": aid})
    return JSONResponse(status_code=204, content=None)
