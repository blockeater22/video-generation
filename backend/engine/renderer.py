"""Avatar video renderer — audio-driven lip/jaw animation composited with ffmpeg.

Pipeline: avatar image -> face detection (OpenCV) -> pre-rendered jaw-open states
-> per-frame selection driven by the speech audio RMS envelope -> background,
captions, watermark -> raw RGB frames piped into ffmpeg -> H.264 MP4.
"""
import math
import subprocess
import tempfile
import wave
from io import BytesIO
from pathlib import Path

import cv2
import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FPS = 25
RES_H = {"720p": 720, "1080p": 1080, "4k": 2160}
RENDER_CAP = 1080  # render internally at <=1080p, ffmpeg upscales for 4k
N_STATES = 7

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

_cascade = None


def _font(size: int):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def video_dims(resolution: str, aspect_ratio: str):
    h = RES_H.get(resolution, 1080)
    ratios = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0}
    w = int(round(h * ratios.get(aspect_ratio, 16 / 9)))
    return w - w % 2, h - h % 2


def load_image(src: str) -> Image.Image:
    if src and str(src).startswith("http"):
        r = httpx.get(src, timeout=25, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (AvatarPlatform renderer)"})
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
    else:
        img = Image.open(src)
    return img.convert("RGB")


def detect_face(img: Image.Image):
    """Returns (x, y, w, h) of the largest detected face, or None."""
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    faces = _cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return int(x), int(y), int(w), int(h)


def audio_envelope(wav_path: str, fps: int = FPS) -> np.ndarray:
    """Per-video-frame normalized RMS amplitude of the speech audio."""
    with wave.open(str(wav_path), "rb") as wf:
        sr, n, ch = wf.getframerate(), wf.getnframes(), wf.getnchannels()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32)
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    spf = max(1, int(sr / fps))
    n_frames = max(1, int(math.ceil(len(data) / spf)))
    env = np.zeros(n_frames)
    for i in range(n_frames):
        seg = data[i * spf:(i + 1) * spf]
        if len(seg):
            env[i] = np.sqrt(np.mean(seg ** 2))
    env = np.convolve(env, np.array([0.25, 0.5, 0.25]), mode="same")
    ref = max(float(np.percentile(env, 95)), 1e-6)
    return np.clip(env / ref, 0.0, 1.0)


