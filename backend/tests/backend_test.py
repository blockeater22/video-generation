"""Backend tests for AvatarPlatform - single tenant, no auth."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://avatar-saas.preview.emergentagent.com').rstrip('/')
# Read from frontend/.env if env not set
if 'REACT_APP_BACKEND_URL' not in os.environ:
    try:
        with open('/app/frontend/.env') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
    except Exception:
        pass

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- Health / root ---
def test_root(s):
    r = s.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_org(s):
    r = s.get(f"{API}/org")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "org_default"
    assert "credits_used" in data
    assert "credits_limit" in data


# --- Dashboard ---
def test_dashboard_stats(s):
    r = s.get(f"{API}/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert "org" in data
    assert "recent_videos" in data and isinstance(data["recent_videos"], list)
    assert "usage_last_30_days" in data
    assert len(data["usage_last_30_days"]) == 30
    assert "counts" in data
    for k in ["total", "completed", "processing", "queued", "failed"]:
        assert k in data["counts"]
    assert "totals" in data
    for k in ["avatars", "voices", "videos"]:
        assert k in data["totals"]


# --- Avatars & Voices seed ---
def test_list_avatars_seed(s):
    r = s.get(f"{API}/avatars")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    stock = [a for a in items if a.get("is_stock")]
    assert len(stock) >= 6


def test_list_voices_seed(s):
    r = s.get(f"{API}/voices")
    assert r.status_code == 200
    items = r.json()
    stock = [v for v in items if v.get("is_stock")]
    assert len(stock) >= 6


# --- Projects CRUD ---
def test_projects_crud(s):
    r = s.get(f"{API}/projects")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = s.post(f"{API}/projects", json={"name": "TEST_proj", "description": "test"})
    assert r.status_code == 200
    pid = r.json()["id"]
    assert r.json()["name"] == "TEST_proj"

    # verify present
    r = s.get(f"{API}/projects")
    assert any(p["id"] == pid for p in r.json())

    # delete
    r = s.delete(f"{API}/projects/{pid}")
    assert r.status_code == 204
    r = s.get(f"{API}/projects")
    assert not any(p["id"] == pid for p in r.json())


# --- Avatars CRUD + processing -> ready ---
def test_avatar_create_processing_then_ready(s):
    r = s.post(f"{API}/avatars", json={"name": "TEST_avatar", "source_type": "image"})
    assert r.status_code == 200
    a = r.json()
    aid = a["id"]
    assert a["status"] == "processing"
    assert a["is_stock"] is False

    # wait for ready (~5s)
    ready = False
    for _ in range(20):
        time.sleep(1)
        items = s.get(f"{API}/avatars").json()
        cur = next((x for x in items if x["id"] == aid), None)
        if cur and cur["status"] == "ready":
            ready = True
            break
    assert ready, "Avatar did not become ready within 20s"

    # delete (non-stock)
    r = s.delete(f"{API}/avatars/{aid}")
    assert r.status_code == 204


def test_avatar_delete_stock_noop(s):
    items = s.get(f"{API}/avatars").json()
    stock = next(x for x in items if x.get("is_stock"))
    r = s.delete(f"{API}/avatars/{stock['id']}")
    assert r.status_code == 204
    # should still exist
    items2 = s.get(f"{API}/avatars").json()
    assert any(x["id"] == stock["id"] for x in items2)


# --- Voices CRUD ---
def test_voice_create_and_delete(s):
    r = s.post(f"{API}/voices", json={"name": "TEST_voice", "language": "en", "engine": "xtts"})
    assert r.status_code == 200
    v = r.json()
    vid = v["id"]
    assert v["is_stock"] is False
    assert v["status"] == "ready"

    r = s.delete(f"{API}/voices/{vid}")
    assert r.status_code == 204


def test_voice_delete_stock_noop(s):
    items = s.get(f"{API}/voices").json()
    stock = next(x for x in items if x.get("is_stock"))
    r = s.delete(f"{API}/voices/{stock['id']}")
    assert r.status_code == 204
    items2 = s.get(f"{API}/voices").json()
    assert any(x["id"] == stock["id"] for x in items2)


# --- Videos full lifecycle ---
def test_video_invalid_avatar_404(s):
    voice = next(v for v in s.get(f"{API}/voices").json() if v.get("is_stock"))
    r = s.post(f"{API}/videos", json={
        "avatar_id": "avt_nonexistent",
        "voice_id": voice["id"],
        "script": "hi",
    })
    assert r.status_code == 404


def test_video_invalid_voice_404(s):
    avatar = next(a for a in s.get(f"{API}/avatars").json() if a.get("is_stock"))
    r = s.post(f"{API}/videos", json={
        "avatar_id": avatar["id"],
        "voice_id": "vce_nonexistent",
        "script": "hi",
    })
    assert r.status_code == 404


def test_video_full_lifecycle(s):
    avatar = next(a for a in s.get(f"{API}/avatars").json() if a.get("is_stock"))
    voice = next(v for v in s.get(f"{API}/voices").json() if v.get("is_stock"))

    org_before = s.get(f"{API}/org").json()
    credits_before = org_before["credits_used"]

    r = s.post(f"{API}/videos", json={
        "avatar_id": avatar["id"],
        "voice_id": voice["id"],
        "title": "TEST_video",
        "script": "Hello world!",
        "resolution": "1080p",
        "aspect_ratio": "16:9",
    })
    assert r.status_code == 202
    v = r.json()
    assert v["status"] == "queued"
    vid = v["id"]

    # GET single
    r = s.get(f"{API}/videos/{vid}")
    assert r.status_code == 200

    # Wait for completion (~10s)
    completed = None
    for _ in range(25):
        time.sleep(1)
        cur = s.get(f"{API}/videos/{vid}").json()
        if cur["status"] == "completed":
            completed = cur
            break
    assert completed is not None, "Video did not complete in 25s"
    assert completed["output_url"], "output_url missing on completed video"
    assert completed["duration_seconds"]

    # Credits incremented
    org_after = s.get(f"{API}/org").json()
    assert org_after["credits_used"] == credits_before + 1

    # List with status filter
    r = s.get(f"{API}/videos", params={"status": "completed"})
    assert r.status_code == 200
    data = r.json()
    assert any(x["id"] == vid for x in data["items"])

    # PATCH title
    r = s.patch(f"{API}/videos/{vid}", json={"title": "TEST_renamed"})
    assert r.status_code == 200
    assert r.json()["title"] == "TEST_renamed"

    # Retry -> queued -> completed
    r = s.post(f"{API}/videos/{vid}/retry")
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    re_completed = False
    for _ in range(25):
        time.sleep(1)
        cur = s.get(f"{API}/videos/{vid}").json()
        if cur["status"] == "completed":
            re_completed = True
            break
    assert re_completed

    # Delete
    r = s.delete(f"{API}/videos/{vid}")
    assert r.status_code == 204
    r = s.get(f"{API}/videos/{vid}")
    assert r.status_code == 404


def test_videos_list_pagination(s):
    r = s.get(f"{API}/videos", params={"page": 1, "per_page": 10})
    assert r.status_code == 200
    d = r.json()
    for k in ["items", "total", "page", "per_page", "has_more"]:
        assert k in d
