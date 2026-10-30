import subprocess
import sys
import types
from types import SimpleNamespace as NS

import numpy as np
import pytest

from app import transcribe as tr
from app.render import ffmpeg_exe


@pytest.fixture
def video(tmp_path):
    """Valódi, 2 másodperces MP4 hanggal (videó + AAC hang)."""
    path = tmp_path / "próba videó.mp4"
    subprocess.run(
        [ffmpeg_exe(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-c:a", "aac",
         "-shortest", str(path)],
        check=True,
    )
    return path


def test_load_audio_real_video(video):
    audio = tr.load_audio(str(video))
    assert audio.dtype == np.float32
    assert abs(len(audio) / tr.SAMPLE_RATE - 2.0) < 0.1
    assert np.abs(audio).max() > 0.1


def test_load_audio_bad_file(tmp_path):
    bad = tmp_path / "rossz.mp4"
    bad.write_bytes(b"nem video")
    with pytest.raises(RuntimeError, match="hangot"):
        tr.load_audio(str(bad))


def _fake_whisper(monkeypatch, fail_on_cuda=False):
    calls = {"init": []}

    class FakeModel:
        def __init__(self, name, device, compute_type):
            self.device = device
            calls["init"].append(device)

        def transcribe(self, audio, **kw):
            if fail_on_cuda and self.device == "cuda":
                raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
            calls["audio"], calls["kw"] = audio, kw
            segs = [NS(end=2.0, words=[NS(start=0.1, end=0.5, word=" Jó", probability=0.9),
                                       NS(start=0.6, end=1.0, word=" estét.", probability=0.3)])]
            return iter(segs), NS(duration=4.0)

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    monkeypatch.setattr(tr, "_model", None)
    return calls


def test_transcribe_collects_words(monkeypatch, video):
    calls = _fake_whisper(monkeypatch)
    progress = []
    words = tr.transcribe(str(video), "small", "hu", "Kossuth", lambda p, m: progress.append(p))
    assert [w.text for w in words] == [" Jó", " estét."]
    assert [w.p for w in words] == [0.9, 0.3]
    # A modell a már kiolvasott hangot kapja, nem a fájlt
    assert isinstance(calls["audio"], np.ndarray)
    assert calls["kw"]["language"] == "hu" and calls["kw"]["initial_prompt"] == "Kossuth"
    assert calls["kw"]["word_timestamps"] is True
    assert progress[-1] == 0.5


def test_transcribe_falls_back_to_cpu(monkeypatch, video):
    calls = _fake_whisper(monkeypatch, fail_on_cuda=True)
    monkeypatch.setattr(tr, "_device", lambda: ("cuda", "float16"))
    words = tr.transcribe(str(video), "small", "hu", "", lambda p, m: None)
    assert len(words) == 2
    assert calls["init"] == ["cuda", "cpu"]
