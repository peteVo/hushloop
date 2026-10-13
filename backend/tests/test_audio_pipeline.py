"""Exercise full local audio pipeline without an AI GPU."""
from __future__ import annotations

import asyncio
import math
import shutil
import struct
import time
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hushloop.app import create_app
from hushloop.provider import GenerationError, normalize_audio


class FixtureProvider:
    name = "Integration test tone"

    async def generate(self, dest: Path, prompt: str, bpm: int, seconds: int):
        await asyncio.to_thread(self.write_wav, dest, 9, False)

    @staticmethod
    def write_wav(dest: Path, seconds: int, silent: bool, trailing_silence: int = 0):
        sample_rate = 16000
        with wave.open(str(dest), "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(sample_rate)
            for offset in range(0, seconds * sample_rate, 4000):
                frames = bytearray()
                for i in range(offset, min(offset + 4000, seconds * sample_rate)):
                    t = i / sample_rate
                    fade = min(1, t / .1, (seconds - t) / .1)
                    sample = 0 if silent or t >= seconds - trailing_silence else int(
                        14000 * fade * math.sin(2 * math.pi * 220 * t)
                    )
                    frames.extend(struct.pack("<h", sample))
                sound.writeframesraw(frames)


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe required to exercise real audio pipeline",
)
def test_generation_serving_and_feedback(tmp_path):
    with TestClient(create_app(tmp_path, FixtureProvider())) as client:
        changed = client.post("/api/settings", json={
            "generation_enabled": True, "track_seconds": 30, "buffer_minutes": 2,
        })
        assert changed.status_code == 200
        item = None
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            response = client.get("/api/tracks/next")
            if response.status_code == 200:
                item = response.json()
                break
            time.sleep(.25)
        assert item is not None, client.get("/api/status").json()
        assert 8 <= item["duration"] <= 10
        response = client.get(item["url"])
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/mpeg")
        assert len(response.content) > 8192
        assert client.post("/api/tracks/" + item["id"] + "/played").status_code == 200
        assert client.post("/api/tracks/" + item["id"] + "/feedback",
                           json={"favorite": True}).status_code == 200
        favorites = client.get("/api/tracks", params={"favorites": "true"}).json()
        assert any(track["id"] == item["id"] for track in favorites)
        assert client.post("/api/settings", json={"generation_enabled": False}).status_code == 200


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe required to test silence rejection",
)
def test_silent_output_rejected(tmp_path):
    source = tmp_path / "silence.wav"
    FixtureProvider.write_wav(source, 9, True)
    with pytest.raises(GenerationError, match="silent or corrupt"):
        normalize_audio(source, tmp_path / "result.mp3")
    assert not (tmp_path / "result.mp3").exists()


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe required to test silence trimming",
)
def test_long_trailing_silence_is_trimmed(tmp_path):
    source = tmp_path / "trailing-silence.wav"
    FixtureProvider.write_wav(source, 12, False, trailing_silence=3)
    duration = normalize_audio(source, tmp_path / "result.mp3")
    assert 8 <= duration < 11
