from app.segment import Rules, Word, apply_corrections, words_to_cues, wrap
from app.srt import from_srt, to_srt, to_txt


def words_from(text, start=0.0, step=0.4):
    out = []
    t = start
    for w in text.split():
        out.append(Word(t, t + step - 0.05, " " + w))
        t += step
    return out


def test_wrap_balanced_and_fits():
    lines = wrap("Ma este a parlament elfogadta az új költségvetési törvényt", 37, 2)
    assert len(lines) == 2
    assert all(len(line) <= 37 for line in lines)
    assert abs(len(lines[0]) - len(lines[1])) < 12


def test_wrap_avoids_article_at_line_end():
    lines = wrap("Holnap reggel indul el a nagy kerékpáros verseny", 30, 2)
    assert not lines[0].endswith(" a")


def test_wrap_too_long_returns_none():
    assert wrap("x" * 100, 37, 2) is None


def test_cues_respect_limits():
    text = ("Jó estét kívánok, ez az esti híradó. A kormány ma bejelentette, hogy jövő hónaptól "
            "emelkednek a nyugdíjak. Az ellenzék szerint ez nem elég, mert az infláció magas.")
    cues = words_to_cues(words_from(text), Rules())
    assert len(cues) > 2
    for c in cues:
        lines = c["text"].split("\n")
        assert len(lines) <= 2
        assert all(len(line) <= 37 for line in lines)
        assert c["end"] > c["start"]
    for a, b in zip(cues, cues[1:]):
        assert a["end"] <= b["start"]


def test_pause_starts_new_cue():
    words = words_from("Első mondat itt") + words_from("második rész", start=5.0)
    cues = words_to_cues(words)
    assert len(cues) == 2
    assert cues[1]["text"] == "második rész"


def test_min_duration():
    cues = words_to_cues([Word(1.0, 1.2, "Igen.")])
    assert cues[0]["end"] - cues[0]["start"] >= 1.0


def test_srt_roundtrip():
    cues = [{"start": 1.5, "end": 3.25, "text": "Első sor\nmásodik sor"},
            {"start": 3661.001, "end": 3662.0, "text": "Árvíztűrő tükörfúrógép"}]
    text = to_srt(cues)
    assert "01:01:01,001 --> 01:01:02,000" in text
    assert from_srt("﻿" + text.replace("\n", "\r\n")) == cues


def test_txt_has_only_text():
    cues = [{"start": 1.5, "end": 3.25, "text": "Első sor\nmásodik sor"},
            {"start": 4.0, "end": 5.0, "text": "  "},
            {"start": 6.0, "end": 7.0, "text": "Árvíztűrő tükörfúrógép"}]
    assert to_txt(cues) == "Első sor második sor\n\nÁrvíztűrő tükörfúrógép\n"


def test_unsure_words_are_marked():
    words = [Word(0.0, 0.4, " Megérkezett"), Word(0.5, 0.9, " Kovács", 0.2), Word(1.0, 1.4, " Péter.", 0.95)]
    cues = words_to_cues(words)
    assert cues[0]["unsure"] == [{"text": "Kovács", "start": 0.5, "end": 0.9}]


def test_corrections_whole_word_and_rewrap():
    cues = [{"start": 0, "end": 2, "text": "Ma Kovacs Péter beszélt,\nKovacsné nem."}]
    n = apply_corrections(cues, [{"from": "kovacs", "to": "Kovács"}], Rules())
    assert n == 1
    assert cues[0]["text"].replace("\n", " ") == "Ma Kovács Péter beszélt, Kovacsné nem."


def test_long_dashes_become_short_in_outputs():
    from app.srt import to_txt

    cues = [{"start": 1, "end": 3, "text": "Ez — mondta — igaz.\nA 10–12. oldal −5 fok"}]
    assert "Ez - mondta - igaz.\nA 10-12. oldal -5 fok" in to_srt(cues)
    assert to_txt(cues) == "Ez - mondta - igaz. A 10-12. oldal -5 fok\n"
    assert "00:00:01,000 --> 00:00:03,000" in to_srt(cues)
    for ch in "‐‑‒–—―−":
        assert ch not in to_srt(cues) + to_txt(cues)
