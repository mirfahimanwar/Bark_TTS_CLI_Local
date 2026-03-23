"""
bark_tts.py — A better CLI for Bark TTS (github.com/suno-ai/bark)

QUICK START:
  python bark_tts.py "Hello world"
  python bark_tts.py "Hello world" --voice v2/en_speaker_9 --play
  python bark_tts.py --interactive
  python bark_tts.py --list-voices

FULL USAGE:
  python bark_tts.py <text>           [--voice PRESET] [--out FILE]
                                      [--play] [--temp T] [--seed N]
                                      [--small] [--cpu]
  python bark_tts.py --interactive    [--voice PRESET] [--temp T]
  python bark_tts.py --list-voices

OFFICIAL BARK NON-VERBAL TOKENS:
  [laughter]  [laughs]  [sighs]  [gasps]  [clears throat]  [music]  ♪
  Use ... or — for hesitations.  CAPS for emphasis.
  Example: "That is AMAZING. [laughs] ... okay, let me think."

VOICE PRESETS (built-in):
  Female: v2/en_speaker_0  v2/en_speaker_3  v2/en_speaker_9
  Male:   v2/en_speaker_1  v2/en_speaker_6  v2/en_speaker_7
  --voice also accepts a path to a .npz cloned voice file

TEMPERATURE:
  --temp controls both text and waveform generation (default: 0.7)
  Lower (0.3–0.5) = more predictable, less filler "um"s
  Higher (0.8–1.0) = more expressive/varied, less stable

ENV VARS:
  SUNO_USE_SMALL_MODELS=1   use smaller/faster models (~1GB instead of ~5GB)
  SUNO_OFFLOAD_CPU=1        offload unused models to CPU (saves VRAM)
"""

import argparse
import os
import sys
import time

import numpy as np
import scipy.io.wavfile as wav

# ── Optional playback ────────────────────────────────────────────────────────
try:
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except ImportError:
    _HAS_SOUNDDEVICE = False

# ── Bark lives in the bark/ subdirectory (cloned repo) ───────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_BARK_DIR = os.path.join(_HERE, "bark")
if _BARK_DIR not in sys.path:
    sys.path.insert(0, _BARK_DIR)

# Lazy-loaded so --list-voices / --help work without loading models
_models_loaded = False


