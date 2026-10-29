"""Feliratozott MP4 készítése ffmpeg-gel."""
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

FONT_SIZES = {"kicsi": 16, "kozepes": 20, "nagy": 24}


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(path: Path) -> float:
    import av

    with av.open(str(path)) as container:
        return (container.duration or 0) / 1_000_000


def _style(font_size: str, box: bool) -> str:
    size = FONT_SIZES.get(font_size, 20)
    parts = ["FontName=Arial", f"FontSize={size}", "PrimaryColour=&H00FFFFFF", "MarginV=18"]
    if box:
        parts += ["BorderStyle=3", "Outline=1", "Shadow=0", "BackColour=&H80000000", "OutlineColour=&H80000000"]
    else:
        parts += ["BorderStyle=1", "Outline=1.5", "Shadow=0.5", "OutlineColour=&H00000000"]
    return ",".join(parts)


def render(
    workdir: Path,
    source: str,
    srt: str,
    output: str,
    mode: str = "burn",
    font_size: str = "kozepes",
    box: bool = False,
    progress: Callable[[float, str], None] = lambda p, m: None,
) -> None:
    """A fájlneveket a munkakönyvtárhoz képest adjuk meg, így nem kell
    az ffmpeg szűrőben Windows-os elérési utakat escape-elni."""
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-nostats", "-progress", "pipe:1", "-i", source]
    if mode == "burn":
        cmd += [
            "-vf", f"subtitles={srt}:charenc=UTF-8:force_style='{_style(font_size, box)}'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
        ]
    else:  # beágyazott, ki-/bekapcsolható felirat
        cmd += [
            "-i", srt, "-map", "0:v", "-map", "0:a?", "-map", "1:0",
            "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
            "-metadata:s:s:0", "language=hun",
        ]
    cmd += ["-movflags", "+faststart", output]

    total = duration(workdir / source) or 1
    proc = subprocess.Popen(
        cmd, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    stderr_tail: list[str] = []

    def read_stderr():
        for line in proc.stderr:
            stderr_tail.append(line)
            del stderr_tail[:-30]

    t = threading.Thread(target=read_stderr, daemon=True)
    t.start()
    for line in proc.stdout:
        key, _, value = line.strip().partition("=")
        if key == "out_time_us" and value.isdigit():
            p = min(int(value) / 1_000_000 / total, 1)
            progress(p, f"Videó készítése… {round(p * 100)}%")
    proc.wait()
    t.join(timeout=2)
    if proc.returncode != 0:
        raise RuntimeError("Az ffmpeg hibával leállt:\n" + "".join(stderr_tail[-10:]))
