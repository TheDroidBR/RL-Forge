"""
Swapper — high-level item swap/restore logic.
Uses upk.py for all binary operations.
"""

import os
import shutil
import csv
import json
import requests
from pathlib import Path
from core.utils import get_data_dir
from core.i18n import t
from .upk import (
    decrypt_upk, encrypt_upk, patch_names,
    get_material_and_chassis_names, detect_names_from_file,
    get_wheel_and_mesh_names, detect_wheel_names_from_file
)

PRODUCTS_URL = "https://raw.githubusercontent.com/ShinyEmii/Toga-Files/refs/heads/master/products.csv"

CONFIG_FILE  = get_data_dir() / "data" / "config.json"
CSV_FILE     = get_data_dir() / "data" / "products.csv"


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

def save_config(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Products CSV
# ─────────────────────────────────────────────────────────────────────────────

def fetch_products_csv(progress_cb=None) -> None:
    """Download the latest products.csv from Toga-Files."""
    if progress_cb:
        progress_cb("Baixando products.csv...")
    resp = requests.get(PRODUCTS_URL, timeout=20)
    resp.raise_for_status()
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_FILE, "wb") as f:
        f.write(resp.content)
    if progress_cb:
        progress_cb("products.csv atualizado com sucesso!")

def load_products() -> list[dict]:
    """Load all products from the local CSV."""
    if not CSV_FILE.exists():
        return []
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("Name", "").strip()]

def filter_products(products: list[dict], query: str = "", slot: str = "") -> list[dict]:
    """Filter products by search query and/or slot type, with multi-term fuzzy matching and paint color shorthand mappings."""
    result = products
    if slot and slot != "Todos":
        result = [p for p in result if p.get("Slot", "").strip().lower() == slot.lower()]
    if query:
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if terms:
            filtered = []
            for p in result:
                label_l = p.get("Label", "").lower()
                name_l = p.get("Name", "").lower()
                
                match = True
                for term in terms:
                    # Specialized shorthand mappings for paint colors
                    if term == "tw" and ("titanium white" in label_l or "tw" in label_l or "tw" in name_l):
                        continue
                    if term == "bs" and ("burnt sienna" in label_l or "bs" in label_l or "bs" in name_l):
                        continue
                    if term == "fg" and ("forest green" in label_l or "fg" in label_l or "fg" in name_l):
                        continue
                    if term == "sb" and ("sky blue" in label_l or "sb" in label_l or "sb" in name_l):
                        continue
                    if term == "bk" and ("black" in label_l or "bk" in label_l or "bk" in name_l):
                        continue
                    if term == "cr" and ("crimson" in label_l or "cr" in label_l or "cr" in name_l):
                        continue
                    if term == "cb" and ("cobalt" in label_l or "cb" in label_l or "cb" in name_l):
                        continue
                    if term == "sf" and ("saffron" in label_l or "sf" in label_l or "sf" in name_l):
                        continue
                    if term == "lm" and ("lime" in label_l or "lm" in label_l or "lm" in name_l):
                        continue
                    if term in label_l or term in name_l:
                        continue
                    match = False
                    break
                if match:
                    filtered.append(p)
            result = filtered
    return result

def get_slots(products: list[dict]) -> list[str]:
    """Return unique slot names."""
    slots = sorted({p.get("Slot", "").strip() for p in products if p.get("Slot", "").strip()})
    return ["Todos"] + slots


# ─────────────────────────────────────────────────────────────────────────────
# Paint color / variant helpers
# ─────────────────────────────────────────────────────────────────────────────

