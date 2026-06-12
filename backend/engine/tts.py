"""Real text-to-speech via OpenAI TTS (Emergent universal key)."""
import os
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv(Path(__file__).parent.parent / ".env")

MAX_CHUNK = 3800


def _split_text(text: str):
    if len(text) <= MAX_CHUNK:
        return [text]
    chunks, cur = [], ""
    for sent in text.replace("\n", " ").split(". "):
        piece = sent.strip()
        if not piece:
            continue
        if len(cur) + len(piece) + 2 > MAX_CHUNK:
            if cur:
                chunks.append(cur.strip())
            cur = piece
        else:
            cur = f"{cur} {piece}." if cur else piece + "."
    if cur.strip():
        chunks.append(cur.strip())
    return chunks or [text[:MAX_CHUNK]]


async def synthesize_speech(text: str, voice: str = "alloy", speed: float = 1.0,
                            out_path: str = "out.mp3", model: str = "tts-1") -> str:
    """Generate real speech audio from text. Returns path to mp3."""
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    speed = min(4.0, max(0.25, speed))
    chunks = _split_text(text)
    out_path = str(out_path)

    if len(chunks) == 1:
        audio = await tts.generate_speech(text=chunks[0], model=model, voice=voice,
                                          speed=speed, response_format="mp3")
        Path(out_path).write_bytes(audio)
        return out_path

    parts = []
    for i, chunk in enumerate(chunks):
        audio = await tts.generate_speech(text=chunk, model=model, voice=voice,
                                          speed=speed, response_format="mp3")
        p = f"{out_path}.part{i}.mp3"
        Path(p).write_bytes(audio)
        parts.append(p)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in parts:
            f.write(f"file '{p}'\n")
        list_file = f.name
    try:
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                        "-c", "copy", out_path], check=True, capture_output=True)
    finally:
        Path(list_file).unlink(missing_ok=True)
        for p in parts:
            Path(p).unlink(missing_ok=True)
    return out_path
