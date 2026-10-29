import sys
import types
from types import SimpleNamespace as NS

from app import transcribe as tr


def test_transcribe_collects_words(monkeypatch):
    calls = {}

    class FakeModel:
        def __init__(self, name, device, compute_type):
            calls["init"] = (name, device, compute_type)

        def transcribe(self, path, **kw):
            calls["kw"] = kw
            segs = [NS(end=2.0, words=[NS(start=0.1, end=0.5, word=" Jó", probability=0.9), NS(start=0.6, end=1.0, word=" estét.", probability=0.3)])]
            return iter(segs), NS(duration=4.0)

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    monkeypatch.setattr(tr, "_model", None)
    progress = []
    words = tr.transcribe("x.mp4", "small", "hu", "Kossuth", lambda p, m: progress.append(p))
    assert [w.text for w in words] == [" Jó", " estét."]
    assert [w.p for w in words] == [0.9, 0.3]
    assert calls["kw"]["language"] == "hu" and calls["kw"]["initial_prompt"] == "Kossuth"
    assert calls["kw"]["word_timestamps"] is True
    assert progress[-1] == 0.5
