# ruff: noqa: E402
"""
RL Forge — main entry point (headless API server fallback).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from api.server import app, find_free_port

if __name__ == "__main__":
    port = find_free_port()
    # Electron or bat script reads this line to know which port to connect to
    print(f"PORT:{port}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
