import os
import logging
from pathlib import Path

from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from db import db, get_client
from seed import seed_admin, migrate_voices
from media_store import MEDIA_ROOT
from pipeline import ensure_workers
from routers import auth, orgs, projects, avatars, voices, videos, api_keys, webhooks, developer, billing

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AvatarPlatform API")

# Main /api router
api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"message": "AvatarPlatform API", "status": "ok"}


api.include_router(auth.router)
api.include_router(orgs.router)
api.include_router(projects.router)
api.include_router(avatars.router)
api.include_router(voices.router)
api.include_router(videos.router)
api.include_router(api_keys.router)
api.include_router(webhooks.router)
api.include_router(billing.router)
api.include_router(billing.webhook_router)  # -> /api/webhook/stripe

app.include_router(api)
app.include_router(developer.router)  # developer.router already prefixed with /api/v1
app.mount("/api/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")  # generated videos/audio/avatars

# CORS: avoid the invalid "*" + allow_credentials combo. When CORS_ORIGINS is "*",
# reflect any origin via regex (valid with credentials); otherwise use the explicit list.
cors_origins = os.environ.get("CORS_ORIGINS", "*").strip()
if cors_origins == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await seed_admin()
    await migrate_voices()
    ensure_workers()
    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown():
    get_client().close()
