"""ACE-Step REST adapter and a tiny synthetic test provider (not AI music)."""
from __future__ import annotations
import asyncio
import json
import math
import os
import random
import struct
import tempfile
import urllib.parse
import wave
from pathlib import Path

import httpx

class GenerationError(Exception):
    pass

class AceStepProvider:
    name = "ACE-Step 1.5"
    def __init__(self):
        base = os.getenv("HUSHLOOP_ACE_URL", "http://127.0.0.1:8001").rstrip("/")
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("ACE-Step URL must be a local HTTP service")
        self.base = base
        token = os.getenv("HUSHLOOP_ACE_TOKEN")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def generate(self, dest: Path, prompt: str, bpm: int, seconds: int):
        async with httpx.AsyncClient(base_url=self.base, headers=self.headers, timeout=45) as client:
            payload = {
                "prompt": prompt,
                "lyrics": "[Instrumental]",
                "task_type": "text2music",
                "thinking": True,
                "use_cot_caption": False,
                "use_cot_language": False,
                "use_cot_metas": False,
                "model": "acestep-v15-turbo",
                "bpm": bpm,
                "audio_duration": seconds,
                "audio_format": "wav",
                "batch_size": 1,
                "inference_steps": 8,
                "use_random_seed": True,
            }
            try:
                r = await client.post("/release_task", json=payload)
                r.raise_for_status()
                body = r.json()
                if body.get("code") != 200 or not body.get("data", {}).get("task_id"):
                    raise GenerationError(f"ACE-Step rejected task: {body.get('error') or body}")
                task_id = body["data"]["task_id"]
                deadline = asyncio.get_running_loop().time() + 600
                while asyncio.get_running_loop().time() < deadline:
                    await asyncio.sleep(3)
                    r = await client.post("/query_result", json={"task_id_list": [task_id]})
                    r.raise_for_status()
                    result = r.json()
                    if result.get("code") != 200:
                        raise GenerationError(str(result.get("error")))
                    items = result.get("data") or []
                    if not items:
                        continue
                    job = items[0]
                    status = job.get("status")
                    if status == 2:
                        raise GenerationError(f"ACE-Step generation failed: {job}")
                    if status != 1:
                        continue
                    raw = job.get("result")
                    files = json.loads(raw) if isinstance(raw, str) else raw
                    if not isinstance(files, list) or not files:
                        raise GenerationError("ACE-Step returned no audio")
                    url = files[0].get("file", "")
                    # Never follow arbitrary URLs provided by a local API.
                    if not url.startswith("/v1/audio?"):
                        raise GenerationError("Invalid ACE-Step audio URL")
                    async with client.stream("GET", url, timeout=120) as audio:
                        audio.raise_for_status()
                        total = 0
                        with dest.open("wb") as out:
                            async for block in audio.aiter_bytes():
                                total += len(block)
                                if total > 150 * 1024 * 1024:
                                    raise GenerationError("Audio exceeds 150 MB")
                                out.write(block)
                    if total < 4096:
                        raise GenerationError("Empty or incomplete generated audio")
                    return
                raise GenerationError("ACE-Step timed out after 10 minutes")
            except (httpx.HTTPError, ValueError, KeyError, IndexError) as e:
                raise GenerationError(f"ACE-Step error: {e}") from e

class MockProvider:
    """A low-fi sine-wave fixture, strictly for UI development and tests."""
    name = "Synthetic demo (no AI)"
    async def generate(self, dest: Path, prompt: str, bpm: int, seconds: int):
        await asyncio.to_thread(self._write, dest, seconds, bpm)

    @staticmethod
    def _write(path: Path, seconds: int, bpm: int):
        rate = 22050
        chord = [174.61, 220.0, 261.63, 349.23]
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            for offset in range(0, seconds * rate, 2048):
                frames = bytearray()
                for n in range(offset, min(offset + 2048, seconds * rate)):
                    t = n / rate
                    pad = sum(math.sin(2 * math.pi * f * t) for f in chord) / 4
                    melody = math.sin(2 * math.pi * (261.63 if int(t * bpm / 30) % 2 else 349.23) * t)
                    fade = min(1, t / 0.5, (seconds - t) / 0.5)
                    sample = int(32767 * 0.13 * fade * (pad * 0.8 + melody * 0.16))
                    frames.extend(struct.pack("<h", sample))
                wav.writeframesraw(frames)

def normalize_audio(source: Path, target: Path, rain: bool = False) -> float:
    """Validate input and encode loudness-normalized MP3 atomically."""
    import subprocess
    def run(args):
        proc = subprocess.run(args, capture_output=True, text=True, timeout=180)
        if proc.returncode:
            raise GenerationError((proc.stderr or proc.stdout)[-1200:])
        return proc

    details = run(["ffprobe", "-v", "error", "-show_entries",
                   "format=duration", "-of", "json", str(source)])
    try:
        duration = float(json.loads(details.stdout)["format"]["duration"])
    except (ValueError, KeyError, TypeError) as e:
        raise GenerationError("Invalid audio duration") from e
    if not 8 <= duration <= 605:
        raise GenerationError(f"Unexpected duration: {duration}s")

    # Detect essentially silent audio before normalization boosts the noise.
    scan = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(source), "-af", "volumedetect",
         "-f", "null", os.devnull],
        capture_output=True, text=True, timeout=180,
    )
    import re
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", scan.stderr)
    if scan.returncode or not match or float(match.group(1)) < -55:
        raise GenerationError("Generated audio is silent or corrupt")
    temp = target.with_suffix(".partial.mp3")
    try:
        args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(source), "-vn"]
        if rain:
            rain_source = Path(__file__).parent / "assets" / "rain-loop.mp3"
            if not rain_source.is_file():
                raise GenerationError("Rain recording is missing from the installation")
            args += ["-stream_loop", "-1", "-i", str(rain_source),
                     "-filter_complex",
                     "[0:a]silenceremove=stop_periods=1:stop_duration=1.5:stop_threshold=-45dB[music];"
                     "[1:a]volume=0.4[rain];"
                     "[music][rain]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
                     "loudnorm=I=-18:TP=-2:LRA=11"]
        else:
            args += ["-af",
                     "silenceremove=stop_periods=1:stop_duration=1.5:stop_threshold=-45dB,loudnorm=I=-18:TP=-2:LRA=11"]
        args += ["-ar", "44100", "-ac", "2", "-codec:a", "libmp3lame", "-q:a", "3", str(temp)]
        run(args)
        if not temp.is_file() or temp.stat().st_size < 8192:
            raise GenerationError("Normalized audio output is invalid")
        result = run(["ffprobe", "-v", "error", "-show_entries",
                      "format=duration", "-of", "json", str(temp)])
        try:
            duration = float(json.loads(result.stdout)["format"]["duration"])
        except (ValueError, KeyError, TypeError) as e:
            raise GenerationError("Invalid normalized audio duration") from e
        if not 8 <= duration <= 605:
            raise GenerationError(f"Unexpected normalized duration: {duration}s")
        os.replace(temp, target)
        return duration
    finally:
        temp.unlink(missing_ok=True)
