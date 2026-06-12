import os
from pathlib import Path

MEDIA_ROOT = Path(__file__).parent / "media"
for _sub in ("videos", "audio", "avatars", "voice_previews", "thumbnails"):
    (MEDIA_ROOT / _sub).mkdir(parents=True, exist_ok=True)


def public_url(rel: str) -> str:
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/api/media/{rel}"
