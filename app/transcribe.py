"""Beszédfelismerés a faster-whisper modellel (helyben fut, nem kell internet a modell letöltése után)."""
import threading
from typing import Callable

from .segment import Word

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


def get_model(name: str):
    global _model, _model_name
    if _model is None or _model_name != name:
        from faster_whisper import WhisperModel

        device, compute_type = _device()
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
        progress(0, "AI modell betöltése (első alkalommal letöltés, ez eltarthat pár percig)…")
        model = get_model(model_name)
        progress(0, "Beszéd felismerése…")
        segments, info = model.transcribe(
            path,
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
