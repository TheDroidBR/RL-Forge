"""
UPK Engine — decrypt/encrypt via RLUPKTool.exe + pure-Python name table patching.

Decrypt/encrypt delegate to the proven RLUPKTool.exe (from Pengu1ns/RocketLeagueSwapper).
Name table patching is pure Python, ported from the same project's swapper.py.
"""

import struct
import subprocess
import tempfile
import shutil
import os
import base64
from pathlib import Path
from core.utils import get_base_dir

# Path to RLUPKTool.exe, sitting next to this package's parent
_TOOL_EXE = get_base_dir() / "RLUPKTool.exe"

UPK_MAGIC = 0x9E2A83C1


# ─────────────────────────────────────────────────────────────────────────────
# AES key resolver
# ─────────────────────────────────────────────────────────────────────────────

def resolve_aes_key_arg(aes_str: str | None) -> list[str]:
    """
    Return the -k <key_hex> argument list for RLUPKTool.exe.
    Toga-Files CSV uses Base64; RLUPKTool expects hex. Converts automatically.
    Returns [] if no key (uses tool's default).
    """
    if not aes_str or not aes_str.strip():
        return []
    s = aes_str.strip()
    # Already hex (64 chars)
    if len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s):
        return ["-k", s]
    # Hex with 0x prefix
    if s.startswith(("0x", "0X")):
        return ["-k", s[2:]]
    # Base64 (Toga-Files format) → convert to hex
    try:
        raw = base64.b64decode(s)
        if len(raw) in (16, 24, 32):
            return ["-k", raw.hex()]
    except Exception:
        pass
    return []


# ─────────────────────────────────────────────────────────────────────────────
# RLUPKTool wrappers
# ─────────────────────────────────────────────────────────────────────────────

def _run_tool(args: list[str]) -> None:
    """Run RLUPKTool.exe with given args. Raises RuntimeError on failure."""
    if not _TOOL_EXE.exists():
        raise FileNotFoundError(f"RLUPKTool.exe nao encontrado em: {_TOOL_EXE}")
    cmd = [str(_TOOL_EXE)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"RLUPKTool falhou (code {result.returncode}): {result.stderr.strip()}")