# RL paint color names and their display hex colors (UI only)
RL_PAINT_COLORS: dict[str, str] = {
    "Titanium White": "#f0f0f0",
    "Forest Green":   "#228b22",
    "Burnt Sienna":   "#8b4513",
    "Sky Blue":       "#87ceeb",
    "Black":          "#2a2a2a",
    "White":          "#f0f0f0",
    "Grey":           "#808080",
    "Gray":           "#808080",
    "Crimson":        "#dc143c",
    "Pink":           "#ff69b4",
    "Cobalt":         "#0047ab",
    "Saffron":        "#ffaa00",
    "Yellow":         "#ffd700",
    "Lime":           "#7cfc00",
    "Orange":         "#ff8c00",
    "Purple":         "#9b59b6",
    "Unpainted":      "#555577",
}

# Internal suffixes used by Rocket League for name-table painting
PAINT_INTERNAL_NAMES: dict[str, list[str]] = {
    "Titanium White": ["TW", "TitaniumWhite", "White"],
    "Black":          ["Black"],
    "Crimson":        ["Crimson"],
    "Cobalt":         ["Cobalt"],
    "Sky Blue":       ["SkyBlue"],
    "Burnt Sienna":   ["BurntSienna", "BS"],
    "Saffron":        ["Saffron"],
    "Lime":           ["Lime"],
    "Forest Green":   ["ForestGreen", "FG"],
    "Orange":         ["Orange"],
    "Purple":         ["Purple"],
    "Pink":           ["Pink"],
    "Gray":           ["Grey", "Gray"],
    "Grey":           ["Grey", "Gray"],
}

# Sorted longest-first so "Sky Blue" matches before "Blue"
_PAINT_SUFFIXES = sorted(RL_PAINT_COLORS.keys(), key=len, reverse=True)


def get_base_label(label: str) -> str:
    """Strip paint color suffix to get the canonical item name."""
    s = label.strip()
    for color in _PAINT_SUFFIXES:
        if s.lower().endswith(" " + color.lower()):
            return s[: -(len(color) + 1)].strip()
    return s


def get_item_color(label: str) -> str | None:
    """Return the paint color name of an item label, or None if unpainted."""
    s = label.strip()
    for color in _PAINT_SUFFIXES:
        if s.lower().endswith(" " + color.lower()):
            return color
    return None


def get_color_variants(products: list[dict], item: dict) -> list[dict]:
    """
    Return all painted variants of an item (same slot + same base label),
    sorted: unpainted first, then alphabetically by color.
    """
    base  = get_base_label(item.get("Label", ""))
    slot  = item.get("Slot", "").strip().lower()
    result = []
    for p in products:
        if p.get("Slot", "").strip().lower() != slot:
            continue
        if get_base_label(p.get("Label", "")) == base:
            result.append(p)
    # Unpainted first
    result.sort(key=lambda p: (get_item_color(p.get("Label", "")) is not None,
                                get_item_color(p.get("Label", "")) or ""))
    return result



# ─────────────────────────────────────────────────────────────────────────────
# Backup management
# ─────────────────────────────────────────────────────────────────────────────

def get_backup_dir(pkg_dir: str) -> Path:
    cfg = load_config()
    platform = cfg.get("active_platform", "epic")
    
    backup = cfg.get("backup_dir", "")
    if backup:
        return Path(backup) / platform.title()
        
    suffix = "_Epic" if platform == "epic" else "_Steam"
    return Path(pkg_dir).parent / f"_RL_Forge_Backups{suffix}"

def list_backups(pkg_dir: str) -> list[dict]:
    """Return list of active swaps (files that have a backup)."""
    backup_dir = get_backup_dir(pkg_dir)
    if not backup_dir.exists():
        return []
    result = []
    for upk in backup_dir.glob("*_SF.upk"):
        if upk.name.endswith("_T_SF.upk"):
            continue
        
        # Check physical existence in the game's CookedPCConsole directory
        game_file = Path(pkg_dir) / upk.name
        exists_in_game = game_file.exists()
        
        # Check size and readability of the backup file
        try:
            backup_size = upk.stat().st_size
            # Try reading a few bytes to verify it's readable and not locked/corrupted
            with open(upk, "rb") as f:
                f.read(10)
            is_readable = True
        except Exception:
            backup_size = 0
            is_readable = False
            
        result.append({
            "name":           upk.stem.replace("_SF", ""),
            "file":           upk.name,
            "backup_path":    str(upk),
            "exists_in_game": exists_in_game,
            "backup_size":    backup_size,
            "is_readable":    is_readable
        })
    return result

