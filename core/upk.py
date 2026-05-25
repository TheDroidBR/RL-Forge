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

# Oculte totalmente as janelas pretas piscando no Windows ao chamar subprocessos
_SUBPROCESS_KWARGS = {}
if os.name == 'nt':
    _SUBPROCESS_KWARGS['creationflags'] = 0x08000000  # CREATE_NO_WINDOW

def _run_tool(args: list[str]) -> None:
    """Run RLUPKTool.exe with given args. Raises RuntimeError on failure."""
    if not _TOOL_EXE.exists():
        raise FileNotFoundError(f"RLUPKTool.exe nao encontrado em: {_TOOL_EXE}")
    cmd = [str(_TOOL_EXE)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, **_SUBPROCESS_KWARGS)
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
                                capture_output=True, text=True, **_SUBPROCESS_KWARGS)
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
                                capture_output=True, text=True, **_SUBPROCESS_KWARGS)
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
    licensee_version = _read_u16(data, pos)
    pos += 2

    total_header_size_off = pos
    pos += 4

    folder_len = _read_i32(data, pos)
    pos += 4
    if folder_len > 0:
        pos += folder_len
    elif folder_len < 0:
        pos += -folder_len * 2

    pos += 4  # PackageFlags
    name_count_off = pos
    pos += 4
    name_offset_off = pos
    pos += 4
    pos += 4  # ExportCount
    export_offset_off = pos
    pos += 4
    pos += 4  # ImportCount
    import_offset_off = pos
    pos += 4
    depends_offset_off = pos
    pos += 4

    pos += 4 * 4  # Unknown1-4
    pos += 16     # FGuid

    gen_count = _read_i32(data, pos)
    pos += 4
    pos += gen_count * 12

    pos += 4  # EngineVersion
    pos += 4  # CookerVersion
    pos += 4  # CompressionFlags

    chunk_count = _read_i32(data, pos)
    pos += 4
    chunk_entry_size = 24 if licensee_version >= 22 else 16
    pos += chunk_count * chunk_entry_size

    pos += 4  # Unknown5

    str_count = _read_i32(data, pos)
    pos += 4
    for _ in range(str_count):
        slen = _read_i32(data, pos)
        pos += 4
        if slen > 0:
            pos += slen
        elif slen < 0:
            pos += -slen * 2

    unk_count = _read_i32(data, pos)
    pos += 4
    for _ in range(unk_count):
        pos += 5 * 4
        arr_len = _read_i32(data, pos)
        pos += 4
        pos += arr_len * 4

    pos += 4  # garbage_size_off (unused)
    chunk_info_off_off  = pos
    pos += 4
    pos += 4  # last_block_size_off (unused)

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
                ok = False
                break
            length = _read_i32(data, cursor)
            # Handle Unicode (negative length)
            abs_len = length if length > 0 else -length * 2
            if abs_len == 0 or abs_len > 2048:
                ok = False
                break
            cursor = cursor + 4 + abs_len + flags_size
            if cursor > file_len:
                ok = False
                break
        # Some UPKs might have padding after the name table, so we check if we've reached
        # at least one of the following tables.
        if ok and cursor <= max(targets):
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
    is_unicode      = old_fstring_len < 0
    actual_len      = -old_fstring_len * 2 if is_unicode else old_fstring_len
    old_fstring_end = entry_start + 4 + actual_len
    old_flags       = bytes(ba[old_fstring_end:old_entry_end])

    # 1. Encode replacement in the same format as original
    if is_unicode:
        new_bytes = replace.encode("utf-16-le") + b"\x00\x00"
        old_data_len = actual_len
    else:
        new_bytes = replace.encode("latin-1") + b"\x00"
        old_data_len = actual_len

    # 2. Optimization: Null-pad if shorter or equal to maintain structure
    if len(new_bytes) <= old_data_len:
        padding = b"\x00" * (old_data_len - len(new_bytes))
        new_entry = struct.pack("<i", old_fstring_len) + new_bytes + padding + old_flags
        ba[entry_start:old_entry_end] = new_entry
        return bytes(ba)

    # 3. If longer, we must shift (standard UE3 expansion)
    new_fstring = struct.pack("<i", -(len(new_bytes)//2) if is_unicode else len(new_bytes)) + new_bytes
    new_entry   = new_fstring + old_flags
    delta       = len(new_entry) - (old_entry_end - entry_start)
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

    # Shift Export Table serial offsets to ensure binary alignments of serialized data (models, assets) match
    new_export_offset = _read_i32(ba, hdr["export_offset_off"])
    export_count = _read_i32(ba, hdr["export_offset_off"] - 4)
    for i in range(export_count):
        off = new_export_offset + i * 72
        if off + 72 > len(ba):
            break
        serial_offset = _read_i32(ba, off + 36)
        if serial_offset >= old_entry_end:
            _write_i32(ba, off + 36, serial_offset + delta)

    return bytes(ba)


def _get_name_indices(data: bytes) -> tuple[dict[str, int], list[str]]:
    """Returns a map of {name_lower: index} and a list of all names."""
    if _read_u32(data, 0) != UPK_MAGIC:
        raise ValueError("Arquivo UPK invalido.")
    hdr = _parse_full_header(data)
    flags_size = _detect_flags_size(data, hdr)
    cursor = hdr["name_table_start"]
    
    name_map = {}
    names = []
    for i in range(hdr["name_count"]):
        name_str, after_s = _parse_fstring(data, cursor)
        name_map[name_str.lower()] = i
        names.append(name_str)
        cursor = after_s + flags_size
        
    return name_map, names


def patch_upk_colors(
    data: bytes,
    r: float = None, g: float = None, b: float = None, a: float = None,
    rf: float = None, gf: float = None, bf: float = None, af: float = None,
    item_name: str = "",
    is_boost: bool = False
) -> bytes:
    """
    Intelligently search and replace color properties in UPK data.
    Uses heuristics to distinguish between Colors and Physics (Size/Velocity).
    """
    ba = bytearray(data)
    name_map, names = _get_name_indices(ba)
    
    lc_idx = name_map.get("linearcolor")
    vec_idx = name_map.get("vector")
    sp_idx = name_map.get("structproperty")
    pv_idx = name_map.get("parametervalue")
    v_idx = name_map.get("value")
    
    if sp_idx is None:
        return data

    import struct
    
    # Restrict patching only to MaterialInstanceConstant or Particle System exports to prevent global shader corruption
    mic_ranges = []
    try:
        hdr = _parse_full_header(ba)
        export_offset = hdr["export_offset"]
        export_count = _read_i32(ba, hdr["export_offset_off"] - 4)
        
        import_offset = hdr["import_offset"]
        import_count = _read_i32(ba, hdr["import_offset_off"] - 4)
        
        imports = []
        for i in range(import_count):
            off = import_offset + i * 28
            vals = [struct.unpack_from("<i", ba, off+o)[0] for o in range(0, 28, 4)]
            obj_name = names[vals[5]] if 0 <= vals[5] < len(names) else f"Idx_{vals[5]}"
            imports.append(obj_name)
            
        # We also allow particle modules and distribution classes for boosts/trails to enable paint colors
        allowed_classes = {
            "MaterialInstanceConstant",
            "MaterialInstanceConstantReal",
            "MaterialInstanceConstantReal_TA",
            "MaterialInstanceConstant_TA"
        }
        effective_is_boost = is_boost or "boost" in item_name.lower() or "alphareward" in item_name.lower() or "trail" in item_name.lower() or "goal" in item_name.lower()
        effective_is_body = "body" in item_name.lower() or "chassis" in item_name.lower()
        effective_is_wheels = "wheel" in item_name.lower() or "rim" in item_name.lower()
        if effective_is_boost:
            allowed_classes.update({
                "ParticleModuleColor",
                "ParticleModuleColorOverLife",
                "ParticleModuleColorScaleOverLife",
                "ParticleModuleParameterDynamic",
                "ParticleSpriteEmitter",
                "ParticleSystem",
                "ParticleSystemComponent",
                "DistributionVectorParticleParameter",
                "DistributionFloatParticleParameter",
                "FXActor_Boost_TA",
                "FXTrait_BoostParticle_TA"
            })
            
        for i in range(export_count):
            off = export_offset + i * 72
            if off + 72 > len(ba):
                break
            class_idx = struct.unpack_from("<i", ba, off)[0]
            serial_size = struct.unpack_from("<i", ba, off + 32)[0]
            serial_offset = struct.unpack_from("<i", ba, off + 36)[0]
            
            class_name = "Class"
            if class_idx < 0:
                class_name = imports[-class_idx - 1]
            
            if class_name in allowed_classes:
                mic_ranges.append((serial_offset, serial_offset + serial_size))
                
        if effective_is_boost or effective_is_body or effective_is_wheels:
            mic_ranges = None
    except Exception:
        mic_ranges = None
    
    # Names that are ALWAYS colors
    hard_color_names = {
        "carboostglowcolor", "sourcecolor", "colorparams", 
        "startcolor", "color", "diffusecolor", "specularcolor", "emissivecolor",
        "tint", "rimcolor", "paintcolor", "primarycolor", "secondarycolor",
        # Car & Item Paint / Accent Parameters
        "customcolor", "customcolors", "trimcolor", "tirecolor", "teamcolor",
        "lightcolor", "headlightcolor", "taillightcolor", "boostglowcolor",
        "fresnelcolor", "bodycolor", "chassiscolor", "rimrgb", "trimpaintable",
        # Flame and Combustion parameters
        "inner_color", "outer_color",
        # Additional Wheel Paint & Material properties for high coverage
        "accentcolor", "hubcolor", "spokecolor", "wheelcolor", "glowcolor",
        "vfxcolor", "metalcolor", "overlaycolor", "underglowcolor", "tire_color", "rim_color"
    }
    
    # Names that are AMBIGUOUS (could be color or size/velocity)
    ambiguous_names = {"constant", "vector", "value"}
    
    # Cache indices for speed
    hard_indices = {name_map[n] for n in hard_color_names if n in name_map}
    ambig_indices = {name_map[n] for n in ambiguous_names if n in name_map}
    
    idx = 0
    sp_search = struct.pack("<I", sp_idx) + b'\x00\x00\x00\x00'
    
    while True:
        idx = ba.find(sp_search, idx)
        if idx == -1:
            break
            
        if idx >= 8 and len(ba) >= idx + 24:
            size = struct.unpack("<I", ba[idx+8:idx+12])[0]
            struct_type_idx = struct.unpack("<I", ba[idx+16:idx+20])[0]
            name_idx = struct.unpack("<I", ba[idx-8:idx-4])[0]
            
            should_patch = False
            is_linear = (struct_type_idx == lc_idx and size >= 16)
            is_vector = (struct_type_idx == vec_idx and size >= 12)
            
            if is_linear or is_vector:
                # If the property name is 'ParameterValue' or 'Value' (generic struct fields),
                # resolve its parent parameter name from the preceding NameProperty at idx-16
                resolved_name_idx = name_idx
                if name_idx in (pv_idx, v_idx) and idx >= 16:
                    parent_idx = struct.unpack("<I", ba[idx-16:idx-12])[0]
                    if 0 <= parent_idx < len(names):
                        resolved_name_idx = parent_idx
                
                if resolved_name_idx in hard_indices:
                    should_patch = True
                elif resolved_name_idx in ambig_indices:
                    # HEURISTIC: Is this Vector/Constant actually a color?
                    vals = struct.unpack("<fff", ba[idx+24:idx+36])
                    
                    # 1. Uniformity Check: Size/Scale often uses (1,1,1) or (X,X,X)
                    is_uniform = (vals[0] == vals[1] == vals[2])
                    
                    # 2. Integer Check: Physics values are often round numbers (50.0, 100.0)
                    # Colors usually have fractional parts (0.668...)
                    is_integer = all(v == float(int(v)) for v in vals)
                    
                    # 3. Magnitude Check: Extremely large values are usually velocity/acceleration
                    # (Though some glows are bright, > 5000 is usually not a color)
                    is_extreme = any(abs(v) > 5000 for v in vals)
                    
                    # Heuristic Rule:
                    # - If it matches the Alpha Boost "Orange" signature exactly, it's definitely a color.
                    # - Otherwise, if it's not uniform, not a simple integer, and not extreme, it's very likely a color.
                    
                    is_alpha_boost = "alphareward" in item_name.lower() or "alpha_reward" in item_name.lower()
                    if is_alpha_boost:
                        signatures = [
                            (2.5, 1.0, 0.125),
                            (1.0, 0.11, 0.0),
                            (1.0, 0.6689812541007996, 0.08848005533218384),
                            (4.5, 0.9375, 0.15000000596046448),
                            (1.5, 0.800000011920929, 0.20000000298023224)
                        ]
                        if any(all(abs(vals[i] - sig[i]) < 0.01 for i in range(3)) for sig in signatures):
                            should_patch = True
                        else:
                            should_patch = False
                    else:
                        if not is_uniform and not is_extreme:
                            should_patch = True
                        elif not is_integer and not is_extreme:
                            should_patch = True
 
            if should_patch:
                if mic_ranges is not None and not any(start <= idx < end for start, end in mic_ranges):
                    should_patch = False
 
            if should_patch:
                # Decide color target: main body color vs exhaust flame color
                resolved_name = names[resolved_name_idx].lower() if 0 <= resolved_name_idx < len(names) else ""
                
                is_flame_prop = resolved_name in ("inner_color", "outer_color", "carboostglowcolor", "boostglowcolor", "constant")
                
                if is_flame_prop:
                    if rf is not None:
                        curr_r, curr_g, curr_b = rf, gf, bf
                        curr_a = af if af is not None else 1.0
                        
                        # If black paint is chosen (value <= 0.02), force absolute zero to create solid 100% black soot
                        if curr_r <= 0.02 and curr_g <= 0.02 and curr_b <= 0.02:
                            curr_r, curr_g, curr_b = 0.0, 0.0, 0.0
                            
                        if is_linear:
                            struct.pack_into("<ffff", ba, idx+24, curr_r, curr_g, curr_b, curr_a)
                        else:
                            struct.pack_into("<fff", ba, idx+24, curr_r, curr_g, curr_b)
                else:
                    if r is not None:
                        curr_r, curr_g, curr_b = r, g, b
                        curr_a = a
                        
                        # If black paint is chosen (value <= 0.02), force absolute zero to create solid 100% black soot
                        if curr_r <= 0.02 and curr_g <= 0.02 and curr_b <= 0.02:
                            curr_r, curr_g, curr_b = 0.0, 0.0, 0.0
                            
                        if is_linear:
                            struct.pack_into("<ffff", ba, idx+24, curr_r, curr_g, curr_b, curr_a)
                        else:
                            struct.pack_into("<fff", ba, idx+24, curr_r, curr_g, curr_b)
        
        idx += 1
        
    return bytes(ba)


def get_material_and_chassis_names(data: bytes) -> tuple[str | None, str | None]:
    """
    Scan the name table to extract the main body material (MIC_Body_*) 
    and main chassis material (Chassis_*_MIC / *Chassis_MIC).
    """
    try:
        name_map, names = _get_name_indices(data)
    except Exception:
        return None, None
        
    body_mat = None
    chassis_mat = None
    
    for name in names:
        nl = name.lower()
        if nl.startswith("mic_body_") and not nl.endswith("_all") and not nl.endswith("_paintable"):
            body_mat = name
            break
            
    for name in names:
        nl = name.lower()
        if "chassis" in nl and nl.endswith("mic"):
            chassis_mat = name
            break
            
    return body_mat, chassis_mat


def get_wheel_and_mesh_names(data: bytes) -> tuple[str | None, str | None, str | None]:
    """
    Scan the name table to extract:
    1. Wheel unpainted material (Wheel_*_MIC or MIC_Wheel_*)
    2. Wheel painted material (Wheel_*_MIC_PAINTED)
    3. Wheel static/skeletal mesh (WHEEL_*_SM or WHEEL_*_SK)
    """
    try:
        name_map, names = _get_name_indices(data)
    except Exception:
        return None, None, None
        
    wheel_mat = None
    wheel_mat_painted = None
    wheel_sm = None
    
    # 1. Passagem Principal: Padrões ideais
    for name in names:
        nl = name.lower()
        if ("wheel" in nl or "rim" in nl) and "mic" in nl:
            if "painted" in nl:
                wheel_mat_painted = name
            else:
                wheel_mat = name
        elif ("wheel" in nl or "rim" in nl) and (nl.endswith("_sm") or nl.endswith("_sk")):
            wheel_sm = name
            
    # 2. Segunda Passagem (Fallback para materiais seletivos em UPKs de rodas)
    if not wheel_mat:
        for name in names:
            nl = name.lower()
            if nl.startswith("mic_") or nl.endswith("_mic") or nl.endswith("_mic_painted"):
                if "body" not in nl and "chassis" not in nl and "decal" not in nl:
                    if "painted" in nl:
                        wheel_mat_painted = name
                    else:
                        wheel_mat = name
                        
    # 3. Terceira Passagem (Fallback para meshes estáticas)
    if not wheel_sm:
        for name in names:
            nl = name.lower()
            if nl.endswith("_sm") or nl.endswith("_sk"):
                if "body" not in nl and "chassis" not in nl:
                    wheel_sm = name
                    
    return wheel_mat, wheel_mat_painted, wheel_sm


def get_package_names_from_file(file_path: Path, aes: str | None) -> list[str]:
    """Decrypt a UPK file temporarily and extract all its name table entries."""
    if not file_path.exists():
        return []
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dec = Path(tmp) / "temp_dec.upk"
        try:
            decrypt_upk(str(file_path), aes, str(tmp_dec))
            with open(tmp_dec, "rb") as f:
                data = f.read()
            _, names = _get_name_indices(data)
            return names
        except Exception:
            return []


def resolve_casing_from_names(desired_name: str, names: list[str]) -> str:
    """
    Search case-insensitively in `names` for `desired_name`.
    If found, return the exact casing from `names`.
    Otherwise, return `desired_name`.
    """
    desired_lower = desired_name.lower()
    for name in names:
        if name.lower() == desired_lower:
            return name
    return desired_name


def get_material_and_chassis_names_from_list(names: list[str]) -> tuple[str | None, str | None]:
    """Scan an in-memory names list to extract the main body and chassis materials."""
    body_mat = None
    chassis_mat = None
    
    for name in names:
        nl = name.lower()
        if nl.startswith("mic_body_") and not nl.endswith("_all") and not nl.endswith("_paintable"):
            body_mat = name
            break
            
    for name in names:
        nl = name.lower()
        if "chassis" in nl and nl.endswith("mic"):
            chassis_mat = name
            break
            
    return body_mat, chassis_mat


def get_wheel_and_mesh_names_from_list(names: list[str]) -> tuple[str | None, str | None, str | None]:
    """Scan an in-memory names list to extract wheel materials and static/skeletal mesh names."""
    wheel_mat = None
    wheel_mat_painted = None
    wheel_sm = None
    
    # 1. Passagem Principal: Padrões ideais
    for name in names:
        nl = name.lower()
        if ("wheel" in nl or "rim" in nl) and "mic" in nl:
            if "painted" in nl:
                wheel_mat_painted = name
            else:
                wheel_mat = name
        elif ("wheel" in nl or "rim" in nl) and (nl.endswith("_sm") or nl.endswith("_sk")):
            wheel_sm = name
            
    # 2. Segunda Passagem (Fallback para materiais seletivos em UPKs de rodas)
    if not wheel_mat:
        for name in names:
            nl = name.lower()
            if nl.startswith("mic_") or nl.endswith("_mic") or nl.endswith("_mic_painted"):
                if "body" not in nl and "chassis" not in nl and "decal" not in nl:
                    if "painted" in nl:
                        wheel_mat_painted = name
                    else:
                        wheel_mat = name
                        
    # 3. Terceira Passagem (Fallback para meshes estáticas)
    if not wheel_sm:
        for name in names:
            nl = name.lower()
            if nl.endswith("_sm") or nl.endswith("_sk"):
                if "body" not in nl and "chassis" not in nl:
                    wheel_sm = name
                    
    return wheel_mat, wheel_mat_painted, wheel_sm


def detect_names_from_file(file_path: Path, aes: str | None) -> tuple[str | None, str | None]:
    """Decrypt a UPK file temporarily and extract its material and chassis names."""
    if not file_path.exists():
        return None, None
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dec = Path(tmp) / "temp_dec.upk"
        try:
            decrypt_upk(str(file_path), aes, str(tmp_dec))
            with open(tmp_dec, "rb") as f:
                data = f.read()
            return get_material_and_chassis_names(data)
        except Exception:
            return None, None


def detect_wheel_names_from_file(file_path: Path, aes: str | None) -> tuple[str | None, str | None, str | None]:
    """Decrypt a UPK file temporarily and extract its wheel material and mesh names."""
    if not file_path.exists():
        return None, None, None
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dec = Path(tmp) / "temp_dec.upk"
        try:
            decrypt_upk(str(file_path), aes, str(tmp_dec))
            with open(tmp_dec, "rb") as f:
                data = f.read()
            return get_wheel_and_mesh_names(data)
        except Exception:
            return None, None, None


def patch_names(
    data: bytes,
    find: str,
    replace: str,
    target_body_mat: str | None = None,
    target_chassis_mat: str | None = None,
    equipped_body_mat: str | None = None,
    equipped_chassis_mat: str | None = None,
    target_wheel_mat: str | None = None,
    target_wheel_mat_painted: str | None = None,
    target_wheel_sm: str | None = None,
    equipped_wheel_mat: str | None = None,
    equipped_wheel_mat_painted: str | None = None,
    equipped_wheel_sm: str | None = None,
    equipped_names: list[str] | None = None
) -> bytes:
    """
    Comprehensively patch all possible package and resource bind variants in the name table.
    This guarantees that packages, skeletal meshes, materials, chassis, wheels, and texture packages
    align perfectly with Rocket League's Master Database asset bindings.
    """
    # Scan for composite names dynamically in this package's name table
    composite_variants = []
    try:
        _, names = _get_name_indices(data)
        for name in names:
            if name.lower().startswith(find.lower() + "."):
                rep = replace + name[len(find):]
                composite_variants.append((name, rep))
    except Exception:
        pass

    find_sub = find.replace("Body_", "").replace("body_", "")
    replace_sub = replace.replace("Body_", "").replace("body_", "")
    
    find_sub_cap = find_sub.capitalize()
    replace_sub_cap = replace_sub.capitalize()
    
    variants = [
        # 1. Base / Package names
        (find, replace),
        (find + "_SF", replace + "_SF"),
        
        # 2. Texture package variations
        (find + "_T", replace + "_T"),
        (find + "_T_SF", replace + "_T_SF"),
        (find + "_Textures", replace + "_Textures"),
        (find + "_Textures_SF", replace + "_Textures_SF"),
        
        # 3. Skeletal Mesh & Physics variants
        (find + "_SK", replace + "_SK"),
        (find + "_Physics", replace + "_Physics"),
        (find + "_Thumbnail", replace + "_Thumbnail"),
        
        # 4. Materials & Chassis variants (various casings)
        ("MIC_Body_" + find_sub, "MIC_Body_" + replace_sub),
        ("MIC_Body_" + find_sub_cap, "MIC_Body_" + replace_sub_cap),
        ("MIC_Chassis_" + find_sub, "MIC_Chassis_" + replace_sub),
        ("MIC_Chassis_" + find_sub_cap, "MIC_Chassis_" + replace_sub_cap),
        (find_sub + "Chassis_MIC", replace_sub + "Chassis_MIC"),
        (find_sub_cap + "Chassis_MIC", replace_sub_cap + "Chassis_MIC"),
    ]
    
    # Exclude any generic variants that would conflict with our specific, detected material/chassis names
    exclude_find_names = set()
    if target_body_mat:
        exclude_find_names.add(target_body_mat.lower())
    if target_chassis_mat:
        exclude_find_names.add(target_chassis_mat.lower())
    if target_wheel_mat:
        exclude_find_names.add(target_wheel_mat.lower())
    if target_wheel_mat_painted:
        exclude_find_names.add(target_wheel_mat_painted.lower())
    if target_wheel_sm:
        exclude_find_names.add(target_wheel_sm.lower())
    
    # Filter duplicates, empty pairs, and conflicts
    seen = set()
    unique_variants = []
    
    # Add composite variants detected in the package name table first!
    for f, r in composite_variants:
        if (f, r) not in seen:
            seen.add((f, r))
            unique_variants.append((f, r))

    # Add specific dynamic mappings!
    if target_body_mat and equipped_body_mat:
        seen.add((target_body_mat, equipped_body_mat))
        unique_variants.append((target_body_mat, equipped_body_mat))
    if target_chassis_mat and equipped_chassis_mat:
        seen.add((target_chassis_mat, equipped_chassis_mat))
        unique_variants.append((target_chassis_mat, equipped_chassis_mat))
        
    # Add dynamic wheel specific mappings!
    if target_wheel_mat and equipped_wheel_mat:
        seen.add((target_wheel_mat, equipped_wheel_mat))
        unique_variants.append((target_wheel_mat, equipped_wheel_mat))
    if target_wheel_mat_painted and equipped_wheel_mat_painted:
        seen.add((target_wheel_mat_painted, equipped_wheel_mat_painted))
        unique_variants.append((target_wheel_mat_painted, equipped_wheel_mat_painted))
    if target_wheel_sm and equipped_wheel_sm:
        seen.add((target_wheel_sm, equipped_wheel_sm))
        unique_variants.append((target_wheel_sm, equipped_wheel_sm))
        
    for f, r in variants:
        if f == r or (f, r) in seen:
            continue
        if f.lower() in exclude_find_names:
            # Skip conflicting generic fallback
            continue
        seen.add((f, r))
        unique_variants.append((f, r))
    
    for f, r in unique_variants:
        if equipped_names:
            r = resolve_casing_from_names(r, equipped_names)
        data = patch_upk_names(data, f, r)
        
    return data
