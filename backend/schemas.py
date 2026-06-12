from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal


class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class ForgotReq(BaseModel):
    email: EmailStr


class ResetReq(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


class OrgUpdate(BaseModel):
    name: Optional[str] = None


class InviteCreate(BaseModel):
    email: EmailStr
    role: Literal["admin", "member", "viewer"] = "member"


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AvatarCreate(BaseModel):
    name: str
    source_type: Literal["image", "video", "stock"] = "image"
    source_asset_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class VoiceCreate(BaseModel):
    name: str
    language: str = "en"
    gender: Optional[str] = None
    engine: Literal["xtts", "f5-tts", "elevenlabs"] = "xtts"
    sample_audio_url: Optional[str] = None


class VideoCreate(BaseModel):
    avatar_id: str
    voice_id: str
    title: Optional[str] = None
    project_id: Optional[str] = None
    input_type: Literal["text", "audio"] = "text"
    script: Optional[str] = Field(None, max_length=10000)
    input_audio_url: Optional[str] = None
    resolution: Literal["720p", "1080p", "4k"] = "1080p"
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    background_type: Literal["solid", "image", "video", "transparent"] = "solid"
    background_value: Optional[str] = "#0A0A0A"
    settings: dict = Field(default_factory=dict)


class VideoPatch(BaseModel):
    title: Optional[str] = None


class ApiKeyCreate(BaseModel):
    name: str
    environment: Literal["live", "test"] = "live"


class WebhookCreate(BaseModel):
    url: str
    events: List[str] = Field(default_factory=lambda: ["video.completed", "video.failed"])


class CheckoutReq(BaseModel):
    plan: Literal["starter", "pro"]
    origin_url: str
