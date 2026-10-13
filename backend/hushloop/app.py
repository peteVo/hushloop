"""Local-only FastAPI radio, generation scheduler and player API."""
from __future__ import annotations
import asyncio
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .presets import PRESETS, create_prompt
from .provider import AceStepProvider, MockProvider, normalize_audio
from .store import Store

class SettingsPatch(BaseModel):
    mood: str | None = None
    generation_enabled: bool | None = None
    buffer_minutes: int | None = Field(default=None, ge=2, le=30)
    cache_limit_mb: int | None = Field(default=None, ge=256, le=20000)
    track_seconds: int | None = Field(default=None, ge=30, le=300)
    volume: float | None = Field(default=None, ge=0, le=1)

class FeedbackPatch(BaseModel):
    favorite: bool | None = None
    disliked: bool | None = None

class Runtime:
    def __init__(self, root: Path, provider):
        self.root = Path(root)
        self.audio = self.root / "audio"
        self.audio.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.root / "hushloop.sqlite3")
        self.provider = provider
        self.busy = False
        self.last_error = None
        self.task: asyncio.Task | None = None

    async def loop(self):
        try:
            while True:
                conf = self.store.config()
                mood = conf["mood"]
                seconds, _ = self.store.buffered(mood)
                if not conf["generation_enabled"] or seconds >= conf["buffer_minutes"] * 60:
                    await asyncio.sleep(2)
                    continue
                self.busy = True
                identifier = uuid4().hex
                source = self.root / f"{identifier}.source.wav"
                target = self.audio / f"{identifier}.mp3"
                prompt, bpm = create_prompt(mood)
                try:
                    await self.provider.generate(source, prompt, bpm, conf["track_seconds"])
                    duration = await asyncio.to_thread(normalize_audio, source, target)
                    self.store.add({
                        "id": identifier, "mood": mood,
                        "title": f"{PRESETS[mood]['name']} · {time.strftime('%H:%M')}",
                        "prompt": prompt, "bpm": bpm, "duration": duration,
                        "filename": target.name, "created_at": time.time(),
                    })
                    self.last_error = None
                    await asyncio.to_thread(
                        self.store.prune, self.audio, conf["cache_limit_mb"] * 1024 * 1024
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    target.unlink(missing_ok=True)
                    self.last_error = str(e)[:500]
                    await asyncio.sleep(12)
                finally:
                    source.unlink(missing_ok=True)
                    self.busy = False
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            return

def create_app(root: Path | None = None, provider=None) -> FastAPI:
    base = Path(root or os.getenv("HUSHLOOP_DATA_DIR", "data")).resolve()
    engine = provider or (
        MockProvider() if os.getenv("HUSHLOOP_PROVIDER", "ace") == "mock"
        else AceStepProvider()
    )
    runtime = Runtime(base, engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime.task = asyncio.create_task(runtime.loop())
        yield
        runtime.task.cancel()
        try:
            await runtime.task
        except asyncio.CancelledError:
            pass

    app = FastAPI(title="Hushloop", version="0.1.0", lifespan=lifespan)
    app.state.runtime = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health():
        return {"ok": True, "provider": runtime.provider.name}

    @app.get("/api/presets")
    def presets():
        return PRESETS

    @app.get("/api/status")
    def status():
        cfg = runtime.store.config()
        seconds, count = runtime.store.buffered(cfg["mood"])
        return {
            "settings": cfg, "provider": runtime.provider.name,
            "generating": runtime.busy,
            "buffered_seconds": round(seconds),
            "queued_tracks": count,
            "total_tracks": runtime.store.count(),
            "last_error": runtime.last_error,
        }

    @app.post("/api/settings")
    def settings(patch: SettingsPatch):
        update = patch.model_dump(exclude_none=True)
        if "mood" in update and update["mood"] not in PRESETS:
            raise HTTPException(422, "Unknown mood")
        return runtime.store.configure(update)

    @app.get("/api/tracks/next")
    def next_track(exclude: str | None = Query(default=None, max_length=64)):
        mood = runtime.store.config()["mood"]
        track = runtime.store.next(mood, exclude)
        if track is None:
            raise HTTPException(404, "No tracks buffered yet")
        return track

    @app.get("/api/tracks")
    def tracks(favorites: bool = False, limit: int = Query(30, ge=1, le=100)):
        return runtime.store.tracks(favorites, limit)

    @app.post("/api/tracks/{track_id}/played")
    def played(track_id: str):
        if not runtime.store.played(track_id):
            raise HTTPException(404, "Track not found")
        return {"ok": True}

    @app.post("/api/tracks/{track_id}/feedback")
    def feedback(track_id: str, patch: FeedbackPatch):
        runtime.store.feedback(track_id, patch.favorite, patch.disliked)
        return {"ok": True}

    @app.get("/audio/{track_id}.mp3")
    def audio(track_id: str):
        if not track_id.isalnum() or len(track_id) != 32:
            raise HTTPException(404)
        file = runtime.audio / f"{track_id}.mp3"
        if not file.is_file():
            raise HTTPException(404, "Cached audio no longer exists")
        return FileResponse(file, media_type="audio/mpeg", filename=file.name)

    return app

app = create_app()