def _load_models(small: bool = False, cpu: bool = False) -> None:
    global _models_loaded
    if _models_loaded:
        return
    if small:
        os.environ["SUNO_USE_SMALL_MODELS"] = "1"
    if cpu:
        os.environ["SUNO_OFFLOAD_CPU"] = "1"
    from bark.generation import preload_models
    print("Loading Bark models (first run downloads ~5 GB to ~/.cache/suno/)…")
    preload_models()
    _models_loaded = True


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-sized chunks (~13s max per Bark context window)."""
    import re
    # Split on sentence-ending punctuation, keeping the delimiter
    parts = re.split(r'(?<=[.!?…])\s+', text.strip())
    chunks = []
    current = ""
    for part in parts:
        candidate = (current + " " + part).strip() if current else part
        # Rough proxy: Bark encodes ~13 chars/token for English; 200 chars ≈ safe limit
        if len(candidate) > 200 and current:
            chunks.append(current)
            current = part
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text]


def _generate(
    text: str,
    voice: str | None,
    temp: float,
    seed: int | None,
    small: bool,
    cpu: bool,
) -> tuple[np.ndarray, int]:
    """Run generation and return (audio_array, sample_rate).

    Long texts are automatically split into sentence chunks and concatenated
    to work around Bark's ~13-second per-pass context window limit.
    """
    import torch
    from bark.generation import generate_text_semantic, SAMPLE_RATE
    from bark.api import semantic_to_waveform

    _load_models(small=small, cpu=cpu)

    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)

    chunks = _split_sentences(text)
    if len(chunks) > 1:
        print(f"  (splitting into {len(chunks)} chunks for long text)")

    audio_parts = []
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            print(f"  Chunk {i+1}/{len(chunks)}: \"{chunk[:60]}{'…' if len(chunk)>60 else ''}\"")
        semantic = generate_text_semantic(
            chunk,
            history_prompt=voice,
            temp=temp,
            min_eos_p=0.05,
        )
        audio_parts.append(semantic_to_waveform(semantic, history_prompt=voice, temp=temp))

    audio = np.concatenate(audio_parts) if len(audio_parts) > 1 else audio_parts[0]
    return audio, SAMPLE_RATE


def _play(audio: np.ndarray, sr: int) -> None:
    if not _HAS_SOUNDDEVICE:
        print("sounddevice not installed — run: pip install sounddevice", file=sys.stderr)
        return
    sd.play(audio.astype(np.float32), samplerate=sr)
    sd.wait()


def _save(audio: np.ndarray, sr: int, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    wav.write(path, sr, pcm)
    print(f"Saved → {path}  ({len(pcm)/sr:.2f}s)")


def cmd_generate(args: argparse.Namespace) -> None:
    text = args.text
    print(f'Generating: "{text}"')
    t0 = time.time()
    audio, sr = _generate(
        text=text,
        voice=args.voice,
        temp=args.temp,
        seed=args.seed,
        small=args.small,
        cpu=args.cpu,
    )
    print(f"Done in {time.time()-t0:.1f}s  ({len(audio)/sr:.2f}s of audio)")

    if args.out:
        _save(audio, sr, args.out)
    else:
        # Default output filename based on first few words
        slug = "_".join(text.split()[:4])
        slug = "".join(c if c.isalnum() or c == "_" else "" for c in slug)[:40]
        path = os.path.join(args.output_dir, f"{slug}.wav")
        _save(audio, sr, path)

    if args.play:
        _play(audio, sr)


def cmd_interactive(args: argparse.Namespace) -> None:
    print("Bark interactive mode  (Ctrl-C or type 'quit' to exit)")
    print(f"Voice: {args.voice or 'default'}  |  Temp: {args.temp}")
    if args.voice:
        print(f"Using voice: {args.voice}")
    print()

    # Pre-load once so the loop is snappy
    _load_models(small=args.small, cpu=args.cpu)

    session_dir = os.path.join(
        args.output_dir, f"session_{int(time.time())}"
    )
    os.makedirs(session_dir, exist_ok=True)
    count = 0

    while True:
        try:
            text = input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not text or text.lower() in ("quit", "exit", "q"):
            break

        # Allow changing voice mid-session: /voice v2/en_speaker_3
        if text.startswith("/voice "):
            args.voice = text[7:].strip()
            print(f"Voice → {args.voice}")
            continue
        if text.startswith("/temp "):
            try:
                args.temp = float(text[6:].strip())
                print(f"Temp → {args.temp}")
            except ValueError:
                print("Usage: /temp 0.5")
            continue
        if text in ("/help", "/?"):
            print("  /voice PRESET   — change voice  (e.g. /voice v2/en_speaker_0)")
            print("  /temp VALUE     — change temperature  (e.g. /temp 0.4)")
            print("  /quit           — exit")
            continue

        t0 = time.time()
        try:
            audio, sr = _generate(
                text=text,
                voice=args.voice,
                temp=args.temp,
                seed=args.seed,
                small=args.small,
                cpu=args.cpu,
            )
        except Exception as exc:
            print(f"  Error: {exc}")
            continue

        count += 1
        path = os.path.join(session_dir, f"{count:03d}.wav")
        _save(audio, sr, path)
        print(f"  Generated in {time.time()-t0:.1f}s")

        if args.play:
            _play(audio, sr)


def cmd_list_voices() -> None:
    """Print all built-in voice presets."""
    voices = {
        "English (female)":  ["v2/en_speaker_0", "v2/en_speaker_3", "v2/en_speaker_9"],
        "English (male)":    ["v2/en_speaker_1", "v2/en_speaker_2", "v2/en_speaker_4",
                               "v2/en_speaker_5", "v2/en_speaker_6", "v2/en_speaker_7",
                               "v2/en_speaker_8"],
        "German":   [f"v2/de_speaker_{i}" for i in range(10)],
        "Spanish":  [f"v2/es_speaker_{i}" for i in range(10)],
        "French":   [f"v2/fr_speaker_{i}" for i in range(10)],
        "Hindi":    [f"v2/hi_speaker_{i}" for i in range(10)],
        "Italian":  [f"v2/it_speaker_{i}" for i in range(10)],
        "Japanese": [f"v2/ja_speaker_{i}" for i in range(10)],
        "Korean":   [f"v2/ko_speaker_{i}" for i in range(10)],
        "Polish":   [f"v2/pl_speaker_{i}" for i in range(10)],
        "Portuguese": [f"v2/pt_speaker_{i}" for i in range(10)],
        "Russian":  [f"v2/ru_speaker_{i}" for i in range(10)],
        "Turkish":  [f"v2/tr_speaker_{i}" for i in range(10)],
        "Chinese":  [f"v2/zh_speaker_{i}" for i in range(10)],
    }
    for lang, presets in voices.items():
        print(f"\n{lang}:")
        for p in presets:
            print(f"  {p}")
    print("\nPass any of these to --voice, e.g.:  --voice v2/en_speaker_9")
    print("You can also pass a path to a .npz cloned voice file.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bark_tts",
        description="Bark TTS — better CLI  (github.com/suno-ai/bark)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Positional text (optional — omit for --interactive)
    parser.add_argument(
        "text", nargs="?", default=None,
        help="Text to synthesize. Omit to use --interactive mode.",
    )

    # Voice / quality
    parser.add_argument(
        "--voice", "-v", default=None, metavar="PRESET",
        help="Voice preset string or path to .npz cloned voice. "
             "Run --list-voices to see all options. (default: Bark's random voice)",
    )
    parser.add_argument(
        "--temp", "-t", type=float, default=0.7, metavar="T",
        help="Generation temperature for both text and waveform stages. "
             "Lower = less filler/variance. Recommended range: 0.4–0.8. (default: 0.7)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, metavar="N",
        help="Random seed for reproducible output.",
    )

    # Output
    parser.add_argument(
        "--out", "-o", default=None, metavar="FILE",
        help="Output .wav file path. Default: auto-named in --output-dir.",
    )
    parser.add_argument(
        "--output-dir", default="output", metavar="DIR",
        help="Directory for auto-named output files. (default: ./output/)",
    )
    parser.add_argument(
        "--play", "-p", action="store_true",
        help="Play audio immediately after generating.",
    )

    # Modes
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Interactive prompt loop. Type text, get audio. /voice and /temp to change settings.",
    )
    parser.add_argument(
        "--list-voices", action="store_true",
        help="Print all built-in voice presets and exit.",
    )

    # Performance
    parser.add_argument(
        "--small", action="store_true",
        help="Use smaller/faster models (~1 GB vs ~5 GB). Lower quality.",
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Offload unused models to CPU to save VRAM (slower).",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_voices:
        cmd_list_voices()
        return

    if args.interactive:
        cmd_interactive(args)
        return

    if not args.text:
        parser.print_help()
        print("\nError: provide text to synthesize, or use --interactive.", file=sys.stderr)
        sys.exit(1)

    cmd_generate(args)


if __name__ == "__main__":
    main()
