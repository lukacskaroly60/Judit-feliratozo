# Judit feliratozó

Egyszerű, gyors feliratozó program: **MP4 be → feliratos MP4 ki.**

1. Behúzod a videót a böngészőablakba.
2. A program mesterséges intelligenciával (Whisper) leírja a magyar beszédet, és
   rögtön szabályos feliratokra bontja: soronként legfeljebb 37 karakter, legfeljebb
   2 sor, kiegyensúlyozott sortörés, ésszerű megjelenési idő.
3. Átnézed és javítod: a videó mellett ott a feliratlista, a felirat élőben látszik a
   képen, a hibás feliratok (túl hosszú sor, túl gyors, átfedés) pirossal jelennek meg,
   azokat a szavakat pedig, amelyekben az AI bizonytalan, narancssárgával kiemeli.
4. Egy kattintás: **Feliratos MP4 készítése** → letöltöd a kész videót (vagy SRT-t).

Minden a saját gépen fut, a videó nem kerül fel az internetre. Internet csak a
telepítéshez és az AI modell első letöltéséhez kell.

## Telepítés és indítás (Windows)

1. Telepítsd a **Python 3.12**-t: <https://www.python.org/downloads/release/python-31210/>
   (lent: **„Windows installer (64-bit)”**; a telepítőben pipáld be: **„Add python.exe to PATH”**).
   - **Ne a legújabb verziót** töltsd le (3.15): ahhoz az AI egyes részei még nem
     jelentek meg. A program a 3.10–3.14 közötti 64 bites Pythonokkal működik.
   - Ha már van másik Python a gépen, a 3.12 nyugodtan mellé telepíthető; az
     `Inditas.bat` magától a megfelelőt választja.
2. Töltsd le ezt a mappát (GitHubon: **Code → Download ZIP**), és csomagold ki.
3. Kattints duplán az **`Inditas.bat`** fájlra.
   - Az első indítás pár percig tart, mert települnek a szükséges részek.
   - Ha a telepítés megszakad, egyszerűen indítsd újra: elölről kezdi.
   - Az első feliratozáskor a program letölti az AI modellt (kb. 3 GB), ez egyszeri.
4. Magától megnyílik a böngésző a <http://127.0.0.1:8765> címen. Ha nem, írd be kézzel.

A programot a fekete ablak bezárásával lehet leállítani.

macOS-en vagy Linuxon az `inditas.sh` fájllal indul (`./inditas.sh`).

## Hordozható változat (pendrive-ról, telepítés nélkül)

Ha nem szeretnél semmit telepíteni a gépre, a program egy mappából – akár pendrive-ról –
is futtatható. Ehhez a gépre **nem kell Python**, és **semmi nem marad utána**: a Python,
az AI modell és a munkák is mind a mappában vannak.

**Előkészítés (egyszer, internettel, egy 64 bites Windowsos gépen):**

1. Másold a program kibontott mappáját a pendrive-ra.
2. Kattints duplán a **`Hordozhato_elokeszites.bat`** fájlra. Letölti a Pythont és a
   szükséges részeket a mappába, majd megkérdezi, melyik AI modellt töltse le
   (ajánlott: 1 = legpontosabb). Ez a pendrive sebességétől függően 10–30 perc.
   - Ha megszakad, csak futtasd újra: onnan folytatja, ahol abbahagyta.
   - Ha a Windows kék ablakkal figyelmeztet: **További információ → Futtatás mindenképp**.

**Használat (bármelyik Windowsos gépen):**

- Dupla kattintás a **`Hordozhato_inditas.bat`** fájlra. Ha előre letöltötted a modellt,
  internet sem kell hozzá.

**Amire figyelj:**

- Legalább **8 GB** szabad hely kell (a videók miatt inkább 16–32 GB-os pendrive).
- **USB 3-as** pendrive ajánlott, különben lassú a modell betöltése.
- FAT32-es pendrive-on egy fájl legfeljebb 4 GB lehet; nagy videókhoz formázd **exFAT**-ra.
- Ha az előkészítés azt írja, hogy hiányzik a „Visual C++ futtatókörnyezet”, telepítsd
  innen, majd futtasd újra: <https://aka.ms/vs/17/release/vc_redist.x64.exe>