def decrypt_upk(src_path: str, aes_str: str | None, out_path: str) -> None:
    """
    Decrypt src_path -> out_path using RLUPKTool.exe.
    RLUPKTool writes <name>_decrypted.upk next to the source file,
    so we copy source to a temp dir and collect from there.
    """
    src = Path(src_path)
    out = Path(out_path)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir  = Path(tmp)
        work     = tmp_dir / src.name
        shutil.copy2(src, work)

        # RLUPKTool does NOT need -k; the default key covers all RL items
        result = subprocess.run([str(_TOOL_EXE), str(work)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"RLUPKTool decrypt falhou: {result.stderr.strip() or result.stdout.strip()}")

        decrypted = tmp_dir / (work.stem + "_decrypted.upk")
        if not decrypted.exists():
            raise FileNotFoundError(f"RLUPKTool nao gerou o decrypted: {decrypted}")

        shutil.copy2(decrypted, out)


def encrypt_upk(src_path: str, aes_str: str | None, out_path: str) -> None:
    """
    Re-encrypt a decrypted .upk -> out_path using RLUPKTool.exe.
    RLUPKTool detects that input ends with _decrypted.upk and re-encrypts.
    Output will be <stem_without_decrypted>_reencrypted.upk next to source.
    """
    src = Path(src_path)
    out = Path(out_path)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        work    = tmp_dir / src.name
        shutil.copy2(src, work)

        result = subprocess.run([str(_TOOL_EXE), str(work)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"RLUPKTool encrypt falhou: {result.stderr.strip() or result.stdout.strip()}")

        # Find the reencrypted output
        candidates = list(tmp_dir.glob("*_reencrypted.upk"))
        if not candidates:
            raise FileNotFoundError(f"RLUPKTool nao gerou _reencrypted.upk em {tmp_dir}")
        shutil.copy2(candidates[0], out)



# ─────────────────────────────────────────────────────────────────────────────
# Struct helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def _read_i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]

def _read_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]

def _write_i32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<i", data, offset, value)


# ─────────────────────────────────────────────────────────────────────────────
# UE3 FString parser
# ─────────────────────────────────────────────────────────────────────────────

def _parse_fstring(data: bytes, offset: int) -> tuple[str, int]:
    length = _read_i32(data, offset)
    offset += 4
    if length <= 0:
        return ("", offset)
    raw = data[offset: offset + length]
    if (length >= 2 and length % 2 == 0
            and all(raw[i] == 0 for i in range(1, length, 2))):
        s = raw.decode("utf-16-le", errors="replace").rstrip("\x00")
    else:
        s = raw.decode("latin-1", errors="replace").rstrip("\x00")
    return (s, offset + length)


# ─────────────────────────────────────────────────────────────────────────────
# Full header parser
# ─────────────────────────────────────────────────────────────────────────────

def _parse_full_header(data: bytes) -> dict:
    pos = 0
    pos += 4  # Tag
    pos += 2  # FileVersion
    licensee_version = _read_u16(data, pos); pos += 2

    total_header_size_off = pos; pos += 4

    folder_len = _read_i32(data, pos); pos += 4
    if folder_len > 0:    pos += folder_len
    elif folder_len < 0:  pos += -folder_len * 2

    pos += 4  # PackageFlags
    name_count_off = pos; pos += 4
    name_offset_off = pos; pos += 4
    pos += 4  # ExportCount
    export_offset_off = pos; pos += 4
    pos += 4  # ImportCount
    import_offset_off = pos; pos += 4
    depends_offset_off = pos; pos += 4

    pos += 4 * 4  # Unknown1-4
    pos += 16     # FGuid

    gen_count = _read_i32(data, pos); pos += 4
    pos += gen_count * 12

    pos += 4  # EngineVersion
    pos += 4  # CookerVersion
    pos += 4  # CompressionFlags

    chunk_count = _read_i32(data, pos); pos += 4
    chunk_entry_size = 24 if licensee_version >= 22 else 16
    pos += chunk_count * chunk_entry_size

    pos += 4  # Unknown5

    str_count = _read_i32(data, pos); pos += 4
    for _ in range(str_count):
        slen = _read_i32(data, pos); pos += 4
        if slen > 0:    pos += slen
        elif slen < 0:  pos += -slen * 2

    unk_count = _read_i32(data, pos); pos += 4
    for _ in range(unk_count):
        pos += 5 * 4
        arr_len = _read_i32(data, pos); pos += 4
        pos += arr_len * 4

    garbage_size_off    = pos; pos += 4
    chunk_info_off_off  = pos; pos += 4
    last_block_size_off = pos; pos += 4

    name_offset   = _read_i32(data, name_offset_off)
    export_offset = _read_i32(data, export_offset_off)
    import_offset = _read_i32(data, import_offset_off)

    return {
        "total_header_size_off": total_header_size_off,
        "name_count_off":        name_count_off,
        "name_offset_off":       name_offset_off,
        "export_offset_off":     export_offset_off,
        "import_offset_off":     import_offset_off,
        "depends_offset_off":    depends_offset_off,
        "chunk_info_off_off":    chunk_info_off_off,
        "name_table_start":      name_offset,
        "name_count":            _read_i32(data, name_count_off),
        "export_offset":         export_offset,
        "import_offset":         import_offset,
    }


def _detect_flags_size(data: bytes, hdr: dict) -> int:
    targets  = {hdr["import_offset"], hdr["export_offset"]}
    file_len = len(data)
    for flags_size in (8, 4):
        cursor = hdr["name_table_start"]
        ok = True
        for _ in range(hdr["name_count"]):
            if cursor + 4 > file_len:
                ok = False; break
            length = _read_i32(data, cursor)
            if length <= 0 or length > 1024:
                ok = False; break
            cursor = cursor + 4 + length + flags_size
            if cursor > file_len:
                ok = False; break
        if ok and cursor in targets:
            return flags_size
    raise ValueError("Nao foi possivel determinar o tamanho dos flags da name table.")


# ─────────────────────────────────────────────────────────────────────────────
# Name table patching (pure Python)
# ─────────────────────────────────────────────────────────────────────────────

def patch_upk_names(data: bytes, find: str, replace: str) -> bytes:
    """Patch a single name entry and update all affected header offsets."""
    ba = bytearray(data)

    if _read_u32(ba, 0) != UPK_MAGIC:
        raise ValueError("Arquivo UPK invalido (magic errado). Arquivo deve estar decriptado.")

    hdr        = _parse_full_header(ba)
    flags_size = _detect_flags_size(ba, hdr)

    cursor        = hdr["name_table_start"]
    entry_start   = None
    old_entry_end = None
    found         = False

    for _ in range(hdr["name_count"]):
        entry_start       = cursor
        name_str, after_s = _parse_fstring(ba, cursor)
        entry_end         = after_s + flags_size
        if name_str.lower() == find.lower():
            old_entry_end = entry_end
            found = True
            break
        cursor = entry_end

    if not found:
        return data

    old_fstring_len = _read_i32(ba, entry_start)
    old_fstring_end = entry_start + 4 + old_fstring_len
    old_flags       = bytes(ba[old_fstring_end:old_entry_end])

    old_str_bytes = find.encode("latin-1")
    null_count    = old_fstring_len - len(old_str_bytes)
    if null_count < 1:
        null_count = 1
    new_str_bytes = replace.encode("latin-1") + b"\x00" * null_count
    new_fstring   = struct.pack("<i", len(new_str_bytes)) + new_str_bytes
    new_entry     = new_fstring + old_flags

    delta = len(new_entry) - (old_entry_end - entry_start)
    ba[entry_start:old_entry_end] = new_entry

    if delta == 0:
        return bytes(ba)

    def shift_abs(field_off: int) -> None:
        val = _read_i32(ba, field_off)
        if val >= old_entry_end:
            _write_i32(ba, field_off, val + delta)

    shift_abs(hdr["total_header_size_off"])
    shift_abs(hdr["export_offset_off"])
    shift_abs(hdr["import_offset_off"])
    shift_abs(hdr["depends_offset_off"])

    name_offset    = _read_i32(ba, hdr["name_offset_off"])
    chunk_info_rel = _read_i32(ba, hdr["chunk_info_off_off"])
    chunk_info_abs = name_offset + chunk_info_rel
    if chunk_info_abs >= old_entry_end:
        _write_i32(ba, hdr["chunk_info_off_off"], chunk_info_rel + delta)

    return bytes(ba)


def patch_names(data: bytes, find: str, replace: str) -> bytes:
    """Patch `find` -> `replace` and `find_SF` -> `replace_SF` in the name table."""
    data = patch_upk_names(data, find, replace)
    data = patch_upk_names(data, find + "_SF", replace + "_SF")
    return data
