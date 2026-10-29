"""Judit feliratozó – webes felület és API."""
import json
import re
import shutil
import threading
import time
import traceback
import unicodedata
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import render, srt
from .segment import Rules, apply_corrections, fix_timing, words_to_cues

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "projects"
DATA.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).resolve().parent / "static"
DICTIONARY = ROOT / "data" / "szotar.json"

app = FastAPI(title="Judit feliratozó")

# Futó / befejezett háttérfeladatok projektenként (csak memóriában).
jobs: dict[str, dict] = {}
_save_lock = threading.Lock()


# ---------- projekt tárolás ----------

def project_dir(pid: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", pid):
        raise HTTPException(404, "Nincs ilyen projekt")
    d = DATA / pid
    if not (d / "project.json").exists():
        raise HTTPException(404, "Nincs ilyen projekt")
    return d


def load(pid: str) -> dict:
    return json.loads((project_dir(pid) / "project.json").read_text("utf-8"))


def save(project: dict) -> None:
    d = DATA / project["id"]
    project["updated"] = time.time()
    with _save_lock:
        tmp = d / "project.json.tmp"
        tmp.write_text(json.dumps(project, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(d / "project.json")


def load_dictionary() -> dict:
    """Projekteken átívelő tudás: megjegyzett javítások és a gyakori nevek listája."""
    if DICTIONARY.exists():
        return json.loads(DICTIONARY.read_text("utf-8"))
    return {"pairs": [], "names": ""}


def save_dictionary(d: dict) -> None:
    tmp = DICTIONARY.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DICTIONARY)


def output_outdated(d: Path, project: dict) -> bool:
    out = d / "output.mp4"
    return out.exists() and out.stat().st_mtime < project.get("cues_changed", 0)


def disposition(name: str) -> dict:
    """Letöltési fájlnév ékezetekkel, és ékezet nélküli tartalékkal a régebbi programoknak."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().replace('"', "")
    return {"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"}


def output_name(project: dict) -> str:
    return Path(project["name"]).stem + "_feliratos.mp4"


# ---------- háttérfeladatok ----------

def run_job(pid: str, kind: str, fn) -> None:
    if jobs.get(pid, {}).get("state") == "running":
        raise HTTPException(409, "Már fut egy feladat ennél a videónál")
    job = {"kind": kind, "state": "running", "progress": 0.0, "message": "Indítás…", "started": time.time()}
    jobs[pid] = job

    def progress(p: float, msg: str) -> None:
        job["progress"], job["message"] = p, msg

    def target():
        try:
            fn(progress)
            job.update(state="done", progress=1.0, message="Kész")
        except Exception as e:  # a hibát a felületen mutatjuk meg
            traceback.print_exc()
            job.update(state="error", message=str(e))

    threading.Thread(target=target, daemon=True).start()


# ---------- API ----------

class Unsure(BaseModel):
    text: str
    start: float
    end: float


class Cue(BaseModel):
    start: float
    end: float
    text: str
    unsure: list[Unsure] = []


class CuesIn(BaseModel):
    cues: list[Cue]


class TranscribeIn(BaseModel):
    model: str = "large-v3"
    language: str = "hu"
    prompt: str = ""
    max_chars: int = 37
    max_lines: int = 2
    max_cps: float = 15.0


class DictionaryIn(BaseModel):
    pairs: list[dict]
    names: str = ""


class RenderIn(BaseModel):
    mode: str = "burn"
    font_size: str = "kozepes"
    box: bool = False


@app.get("/api/projects")
def list_projects():
    items = []
    for f in DATA.glob("*/project.json"):
        p = json.loads(f.read_text("utf-8"))
        items.append({
            "id": p["id"], "name": p["name"], "updated": p.get("updated", 0),
            "cues": len(p.get("cues", [])), "has_output": (f.parent / "output.mp4").exists(),
            "unsure": sum(len(c.get("unsure", [])) for c in p.get("cues", [])),
        })
    return sorted(items, key=lambda x: -x["updated"])


@app.post("/api/projects")
def create_project(file: UploadFile = File(...)):
    pid = uuid.uuid4().hex[:12]
    d = DATA / pid
    d.mkdir(parents=True)
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    source = "source" + ext
    with open(d / source, "wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)
    project = {"id": pid, "name": file.filename or "video.mp4", "source": source,
               "created": time.time(), "cues": [], "settings": {}}
    # Ha a videóban már van feliratsáv (pl. egy korábban itt készült MP4), betöltjük javításra.
    try:
        embedded = render.extract_subtitles(d, source)
        if embedded:
            project["cues"] = srt.from_srt(embedded)
            project["imported_from_video"] = True
    except Exception:
        traceback.print_exc()
    save(project)
    return project


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    project = load(pid)
    project["job"] = jobs.get(pid)
    project["has_output"] = (project_dir(pid) / "output.mp4").exists()
    project["output_outdated"] = output_outdated(project_dir(pid), project)
    return project


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    if jobs.get(pid, {}).get("state") == "running":
        raise HTTPException(409, "Előbb várd meg, amíg a feladat befejeződik")
    shutil.rmtree(project_dir(pid))
    jobs.pop(pid, None)
    return {"ok": True}


@app.get("/api/projects/{pid}/video")
def get_video(pid: str):
    project = load(pid)
    return FileResponse(project_dir(pid) / project["source"])


@app.put("/api/projects/{pid}/cues")
def put_cues(pid: str, body: CuesIn):
    project = load(pid)
    project["cues"] = [c.model_dump() for c in body.cues]
    project["cues_changed"] = time.time()
    save(project)
    return {"ok": True, "updated": project["updated"]}


@app.get("/api/dictionary")
def get_dictionary():
    return load_dictionary()


@app.put("/api/dictionary")
def put_dictionary(body: DictionaryIn):
    pairs = [{"from": p.get("from", "").strip(), "to": p.get("to", "")} for p in body.pairs]
    d = {"pairs": [p for p in pairs if p["from"]], "names": body.names}
    save_dictionary(d)
    return d


@app.get("/api/projects/{pid}/job")
def get_job(pid: str):
    project_dir(pid)
    return jobs.get(pid) or {"state": "idle"}


@app.post("/api/projects/{pid}/transcribe")
def start_transcribe(pid: str, body: TranscribeIn):
    project = load(pid)
    path = str(project_dir(pid) / project["source"])
    rules = Rules(max_chars=body.max_chars, max_lines=body.max_lines, max_cps=body.max_cps)

    def work(progress):
        from .transcribe import transcribe

        words = transcribe(path, body.model, body.language, body.prompt, progress)
        progress(1, "Feliratok tördelése…")
        p = load(pid)
        cues = words_to_cues(words, rules)
        fixed = apply_corrections(cues, load_dictionary()["pairs"], rules)
        p["cues"] = fix_timing(cues, rules)
        p["cues_changed"] = time.time()
        p["settings"] = body.model_dump()
        p["dictionary_fixes"] = fixed
        save(p)

    if body.prompt.strip():
        d = load_dictionary()
        d["names"] = body.prompt.strip()
        save_dictionary(d)
    run_job(pid, "transcribe", work)
    return {"ok": True}


@app.post("/api/projects/{pid}/import-srt")
async def import_srt(pid: str, file: UploadFile = File(...)):
    project = load(pid)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1250")  # régi magyar Windows-os SRT-k
    try:
        project["cues"] = srt.from_srt(text)
    except ValueError as e:
        raise HTTPException(400, str(e))
    project["cues_changed"] = time.time()
    save(project)
    return project


@app.get("/api/projects/{pid}/export.srt")
def export_srt(pid: str):
    project = load(pid)
    name = Path(project["name"]).stem + ".srt"
    return PlainTextResponse(
        "﻿" + srt.to_srt(project["cues"]),
        media_type="application/x-subrip; charset=utf-8",
        headers=disposition(name),
    )


@app.post("/api/projects/{pid}/retime")
def retime(pid: str):
    """Időzítés javítása (minimális hossz, olvasási sebesség, rések)."""
    project = load(pid)
    s = project.get("settings") or {}
    rules = Rules(max_chars=s.get("max_chars", 37), max_lines=s.get("max_lines", 2), max_cps=s.get("max_cps", 15.0))
    project["cues"] = fix_timing(sorted(project["cues"], key=lambda c: c["start"]), rules)
    project["cues_changed"] = time.time()
    save(project)
    return project


@app.post("/api/projects/{pid}/render")
def start_render(pid: str, body: RenderIn):
    project = load(pid)
    d = project_dir(pid)
    if not project["cues"]:
        raise HTTPException(400, "Még nincs felirat")
    (d / "subs.srt").write_text(srt.to_srt(project["cues"]), "utf-8")
    (d / "output.mp4").unlink(missing_ok=True)

    def work(progress):
        render.render(d, project["source"], "subs.srt", "output.tmp.mp4", body.mode, body.font_size, body.box, progress)
        (d / "output.tmp.mp4").replace(d / "output.mp4")

    run_job(pid, "render", work)
    return {"ok": True}


@app.get("/api/projects/{pid}/output")
def get_output(pid: str):
    project = load(pid)
    f = project_dir(pid) / "output.mp4"
    if not f.exists():
        raise HTTPException(404, "Még nincs elkészült videó")
    return FileResponse(f, media_type="video/mp4", headers=disposition(output_name(project)))


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
