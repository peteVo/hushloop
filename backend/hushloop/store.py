"""SQLite metadata, queue rotation and persistent settings."""
from __future__ import annotations
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

DEFAULTS = {
    "mood": "rainy",
    "generation_enabled": False,
    "buffer_minutes": 5,
    "cache_limit_mb": 2048,
    "track_seconds": 90,
    "volume": 0.65,
}

class Store:
    def __init__(self, db_path: Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tracks (
                    id TEXT PRIMARY KEY,
                    mood TEXT NOT NULL,
                    title TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    bpm INTEGER NOT NULL,
                    duration REAL NOT NULL,
                    filename TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_played REAL,
                    play_count INTEGER NOT NULL DEFAULT 0,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    disliked INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS tracks_queue
                    ON tracks(mood, disliked, last_played, created_at);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def config(self) -> dict[str, Any]:
        with closing(self.connect()) as db:
            values = {r["key"]: json.loads(r["value"])
                      for r in db.execute("SELECT key, value FROM settings")}
        return {**DEFAULTS, **values}

    def configure(self, updates: dict[str, Any]) -> dict[str, Any]:
        with closing(self.connect()) as db:
            with db:
                for key, value in updates.items():
                    db.execute(
                        "INSERT INTO settings(key,value) VALUES(?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, json.dumps(value)),
                    )
        return self.config()

    def add(self, track: dict[str, Any]):
        with closing(self.connect()) as db:
            with db:
                db.execute(
                    "INSERT INTO tracks(id,mood,title,prompt,bpm,duration,filename,created_at) "
                    "VALUES(:id,:mood,:title,:prompt,:bpm,:duration,:filename,:created_at)",
                    track,
                )

    @staticmethod
    def public(row):
        if row is None:
            return None
        value = dict(row)
        value.pop("filename", None)
        value["url"] = f"/audio/{value['id']}.mp3"
        value["favorite"] = bool(value["favorite"])
        value["disliked"] = bool(value["disliked"])
        return value

    def next(self, mood: str, exclude: str | None = None):
        sql = (
            "SELECT * FROM tracks WHERE mood=? AND disliked=0 "
            "AND (? IS NULL OR id!=?) "
            "ORDER BY CASE WHEN last_played IS NULL THEN 0 ELSE 1 END, "
            "last_played ASC, created_at ASC LIMIT 1"
        )
        with closing(self.connect()) as db:
            row = db.execute(sql, (mood, exclude, exclude)).fetchone()
            if row is None and exclude:
                row = db.execute(sql, (mood, None, None)).fetchone()
        return self.public(row)

    def buffered(self, mood: str) -> tuple[float, int]:
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT COALESCE(SUM(duration),0) AS seconds, COUNT(*) AS count "
                "FROM tracks WHERE mood=? AND disliked=0 AND last_played IS NULL",
                (mood,),
            ).fetchone()
        return float(row["seconds"]), int(row["count"])

    def played(self, track_id: str) -> bool:
        with closing(self.connect()) as db:
            with db:
                cur = db.execute(
                    "UPDATE tracks SET last_played=?, play_count=play_count+1 WHERE id=?",
                    (time.time(), track_id),
                )
                return cur.rowcount > 0

    def feedback(self, track_id: str, favorite: bool | None, disliked: bool | None):
        updates = []
        params = []
        if favorite is not None:
            updates.append("favorite=?")
            params.append(int(favorite))
        if disliked is not None:
            updates.append("disliked=?")
            params.append(int(disliked))
        if not updates:
            return
        with closing(self.connect()) as db:
            with db:
                db.execute(
                    f"UPDATE tracks SET {', '.join(updates)} WHERE id=?",
                    (*params, track_id),
                )

    def tracks(self, favorites: bool = False, limit: int = 30):
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT * FROM tracks WHERE (?=0 OR favorite=1) "
                "ORDER BY COALESCE(last_played,created_at) DESC LIMIT ?",
                (int(favorites), limit),
            ).fetchall()
        return [self.public(r) for r in rows]

    def count(self):
        with closing(self.connect()) as db:
            return db.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]

    def prune(self, audio_dir: Path, max_bytes: int):
        # Never delete unplayed, favorited or recently used tracks.
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT id,filename,play_count,last_played,favorite FROM tracks "
                "ORDER BY COALESCE(last_played,created_at) ASC"
            ).fetchall()
            sizes = {}
            for row in rows:
                p = audio_dir / row["filename"]
                sizes[row["id"]] = p.stat().st_size if p.is_file() else 0
            total = sum(sizes.values())
            for row in rows:
                if total <= max_bytes:
                    break
                if row["favorite"] or not row["play_count"]:
                    continue
                if row["last_played"] and time.time()-row["last_played"] < 7200:
                    continue
                p = audio_dir / row["filename"]
                p.unlink(missing_ok=True)
                with db:
                    db.execute("DELETE FROM tracks WHERE id=?", (row["id"],))
                total -= sizes[row["id"]]
