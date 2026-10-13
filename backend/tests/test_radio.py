import time
from pathlib import Path
from fastapi.testclient import TestClient
from hushloop.app import create_app
from hushloop.presets import PRESETS, create_prompt
from hushloop.store import Store

class Noop:
    name = "Noop"
    async def generate(self, *args):
        raise AssertionError("Should not generate unless enabled")

class FailingProvider:
    name = "Unavailable inference server"

    async def generate(self, *args):
        raise RuntimeError("inference server unavailable")

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

def test_cached_track_remains_available_when_generation_fails(tmp_path):
    with TestClient(create_app(tmp_path, FailingProvider())) as client:
        runtime = client.app.state.runtime
        runtime.store.add(dict(
            id="cachedtrack00000000000000000000", mood="rainy", title="Cached",
            prompt="lofi", bpm=75, duration=90, filename="cached.mp3", created_at=1,
        ))
        client.post("/api/settings", json={"generation_enabled": True})
        deadline = time.monotonic() + 3
        while runtime.last_error is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert runtime.last_error == "inference server unavailable"
        assert client.get("/api/tracks/next").json()["id"] == "cachedtrack00000000000000000000"

def test_presets():
    for item in PRESETS.values():
        assert item["bpm"][0] < item["bpm"][1]

def test_rainy_and_jazzhop_prompts_name_their_audible_signatures():
    rainy, _ = create_prompt("rainy")
    jazzhop, _ = create_prompt("jazzhop")
    assert "continuous soft rain" in rainy and "repeating Rhodes chord progression" in rainy
    assert "jazzhop beat" in jazzhop and "walking upright bass" in jazzhop
    assert "muted trumpet phrases" in jazzhop
    assert "same arrangement, harmony and rhythm throughout" in rainy
    assert "same arrangement, harmony and rhythm throughout" in jazzhop
    assert len(rainy) <= 512 and len(jazzhop) <= 512
