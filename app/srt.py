"""SRT olvasás és írás."""
import re

_TC = re.compile(r"(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})")


def format_tc(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_tc(text: str) -> float:
    m = _TC.search(text)
    if not m:
        raise ValueError(f"Hibás időkód: {text!r}")
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def to_srt(cues: list[dict]) -> str:
    blocks = []
    for cue in cues:
        text = cue["text"].strip()
        if not text:
            continue
        blocks.append(f"{len(blocks) + 1}\n{format_tc(cue['start'])} --> {format_tc(cue['end'])}\n{text}\n")
    return "\n".join(blocks)


def from_srt(content: str) -> list[dict]:
    content = content.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.split("\n")
        idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if idx is None:
            continue
        start_s, end_s = lines[idx].split("-->", 1)
        text = "\n".join(line.strip() for line in lines[idx + 1:]).strip()
        cues.append({"start": parse_tc(start_s), "end": parse_tc(end_s), "text": text})
    cues.sort(key=lambda c: c["start"])
    return cues
