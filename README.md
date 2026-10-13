# hushloop.

**Your infinite soundtrack for deep focus.**

A local-first, queue-based AI instrumental lo-fi radio for Windows, designed for everyday studying and coding. Hushloop runs a lightweight React music player and a Python scheduler alongside a **separate ACE-Step 1.5 local inference server**.

> **Status: early functional MVP.** Backend generation, normalization, SQLite queueing, radio controls and mood selection are implemented. The synthetic demo mode is *not* AI-generated music. Actual ACE-Step inference, crossfade listening quality, long-running playback and Windows packaging still need validation on the target PC.

## How it works

- Four instrumental moods: Rainy Café, Midnight Coding, Jazzhop, Ambient Focus.
- ACE-Step 1.5 turbo generates individual 90-second tracks on your own GPU.
- FFmpeg checks length and silence, normalizes loudness to -18 LUFS target, and caches an MP3.
- SQLite tracks metadata, favorites, playback history, and the next available track.
- The backend keeps a configurable buffer of unplayed tracks and generates new music when it gets low.
- React/Web Audio switches tracks with gain-node crossfades and can replay older cached tracks if generation is paused.
- Inference stops when the target buffer is filled; playback itself does not need the model on the GPU.
- Everything is local; Hushloop binds only to localhost.

## Requirements

- Windows 11 (other systems may work but are not targeted yet)
- Python 3.11 or 3.12; Node.js 20+; FFmpeg and ffprobe available in PATH
- For AI mode: NVIDIA CUDA GPU, ACE-Step 1.5 installed in a **separate** directory
- At least several GB free for the official model weights and cached audio

## 1. Get this project

In PowerShell:

~~~powershell
cd E:\Programs
git clone https://github.com/peteVo/hushloop.git
cd hushloop
~~~

If the folder already exists, use \`git -C E:\Programs\hushloop pull\` instead (back up any uncommitted changes first).

## 2. Run the Python radio server

~~~powershell
cd E:\Programs\hushloop\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:HUSHLOOP_PROVIDER="mock"  # First test UI without a GPU/model
python -m uvicorn hushloop.app:app --host 127.0.0.1 --port 8000
~~~

Open http://127.0.0.1:8000/health. The mocked provider generates **simple test tones**, not realistic lo-fi music.

## 3. Run the player

In **another** PowerShell terminal:

~~~powershell
cd E:\Programs\hushloop\frontend
npm install
npm run dev
~~~

Open http://127.0.0.1:5173. Select a mood and press Play. The player turns on generation, fills the queue, caches audio, and switches tracks. On first launch the player waits until one track has been prepared.

## 4. Connect real ACE-Step 1.5

Follow the upstream **official** instructions: https://github.com/ace-step/ACE-Step-1.5 and https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md.

A separate installation is strongly recommended (CUDA packages are not installed into Hushloop's Python environment).

~~~powershell
cd E:\Programs
git clone https://github.com/ace-step/ACE-Step-1.5.git
cd ACE-Step-1.5
# Install uv if not already installed: https://docs.astral.sh/uv/
uv sync
uv run acestep-api
~~~

Upstream also provides Windows launcher scripts, such as \`start_api_server.bat\`. The server defaults to http://127.0.0.1:8001. Check http://127.0.0.1:8001/health first. The first run may download large model weights. Hushloop uses ACE-Step's 2B Turbo model and sends \`thinking=false\`. On an 8 GB laptop GPU, start with ACE-Step's LLM disabled (\`ACESTEP_INIT_LLM=false\`) to leave VRAM for generation; consider its 0.6B language model with the PyTorch backend only after confirming available memory.

Stop the Hushloop backend and restart it in AI mode:

~~~powershell
cd E:\Programs\hushloop\backend
.\.venv\Scripts\Activate.ps1
$env:HUSHLOOP_PROVIDER="ace"
$env:HUSHLOOP_ACE_URL="http://127.0.0.1:8001"
python -m uvicorn hushloop.app:app --host 127.0.0.1 --port 8000
~~~

The frontend remains at http://127.0.0.1:5173.

## Tests

~~~powershell
cd E:\Programs\hushloop\backend
python -m pytest tests -v
cd ..\frontend
npm run build
~~~

The GitHub Actions workflow also checks backend unit/API tests and builds the frontend. These tests do **not** validate AI output quality, VRAM, continuous playback for hours, or Windows packaging.

## Technical notes

- Default backend bind: \`127.0.0.1:8000\`; development UI: \`127.0.0.1:5173\`.
- Environment settings: see \`backend/.env.example\`. They are environment variables, not automatically read from a .env file.
- Music cache and SQLite are stored in \`backend/data\` by default and are gitignored.
- File downloads are only served from Hushloop's cache; the ACE adapter rejects non-local API URLs and arbitrary download locations.
- Only one generation job runs at a time. The buffer target controls when it pauses. New tracks are synthesized independently, **not** mathematically continuous compositions.
- Browser playback requires an initial user gesture; sample-accurate transitions and crossfade quality must be assessed by ear.
- Playback history is local and favorites prevent automatic cache eviction.
- For best results use wired headphones or stable Bluetooth audio; browsers and Windows can independently introduce output latency.

## Licensing

Hushloop code is released under the MIT license (see LICENSE). ACE-Step is an independent project and is **not bundled**; review its current code/model licenses and rules before distributing generated recordings. Avoid prompts that imitate specific artists or copyrighted recordings without permission.

## Roadmap

1. **MVP foundation:** Backend, caching, queue, instrumental mood presets, React UI, CI.
2. **Target GPU validation:** Real ACE-Step installation and benchmarks; investigate Windows and model compatibility and improve failure recovery.
3. **Listening tests:** Audible transition QA, prompt quality, repeated playback, loudness, memory use and temperature.
4. **Product polish:** Desktop packaging (Tauri), resource monitoring, power-saving mode, richer scene animations, keyboard/media keys and custom presets.
5. **Optional procedural mode:** Evaluate Tone.js against cached AI music rather than assuming it is good enough.

Contributions welcome.
