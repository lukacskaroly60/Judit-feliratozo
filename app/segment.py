"""Szószintű időbélyegekből televíziós feliratokat készít.

Szabályok (alapértelmezésben, beállíthatók):
- legfeljebb 2 sor, soronként legfeljebb 37 karakter,
- egy felirat 1–6 másodpercig látszik,
- szünetnél, illetve mondatvégnél új felirat kezdődik,
- a két sor tördelése kiegyensúlyozott, írásjel után szívesebben tör,
  névelőt / kötőszót nem hagy a sor végén.
"""
from dataclasses import dataclass

SENTENCE_END = (".", "?", "!", "…")
SOFT_BREAK = (",", ";", ":", "–", "-")
# Ezek után nem szerencsés sort/feliratot törni.
WEAK_WORDS = {
    "a", "az", "egy", "és", "s", "de", "hogy", "ha", "vagy", "mert", "mint",
    "is", "sem", "nem", "meg", "ami", "aki", "amely", "amit", "akkor", "pedig",
}


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Rules:
    max_chars: int = 37
    max_lines: int = 2
    max_duration: float = 6.0
    min_duration: float = 1.0
    pause: float = 0.6
    min_gap: float = 0.08
    max_cps: float = 15.0


def _join(words: list[Word]) -> str:
    return " ".join(w.text for w in words)


def _break_penalty(word: str) -> int:
    """Mennyire rossz egy adott szó után törni (kisebb = jobb)."""
    if word.endswith(SENTENCE_END):
        return -12
    if word.endswith(SOFT_BREAK):
        return -8
    if word.lower().strip("\"'„”") in WEAK_WORDS:
        return 10
    return 0


def wrap(text: str, max_chars: int = 37, max_lines: int = 2) -> list[str] | None:
    """Szöveg tördelése sorokra. None, ha nem fér el."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return [text]
    if max_lines < 2:
        return None
    words = text.split(" ")
    best, best_score = None, None
    for i in range(1, len(words)):
        first, rest = " ".join(words[:i]), " ".join(words[i:])
        if len(first) > max_chars:
            break
        tail = [rest] if len(rest) <= max_chars else wrap(rest, max_chars, max_lines - 1)
        if tail is None:
            continue
        score = abs(len(first) - len(tail[0])) + _break_penalty(words[i - 1])
        if best_score is None or score < best_score:
            best, best_score = [first, *tail], score
    return best


def words_to_cues(words: list[Word], rules: Rules | None = None) -> list[dict]:
    rules = rules or Rules()
    capacity = rules.max_chars * rules.max_lines
    groups: list[list[Word]] = []
    cur: list[Word] = []

    for w in words:
        w = Word(w.start, w.end, w.text.strip())
        if not w.text:
            continue
        if cur:
            gap = w.start - cur[-1].end
            candidate = _join(cur + [w])
            overflow = len(candidate) > capacity or wrap(candidate, rules.max_chars, rules.max_lines) is None
            too_long = w.end - cur[0].start > rules.max_duration
            sentence_done = cur[-1].text.endswith(SENTENCE_END) and len(_join(cur)) >= 15
            if gap >= rules.pause or sentence_done:
                groups.append(cur)
                cur = []
            elif overflow or too_long:
                # Jobb töréspontot keresünk visszafelé (írásjel után),
                # hogy ne maradjon csonka a felirat vége.
                cut = len(cur)
                best = 0
                for i in range(len(cur) - 1, len(cur) // 2 - 1, -1):
                    p = _break_penalty(cur[i].text)
                    if p < best:
                        best, cut = p, i + 1
                groups.append(cur[:cut])
                cur = cur[cut:]
        cur.append(w)
    if cur:
        groups.append(cur)

    cues = []
    for g in groups:
        text = _join(g)
        lines = wrap(text, rules.max_chars, rules.max_lines) or [text]
        cues.append({"start": g[0].start, "end": g[-1].end, "text": "\n".join(lines)})
    return fix_timing(cues, rules)


def fix_timing(cues: list[dict], rules: Rules | None = None) -> list[dict]:
    """Minimális időtartam, olvasási sebesség és a feliratok közti rés biztosítása."""
    rules = rules or Rules()
    for i, cue in enumerate(cues):
        limit = cues[i + 1]["start"] - rules.min_gap if i + 1 < len(cues) else float("inf")
        chars = len(cue["text"].replace("\n", ""))
        wanted = max(rules.min_duration, chars / rules.max_cps)
        wanted = min(wanted, rules.max_duration)
        if cue["end"] - cue["start"] < wanted:
            cue["end"] = cue["start"] + wanted
        cue["end"] = max(cue["start"] + 0.2, min(cue["end"], limit))
        cue["start"] = round(cue["start"], 3)
        cue["end"] = round(cue["end"], 3)
    return cues
