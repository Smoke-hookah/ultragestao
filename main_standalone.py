#!/usr/bin/env python3
"""
Entry point for the standalone executable.
Starts the Flask server and opens the browser automatically.
"""

import os
import sys
import threading
import time
import webbrowser
import multiprocessing
from pathlib import Path


def _configure_utf8_stdio() -> None:
    """Best-effort: avoid UnicodeEncodeError in Windows consoles."""
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _pick_xml_folder() -> int:
    """Open a folder picker and print the selected path to stdout."""
    _configure_utf8_stdio()
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
            root.update()
        except Exception:
            pass

        folder = filedialog.askdirectory(
            title="Selecionar Pasta com XMLs",
            initialdir=str(Path.home() / "Desktop"),
        )
        root.destroy()

        if folder:
            sys.stdout.write(str(folder))
            sys.stdout.flush()
            return 0
        return 1
    except Exception:
        return 2


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    RUNTIME_DIR = Path(sys.executable).parent
    os.chdir(BASE_DIR)
else:
    BASE_DIR = Path(__file__).parent
    RUNTIME_DIR = BASE_DIR


def _resolve_playwright_browsers_dir(runtime_dir: Path) -> Path:
    root_candidate = runtime_dir / "playwright-browsers"
    internal_candidate = runtime_dir / "_internal" / "playwright-browsers"
    if root_candidate.exists() or not internal_candidate.exists():
        return root_candidate
    return internal_candidate

CONFIG_DIR = RUNTIME_DIR / "config"
OUTPUT_DIR = RUNTIME_DIR / "output"
LOGS_DIR = RUNTIME_DIR / "logs"
PLAYWRIGHT_BROWSERS_DIR = _resolve_playwright_browsers_dir(RUNTIME_DIR)

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

os.environ["ULTRADANFE_BASE_DIR"] = str(BASE_DIR)
os.environ["ULTRADANFE_CONFIG_DIR"] = str(CONFIG_DIR)
os.environ["ULTRADANFE_OUTPUT_DIR"] = str(OUTPUT_DIR)
os.environ["ULTRADANFE_LOGS_DIR"] = str(LOGS_DIR)
os.environ["ULTRADANFE_PLAYWRIGHT_BROWSERS_DIR"] = str(PLAYWRIGHT_BROWSERS_DIR)


def open_browser() -> None:
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")


def main() -> None:
    _configure_utf8_stdio()

    from api import app

    print("=" * 60)
    print("UltraDanfe XML - Sistema de Processamento de Notas Fiscais")
    print("=" * 60)
    print(f"Diretorio base: {BASE_DIR}")
    print(f"Diretorio de runtime: {RUNTIME_DIR}")
    print(f"Config: {CONFIG_DIR}")
    print(f"Saida: {OUTPUT_DIR}")
    print(f"Logs: {LOGS_DIR}")
    print("Iniciando servidor...")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    print("\n[OK] Servidor iniciado em http://127.0.0.1:5000")
    print("[OK] O navegador sera aberto automaticamente")
    print("\nPressione Ctrl+C para encerrar\n")

    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True,
        )
    except KeyboardInterrupt:
        print("\n\nEncerrando servidor...")
        sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if "--pick-xml-folder" in sys.argv:
        raise SystemExit(_pick_xml_folder())
    main()
