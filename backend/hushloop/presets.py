"""Lo-fi moods and prompt generation without remote LLMs."""
from __future__ import annotations
import random

PRESETS = {
    "rainy": {
        "name": "Rainy Café", "bpm": [70, 85],
        "description": "Warm electric piano, soft jazz seventh and ninth chords, gentle brushed drums, subdued vinyl texture, subtle rain ambience, intimate cozy café atmosphere",
    },
    "coding": {
        "name": "Midnight Coding", "bpm": [65, 90],
        "description": "Minimal drifting Rhodes melody, deep rounded bass, featherlight percussion, restrained atmospheric analog synthesizers, steady repetitive groove, spacious calm arrangement",
    },
    "jazzhop": {
        "name": "Jazzhop", "bpm": [75, 100],
        "description": "Mellow jazz piano improvisation, soft muted guitar phrases, relaxed dusty hip-hop drums, warm acoustic bass, subtle swing and jazz harmony",
    },
    "ambient": {
        "name": "Ambient Focus", "bpm": [55, 75],
        "description": "Slow evolving ambient pads, soft warm keys, long sustained chords, minimal or no percussion, serene peaceful atmosphere, unobtrusive harmonic motion",
    },
}
VARIATIONS = [
    "gentle tape saturation and soft high-end",
    "understated melodic phrasing and spacious arrangement",
    "subtle harmonic variation and delicate dynamics",
    "warm organic instrumentation and rounded transients",
    "restrained improvisation with consistent relaxed groove",
]

def create_prompt(mood: str) -> tuple[str, int]:
    preset = PRESETS[mood]
    bpm = random.randint(*preset["bpm"])
    prompt = (
        f"Instrumental lo-fi background music, {preset['description']}, "
        f"{random.choice(VARIATIONS)}. {bpm} BPM. "
        "No vocals, no singing, no spoken words, no dramatic drops, "
        "no abrupt changes. Soft dynamics, suitable for concentration."
    )
    return prompt, bpm
