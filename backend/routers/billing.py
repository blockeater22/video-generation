import os
import logging
from fastapi import APIRouter, Depends, Request

from db import db
from core import now_iso, gen_id
from deps import get_current_org
from constants import PLAN_CREDITS, PLAN_PRICES
from schemas import CheckoutReq

from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])
webhook_router = APIRouter(tags=["billing-webhook"])


def _webhook_url(default_base: str) -> str:
    """Public webhook URL. Configurable via STRIPE_WEBHOOK_URL, else derived from a public base."""
    configured = os.environ.get("STRIPE_WEBHOOK_URL")
    if configured:
        return configured
    return f"{default_base.rstrip('/')}/api/webhook/stripe"


def _stripe(webhook_url: str) -> StripeCheckout:
    return StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)


@router.get("/plans")
async def billing_plans():
    return {"plans": [
        {"id": "free", "name": "Free", "price": 0, "credits": PLAN_CREDITS["free"], "resolution": "720p", "api": False, "members": 1},
        {"id": "starter", "name": "Starter", "price": 29, "credits": PLAN_CREDITS["starter"], "resolution": "1080p", "api": True, "members": 3},
        {"id": "pro", "name": "Pro", "price": 99, "credits": PLAN_CREDITS["pro"], "resolution": "1080p + 4K", "api": True, "members": 10},
        {"id": "enterprise", "name": "Enterprise", "price": None, "credits": "Unlimited", "resolution": "4K", "api": True, "members": "Unlimited"},
    ]}


@router.post("/checkout")
async def billing_checkout(body: CheckoutReq, org: dict = Depends(get_current_org)):
    amount = PLAN_PRICES[body.plan]
    # Webhook URL is derived from the PUBLIC origin sent by the frontend (or env override),
    # never from request.base_url which is the internal cluster address.
    stripe = _stripe(_webhook_url(body.origin_url))
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


async def _apply_plan(org_id: str, plan: str):
    await db.organizations.update_one({"id": org_id}, {"$set": {
        "plan": plan, "subscription_status": "active", "credits_limit": PLAN_CREDITS[plan], "updated_at": now_iso()}})


@router.get("/status/{session_id}")
async def billing_status(session_id: str, request: Request, org: dict = Depends(get_current_org)):
    stripe = _stripe(_webhook_url(str(request.base_url)))
    status = await stripe.get_checkout_status(session_id)
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if tx and status.payment_status == "paid" and not tx.get("processed"):
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
            "payment_status": status.payment_status, "status": status.status, "processed": True}})
        await _apply_plan(tx["organization_id"], tx["plan"])
    elif tx:
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
            "payment_status": status.payment_status, "status": status.status}})
    return {"payment_status": status.payment_status, "status": status.status, "plan": tx["plan"] if tx else None}


@webhook_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    stripe = _stripe(_webhook_url(str(request.base_url)))
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
            await _apply_plan(oid, plan)
    return {"received": True}
