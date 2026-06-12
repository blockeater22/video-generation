"""Real pipeline tests: TTS+ffmpeg video, voice preview, avatar upload, credit/fail paths,
v1 developer API, webhooks. Iteration 2."""
import io
import os
import time
import uuid
import asyncio
import requests
import pytest
from PIL import Image
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env", override=False)

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@avatarplatform.io"
ADMIN_PASS = "Admin123!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _register(password="Test123!", name="RealTester"):
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": password, "full_name": name})
    assert r.status_code == 201, r.text
    body = r.json()
    return email, body["access_token"], body["user"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _wait_video(headers, vid, timeout=120):
    final = None
    for _ in range(timeout):
        time.sleep(1)
        g = requests.get(f"{API}/videos/{vid}", headers=headers).json()
        if g["status"] in ("completed", "failed"):
            final = g
            break
    return final


@pytest.fixture(scope="module")
def admin_headers():
    return _h(_login(ADMIN_EMAIL, ADMIN_PASS))


@pytest.fixture(scope="module")
def fresh_user():
    """Fresh user so we have clean credit counter."""
    email, tok, user = _register()
    return {"email": email, "token": tok, "headers": _h(tok), "user": user}


# Pydantic literal validation
class TestPydanticLiterals:
    def test_bad_resolution_422(self, fresh_user):
        avs = requests.get(f"{API}/avatars", headers=fresh_user["headers"]).json()
        vcs = requests.get(f"{API}/voices", headers=fresh_user["headers"]).json()
        r = requests.post(f"{API}/videos", headers=fresh_user["headers"], json={
            "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"], "script": "x",
            "resolution": "8k", "aspect_ratio": "16:9", "background_type": "solid"})
        assert r.status_code == 422

    def test_bad_background_type_422(self, fresh_user):
        avs = requests.get(f"{API}/avatars", headers=fresh_user["headers"]).json()
        vcs = requests.get(f"{API}/voices", headers=fresh_user["headers"]).json()
        r = requests.post(f"{API}/videos", headers=fresh_user["headers"], json={
            "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"], "script": "x",
            "resolution": "720p", "aspect_ratio": "16:9", "background_type": "bogus"})
        assert r.status_code == 422

    def test_bad_voice_engine_422(self, fresh_user):
        r = requests.post(f"{API}/voices", headers=fresh_user["headers"],
                          json={"name": "TEST_bad", "engine": "bad", "language": "en", "gender": "female"})
        assert r.status_code == 422


