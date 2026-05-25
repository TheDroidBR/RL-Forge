import threading
import time
import requests
import hashlib
import platform
import uuid
from core.utils import get_data_dir

# Solari Metrics Configuration
METRICS_URL = "https://solarirpc.com/counter.php"
APP_ITEM_ID = "rlforge"
APP_VERSION = "2.0.0"

def get_machine_id():
    """Generates a unique, anonymous hash for the machine."""
    try:
        # Use a combination of node name, architecture and getnode
        unique_str = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
        return hashlib.sha256(unique_str.encode()).hexdigest()
    except Exception:
        return "unknown_machine"

def send_ping(uid):
    """Sends a heartbeat to the Solari metrics server."""
    url = f"{METRICS_URL}?action=ping&version={APP_VERSION}&uid={uid}&bd=rl_forge_client"
    try:
        # Try requests first as it's cleaner
        requests.get(url, timeout=10, verify=False, headers={"User-Agent": "RLForge-Client"})
    except Exception:
        try:
            # Fallback to urllib.request (builtin)
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "RLForge-Client"})
            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()
        except Exception:
            pass

def send_increment():
    """Signals that a new unique user has started the app."""
    url = f"{METRICS_URL}?action=increment&item={APP_ITEM_ID}"
    try:
        requests.get(url, timeout=10, verify=False, headers={"User-Agent": "RLForge-Client"})
    except Exception:
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "RLForge-Client"})
            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()
        except Exception:
            pass

def _metrics_loop(uid):
    """Background loop for heartbeats."""
    # Send first ping immediately
    send_ping(uid)
    
    # Check if we should increment total users (first run on this machine)
    flag_file = get_data_dir() / ".metrics_initialized"
    if not flag_file.exists():
        send_increment()
        try:
            get_data_dir().mkdir(parents=True, exist_ok=True)
            flag_file.touch()
        except Exception:
            pass
            
    while True:
        # Ping every 60 seconds (threshold in PHP is 120s)
        time.sleep(60)
        send_ping(uid)

def start_metrics():
    """Initializes and starts the metrics heartbeat in a background thread."""
    uid = get_machine_id()
    t = threading.Thread(target=_metrics_loop, args=(uid,), daemon=True)
    t.start()