def restore_item(item_name: str, pkg_dir: str, log_cb=None) -> None:
    """Restore a single item from backup."""
    backup_dir = get_backup_dir(pkg_dir)
    backup_file = backup_dir / f"{item_name}_SF.upk"
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup não encontrado: {backup_file}")
    dest = Path(pkg_dir) / f"{item_name}_SF.upk"
    shutil.copy2(backup_file, dest)
    backup_file.unlink()
    if log_cb:
        log_cb(t("log_restored", "✅ Restored: {name}").format(name=item_name))

    # Also restore corresponding texture file if it exists
    backup_tex = backup_dir / f"{item_name}_T_SF.upk"
    if backup_tex.exists():
        dest_tex = Path(pkg_dir) / f"{item_name}_T_SF.upk"
        shutil.copy2(backup_tex, dest_tex)
        backup_tex.unlink()
        if log_cb:
            log_cb(t("log_restored_textures", "🎨 Restored textures for: {name}").format(name=item_name))

def restore_all(pkg_dir: str, log_cb=None) -> None:
    """Restore all backed-up items."""
    backups = list_backups(pkg_dir)
    if not backups:
        if log_cb:
            log_cb(t("log_no_backups", "ℹ️ No backups found."))
        return
    for b in backups:
        restore_item(b["name"], pkg_dir, log_cb)

def prettify_filename(filename: str) -> str:
    """Convert a raw upk filename into a friendly, readable Portuguese name."""
    import re
    # Strip suffixes like _SF or _T, and also extension .upk
    name = filename.replace("_SF", "").replace("_T", "")
    if name.lower().endswith(".upk"):
        name = name[:-4]
    
    # Prefix mapping to friendly Portuguese slot names
    prefix_map = {
        "antenna": "Antena",
        "decal": "Decalque",
        "goalexplosion": "Explosão de Gol",
        "wheels": "Rodas",
        "wheel": "Rodas",
        "topper": "Topper",
        "body": "Carro",
        "trail": "Rastro",
        "engineaudio": "Áudio de Motor",
        "boost": "Boost",
    }
    
    parts = name.split("_")
    if not parts:
        return name
        
    prefix = parts[0].lower()
    
    # Check if there are other parts. If not, just title case the name.
    if len(parts) == 1:
        rest = re.sub(r'(?<!^)(?=[A-Z])', ' ', parts[0])
        return rest.title()
        
    # Translate or capitalize the prefix dynamically as fallback
    slot_name = prefix_map.get(prefix, prefix.capitalize())
    
    rest = " ".join(parts[1:])
    # Prettify camelCase (e.g. AlphaReward -> Alpha Reward)
    rest = re.sub(r'(?<!^)(?=[A-Z])', ' ', rest)
    rest = rest.replace("_", " ").strip()
    return f"{slot_name}: {rest}"


# ─────────────────────────────────────────────────────────────────────────────
# Core swap
# ─────────────────────────────────────────────────────────────────────────────

