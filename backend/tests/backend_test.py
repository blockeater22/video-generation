"""AvatarPlatform backend tests - multi-tenant SaaS"""
import os, time, uuid, requests, pytest
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env", override=False)

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@avatarplatform.io"
ADMIN_PASS = "Admin123!"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


def _register(password="Test123!", name="Tester"):
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": password, "full_name": name})
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    body = r.json()
    return email, body["access_token"], body["user"]


# AUTH
class TestAuth:
    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_me(self, admin_headers):
        r = requests.get(f"{API}/auth/me", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == ADMIN_EMAIL
        assert d["org"]["id"] == d["user"]["org_id"]

    def test_unauth_avatars_401(self):
        r = requests.get(f"{API}/avatars")
        assert r.status_code == 401

    def test_register_autoseeds(self):
        _, token, _ = _register()
        h = {"Authorization": f"Bearer {token}"}
        assert len(requests.get(f"{API}/avatars", headers=h).json()) == 6
        assert len(requests.get(f"{API}/voices", headers=h).json()) == 6
        assert len(requests.get(f"{API}/projects", headers=h).json()) == 1

    def test_logout(self, admin_headers):
        r = requests.post(f"{API}/auth/logout", headers=admin_headers)
        assert r.status_code == 200


# Password reset
class TestPasswordReset:
    def test_forgot_password(self):
        email, _, _ = _register()
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200

    def test_reset_invalid_token_400(self):
        r = requests.post(f"{API}/auth/reset-password", json={"token": "INVALID_XYZ", "new_password": "NewPass1!"})
        assert r.status_code == 400

    def test_reset_valid_token_200(self):
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]
        email, _, _ = _register()
        requests.post(f"{API}/auth/forgot-password", json={"email": email})
        time.sleep(0.3)

        async def fetch():
            c = AsyncIOMotorClient(mongo_url)
            db = c[db_name]
            u = await db.users.find_one({"email": email})
            rec = await db.password_reset_tokens.find_one({"user_id": u["id"], "used": False})
            c.close()
            return rec["token"]

        token = asyncio.new_event_loop().run_until_complete(fetch())
        r = requests.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "NewPass1!"})
        assert r.status_code == 200, r.text


# Multi-tenancy
class TestMultiTenancy:
    def test_isolation(self):
        _, tokA, _ = _register()
        _, tokB, _ = _register()
        hA = {"Authorization": f"Bearer {tokA}", "Content-Type": "application/json"}
        hB = {"Authorization": f"Bearer {tokB}"}
        r = requests.post(f"{API}/projects", headers=hA, json={"name": "TEST_projA"})
        assert r.status_code == 200
        pid = r.json()["id"]
        listB = requests.get(f"{API}/projects", headers=hB).json()
        assert all(p["id"] != pid for p in listB)