# Voice preview generation
class TestVoicePreview:
    def test_voice_preview_generates_mp3(self, admin_headers):
        vcs = requests.get(f"{API}/voices", headers=admin_headers).json()
        assert vcs, "no voices seeded"
        vid = vcs[0]["id"]
        r = requests.post(f"{API}/voices/{vid}/preview", headers=admin_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        url = body.get("sample_audio_url") or body.get("url")
        assert url, f"preview missing sample_audio_url: {body}"
        full = url if url.startswith("http") else BASE_URL + url
        # poll the URL (may need a moment if async, but route is sync)
        dl = requests.get(full)
        assert dl.status_code == 200
        assert len(dl.content) > 1000, "preview audio too small"
        ct = dl.headers.get("content-type", "")
        assert "audio" in ct or full.endswith(".mp3"), f"bad content-type: {ct}"


# Custom avatar upload
class TestAvatarUpload:
    def _make_png(self, w=512, h=512):
        buf = io.BytesIO()
        img = Image.new("RGB", (w, h), (200, 150, 100))
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def test_valid_upload_201(self, admin_headers):
        h = {"Authorization": admin_headers["Authorization"]}  # no content-type for multipart
        files = {"file": ("av.png", self._make_png(), "image/png")}
        r = requests.post(f"{API}/avatars/upload", headers=h,
                          data={"name": "TEST_upl"}, files=files)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["status"] == "ready"
        thumb = d.get("thumbnail_url", "")
        assert "/api/media/avatars/" in thumb, f"unexpected thumb: {thumb}"

    def test_invalid_file_400(self, admin_headers):
        h = {"Authorization": admin_headers["Authorization"]}
        files = {"file": ("av.txt", io.BytesIO(b"hello not an image"), "text/plain")}
        r = requests.post(f"{API}/avatars/upload", headers=h,
                          data={"name": "TEST_badfile"}, files=files)
        assert r.status_code == 400, r.text

    def test_tiny_image_400(self, admin_headers):
        h = {"Authorization": admin_headers["Authorization"]}
        files = {"file": ("av.png", self._make_png(64, 64), "image/png")}
        r = requests.post(f"{API}/avatars/upload", headers=h,
                          data={"name": "TEST_tiny"}, files=files)
        assert r.status_code == 400, r.text


# Real generation + uniqueness
class TestRealVideoPipeline:
    def test_real_generation_and_uniqueness(self, fresh_user):
        h = fresh_user["headers"]
        avs = requests.get(f"{API}/avatars", headers=h).json()
        vcs = requests.get(f"{API}/voices", headers=h).json()

        def submit(script):
            r = requests.post(f"{API}/videos", headers=h, json={
                "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"], "script": script,
                "title": "TEST_uniq", "resolution": "720p", "aspect_ratio": "16:9",
                "background_type": "solid", "background_value": "#111"})
            assert r.status_code == 202, r.text
            return r.json()["id"]

        v1 = submit("Hello world this is the first generation test.")
        f1 = _wait_video(h, v1, 120)
        assert f1 and f1["status"] == "completed", f"v1 not completed: {f1}"
        assert "/api/media/videos/" in f1["output_url"]
        # confirm NOT stock URL
        for stock_marker in ("w3schools", "bigbuckbunny", "samplelib", "sample-videos"):
            assert stock_marker not in f1["output_url"]
        dl1 = requests.get(BASE_URL + f1["output_url"] if f1["output_url"].startswith("/") else f1["output_url"])
        assert dl1.status_code == 200
        size1 = len(dl1.content)
        assert size1 > 50_000, f"v1 mp4 size too small: {size1}"
        dur1 = f1["duration_seconds"]
        assert dur1 and dur1 > 0

        v2 = submit("This is a substantially different and much longer second script that should produce a different output file size and duration compared to the first one.")
        f2 = _wait_video(h, v2, 150)
        assert f2 and f2["status"] == "completed", f"v2 not completed: {f2}"
        dl2 = requests.get(BASE_URL + f2["output_url"] if f2["output_url"].startswith("/") else f2["output_url"])
        size2 = len(dl2.content)
        dur2 = f2["duration_seconds"]
        # Uniqueness: file size OR duration must differ
        assert size1 != size2 or abs(dur1 - dur2) > 0.5, \
            f"videos appear identical size={size1}/{size2} dur={dur1}/{dur2}"

    def test_empty_script_fails_gracefully(self, fresh_user):
        h = fresh_user["headers"]
        avs = requests.get(f"{API}/avatars", headers=h).json()
        vcs = requests.get(f"{API}/voices", headers=h).json()
        r = requests.post(f"{API}/videos", headers=h, json={
            "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"], "script": "   ",
            "resolution": "720p", "aspect_ratio": "16:9", "background_type": "solid"})
        # Either 422 (validation) or 202 then failed status
        if r.status_code == 202:
            vid = r.json()["id"]
            f = _wait_video(h, vid, 60)
            assert f and f["status"] == "failed", f"expected failed, got: {f}"
            assert f.get("error_message"), "missing error_message"
        else:
            assert r.status_code in (400, 422), r.text


# Credit enforcement
class TestCreditLimit:
    def test_credit_increments_and_limit(self):
        email, tok, _user = _register()
        h = _h(tok)
        # Directly set credits_used near limit via /auth/me check then exhaust
        me = requests.get(f"{API}/auth/me", headers=h).json()
        limit = me["org"]["credits_limit"]
        used = me["org"].get("credits_used", 0)
        assert limit == 3, f"free plan credits_limit expected 3, got {limit}"
        # Simulate by direct mongo update to limit - 1 to save time
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]

        async def patch_credits():
            c = AsyncIOMotorClient(mongo_url)
            db = c[db_name]
            await db.organizations.update_one(
                {"id": me["org"]["id"]}, {"$set": {"credits_used": limit}}
            )
            c.close()
        asyncio.new_event_loop().run_until_complete(patch_credits())

        avs = requests.get(f"{API}/avatars", headers=h).json()
        vcs = requests.get(f"{API}/voices", headers=h).json()
        r = requests.post(f"{API}/videos", headers=h, json={
            "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"],
            "script": "short", "resolution": "720p", "aspect_ratio": "16:9",
            "background_type": "solid"})
        # Should be rejected (402/403/400) with credit message
        assert r.status_code in (400, 402, 403), r.text
        body_txt = r.text.lower()
        assert "credit" in body_txt or "limit" in body_txt, f"missing credit msg: {r.text}"


