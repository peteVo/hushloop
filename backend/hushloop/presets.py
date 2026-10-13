"""Lo-fi moods and prompt generation without remote LLMs."""
from __future__ import annotations
import random

PRESETS = {
    "rainy": {
        "name": "Rainy Café", "bpm": [70, 85],
        "description": "Calm instrumental lo-fi jazz groove, steady brushed drums and warm upright bass, a simple repeating Rhodes chord progression with a sparse melody, continuous soft rain pattering on a café window, same relaxed groove throughout",
    },
    "coding": {
        "name": "Midnight Coding", "bpm": [65, 90],
        "description": "Clear repeating mid-register electric piano melody in the foreground, warm Rhodes chords, soft featherlight percussion, quiet bass supporting the harmony, restrained atmospheric synthesizers, steady spacious groove",
    },
    "jazzhop": {
        "name": "Jazzhop", "bpm": [75, 100],
        "description": "Instrumental jazzhop beat with steady swung boom-bap kick and snare, warm walking upright bass, Rhodes playing a repeating jazzy seventh-chord progression, a few short muted trumpet phrases, same groove throughout",
    },
    "ambient": {
        "name": "Ambient Focus", "bpm": [55, 75],
        "description": "Slow evolving ambient pads, soft warm keys, long sustained chords, minimal or no percussion, serene peaceful atmosphere, unobtrusive harmonic motion",
    },
}
def create_prompt(mood: str) -> tuple[str, int]:
    preset = PRESETS[mood]
    bpm = random.randint(*preset["bpm"])
    prompt = (
        f"{preset['description']}, "
        f"{bpm} BPM. Keep the same arrangement, harmony and rhythm throughout. "
        "No vocals, breaks, fills or transitions."
    )
    return prompt, bpm
