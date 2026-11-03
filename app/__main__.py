"""Indítás: python -m app"""
import os
import socket
import sys
import threading
import webbrowser

import uvicorn

PORT = int(os.environ.get("PORT", "8765"))


def port_foglalt(port: int) -> bool:
    """Igaz, ha már fut valami (pl. a program egy korábbi példánya) ezen a porton."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    if port_foglalt(PORT):
        print(
            "\n  FIGYELEM: a Judit feliratozó egy MÁSIK példánya már fut"
            f" (http://127.0.0.1:{PORT}).\n"
            "  Valószínűleg egy korábbi (régebbi) változat fekete ablaka van még nyitva.\n\n"
            "  Teendő: zárd be az összes korábbi fekete ablakot (vagy indítsd újra a gépet),\n"
            "  majd indítsd el újra ezt a változatot.\n"
        )
        sys.exit(1)
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"\n  Judit feliratozó fut: http://127.0.0.1:{PORT}\n  (Leállítás: Ctrl+C)\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning")