def build_mouth_states(avatar: Image.Image, face):
    """Pre-render N avatar variants with progressively opened jaw + inner-mouth shadow."""
    if not face:
        return [avatar] * N_STATES
    x, y, w, h = face
    lip_top = int(y + h * 0.66)
    chin = min(avatar.height, int(y + h * 1.08))
    band_h = chin - lip_top
    if band_h <= 4:
        return [avatar] * N_STATES
    cx = x + w // 2
    mouth_cy = int(y + h * 0.80)
    states = [avatar]
    for k in range(1, N_STATES):
        o = k / (N_STATES - 1)
        drop = max(1, int(round(o * h * 0.055)))
        im = avatar.copy()
        band = avatar.crop((0, lip_top, avatar.width, chin)).resize(
            (avatar.width, band_h + drop), Image.BILINEAR)
        im.paste(band, (0, lip_top))
        below = avatar.crop((0, chin, avatar.width, avatar.height))
        if below.height > drop:
            im.paste(below.crop((0, 0, below.width, below.height - drop)), (0, chin + drop))
        # inner-mouth shadow
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        mw, mh = int(w * 0.30), max(2, int(o * h * 0.10))
        cy = mouth_cy + drop // 2
        d.ellipse((cx - mw // 2, cy - mh // 2, cx + mw // 2, cy + mh // 2),
                  fill=(22, 8, 8, int(150 * o)))
        ov = ov.filter(ImageFilter.GaussianBlur(3))
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        states.append(im)
    return states


def caption_segments(script: str, duration: float):
    words = script.split()
    segs, cur = [], []
    for wd in words:
        cur.append(wd)
        if len(" ".join(cur)) >= 34:
            segs.append(" ".join(cur))
            cur = []
    if cur:
        segs.append(" ".join(cur))
    total = sum(len(s) for s in segs) or 1
    out, t = [], 0.0
    for s in segs:
        d = duration * len(s) / total
        out.append((t, t + d, s))
        t += d
    return out


def _strip(text: str, max_w: int, font, bg_alpha=170, fg=(255, 255, 255, 255)):
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = tmp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 18, 10
    strip = Image.new("RGBA", (min(max_w, tw + pad_x * 2), th + pad_y * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    d.rounded_rectangle((0, 0, strip.width - 1, strip.height - 1), radius=8, fill=(0, 0, 0, bg_alpha))
    d.text((pad_x - bbox[0], pad_y - bbox[1]), text, font=font, fill=fg)
    return strip


def render_video(avatar_src: str, audio_path: str, out_path: str, thumb_path: str, *,
                 resolution="1080p", aspect_ratio="16:9", background_type="solid",
                 background_value="#0A0A0A", captions_enabled=True, script="",
                 watermark=False) -> dict:
    out_w, out_h = video_dims(resolution, aspect_ratio)
    scale = min(1.0, RENDER_CAP / out_h)
    rw, rh = int(out_w * scale) // 2 * 2, int(out_h * scale) // 2 * 2

    # Decode speech audio to wav for amplitude analysis
    wav = str(Path(audio_path).with_suffix(".analysis.wav"))
    subprocess.run(["ffmpeg", "-y", "-i", str(audio_path), "-ac", "1", "-ar", "16000", wav],
                   check=True, capture_output=True)
    env = audio_envelope(wav)
    duration = len(env) / FPS

    # Background
    bg = None
    if background_type == "image" and background_value and str(background_value).startswith("http"):
        try:
            bg = ImageOps.fit(load_image(background_value), (rw, rh), Image.LANCZOS)
        except Exception:
            bg = None
    if bg is None:
        color = background_value if (background_value or "").startswith("#") else "#0A0A0A"
        try:
            bg = Image.new("RGB", (rw, rh), color)
        except ValueError:
            bg = Image.new("RGB", (rw, rh), "#0A0A0A")

    # Avatar scaled, bottom-center anchored
    avatar = load_image(avatar_src)
    a_h = int(rh * 0.96)
    a_w = int(avatar.width * a_h / avatar.height)
    if a_w > int(rw * 0.92):
        a_w = int(rw * 0.92)
        a_h = int(avatar.height * a_w / avatar.width)
    avatar = avatar.resize((a_w, a_h), Image.LANCZOS)
    face = detect_face(avatar)
    states = build_mouth_states(avatar, face)
    ax, ay = (rw - a_w) // 2, rh - a_h

    # Captions + watermark
    font = _font(max(16, rh // 30))
    strips = []
    if captions_enabled and script:
        strips = [(s, e, _strip(t, rw - 20, font)) for s, e, t in caption_segments(script, duration)]
    wm = _strip("Made with AvatarPlatform", rw, _font(max(12, rh // 48)),
                bg_alpha=110, fg=(255, 255, 255, 175)) if watermark else None

    vf = f"scale={out_w}:{out_h}:flags=lanczos" if (rw, rh) != (out_w, out_h) else "null"
    err_file = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
    cmd = ["ffmpeg", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{rw}x{rh}", "-r", str(FPS), "-i", "-",
           "-i", str(audio_path),
           "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err_file)

    thumb_idx = min(len(env) - 1, FPS)
    try:
        for i in range(len(env)):
            frame = bg.copy()
            k = int(round(float(env[i]) * (len(states) - 1)))
            dy = int(round(1.5 * math.sin(i * 0.07) + float(env[i]) * 1.2))
            frame.paste(states[k], (ax, ay + dy))
            t = i / FPS
            for s, e, strip in strips:
                if s <= t < e:
                    frame.paste(strip, ((rw - strip.width) // 2, rh - strip.height - int(rh * 0.045)), strip)
                    break
            if wm:
                frame.paste(wm, (rw - wm.width - 12, 12), wm)
            if i == thumb_idx:
                frame.save(thumb_path, quality=85)
            proc.stdin.write(frame.tobytes())
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
    code = proc.wait()
    err_file.close()
    if code != 0:
        tail = Path(err_file.name).read_text()[-1500:]
        Path(err_file.name).unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg encode failed: {tail}")
    Path(err_file.name).unlink(missing_ok=True)
    Path(wav).unlink(missing_ok=True)
    return {"duration_seconds": round(duration, 1), "width": out_w, "height": out_h,
            "face_detected": face is not None}
