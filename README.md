# Judit feliratozó

Egyszerű, gyors feliratozó program: **MP4 be → feliratos MP4 ki.**

1. Behúzod a videót a böngészőablakba.
2. A program mesterséges intelligenciával (Whisper) leírja a magyar beszédet, és
   rögtön szabályos feliratokra bontja: soronként legfeljebb 37 karakter, legfeljebb
   2 sor, kiegyensúlyozott sortörés, ésszerű megjelenési idő.
3. Átnézed és javítod: a videó mellett ott a feliratlista, a felirat élőben látszik a
   képen, a hibás feliratok (túl hosszú sor, túl gyors, átfedés) pirossal jelennek meg.
4. Egy kattintás: **Feliratos MP4 készítése** → letöltöd a kész videót (vagy SRT-t).

Minden a saját gépen fut, a videó nem kerül fel az internetre. Internet csak a
telepítéshez és az AI modell első letöltéséhez kell.

## Telepítés és indítás (Windows)

1. Telepítsd a Pythont: <https://www.python.org/downloads/> (a telepítőben pipáld be:
   **„Add python.exe to PATH”**).
2. Töltsd le ezt a mappát (GitHubon: **Code → Download ZIP**), és csomagold ki.
3. Kattints duplán az **`Inditas.bat`** fájlra.
   - Az első indítás pár percig tart, mert települnek a szükséges részek.
   - Az első feliratozáskor a program letölti az AI modellt (kb. 1,5 GB), ez egyszeri.
4. Magától megnyílik a böngésző a <http://127.0.0.1:8765> címen. Ha nem, írd be kézzel.

A programot a fekete ablak bezárásával lehet leállítani.

macOS-en vagy Linuxon az `inditas.sh` fájllal indul (`./inditas.sh`).

## Sebesség

- **NVIDIA videókártyával** a felismerés nagyon gyors (egy 30 perces műsor 1–3 perc).
- **Csak processzorral** is működik, de lassabb: egy 30 perces műsorra számíts
  10–30 percet a gép erősségétől függően. Ha sietős, a beállításoknál válaszd a
  „Közepes” vagy „Gyors” modellt.

Tipp: a **„Nevek, szakszavak”** mezőbe írt nevek (műsorvezetők, helyszínek,
intézmények) írásmódját az AI sokkal pontosabban eltalálja.

## Gyorsbillentyűk

| Billentyű | Művelet |
|---|---|
| `Ctrl` + `Szóköz` | lejátszás / szünet |
| `Alt` + `←` / `→` | 1 mp vissza / előre (`Shift`-tel: 0,1 mp) |
| `Alt` + `↑` / `↓` | előző / következő felirat |
| `Alt` + `I` / `O` | a felirat kezdete / vége legyen a jelenlegi időpont |
| `Alt` + `P` | a kijelölt felirat lejátszása |
| `Alt` + `N` | új felirat a jelenlegi időpontnál |
| `Alt` + `S` | felirat kettévágása a kurzor helyén |
| `Alt` + `M` | összevonás a következő felirattal |
| `Alt` + `W` | automatikus sortörés |
| `Alt` + `Delete` | felirat törlése |
| `Alt` + `Z` | visszavonás |

Az időkódok kézzel is átírhatók (`00:01:02,500` vagy képkockával `00:01:02:12`).

## Kimenet

- **Beégetett felirat:** mindig látszik, bármilyen lejátszón és weboldalon.
- **Bekapcsolható felirat:** külön feliratsáv az MP4-ben, másodpercek alatt elkészül.
- **SRT:** szabványos feliratfájl, ha a megrendelő külön kéri.

A munka folyamatosan, automatikusan mentődik; a kezdőképernyőn a korábbi munkák
listájából bármikor folytatható. Az adatok a program mappájában, a `data` könyvtárban vannak.

## Fejlesztőknek

```
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m app        # szerver: http://127.0.0.1:8765
.venv/bin/python -m pytest     # tesztek
```

- `app/transcribe.py` – beszédfelismerés (faster-whisper, szószintű időbélyegek)
- `app/segment.py` – feliratokra bontás, sortörés, időzítési szabályok
- `app/render.py` – MP4 készítés ffmpeg-gel (az `imageio-ffmpeg` csomag hozza magával)
- `app/main.py` – FastAPI szerver; `app/static/` – a szerkesztő felület
