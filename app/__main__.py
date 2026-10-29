"""Indítás: python -m app"""
import os
import threading
import webbrowser

import uvicorn

PORT = int(os.environ.get("PORT", "8765"))

if __name__ == "__main__":
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"\n  Judit feliratozó fut: http://127.0.0.1:{PORT}\n  (Leállítás: Ctrl+C)\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning")
