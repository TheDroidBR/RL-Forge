"""
RL Forge — Flask REST API Server
Spawned by Electron main process. Prints PORT:{n} to stdout.
"""
# ruff: noqa: E402

import sys
import socket
import queue
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.swapper import (
    load_config, save_config, load_products, fetch_products_csv,
    filter_products, get_slots, swap, restore_item, restore_all, list_backups,
    get_color_variants, get_item_color, RL_PAINT_COLORS,
    prettify_filename, autodetect_rl_path, encode_combo_code, decode_combo_code,
    get_base_label
)
from core.utils import get_data_dir, is_game_running
from core.i18n import TRANSLATIONS, set_language, t

app = Flask(__name__)

IMAGE_DIR   = get_data_dir() / "data" / "images"
RENDERER_DIR = ROOT / "electron" / "renderer"

# ─── CORS headers for local Electron origin ───────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/api/<path:p>", methods=["OPTIONS"])
def options_handler(p):
    return "", 204


# ─── Utilities ────────────────────────────────────────────────────────────────
def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


# ─── Config ───────────────────────────────────────────────────────────────────
@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.get_json(force=True)
    cfg  = load_config()
    cfg.update(data)
    save_config(cfg)
    if "language" in data:
        set_language(data["language"])
    return jsonify({"ok": True})


# ─── Products ─────────────────────────────────────────────────────────────────
@app.route("/api/products", methods=["GET"])
def get_products():
    products  = load_products()
    search    = request.args.get("search", "")
    slot      = request.args.get("slot", "Todos")
    favs_only = request.args.get("favs_only", "false") == "true"
    page      = int(request.args.get("page", 0))
    per_page  = int(request.args.get("per_page", 15))

    cfg       = load_config()
    favorites = cfg.get("favorites", [])

    filtered = filter_products(products, search, slot)
    if favs_only:
        filtered = [p for p in filtered if p.get("Name", "") in favorites]

    total       = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = max(0, min(page, total_pages - 1))

    start = page * per_page
    page_items = filtered[start : start + per_page]

    for item in page_items:
        item["is_fav"] = item.get("Name", "") in favorites

    return jsonify({
        "items":       page_items,
        "total":       total,
        "page":        page,
        "total_pages": total_pages,
    })


@app.route("/api/products/fetch", methods=["POST"])
def fetch_products():
    try:
        fetch_products_csv()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/slots", methods=["GET"])
def get_slots_list():
    products = load_products()
    slots    = get_slots(products)
    return jsonify({"slots": slots})


# ─── Favorites ────────────────────────────────────────────────────────────────
@app.route("/api/favorites/toggle", methods=["POST"])
def toggle_favorite():
    data = request.get_json(force=True)
    name = data.get("name", "")
    cfg  = load_config()
    favs = cfg.get("favorites", [])
    if name in favs:
        favs.remove(name)
        is_fav = False
    else:
        favs.append(name)
        is_fav = True
    cfg["favorites"] = favs
    save_config(cfg)
    return jsonify({"ok": True, "is_fav": is_fav})


# ─── Swap ─────────────────────────────────────────────────────────────────────
# SSE log queue
_log_queue: queue.Queue = queue.Queue()


@app.route("/api/swap", methods=["POST"])
def do_swap():
    if is_game_running():
        err = t("err_game_running", "Cannot modify game files while Rocket League is running. Please close the game and try again.")
        err_log = t("log_err_game_running", "❌ Safety Error: Rocket League is running! Close the game before swapping or restoring.")
        return jsonify({"ok": False, "error": err, "logs": [err_log]}), 400

    data            = request.get_json(force=True)
    orig_name       = data.get("orig_name")
    target_name     = data.get("target_name")
    pkg_dir         = data.get("pkg_dir")
    hex_color       = data.get("hex_color")        # "#RRGGBB" or null
    hex_color_flame = data.get("hex_color_flame")  # "#RRGGBB" or null
    rgb_intensity   = float(data.get("rgb_intensity", 1.0))

    products = load_products()
    orig   = next((p for p in products if p["Name"] == orig_name), None)
    target = next((p for p in products if p["Name"] == target_name), None)

    if not orig or not target:
        return jsonify({"ok": False, "error": t("err_item_not_found", "Item not found.")}), 404

    # Safety Check: Block swaps with custom RGB paint or choosing a painted variant
    # when the target (final destination) is Body_Octane or OEM wheels.
    # Painting them triggers client crashes & EAC flags because their textures reside in Startup.upk.
    is_painting_attempt = (hex_color is not None and hex_color != "") or (get_item_color(target.get("Label", "")) is not None)
    if is_painting_attempt:
        target_lbl = get_base_label(target.get("Label", "")).lower()
        target_nm = target_name.lower()
        target_sl = target.get("Slot", "").lower()
        is_octane = (target_nm == "body_octane") or (target_lbl == "octane" and target_sl == "body")
        is_oem = ("oem" in target_nm) or (target_lbl == "oem" and target_sl == "wheels")
        if is_octane or is_oem:
            err = t("err_paint_blocking", "Swaps with paint (RGB or painted variant) are not allowed for Octane or OEM wheels as final destination, as their textures reside in the global Startup.upk file.")
            err_log = t("log_err_paint_blocking", "❌ Security Error: Swaps with paint (RGB or painted variant) are not allowed for Octane or OEM wheels as final destination, as their textures reside in the global Startup.upk file.")
            return jsonify({"ok": False, "error": err, "logs": [err_log]}), 400

    rgb_color = None
    if hex_color:
        h = hex_color.lstrip("#")
        rgb_color = (int(h[0:2], 16) / 255.0,
                     int(h[2:4], 16) / 255.0,
                     int(h[4:6], 16) / 255.0)
    elif target.get("Label"):
        color_name = get_item_color(target["Label"])
        if color_name and color_name in RL_PAINT_COLORS:
            fallback_hex = RL_PAINT_COLORS[color_name]
            h = fallback_hex.lstrip("#")
            rgb_color = (int(h[0:2], 16) / 255.0,
                         int(h[2:4], 16) / 255.0,
                         int(h[4:6], 16) / 255.0)

    rgb_color_flame = None
    if hex_color_flame:
        h = hex_color_flame.lstrip("#")
        rgb_color_flame = (int(h[0:2], 16) / 255.0,
                           int(h[2:4], 16) / 255.0,
                           int(h[4:6], 16) / 255.0)
    elif target.get("Label"):
        color_name = get_item_color(target["Label"])
        if color_name and color_name in RL_PAINT_COLORS:
            fallback_hex = RL_PAINT_COLORS[color_name]
            h = fallback_hex.lstrip("#")
            rgb_color_flame = (int(h[0:2], 16) / 255.0,
                               int(h[2:4], 16) / 255.0,
                               int(h[4:6], 16) / 255.0)

    logs = []
    try:
        swap(orig, target, pkg_dir,
             log_cb=logs.append,
             rgb_color=rgb_color,
             rgb_color_flame=rgb_color_flame,
             rgb_intensity=rgb_intensity)
        return jsonify({"ok": True, "logs": logs})
    except Exception as e:
        logs.append(t("err_prefix", "❌ Error: {error}").format(error=str(e)))
        return jsonify({"ok": False, "error": str(e), "logs": logs}), 500


