from pathlib import Path
from fastapi.testclient import TestClient
from hushloop.app import create_app
from hushloop.presets import PRESETS
from hushloop.store import Store

class Noop:
    name = "Noop"
    async def generate(self, *args):
        raise AssertionError("Should not generate unless enabled")

def test_default_off_and_settings(tmp_path):
    with TestClient(create_app(tmp_path, Noop())) as client:
        assert client.get("/health").json()["ok"]
        s = client.get("/api/status").json()
        assert s["settings"]["generation_enabled"] is False
        assert s["queued_tracks"] == 0
        assert client.get("/api/tracks/next").status_code == 404
        assert client.post("/api/settings", json={"mood": "invalid"}).status_code == 422
        assert client.post("/api/settings", json={"buffer_minutes": 0}).status_code == 422
        config = client.post("/api/settings", json={"mood": "coding", "volume": 0.3}).json()
        assert config["mood"] == "coding"
        assert client.get("/api/status").json()["settings"]["volume"] == 0.3

def test_queue_rotation_and_feedback(tmp_path):
    store = Store(tmp_path / "test.db")
    for ix in range(3):
        store.add(dict(
            id=f"id{ix}", mood="rainy", title=str(ix), prompt="lofi",
            bpm=75, duration=90, filename=f"id{ix}.mp3", created_at=ix+1,
        ))
    assert store.buffered("rainy") == (270, 3)
    assert store.next("rainy")["id"] == "id0"
    store.played("id0")
    assert store.next("rainy")["id"] == "id1"
    assert store.buffered("rainy") == (180, 2)
    store.feedback("id1", favorite=True, disliked=True)
    assert store.next("rainy")["id"] == "id2"
    assert store.tracks(True)[0]["id"] == "id1"
    store.played("id2")
    assert store.next("rainy", exclude="id0")["id"] == "id2"
    assert store.next("rainy", exclude="id2")["id"] == "id0"

def test_presets():
    for item in PRESETS.values():
        assert item["bpm"][0] < item["bpm"][1]