A hordozható és a telepíthető változat ugyanaz a program, csak másképp indul.
Egy mappában mindkettő megfér, és ugyanazokat a munkákat (`data` mappa) látják.

## Sebesség

- **NVIDIA videókártyával** a felismerés gyors (egy 30 perces műsor néhány perc).
- **Csak processzorral** is működik, de lassabb: a legpontosabb modellel egy 30 perces
  műsor akár 30–60 perc is lehet a gép erősségétől függően. Ilyenkor a „Gyorsabb”
  (large-v3-turbo) modell jó választás, kb. feleannyi idő alatt végez.

Tipp: a **„Nevek, szakszavak”** mezőbe írt nevek (műsorvezetők, helyszínek,
intézmények) írásmódját az AI sokkal pontosabban eltalálja.

## Pontosság: így lesz hibátlan a felirat

Az AI jó, de nem tévedhetetlen, ezért a program úgy készült, hogy a javítás gyors legyen:

- **Bizonytalan szavak.** Ahol az AI nem biztos a dolgában, a felirat alatt narancssárga
  gomb jelenik meg a szóval („Ellenőrizd: ▶ Kovács”). Rákattintva a program pontosan azt
  a szót játssza le. Az **`Alt` + `U`** a következő bizonytalan szóhoz ugrik, és rögtön
  le is játssza – így végig lehet menni rajtuk anélkül, hogy az egész műsort újra kellene
  nézni. Ha a szót kijavítod, a jelölés magától eltűnik; ha jó volt, a „✓ Jó így” gombbal
  elfogadhatod. A fejlécben látszik, hány szó vár még ellenőrzésre.
- **Javításlista – a program tanul.** Ha egy nevet az AI rendszeresen elront, a
  **Keresés és csere** ablakban pipáld be a „Megjegyzés” lehetőséget. Ettől kezdve minden
  új átírás után automatikusan kijavítja. A listát a **📖 Javításlista** gombbal lehet
  szerkeszteni; ugyanitt megadhatók a gyakori nevek (műsorvezetők, helyszínek), amelyeket
  az AI már a felismeréskor figyelembe vesz.
- **A kész videó később is javítható.** A munka megmarad, bármikor visszanyitható,
  javítható, és a videó egy kattintással újra elkészíthető. Ha a kész videó óta változott
  a felirat, a letöltés gomb narancssárgán figyelmeztet, hogy a javítások még nincsenek
  benne.
- **Kész MP4 visszatöltése.** Ha egy **bekapcsolható feliratos** MP4-et húzol be, a
  program kiolvassa belőle a feliratot, és rögtön javíthatod. (Beégetett feliratot nem
  lehet visszaolvasni, mert az már a kép része – ezért érdemes a munkát a programban
  megtartani, vagy az SRT-t is elmenteni.)
- Alapból a **legpontosabb** AI modell fut (large-v3). Ha sietős, a gyorsabb is választható.

## Gyorsbillentyűk

| Billentyű | Művelet |
|---|---|
| `Ctrl` + `Szóköz` | lejátszás / szünet |
| `Alt` + `←` / `→` | 1 mp vissza / előre (`Shift`-tel: 0,1 mp) |
| `Alt` + `↑` / `↓` | előző / következő felirat |
| `Alt` + `I` / `O` | a felirat kezdete / vége legyen a jelenlegi időpont |
| `Alt` + `U` | következő bizonytalan szó (oda ugrik és lejátssza) |
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
- `Inditas.bat` – telepíthető változat (virtuális környezet a gépre telepített Pythonnal)
- `Hordozhato_elokeszites.bat`, `Hordozhato_inditas.bat` – hordozható változat a Windows
  beágyazott Pythonjával (`python/` mappa); a modell a `data/hf` mappába kerül (`HF_HOME`)