@app.route("/api/restore", methods=["POST"])
def do_restore():
    if is_game_running():
        return jsonify({"ok": False, "error": t("err_game_running", "Cannot modify game files while Rocket League is running. Please close the game and try again.")}), 400

    data      = request.get_json(force=True)
    item_name = data.get("item_name")
    pkg_dir   = data.get("pkg_dir")
    logs      = []
    try:
        restore_item(item_name, pkg_dir, log_cb=logs.append)
        return jsonify({"ok": True, "logs": logs})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "logs": logs}), 500


@app.route("/api/restore-all", methods=["POST"])
def do_restore_all():
    if is_game_running():
        return jsonify({"ok": False, "error": t("err_game_running", "Cannot modify game files while Rocket League is running. Please close the game and try again.")}), 400

    data    = request.get_json(force=True)
    pkg_dir = data.get("pkg_dir")
    logs    = []
    try:
        restore_all(pkg_dir, log_cb=logs.append)
        return jsonify({"ok": True, "logs": logs})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "logs": logs}), 500


@app.route("/api/backups", methods=["GET"])
def get_backups():
    pkg_dir = request.args.get("pkg_dir", "")
    try:
        backups = list_backups(pkg_dir)
        for b in backups:
            b["display_name"] = prettify_filename(b["file"])
        return jsonify({"backups": backups})
    except Exception as e:
        return jsonify({"backups": [], "error": str(e)})


# ─── Color Variants ───────────────────────────────────────────────────────────
@app.route("/api/color-variants", methods=["GET"])
def color_variants():
    name     = request.args.get("name", "")
    products = load_products()
    item     = next((p for p in products if p["Name"] == name), None)
    if not item:
        return jsonify({"variants": [], "current_color": None})
    variants      = get_color_variants(products, item)
    current_color = get_item_color(item.get("Label", ""))
    return jsonify({
        "variants":      variants,
        "current_color": current_color,
        "paint_colors":  RL_PAINT_COLORS,
    })


# ─── Autodetect ───────────────────────────────────────────────────────────────
@app.route("/api/autodetect", methods=["GET"])
def autodetect():
    platform = request.args.get("platform", "epic")
    try:
        path = autodetect_rl_path(platform)
        if path:
            return jsonify({"ok": True, "path": str(path)})
        return jsonify({"ok": False, "path": None})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ─── Combos ───────────────────────────────────────────────────────────────────
@app.route("/api/combos/encode", methods=["POST"])
def encode_combo():
    data  = request.get_json(force=True)
    swaps = data.get("swaps", [])
    try:
        code = encode_combo_code(swaps)
        return jsonify({"ok": True, "code": code})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/combos/decode", methods=["POST"])
def decode_combo():
    data = request.get_json(force=True)
    code = data.get("code", "")
    try:
        result = decode_combo_code(code)
        if result is None:
            return jsonify({"ok": False, "error": t("err_invalid_combo_code", "Invalid combo code.")}), 400
        return jsonify({"ok": True, "swaps": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── Translations ─────────────────────────────────────────────────────────────
@app.route("/api/translations", methods=["GET"])
def get_translations():
    lang    = request.args.get("lang", "pt-BR")
    strings = TRANSLATIONS.get(lang, TRANSLATIONS.get("en", {}))
    return jsonify(strings)


@app.route("/api/paint-colors", methods=["GET"])
def get_paint_colors():
    return jsonify(RL_PAINT_COLORS)


# ─── Game Running ─────────────────────────────────────────────────────────────
@app.route("/api/game-running", methods=["GET"])
def game_running():
    return jsonify({"running": is_game_running()})


# ─── Static: images ───────────────────────────────────────────────────────────
@app.route("/api/images/<path:name>")
def serve_image(name):
    img_path = IMAGE_DIR / name
    if img_path.exists():
        return send_file(img_path)
    return "", 404


# ─── Static: renderer (HTML/CSS/JS) ──────────────────────────────────────────
@app.route("/")
def serve_index():
    return send_from_directory(RENDERER_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(RENDERER_DIR, path)


# ─── Entry ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = find_free_port()
    # Electron reads this line to know which port to connect to
    print(f"PORT:{port}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
