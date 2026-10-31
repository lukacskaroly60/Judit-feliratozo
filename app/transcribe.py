"""Beszédfelismerés a faster-whisper modellel (helyben fut, nem kell internet a modell letöltése után)."""
import subprocess
import threading
from typing import Callable

from .segment import Word

SAMPLE_RATE = 16000

_lock = threading.Lock()
_model = None
_model_name = None


def _device() -> tuple[str, str]:
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def load_audio(path: str):
    """A videó hangja 16 kHz-es mono lebegőpontos tömbként.

    A magunkkal hozott ffmpeg-gel olvassuk ki, nem a faster-whisper saját
    (PyAV-alapú) dekóderével, mert az a PyAV újabb kiadásaival nem működik."""
    import numpy as np

    from .render import ffmpeg_exe

    proc = subprocess.run(
        [ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-i", path,
         "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()[-3:]
        raise RuntimeError("Nem sikerült kiolvasni a hangot a videóból: " + " ".join(err))
    audio = np.frombuffer(proc.stdout, dtype=np.float32)
    if audio.size == 0:
        raise RuntimeError("A videóban nincs hang")
    return audio


def get_model(name: str, force_cpu: bool = False):
    global _model, _model_name
    if force_cpu or _model is None or _model_name != name:
        from faster_whisper import WhisperModel

        device, compute_type = ("cpu", "int8") if force_cpu else _device()
        try:
            _model = WhisperModel(name, device=device, compute_type=compute_type)
        except Exception:
            if device == "cpu":
                raise
            # Van NVIDIA kártya, de hiányoznak a CUDA könyvtárak: processzoron futunk.
            _model = WhisperModel(name, device="cpu", compute_type="int8")
        _model_name = name
    return _model


def transcribe(
    path: str,
    model_name: str = "large-v3-turbo",
    language: str = "hu",
    prompt: str = "",
    progress: Callable[[float, str], None] = lambda p, m: None,
) -> list[Word]:
    with _lock:
        progress(0, "Hang kiolvasása a videóból…")
        audio = load_audio(path)
        progress(0, "AI modell betöltése (első alkalommal letöltés, ez eltarthat pár percig)…")
        model = get_model(model_name)
        try:
            return _run(model, audio, language, prompt, progress)
        except RuntimeError as e:
            # NVIDIA kártya van, de hiányzik hozzá a CUDA (pl. cublas64_12.dll):
            # ez csak a felismerés közben derül ki, ilyenkor processzoron futunk.
            if "cuda" not in str(e).lower() and "cublas" not in str(e).lower() and "cudnn" not in str(e).lower():
                raise
            progress(0, "A videókártya nem használható, átváltás processzorra…")
            model = get_model(model_name, force_cpu=True)
            return _run(model, audio, language, prompt, progress)


def _run(model, audio, language, prompt, progress) -> list[Word]:
    progress(0, "Beszéd felismerése…")
    segments, info = model.transcribe(
        audio,
        language=language or None,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,
        initial_prompt=prompt or None,
    )
    words: list[Word] = []
    total = info.duration or 1
    for seg in segments:
        for w in seg.words or []:
            words.append(Word(w.start, w.end, w.word, w.probability))
        progress(min(seg.end / total, 1), f"Beszéd felismerése… {_mmss(seg.end)} / {_mmss(total)}")
    return words


def _mmss(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"
