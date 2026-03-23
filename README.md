# BarkTTS CLI

A better command-line interface for [Bark](https://github.com/suno-ai/bark) — Suno's open-source text-to-audio model with natural-sounding speech, non-verbal sounds, and multilingual support.

## Features

- Single command synthesis with auto-saved output
- Interactive prompt loop (`--interactive`) — type and hear, change voice/temp mid-session
- `--play` flag to hear audio immediately
- Temperature control (`--temp`) to reduce "um" filler
- Reproducible output with `--seed`
- All 130+ built-in voice presets (`--list-voices`)
- Supports cloned `.npz` voice files (from [bark-with-voice-clone](https://github.com/serp-ai/bark-with-voice-clone))
- CPU fallback mode (`--cpu`) and small model mode (`--small`)

## Requirements

| Requirement | Version |
|---|---|
| Python | **3.9+** (3.10–3.13 tested and working) |
| NVIDIA GPU | Strongly recommended — CPU generation is very slow (~10–30 min/clip) |
| CUDA | 12.4 recommended (12.1 and 11.8 also supported — see requirements.txt) |
| Disk space | ~5 GB for model weights (downloaded automatically on first run) |
| RAM / VRAM | ~6 GB VRAM recommended (use `--small` for 4 GB cards) |

> **CPU-only machines:** Set `SUNO_USE_SMALL_MODELS=1` and expect 10–30 minutes per generation.

## Folder structure

This repo is designed so each TTS model is **fully self-contained** in its own subfolder:

```
TTS_V2/
├── README.md            ← comparison table (top-level overview)
├── BarkTTS/
│   ├── bark_tts.py      ← the CLI (your code)
│   ├── requirements.txt
│   ├── setup.ps1        ← auto-clones bark/ and creates venv/
│   ├── setup.sh
│   ├── README.md
│   ├── bark/            ← cloned by setup, gitignored
│   └── venv/            ← created by setup, gitignored
├── KokoroTTS/
│   ├── kokoro_tts.py
│   ├── requirements.txt
│   ├── setup.ps1
│   └── venv/            ← its own separate venv
├── F5-TTS/
│   └── ...
└── docs/                ← GitHub Pages comparison chart
```

Each model gets its own `venv/` because their dependencies often conflict (different torch versions, etc.). Never share a venv across models.

---

## Install

### Step 1 — Get Python 3.9 or newer

Download from [python.org](https://www.python.org/downloads/).  
Python 3.10–3.13 all work. Check your version: `python --version`

### Step 2 — Clone this repo

```bash
git clone <this-repo-url>
cd BarkTTS
```

### Step 3 — Run setup (creates venv + installs everything)

**Windows (PowerShell):**
```powershell
.\setup.ps1
```

**Linux / macOS:**
```bash
bash setup.sh
```

The setup script will:
1. Check your Python version
2. Create a `venv/` virtual environment
3. Install all dependencies (PyTorch + Bark deps)

> **Windows execution policy error?**  
> Run this once, then retry `.\setup.ps1`:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

> **Wrong CUDA version?**  
> Before running setup, open `setup.ps1` (or `setup.sh`) and change `cu124` in the `pip install torch torchaudio --index-url` line to match your GPU:
>
> | Your CUDA version | Use |
> |---|---|
> | CUDA 12.4+ | `cu124` (default) |
> | CUDA 12.1 | `cu121` |
> | CUDA 11.8 | `cu118` |
> | CPU only | remove the `--index-url` flag entirely |
>
> Check your version: `nvidia-smi` (CUDA version shown in top-right)

### Step 4 — Activate the venv and run

**Windows:**
```powershell
.\venv\Scripts\Activate.ps1
python bark_tts.py "Hello! This is Bark TTS." --play
```

**Linux / macOS:**
```bash
source venv/bin/activate
python bark_tts.py "Hello! This is Bark TTS." --play
```

> **First run downloads ~5 GB of model weights** to `~/.cache/suno/bark_v0/` — this only happens once.

On first run, Bark will download ~5 GB of model weights to:
- Windows: `C:\Users\<you>\.cache\suno\bark_v0\`
- Linux/macOS: `~/.cache/suno/bark_v0/`

This only happens once.

---

## Usage

### Synthesize a single line

```bash
python bark_tts.py "Hello world"
python bark_tts.py "Hello world" --voice v2/en_speaker_9 --play
python bark_tts.py "Hello world" --out my_clip.wav
python bark_tts.py "That is AMAZING. [laughs] ... okay." --voice v2/en_speaker_9
```

### Interactive mode

```bash
python bark_tts.py --interactive
python bark_tts.py --interactive --voice v2/en_speaker_9 --play
```

Type prompts at the `>>>` prompt. Each is saved to `output/session_<timestamp>/`.

In-session commands:
```
/voice v2/en_speaker_3   — switch voice
/temp 0.4                — change temperature
/help                    — show commands
quit                     — exit
```

### List all voice presets

```bash
python bark_tts.py --list-voices
```

### All options

```
positional:
  text                  Text to synthesize

options:
  --voice, -v PRESET    Voice preset or path to .npz cloned voice
  --temp, -t T          Temperature: 0.3–0.5 = less filler, 0.8–1.0 = expressive (default: 0.7)
  --seed N              Random seed for reproducible output
  --out, -o FILE        Output .wav path (default: auto-named in ./output/)
  --output-dir DIR      Directory for auto-named files (default: ./output/)
  --play, -p            Play audio after generating
  --interactive, -i     Interactive prompt loop
  --list-voices         Print all built-in voice presets and exit
  --small               Use smaller models (~1 GB, faster, lower quality)
  --cpu                 Offload unused models to CPU to reduce VRAM usage
```

---

## Non-verbal sounds

Bark supports these **official** non-verbal tokens — use them in your text:

| Token | Sound |
|---|---|
| `[laughter]` | Sustained laughter |
| `[laughs]` | Short laugh |
| `[sighs]` | Audible sigh |
| `[gasps]` | Sharp intake of breath |
| `[clears throat]` | Throat clear |
| `[music]` | Background music hum |
| `♪` | Sung/musical content |
| `...` or `—` | Hesitation pause |
| `CAPS` | Emphasis on a word |

**Tip:** Put a short phonetic lead-in before tokens to avoid "um" filler:
```
"Ha! [laughter]"       ← good
"[laughter]"           ← often produces "um, it turns out..." first
```

---

## Voice presets quick reference

### English speakers

| Preset | Gender | Character notes |
|---|---|---|
| `v2/en_speaker_1` | Male | Neutral, mid-range |
| `v2/en_speaker_9` | Female | ⭐ Default — soft, natural, handles non-verbals well |

> Voice character is probabilistic — Bark may vary slightly each run. `--seed` locks the result.  
> Full speaker reference with audio samples: [Suno voice presets](https://suno-ai.notion.site/8b8e8749ed514b0cbf3f699013548683?v=bc67cff786b04b50b3ceb756fd05f68c)  
> Run `python bark_tts.py --list-voices` to also see all non-English presets (DE, FR, JA, ZH, etc., speakers 0–9 each).

### Non-English languages

`v2/de_speaker_*` `v2/es_speaker_*` `v2/fr_speaker_*` `v2/hi_speaker_*` `v2/it_speaker_*` `v2/ja_speaker_*` `v2/ko_speaker_*` `v2/pl_speaker_*` `v2/pt_speaker_*` `v2/ru_speaker_*` `v2/tr_speaker_*` `v2/zh_speaker_*`

Each language has speakers 0–9. Gender is not officially documented — try a few to find one you like.

---

## Environment variables

```bash
SUNO_USE_SMALL_MODELS=1   # use ~1 GB models (faster, lower quality)
SUNO_OFFLOAD_CPU=1        # offload unused models to CPU (saves VRAM)
```

Windows:
```powershell
$env:SUNO_USE_SMALL_MODELS = "1"
python bark_tts.py "Hello" --play
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'bark'`**  
Make sure your venv is activated and `bark/` exists in the project folder (git cloned).

**`CUDA out of memory`**  
Use `--small` for a lower-VRAM model, or `--cpu` to offload unused weights.

**`sounddevice` / playback not working**  
On Windows this usually just works. On Linux, install PortAudio: `sudo apt install libportaudio2`

**Generation takes forever**  
You're running on CPU. A GPU is strongly recommended. Generation is 3–10 seconds on a modern NVIDIA GPU vs. 10–30 minutes on CPU.

**Output has "um" filler before the sound**  
Lower `--temp` to 0.4–0.5 and add a phonetic lead-in before non-verbal tokens (see above).

---

## Credits

- [Bark](https://github.com/suno-ai/bark) by Suno AI — MIT License
- [bark-with-voice-clone](https://github.com/serp-ai/bark-with-voice-clone) for `.npz` voice creation