def _execute_single_upk_swap(
    orig_name: str,
    target_name: str,
    orig_package: str,
    target_package: str,
    orig_aes: str | None,
    target_aes: str | None,
    pkg_dir: str,
    log_cb=None,
    rgb_color: tuple[float, float, float] | None = None,
    rgb_color_flame: tuple[float, float, float] | None = None,
    rgb_intensity: float = 1.0,
    is_boost: bool = False,
    equipped_is_painted: bool = False
) -> None:
    pkg_path   = Path(pkg_dir)
    backup_dir = get_backup_dir(pkg_dir)

    # Resolve target file: prioritize pristine original from backups to support chained swaps safely
    target_backup = backup_dir / f"{target_package}_SF.upk"
    if target_backup.exists():
        target_file = target_backup
        if log_cb:
            log_cb(t("log_using_original_from_backup", "[info] Using original file for {name} from backup.").format(name=target_package))
    else:
        target_file = pkg_path / f"{target_package}_SF.upk"

    orig_file    = pkg_path / f"{orig_package}_SF.upk"

    if not target_file.exists():
        raise FileNotFoundError(f"Arquivo do item alvo não encontrado:\n{target_file}")
    if not orig_file.exists():
        raise FileNotFoundError(f"Arquivo do item original não encontrado:\n{orig_file}")

    # ── Backup ──────────────────────────────────────────────────────────────
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{orig_package}_SF.upk"
    if not backup_path.exists():
        shutil.copy2(orig_file, backup_path)
        if log_cb:
            log_cb(t("log_original_saved", "[backup] Original saved: {name}").format(name=backup_path.name))
    else:
        if log_cb:
            log_cb(t("log_using_existing_backup", "[info] Using existing original backup."))

    import tempfile
    import io
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # RLUPKTool requires the file to be named *_decrypted.upk to re-encrypt
        decrypted_path = tmp / f"{target_package}_SF_decrypted.upk"
        patched_path   = tmp / f"{orig_package}_SF_decrypted.upk"   # must end in _decrypted.upk!
        reenc_path     = tmp / f"{orig_package}_SF.upk"

        if log_cb:
            log_cb(t("log_decrypting", "[1/4] Decrypting {name}...").format(name=target_file.name))
        decrypt_upk(str(target_file), target_aes, str(decrypted_path))

        if log_cb:
            log_cb(t("log_altering_nametable", "[2/4] Altering name table: {target} -> {orig}...").format(target=target_name, orig=orig_name))
        
        # Otimização de E/S binária: bufferizado totalmente em memória com BytesIO
        with open(decrypted_path, "rb") as f:
            in_mem = io.BytesIO(f.read())
            data = in_mem.getvalue()
        
        # Load all names from the equipped backup file to resolve casings and dynamic names once
        from .upk import (
            get_package_names_from_file,
            get_material_and_chassis_names_from_list,
            get_wheel_and_mesh_names_from_list
        )
        equipped_names = get_package_names_from_file(backup_path, orig_aes)
        
        # Dynamically detect target and equipped material & chassis names
        target_body_mat, target_chassis_mat = get_material_and_chassis_names(data)
        equipped_body_mat, equipped_chassis_mat = get_material_and_chassis_names_from_list(equipped_names)
        
        # Dynamically detect target and equipped wheel materials & meshes
        target_wheel_mat, target_wheel_mat_painted, target_wheel_sm = get_wheel_and_mesh_names(data)
        equipped_wheel_mat, equipped_wheel_mat_painted, equipped_wheel_sm = get_wheel_and_mesh_names_from_list(equipped_names)
        
        if log_cb:
            if target_body_mat or equipped_body_mat:
                log_cb(t("log_material_mapping", "[info] Material mapping: {target} -> {equipped}").format(target=target_body_mat, equipped=equipped_body_mat))
            if target_chassis_mat or equipped_chassis_mat:
                log_cb(t("log_chassis_mapping", "[info] Chassis mapping: {target} -> {equipped}").format(target=target_chassis_mat, equipped=equipped_chassis_mat))
            if target_wheel_mat or equipped_wheel_mat:
                log_cb(f"[info] Wheel mapping: {target_wheel_mat} -> {equipped_wheel_mat}")
            if target_wheel_mat_painted or equipped_wheel_mat_painted:
                log_cb(f"[info] Wheel painted mapping: {target_wheel_mat_painted} -> {equipped_wheel_mat_painted}")
            if target_wheel_sm or equipped_wheel_sm:
                log_cb(f"[info] Wheel mesh mapping: {target_wheel_sm} -> {equipped_wheel_sm}")
        
        # Main swap to the original item's identity with dynamic material/wheel mapping and exact casing resolution
        patched = patch_names(
            data,
            target_name,
            orig_name,
            target_body_mat=target_body_mat,
            target_chassis_mat=target_chassis_mat,
            equipped_body_mat=equipped_body_mat,
            equipped_chassis_mat=equipped_chassis_mat,
            target_wheel_mat=target_wheel_mat,
            target_wheel_mat_painted=target_wheel_mat_painted,
            target_wheel_sm=target_wheel_sm,
            equipped_wheel_mat=equipped_wheel_mat,
            equipped_wheel_mat_painted=equipped_wheel_mat_painted,
            equipped_wheel_sm=equipped_wheel_sm,
            equipped_names=equipped_names
        )
        
        # Apply custom RGB Color if requested
        if rgb_color is not None or rgb_color_flame is not None:
            if log_cb:
                log_cb(t("log_applying_rgb", "🎨 Applying custom RGB paint..."))
            from core.upk import patch_upk_colors
            
            r, g, b = None, None, None
            if rgb_color is not None:
                r, g, b = rgb_color
                r, g, b = r * rgb_intensity, g * rgb_intensity, b * rgb_intensity
                
            rf, gf, bf = None, None, None
            if rgb_color_flame is not None:
                rf, gf, bf = rgb_color_flame
                
            patched = patch_upk_colors(
                patched,
                r=r, g=g, b=b, a=1.0 if r is not None else None,
                rf=rf,
                gf=gf,
                bf=bf,
                af=1.0 if rf is not None else None,
                item_name=target_name,
                is_boost=is_boost
            )
                
        # Otimização de E/S binária: gravando via buffer BytesIO em memória
        out_mem = io.BytesIO(patched)
        with open(patched_path, "wb") as f:
            f.write(out_mem.getbuffer())

        if log_cb:
            log_cb(t("log_recrypting", "[3/4] Re-encrypting..."))
        encrypt_upk(str(patched_path), orig_aes, str(reenc_path))

        if log_cb:
            log_cb(t("log_saving_to", "[4/4] Saving to {name}...").format(name=orig_file.name))
        shutil.copy2(reenc_path, orig_file)