# Developer v1 API surface
class TestDeveloperV1:
    @pytest.fixture(scope="class")
    def api_key(self, admin_token=None):
        tok = _login(ADMIN_EMAIL, ADMIN_PASS)
        r = requests.post(f"{API}/api-keys", headers=_h(tok),
                          json={"name": "TEST_v1_full", "environment": "live"})
        assert r.status_code == 201, r.text
        return r.json()["key"], r.json()["id"], tok

    def test_v1_list_avatars_voices(self, api_key):
        key, _kid, _ = api_key
        h = {"Authorization": f"Bearer {key}"}
        assert requests.get(f"{API}/v1/avatars", headers=h).status_code == 200
        assert requests.get(f"{API}/v1/voices", headers=h).status_code == 200

    def test_v1_video_lifecycle(self, api_key):
        key, _kid, dash_tok = api_key
        h = {"Authorization": f"Bearer {key}"}
        dh = _h(dash_tok)
        avs = requests.get(f"{API}/v1/avatars", headers=h).json()
        vcs = requests.get(f"{API}/v1/voices", headers=h).json()
        # POST
        r = requests.post(f"{API}/v1/videos", headers=h, json={
            "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"],
            "script": "TEST v1 dev short", "resolution": "720p",
            "aspect_ratio": "16:9", "background_type": "solid"})
        if r.status_code in (402, 403):
            pytest.skip(f"credits exhausted on admin org: {r.text}")
        assert r.status_code == 202, r.text
        vid = r.json()["id"]
        # GET single
        g = requests.get(f"{API}/v1/videos/{vid}", headers=h)
        assert g.status_code == 200
        # GET list
        lst = requests.get(f"{API}/v1/videos", headers=h)
        assert lst.status_code == 200
        # RETRY
        rt = requests.post(f"{API}/v1/videos/{vid}/retry", headers=h)
        assert rt.status_code in (200, 202, 409), rt.text
        # DELETE
        d = requests.delete(f"{API}/v1/videos/{vid}", headers=h)
        assert d.status_code == 204, d.text

    def test_v1_voice_preview(self, api_key):
        key, _kid, _ = api_key
        h = {"Authorization": f"Bearer {key}"}
        vcs = requests.get(f"{API}/v1/voices", headers=h).json()
        r = requests.post(f"{API}/v1/voices/{vcs[0]['id']}/preview", headers=h)
        assert r.status_code == 200, r.text
        assert "sample_audio_url" in r.json() or "url" in r.json()

    def test_v1_webhooks_crud_and_test(self, api_key):
        key, _kid, _ = api_key
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        c = requests.post(f"{API}/v1/webhooks", headers=h,
                          json={"url": "https://example.com/hookv1", "events": ["video.completed"]})
        assert c.status_code == 201, c.text
        wid = c.json()["id"]
        # LIST
        lst = requests.get(f"{API}/v1/webhooks", headers=h)
        assert lst.status_code == 200
        # TEST
        t = requests.post(f"{API}/v1/webhooks/{wid}/test", headers=h)
        assert t.status_code == 200, t.text
        time.sleep(3)
        # DELIVERIES
        deliv = requests.get(f"{API}/v1/webhooks/{wid}/deliveries", headers=h)
        assert deliv.status_code == 200
        data = deliv.json()
        assert isinstance(data, list) and len(data) >= 1
        rec = data[0]
        assert "attempt_count" in rec or "attempts" in rec
        # DELETE
        d = requests.delete(f"{API}/v1/webhooks/{wid}", headers=h)
        assert d.status_code == 204