# Dashboard
class TestDashboard:
    def test_stats(self, admin_headers):
        r = requests.get(f"{API}/dashboard/stats", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ("org", "recent_videos", "counts", "totals", "usage_last_30_days"):
            assert k in d
        assert len(d["usage_last_30_days"]) == 30


# CRUD
class TestCRUD:
    def test_avatar_create_delete(self, admin_headers):
        r = requests.post(f"{API}/avatars", headers=admin_headers, json={"name": "TEST_av", "source_type": "image"})
        assert r.status_code == 200
        aid = r.json()["id"]
        d = requests.delete(f"{API}/avatars/{aid}", headers=admin_headers)
        assert d.status_code == 204

    def test_stock_avatar_delete_400(self, admin_headers):
        avs = requests.get(f"{API}/avatars", headers=admin_headers).json()
        stock = next(a for a in avs if a.get("is_stock"))
        d = requests.delete(f"{API}/avatars/{stock['id']}", headers=admin_headers)
        assert d.status_code == 400

    def test_voice_create_delete(self, admin_headers):
        r = requests.post(f"{API}/voices", headers=admin_headers,
                          json={"name": "TEST_v", "engine": "neural", "language": "en", "gender": "female"})
        assert r.status_code == 200
        vid = r.json()["id"]
        d = requests.delete(f"{API}/voices/{vid}", headers=admin_headers)
        assert d.status_code == 204

    def test_stock_voice_delete_400(self, admin_headers):
        vs = requests.get(f"{API}/voices", headers=admin_headers).json()
        stock = next(v for v in vs if v.get("is_stock"))
        d = requests.delete(f"{API}/voices/{stock['id']}", headers=admin_headers)
        assert d.status_code == 400

    def test_project_create(self, admin_headers):
        r = requests.post(f"{API}/projects", headers=admin_headers, json={"name": "TEST_proj"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_proj"


# Videos lifecycle
class TestVideos:
    def test_full_lifecycle(self, admin_headers):
        avs = requests.get(f"{API}/avatars", headers=admin_headers).json()
        vcs = requests.get(f"{API}/voices", headers=admin_headers).json()
        me_before = requests.get(f"{API}/auth/me", headers=admin_headers).json()
        credits_before = me_before["org"].get("credits_used", 0)

        payload = {"avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"], "script": "TEST hello",
                   "title": "TEST_v", "resolution": "1080p", "aspect_ratio": "16:9",
                   "background_type": "color", "background_value": "#000"}
        c = requests.post(f"{API}/videos", headers=admin_headers, json=payload)
        assert c.status_code == 202, c.text
        vid = c.json()["id"]
        assert c.json()["status"] == "queued"

        completed = None
        for _ in range(25):
            time.sleep(1)
            g = requests.get(f"{API}/videos/{vid}", headers=admin_headers).json()
            if g["status"] == "completed":
                completed = g
                break
        assert completed, "video did not complete in 25s"
        assert completed["output_url"]
        assert completed["duration_seconds"] is not None

        me_after = requests.get(f"{API}/auth/me", headers=admin_headers).json()
        assert me_after["org"].get("credits_used", 0) > credits_before

        lst = requests.get(f"{API}/videos?status=completed", headers=admin_headers).json()
        assert any(v["id"] == vid for v in lst["items"])

        p = requests.patch(f"{API}/videos/{vid}", headers=admin_headers, json={"title": "TEST_renamed"})
        assert p.status_code == 200 and p.json()["title"] == "TEST_renamed"

        rt = requests.post(f"{API}/videos/{vid}/retry", headers=admin_headers)
        assert rt.status_code == 200

        d = requests.delete(f"{API}/videos/{vid}", headers=admin_headers)
        assert d.status_code == 204
        gone = requests.get(f"{API}/videos/{vid}", headers=admin_headers)
        assert gone.status_code == 404


# API Keys + Developer API
class TestApiKeys:
    def test_full(self, admin_headers):
        r = requests.post(f"{API}/api-keys", headers=admin_headers, json={"name": "TEST_key", "environment": "live"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert "key" in body and "key_prefix" in body
        assert "key_hash" not in body
        plaintext = body["key"]
        kid = body["id"]

        lst = requests.get(f"{API}/api-keys", headers=admin_headers).json()
        for k in lst:
            assert "key_hash" not in k and "key" not in k

        h = {"Authorization": f"Bearer {plaintext}"}
        assert requests.get(f"{BASE_URL}/api/v1/avatars", headers=h).status_code == 200
        assert requests.get(f"{BASE_URL}/api/v1/voices", headers=h).status_code == 200

        avs = requests.get(f"{API}/avatars", headers=admin_headers).json()
        vcs = requests.get(f"{API}/voices", headers=admin_headers).json()
        post = requests.post(f"{BASE_URL}/api/v1/videos", headers=h, json={
            "avatar_id": avs[0]["id"], "voice_id": vcs[0]["id"], "script": "TEST_v1",
            "resolution": "1080p", "aspect_ratio": "16:9",
            "background_type": "color", "background_value": "#fff"})
        assert post.status_code == 202, post.text

        d = requests.delete(f"{API}/api-keys/{kid}", headers=admin_headers)
        assert d.status_code == 204


# Webhooks
class TestWebhooks:
    def test_crud_and_test(self, admin_headers):
        r = requests.post(f"{API}/webhooks", headers=admin_headers,
                          json={"url": "https://example.com/hook", "events": ["video.completed"]})
        assert r.status_code == 201, r.text
        wid = r.json()["id"]

        lst = requests.get(f"{API}/webhooks", headers=admin_headers).json()
        assert any(w["id"] == wid for w in lst)

        t = requests.post(f"{API}/webhooks/{wid}/test", headers=admin_headers)
        assert t.status_code == 200
        time.sleep(1.5)
        deliveries = requests.get(f"{API}/webhooks/{wid}/deliveries", headers=admin_headers).json()
        assert isinstance(deliveries, list) and len(deliveries) >= 1

        d = requests.delete(f"{API}/webhooks/{wid}", headers=admin_headers)
        assert d.status_code == 204


# Billing
class TestBilling:
    def test_plans(self, admin_headers):
        r = requests.get(f"{API}/billing/plans", headers=admin_headers)
        assert r.status_code == 200
        plans = r.json()["plans"]
        assert len(plans) == 4
        assert {p["id"] for p in plans} == {"free", "starter", "pro", "enterprise"}

    def test_checkout(self, admin_headers):
        r = requests.post(f"{API}/billing/checkout", headers=admin_headers,
                          json={"plan": "pro", "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "url" in d and "session_id" in d and d["url"].startswith("http")


# Team
class TestTeam:
    def test_members_invites(self, admin_headers):
        ms = requests.get(f"{API}/members", headers=admin_headers).json()
        assert any(m["role"] == "owner" for m in ms)

        inv = requests.post(f"{API}/invitations", headers=admin_headers,
                            json={"email": f"TEST_{uuid.uuid4().hex[:6]}@x.com", "role": "member"})
        assert inv.status_code == 200, inv.text
        iid = inv.json()["id"]

        lst = requests.get(f"{API}/invitations", headers=admin_headers).json()
        assert any(i["id"] == iid for i in lst)

        d = requests.delete(f"{API}/invitations/{iid}", headers=admin_headers)
        assert d.status_code == 204