def swap(
    orig: dict,
    target: dict,
    pkg_dir: str,
    log_cb=None,
    rgb_color: tuple[float, float, float] | None = None,
    rgb_color_flame: tuple[float, float, float] | None = None,
    rgb_intensity: float = 1.0
) -> None:
    """
    Swap target package to look like orig (locally, client-side only).
    """
    orig_name   = orig["Name"].strip()
    target_name = target["Name"].strip()
    orig_package = orig.get("Package", "").strip() or orig_name
    target_package = target.get("Package", "").strip() or target_name
    orig_aes    = orig.get("AES", "").strip() or None
    target_aes  = target.get("AES", "").strip() or None

    target_slot = target.get("Slot", "").strip().lower()
    is_body = target_slot == "body"
    is_boost = target_slot == "rocket boost"
    is_wheels = target_slot == "wheels"
    is_paintable = is_body or is_boost or is_wheels

    # Chassis de carros (Body), Rocket Boosts e Rodas (Wheels) suportam injeção de cor estável
    if not is_paintable:
        if rgb_color is not None or rgb_color_flame is not None:
            if log_cb:
                log_cb(t("log_paint_ignored", "[info] Paint ignored: only bodies, rocket boosts and wheels support custom color injection."))
        rgb_color = None
        rgb_color_flame = None

    # Autodetect paint color if target item label has a paint suffix and no rgb_color is provided
    if rgb_color is None and target.get("Label") and is_paintable:
        color_name = get_item_color(target["Label"])
        if color_name and color_name in RL_PAINT_COLORS:
            fallback_hex = RL_PAINT_COLORS[color_name]
            h = fallback_hex.lstrip("#")
            rgb_color = (int(h[0:2], 16) / 255.0,
                         int(h[2:4], 16) / 255.0,
                         int(h[4:6], 16) / 255.0)
            if log_cb:
                log_cb(f"[info] Autodetected paint color '{color_name}' from target label, applying RGB: {rgb_color}")

    if rgb_color_flame is None and rgb_color is not None:
        rgb_color_flame = rgb_color

    if orig_name == "WHEEL_Star" or target_name == "WHEEL_Star":
        raise ValueError(t("oem_disabled_msg"))

    if orig_name == "Body_Spark" or target_name == "Body_Spark":
        raise ValueError(t("gizmo_disabled_msg"))

    if "cannonboy" in orig_name.lower() or "cannonboy" in target_name.lower():
        raise ValueError(t("triton_disabled_msg"))

    if orig_name == target_name and rgb_color is None:
        raise ValueError("Item original e alvo são o mesmo (escolha uma cor para pintar).")

    # Determina se o item equipado é pintado
    equipped_is_painted = get_item_color(orig.get("Label", "")) is not None

    # 1. Swap main UPK
    if log_cb:
        log_cb(t("log_starting_swap", "🔄 Starting main package swap..."))
    _execute_single_upk_swap(
        orig_name=orig_name,
        target_name=target_name,
        orig_package=orig_package,
        target_package=target_package,
        orig_aes=orig_aes,
        target_aes=target_aes,
        pkg_dir=pkg_dir,
        log_cb=log_cb,
        rgb_color=rgb_color,
        rgb_color_flame=rgb_color_flame,
        rgb_intensity=rgb_intensity,
        is_boost=(target.get("Slot") == "Rocket Boost"),
        equipped_is_painted=equipped_is_painted
    )

    # 2. Swap texture UPK (_T_SF.upk) if they exist
    orig_tex_file = Path(pkg_dir) / f"{orig_package}_T_SF.upk"
    target_tex_file = Path(pkg_dir) / f"{target_package}_T_SF.upk"
    
    backup_dir = get_backup_dir(pkg_dir)
    target_tex_backup = backup_dir / f"{target_package}_T_SF.upk"

    if orig_tex_file.exists() and (target_tex_file.exists() or target_tex_backup.exists()):
        if log_cb:
            log_cb(t("log_textures_detected", "🎨 Texture packages detected! Performing texture swap..."))
        _execute_single_upk_swap(
            orig_name=orig_name,
            target_name=target_name,
            orig_package=f"{orig_package}_T",
            target_package=f"{target_package}_T",
            orig_aes=orig_aes,
            target_aes=target_aes,
            pkg_dir=pkg_dir,
            log_cb=log_cb,
            rgb_color=None,  # Texture package does not require coloring
            rgb_color_flame=None,
            rgb_intensity=1.0,
            is_boost=(target.get("Slot") == "Rocket Boost"),
            equipped_is_painted=equipped_is_painted
        )

    if log_cb:
        log_cb(t("log_swap_completed", "[OK] Swap completed! {orig} now looks like {target}.").format(orig=orig_name, target=target_name))


