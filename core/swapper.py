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
from .upk import decrypt_upk, encrypt_upk, patch_names

PRODUCTS_URL = "https://raw.githubusercontent.com/ShinyEmii/Toga-Files/refs/heads/master/products.csv"
from core.utils import get_base_dir, get_data_dir

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
    """Filter products by search query and/or slot type."""
    result = products
    if slot and slot != "Todos":
        result = [p for p in result if p.get("Slot", "").strip().lower() == slot.lower()]
    if query:
        q = query.strip().lower()
        result = [p for p in result if q in p.get("Label", "").lower() or q in p.get("Name", "").lower()]
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
PAINT_INTERNAL_NAMES: dict[str, str] = {
    "Titanium White": "TW",
    "Black":          "Black",
    "Crimson":        "Crimson",
    "Cobalt":         "Cobalt",
    "Sky Blue":       "SkyBlue",
    "Burnt Sienna":   "BurntSienna",
    "Saffron":        "Saffron",
    "Lime":           "Lime",
    "Forest Green":   "ForestGreen",
    "Orange":         "Orange",
    "Purple":         "Purple",
    "Pink":           "Pink",
    "Gray":           "Grey",
    "Grey":           "Grey",
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
    backup = cfg.get("backup_dir", "")
    if backup:
        return Path(backup)
    return Path(pkg_dir).parent / "_RL_Forge_Backups"

def list_backups(pkg_dir: str) -> list[dict]:
    """Return list of active swaps (files that have a backup)."""
    backup_dir = get_backup_dir(pkg_dir)
    if not backup_dir.exists():
        return []
    result = []
    for upk in backup_dir.glob("*_SF.upk"):
        result.append({
            "name":       upk.stem.replace("_SF", ""),
            "file":       upk.name,
            "backup_path": str(upk),
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
        log_cb(f"✅ Restaurado: {item_name}")

def restore_all(pkg_dir: str, log_cb=None) -> None:
    """Restore all backed-up items."""
    backups = list_backups(pkg_dir)
    if not backups:
        if log_cb: log_cb("ℹ️ Nenhum backup encontrado.")
        return
    for b in backups:
        restore_item(b["name"], pkg_dir, log_cb)


# ─────────────────────────────────────────────────────────────────────────────
# Core swap
# ─────────────────────────────────────────────────────────────────────────────

def swap(
    orig: dict,
    target: dict,
    pkg_dir: str,
    log_cb=None,
    target_color: str = "Unpainted"
) -> None:
    """
    Swap target package to look like orig (locally, client-side only).

    orig   = item you have equipped (its file will be overwritten)
    target = item whose visuals you want to see (its file is the source)

    Steps:
      1. Backup orig_SF.upk
      2. Read target_SF.upk
      3. Decrypt with target's AES key
      4. Patch name table: target_name → orig_name (and _SF variant)
      5. Re-encrypt with orig's AES key
      6. Write over orig_SF.upk
    """
    orig_name   = orig["Name"].strip()
    target_name = target["Name"].strip()
    orig_aes    = orig.get("AES", "").strip() or None
    target_aes  = target.get("AES", "").strip() or None

    if orig_name == target_name and (not target_color or target_color == "Unpainted"):
        raise ValueError("Item original e alvo são o mesmo e nenhuma pintura foi selecionada.")

    pkg_path     = Path(pkg_dir)
    target_file  = pkg_path / f"{target_name}_SF.upk"
    orig_file    = pkg_path / f"{orig_name}_SF.upk"
    backup_dir   = get_backup_dir(pkg_dir)

    if not target_file.exists():
        raise FileNotFoundError(f"Arquivo do item alvo não encontrado:\n{target_file}")
    if not orig_file.exists():
        raise FileNotFoundError(f"Arquivo do item original não encontrado:\n{orig_file}")

    # ── Step 1: Backup ──────────────────────────────────────────────────────
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{orig_name}_SF.upk"
    if not backup_path.exists():
        shutil.copy2(orig_file, backup_path)
        if log_cb: log_cb(f"[backup] Original salvo: {backup_path.name}")
    else:
        if log_cb: log_cb(f"[info] Usando backup original já existente.")

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # RLUPKTool requires the file to be named *_decrypted.upk to re-encrypt
        decrypted_path = tmp / f"{target_name}_SF_decrypted.upk"
        patched_path   = tmp / f"{orig_name}_SF_decrypted.upk"   # must end in _decrypted.upk!
        reenc_path     = tmp / f"{orig_name}_SF.upk"

        if log_cb: 
            msg = f"[1/4] Descriptografando {target_file.name}"
            if target_color and target_color != "Unpainted":
                msg += f" (Pintura: {target_color})"
            log_cb(f"{msg}...")
        decrypt_upk(str(target_file), target_aes, str(decrypted_path))

        if log_cb: log_cb(f"[2/4] Alterando name table: {target_name} -> {orig_name}...")
        with open(decrypted_path, "rb") as f:
            data = f.read()
        
        # ── Magic Paint Injection ──
        # If a color is selected, we try to patch the name table to 'force' the paint
        if target_color and target_color != "Unpainted":
            suffix = PAINT_INTERNAL_NAMES.get(target_color)
            if suffix:
                if log_cb: log_cb(f"🎨 Aplicando técnica de pintura: {target_color} ({suffix})")
                # Common patterns for painted items in name table
                # 1. {Name}_Painted_{Suffix}
                # 2. {Name}_{Suffix}
                # We replace the base name with the painted version BEFORE swapping it to the original name
                data = patch_names(data, target_name, f"{target_name}_Painted_{suffix}")
                data = patch_names(data, f"{target_name}_SF", f"{target_name}_Painted_{suffix}_SF")

        # Now do the main swap to the original item's identity
        data = patch_names(data, target_name, orig_name)
        # Also patch with the paint suffix in case it was already there or we just added it
        if target_color and target_color != "Unpainted":
            suffix = PAINT_INTERNAL_NAMES.get(target_color)
            data = patch_names(data, f"{target_name}_Painted_{suffix}", orig_name)

        with open(patched_path, "wb") as f:
            f.write(data)

        if log_cb: log_cb(f"[3/4] Re-criptografando...")
        encrypt_upk(str(patched_path), orig_aes, str(reenc_path))

        if log_cb: log_cb(f"[4/4] Salvando em {orig_file.name}...")
        shutil.copy2(reenc_path, orig_file)


    if log_cb: log_cb(f"[OK] Swap concluido! {orig_name} agora parece {target_name}.")

