import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, clean
from pipeline import deliver_webhooks
from schemas import WebhookCreate

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("")
async def list_webhooks(org: dict = Depends(get_current_org)):
    return await db.webhooks.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("", status_code=201)
async def create_webhook(body: WebhookCreate, org: dict = Depends(get_current_org)):
    doc = {"id": gen_id("whk"), "organization_id": org["id"], "url": body.url, "events": body.events,
           "secret": "whsec_" + secrets.token_hex(24), "is_active": True, "last_triggered_at": None,
           "failure_count": 0, "created_at": now_iso()}
    await db.webhooks.insert_one(doc)
    return clean(doc)


@router.delete("/{wid}", status_code=204)
async def delete_webhook(wid: str, org: dict = Depends(get_current_org)):
    await db.webhooks.delete_one({"id": wid, "organization_id": org["id"]})
    await db.webhook_deliveries.delete_many({"webhook_id": wid})
    return JSONResponse(status_code=204, content=None)


@router.get("/{wid}/deliveries")
async def webhook_deliveries(wid: str, org: dict = Depends(get_current_org)):
    hook = await db.webhooks.find_one({"id": wid, "organization_id": org["id"]})
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return await db.webhook_deliveries.find({"webhook_id": wid}, {"_id": 0}).sort("delivered_at", -1).to_list(100)


@router.post("/{wid}/test")
async def test_webhook(wid: str, org: dict = Depends(get_current_org)):
    hook = await db.webhooks.find_one({"id": wid, "organization_id": org["id"]})
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await deliver_webhooks(org["id"], "video.completed", {"video": {"id": "vid_test", "status": "completed",
                           "output_url": "https://example.com/videos/vid_test.mp4", "duration_seconds": 12.3}})
    return {"message": "Test event dispatched"}
