import os
import jwt
import bcrypt
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, Depends

JWT_ALGORITHM = "HS256"
ACCESS_MIN = 60
REFRESH_DAYS = 30


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def gen_id(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---------------- Passwords ----------------
def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------- JWT ----------------
def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MIN)}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "type": "refresh",
               "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS)}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])


# ---------------- API keys ----------------
def make_api_key(test: bool = False) -> str:
    prefix = "ap_test_" if test else "ap_live_"
    return prefix + secrets.token_hex(20)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------------- Webhook signature ----------------
def sign_payload(payload_bytes: bytes, secret: str) -> str:
    import hmac
    return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