# ─────────────────────────────────────────────────────────────────────────────
# QoL Premium Enhancements: Base64 Preset Sharing & Auto-Folder Finder
# ─────────────────────────────────────────────────────────────────────────────

def encode_combo_code(swaps: list) -> str:
    """
    Encode a list of swaps into a zlib compressed and Base64 URL-safe string.
    Keys are shortened ('o'=orig_name, 't'=target_name, 's'=slot) to minimize length.
    """
    import zlib
    import base64
    import json
    
    cleaned = []
    for s in swaps:
        entry = {
            "o": s.get("orig_name"),
            "t": s.get("target_name"),
            "s": s.get("slot")
        }
        if s.get("hex_color"):
            entry["c"] = s.get("hex_color")
        if s.get("intensity") is not None and s.get("intensity") != 1.0:
            entry["i"] = s.get("intensity")
        if s.get("hex_color_flame"):
            entry["cf"] = s.get("hex_color_flame")
        if s.get("magnet") is not None:
            entry["m"] = 1 if s.get("magnet") else 0
        cleaned.append(entry)
    json_bytes = json.dumps(cleaned).encode("utf-8")
    compressed = zlib.compress(json_bytes)
    return base64.urlsafe_b64encode(compressed).decode("utf-8")


def decode_combo_code(code: str) -> list | None:
    """
    Decode a zlib-compressed Base64 URL-safe string back into a list of swaps.
    """
    import zlib
    import base64
    import json
    
    try:
        decoded_b64 = base64.urlsafe_b64decode(code.strip().encode("utf-8"))
        decompressed = zlib.decompress(decoded_b64)
        data = json.loads(decompressed.decode("utf-8"))
        if not isinstance(data, list):
            return None
        
        swaps = []
        for item in data:
            if not isinstance(item, dict) or "o" not in item or "t" not in item:
                return None
            swaps.append({
                "orig_name": item["o"],
                "target_name": item["t"],
                "slot": item.get("s", "?"),
                "hex_color": item.get("c"),
                "intensity": item.get("i", 1.0),
                "hex_color_flame": item.get("cf"),
                "magnet": item.get("m", 1) == 1
            })
        return swaps
    except Exception:
        return None


