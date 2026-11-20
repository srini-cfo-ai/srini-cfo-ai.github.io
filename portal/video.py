"""Make narrated videos from a script using open models: Piper (open-source neural TTS) + FFmpeg.

Output: media/<slug>/long.mp4 (1920x1080, YouTube/Facebook/site)
        media/<slug>/short.mp4 (1080x1920, YouTube Shorts / Instagram Reels / Facebook Reels)
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import requests

from . import graphics
from .content import MEDIA_DIR, ROOT

VOICE = os.getenv("PIPER_VOICE", "en_GB-alan-medium")
VOICE_DIR = Path(os.getenv("PIPER_VOICE_DIR", ROOT / ".cache" / "piper"))
FPS = 30


# ----------------------------------------------------------------------------- tools
def ffmpeg() -> str:
    exe = os.getenv("FFMPEG") or shutil.which("ffmpeg")
    if not exe:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    return exe


def _run(cmd: list[str]):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-2000:]}")
    return r


# ----------------------------------------------------------------------------- text to speech
def _piper_model() -> Path:
    lang, name, quality = VOICE.split("-")
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang.split('_')[0]}/{lang}/{name}/{quality}/{VOICE}"
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".onnx", ".onnx.json"):
        f = VOICE_DIR / f"{VOICE}{ext}"
        if not f.exists():
            print(f"[tts] downloading voice {f.name}")
            r = requests.get(base + ext, timeout=300)
            r.raise_for_status()
            f.write_bytes(r.content)
    return VOICE_DIR / f"{VOICE}.onnx"


_piper_voice = None


def _tts_piper(text: str, out: Path):
    global _piper_voice
    from piper import PiperVoice  # pip install piper-tts
    if _piper_voice is None:
        _piper_voice = PiperVoice.load(str(_piper_model()))
    with wave.open(str(out), "wb") as wf:
        if hasattr(_piper_voice, "synthesize_wav"):
            _piper_voice.synthesize_wav(text, wf)
        else:
            _piper_voice.synthesize(text, wf)


def _tts_espeak(text: str, out: Path):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak not installed")
    _run([exe, "-v", "en-gb", "-s", "158", "-w", str(out), text])


def _tts_windows(text: str, out: Path):
    if platform.system() != "Windows":
        raise RuntimeError("not Windows")
    safe = text.replace("'", "''")
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.Rate=0; $s.SetOutputToWaveFile('{out}'); $s.Speak('{safe}'); $s.Dispose()")
    _run(["powershell", "-NoProfile", "-Command", ps])


def speak(text: str, out: Path) -> float:
    """Synthesize speech to WAV and return its duration (seconds)."""
    errors = []
    for engine in (_tts_piper, _tts_espeak, _tts_windows):
        try:
            engine(text, out)
            with wave.open(str(out)) as w:
                dur = w.getnframes() / w.getframerate()
            if dur > 0.3:
                return dur
        except Exception as e:
            errors.append(f"{engine.__name__}: {e}")
    raise RuntimeError("No TTS engine worked: " + " | ".join(errors))


# ----------------------------------------------------------------------------- video
def _segment(img: Path, wav: Path, dur: float, out: Path, size: tuple[int, int]):
    w, h = size
    pad = 0.7
    frames = int((dur + pad) * FPS)
    vf = (f"[0:v]scale={w * 2}:{h * 2},zoompan=z='min(zoom+0.0004,1.06)':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={FPS},format=yuv420p[v];"
          f"[1:a]aresample=44100,apad=pad_dur={pad}[a]")
    _run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(img), "-i", str(wav), "-filter_complex", vf,
          "-map", "[v]", "-map", "[a]", "-t", f"{dur + pad:.2f}", "-c:v", "libx264", "-preset", "medium",
          "-crf", "21", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ac", "2", str(out)])


def make_video(script: dict, out: Path, size: tuple[int, int], title: str, kicker: str, footer: str) -> Path:
    """script = {"hook": str, "slides": [{"heading","narration"}], "close": str}"""
    slides = script["slides"]
    frames = [(dict(title=title, body=""), script["hook"])]
    for i, s in enumerate(slides):
        frames.append((dict(title=s["heading"], body=s["narration"], number=f"{i + 1:02d}"), s["narration"]))
    frames.append((dict(title=script["close"], body=footer), script["close"]))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        segs = []
        for i, (card, narration) in enumerate(frames):
            img = graphics.render_card(tmp / f"s{i}.png", size, kicker=kicker, footer=footer,
                                       progress=(i, len(frames)), **card)
            wav = tmp / f"s{i}.wav"
            dur = speak(narration, wav)
            seg = tmp / f"s{i}.mp4"
            _segment(img, wav, dur, seg, size)
            segs.append(seg)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs))
        out.parent.mkdir(parents=True, exist_ok=True)
        _run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
              "-c", "copy", "-movflags", "+faststart", str(out)])
    print(f"[video] {out.name} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


def make_post_videos(slug: str, copy: dict, title: str, profile: dict, url: str) -> dict[str, Path]:
    footer = url.replace("https://", "").rstrip("/").split("/blog/")[0] if url else profile["display_name"]
    kicker = profile["display_name"]
    d = MEDIA_DIR / slug
    return {
        "long": make_video(copy["video"], d / "long.mp4", (1920, 1080), title, kicker, footer),
        "short": make_video(copy["short"], d / "short.mp4", (1080, 1920), title, kicker, footer),
    }
