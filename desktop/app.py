#!/usr/bin/env python3
"""
TaxTrouble - Standalone Linux Desktop App
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

try:
    import webview
except ImportError:
    print("Installing PyWebView...")
    os.system("pip install pywebview[gtk] --quiet")
    import webview

from server import app as fastapi_app

import uvicorn


def run_backend():
    """Run FastAPI backend in background thread."""
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        access_log=False
    )


def main():
    print("Starting TaxTrouble Desktop App...")
    
    # Start backend in background
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Give backend time to start
    time.sleep(2)
    
    # Create desktop window
    webview.create_window(
        title="TaxTrouble - Texas Tax & Lien Scraper",
        url="http://127.0.0.1:8000",
        width=1400,
        height=900,
        resizable=True,
        min_size=(1000, 700)
    )
    
    webview.start()


if __name__ == "__main__":
    main()