def autodetect_rl_path(platform: str) -> str | None:
    """
    Autodetect Rocket League's CookedPCConsole installation folder for Steam or Epic Games.
    Uses public Windows registries and game client JSON manifests.
    """
    if os.name != 'nt':
        return None
        
    import winreg
    
    try:
        if platform == "steam":
            # 1. Search Steam Registry for SteamPath
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                steam_path_str = winreg.QueryValueEx(key, "SteamPath")[0]
            if steam_path_str:
                steam_path = Path(steam_path_str.replace("/", "\\"))
                
                # Check default library location:
                default_rl = steam_path / "steamapps" / "common" / "rocketleague" / "TAGame" / "CookedPCConsole"
                if default_rl.exists():
                    return str(default_rl)
                
                # Scan Steam libraryfolders.vdf for custom libraries
                lib_vdf = steam_path / "steamapps" / "libraryfolders.vdf"
                if lib_vdf.exists():
                    import re
                    with open(lib_vdf, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    # Find all library directory paths
                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for p in paths:
                        p_cleaned = Path(p.replace("\\\\", "\\"))
                        rl_path = p_cleaned / "steamapps" / "common" / "rocketleague" / "TAGame" / "CookedPCConsole"
                        if rl_path.exists():
                            return str(rl_path)
                            
        elif platform == "epic":
            # 2. Epic Games stores installation manifests under %ProgramData%\Epic\EpicGamesLauncher\Data\Manifests
            program_data = os.environ.get("ProgramData")
            if program_data:
                manifest_dir = Path(program_data) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
                if manifest_dir.exists():
                    for manifest_file in manifest_dir.glob("*.item"):
                        try:
                            with open(manifest_file, "r", encoding="utf-8", errors="ignore") as f:
                                data = json.load(f)
                            
                            # Rocket League AppName is commonly "RocketLeague"
                            if data.get("AppName") == "RocketLeague" or "rocketleague" in data.get("MandatoryAppFolderName", "").lower():
                                install_loc = data.get("InstallLocation")
                                if install_loc:
                                    rl_path = Path(install_loc) / "TAGame" / "CookedPCConsole"
                                    if rl_path.exists():
                                        return str(rl_path)
                        except Exception:
                            pass
                            
            # Fallback Epic games common directories
            epic_default = Path("C:\\Program Files\\Epic Games\\rocketleague\\TAGame\\CookedPCConsole")
            if epic_default.exists():
                return str(epic_default)
                
    except Exception:
        # Silently absorb registry read issues
        pass
        
    return None


