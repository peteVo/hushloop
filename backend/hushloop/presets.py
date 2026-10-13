"""Lo-fi moods and prompt generation without remote LLMs."""
from __future__ import annotations
import random

PRESETS = {
    "rainy": {
        "name": "Rainy Café", "bpm": [70, 85],
        "description": "Lo-fi café instrumental with clearly audible continuous rainfall in the foreground, raindrops pattering against a window throughout, warm Rhodes piano playing rich jazz seventh and ninth chords, upright bass and brushed drums",
    },
    "coding": {
        "name": "Midnight Coding", "bpm": [65, 90],
        "description": "Minimal drifting Rhodes melody, deep rounded bass, featherlight percussion, restrained atmospheric analog synthesizers, steady repetitive groove, spacious calm arrangement",
    },
    "jazzhop": {
        "name": "Jazzhop", "bpm": [75, 100],
        "description": "Distinct jazzhop boom-bap with swung kick, snare and hi-hat, walking upright bass, Rhodes and acoustic piano comping blue notes and rich seventh chords, short muted trumpet and saxophone phrases, dusty vinyl warmth",
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
        f"{preset['description']}, "
        f"{random.choice(VARIATIONS)}. {bpm} BPM. "
        "No vocals, no singing, no spoken words, no dramatic drops, "
        "no abrupt changes. Soft dynamics, suitable for concentration."
    )
    return prompt, bpm
