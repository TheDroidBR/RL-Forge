import json
from core.utils import get_data_dir

CONFIG_FILE = get_data_dir() / "data" / "config.json"

_current_lang = "en"

# Load initial language from config
try:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
            _current_lang = cfg.get("language", "en")
except Exception:
    _current_lang = "en"

TRANSLATIONS = {
    "en": {
        "title": "🚀 RL Forge",
        "btn_game_folder": "📁 Game Folder",
        "btn_update_items": "☁️ Update Items",
        "btn_credits": "Credits",
        "loading_init": "Initializing application...",
        "btn_clear": "Clear",
        "console_title": "💻 EXECUTION CONSOLE",
        "search_placeholder": "🔍 Search...",
        "all": "All",
        "tab_swap": "⚡  Swap",
        "tab_combos": "📦  Combos",
        "tab_backups": "💾  Backups",
        "slot_antenna": "Antenna",
        "slot_decal": "Decal",
        "slot_goal_explosion": "Goal Explosion",
        "slot_wheels": "Wheels",
        "slot_topper": "Topper",
        "slot_body": "Body",
        "slot_trail": "Trail",
        "slot_engine_audio": "Engine Audio",
        "slot_rocket_boost": "Boost",
        # Extra strings in Swap Panel
        "select_item": "Select an item to customize",
        "equip_standard": "Equip Standard Boost in-game",
        "custom_paint": "Custom Paint:",
        "intensity": "Intensity:",
        "btn_apply_swap": "Apply Swap",
        "btn_restore": "Restore",
        # Extra strings in Backups Panel
        "no_backups": "No active backups found.",
        "btn_restore_all": "Restore All",
        "backup_name": "Backup Name",
        "action": "Action",
        # Extra strings in Combos Panel
        "select_combo": "Select a Combo preset",
        "btn_apply_combo": "Apply Combo",
        "combo_slots": "Combo Slots",
        "search_combos": "Search Combos...",
        "credits_title": "RL Forge Credits",
        "credits_msg": "RL Forge - Client-side Item Swap Utility\n\nDeveloped with dark aesthetics and absolute precision.\nSpecial thanks to the community and contributors.",
        # UI Titles
        "orig_picker_title": "ITEM YOU ARE EQUIPPING",
        "target_picker_title": "VISUAL LOOK YOU WANT",
        "sel_none": "None selected",
        "btn_swap_action": "⚡ SWAP",
        "btn_save_combo": "💾 Save Combo",
        "paint_section_title": "🎨 PAINT",
        "btn_select_color": "Select Color",
        "btn_clear_color": "Clear Color",
        "flame_section_title": "🔥 EXHAUST FLAME",
        "flame_magnet_label": "🧲 Magnet",
        "btn_select_flame_color": "Select Color",
        "btn_clear_flame_color": "Clear Color",
        "intensity_label_fmt": "Brightness: {val}x",
        "combos_title": "PRESETS & COMBOS",
        "no_combos": "No custom combos saved yet.",
        "combo_name_placeholder": "Combo Name...",
        "combo_saved": "Combo saved successfully!",
        "combo_applied": "Combo applied successfully!",
        "restore_completed": "All backups restored successfully!",
        # Platform & Path Separation
        "platform_active_changed": "Active platform changed to: {platform}",
        "pkg_dir_configured": "📁 Game folder configured: {folder}",
        "pkg_dir_autodetected": "📁 Auto-detected: {folder}",
        "combos_header_title": "📦  My Saved Combos",
        "backups_header_title": "💾  Active Backups",
        "no_backups_msg": "No active swaps.\nMake a swap in the Swap tab!",
        "no_combos_msg": "No combos saved.\nClick 'Save Combo' in the Swap tab!",
        "btn_restore_all_title": "↺ Restore All",
        "btn_refresh": "🔄 Refresh",
        "btn_restore_one": "Restore",
        "btn_apply_preset": "▶ Apply All",
        "console_header_title": "💻 EXECUTION CONSOLE",
        "folder_not_configured_title": "⚠️  Folder not configured",
        "btn_credits_title": "ℹ️ Credits",
        "credits_version_license": "Version {version} — Under GNU GPL v3.0 License",
        "credits_main_text": "Developed by **TheDroid** with love for the community.\n\nThis project is only possible thanks to the modding community:\n\n• ShinyEmii (Toga-Files): Item database and AES keys.\n• AltimorTASDK (RLUPKTool): Decryption engine (MIT License).\n\nThe source code of RL Forge is open and free under GNU GPL v3.0.",
        "console_ready": "Ready.",
        # QoL & Base64 Presets Share
        "recent_colors_title": "RECENT COLORS",
        "btn_import_code": "📥 Import Code",
        "btn_export_code_title": "📋 Export",
        "dialog_import_title": "Import Combo",
        "dialog_import_msg": "Paste the combo code below:",
        "dialog_import_name_title": "Combo Name",
        "dialog_import_name_msg": "Give a name to the imported combo:",
        "import_invalid_code": "❌ Invalid combo code.",
        "import_success": "✅ Combo '{name}' imported successfully!",
        "export_success": "📋 Combo code copied to clipboard!",
        "btn_autodetect": "🔍 Auto-Detect",
        "autodetect_failed": "❌ Could not auto-detect Rocket League folder. Please select it manually.",
        "autodetect_success": "📁 Rocket League folder auto-detected successfully!",
        "backup_not_in_game_tooltip": "The modified file was not found in the game folder (already restored or deleted).",
        "backup_not_readable_tooltip": "The backup file is unreadable or corrupted.",
        # Platform mode toggle
        "platform_label": "Platform",
        "platform_epic": "Epic",
        "platform_steam": "Steam",
        "platform_switch_toast": "Platform: {platform}",
        "platform_folder_missing": "No folder configured for {platform}. Select or auto-detect it.",
        # Terminal & Safety Localization
        "log_restored": "✅ Restored: {name}",
        "log_restored_textures": "🎨 Restored textures for: {name}",
        "log_no_backups": "ℹ️ No backups found.",
        "log_using_original_from_backup": "[info] Using original file for {name} from backup.",
        "log_original_saved": "[backup] Original saved: {name}",
        "log_using_existing_backup": "[info] Using existing original backup.",
        "log_decrypting": "[1/4] Decrypting {name}...",
        "log_altering_nametable": "[2/4] Altering name table: {target} -> {orig}...",
        "log_material_mapping": "[info] Material mapping: {target} -> {equipped}",
        "log_chassis_mapping": "[info] Chassis mapping: {target} -> {equipped}",
        "log_applying_rgb": "🎨 Applying custom RGB paint...",
        "log_recrypting": "[3/4] Re-encrypting...",
        "log_saving_to": "[4/4] Saving to {name}...",
        "log_starting_swap": "🔄 Starting main package swap...",
        "log_textures_detected": "🎨 Texture packages detected! Performing texture swap...",
        "log_swap_completed": "[OK] Swap completed! {orig} now looks like {target}.",
        "log_wheel_paint_ignored": "[info] Paint ignored: unpainted wheels do not support stable color injection due to Rocket League's native runtime overrides.",
        "log_paint_ignored": "[info] Paint ignored: only bodies and rocket boosts support custom color injection due to game engine restrictions.",
        "err_item_not_found": "Item not found.",
        "err_invalid_combo_code": "Invalid combo code.",
        "err_paint_blocking": "Swaps with paint (RGB or painted variant) are not allowed for Octane or OEM wheels as final destination, as their textures reside in the global Startup.upk file.",
        "log_err_paint_blocking": "❌ Security Error: Swaps with paint (RGB or painted variant) are not allowed for Octane or OEM wheels as final destination, as their textures reside in the global Startup.upk file.",
        "err_prefix": "❌ Error: {error}",
        "err_game_running": "Cannot modify game files while Rocket League is running. Please close the game and try again.",
        "log_err_game_running": "❌ Safety Error: Rocket League is running! Close the game before swapping or restoring.",
        "modal_game_running_title": "⚠️ Rocket League is Running",
        "modal_game_running_body": "Cannot perform swaps or restorations while Rocket League is running. Please close the game first!",
        "btn_close_warning": "Got it",
        "oem_disabled_msg": "This item cannot be changed due to technical limitations of the game (Startup.upk).",
        "oem_badge_label": "⚠️ Unavailable",
        "gizmo_disabled_msg": "Gizmo (Body_Spark) cannot be swapped due to an incompatibility in its internal file structure that causes the game to crash.",
        "gizmo_badge_label": "⚠️ Unavailable",
        "triton_disabled_msg": "Triton (cannonboy) cannot be swapped due to an incompatibility in its internal SeekFree package structure that causes the game to crash during garage rendering.",
    },
    "pt-BR": {
        "title": "🚀 RL Forge",
        "btn_game_folder": "📁 Pasta do Jogo",
        "btn_update_items": "☁️ Atualizar Itens",
        "btn_credits": "Créditos",
        "loading_init": "Inicializando aplicação...",
        "btn_clear": "Limpar",
        "console_title": "💻 TERMINAL DE EXECUÇÃO",
        "search_placeholder": "🔍 Buscar...",
        "all": "Todos",
        "tab_swap": "⚡  Swap",
        "tab_combos": "📦  Combos",
        "tab_backups": "💾  Backups",
        "slot_antenna": "Antena",
        "slot_decal": "Decalque",
        "slot_goal_explosion": "Explosão de Gol",
        "slot_wheels": "Rodas",
        "slot_topper": "Topper",
        "slot_body": "Carro",
        "slot_trail": "Rastro",
        "slot_engine_audio": "Áudio de Motor",
        "slot_rocket_boost": "Boost",
        # Extra strings in Swap Panel
        "select_item": "Selecione um item para customizar",
        "equip_standard": "Equipe o Boost Padrão no jogo",
        "custom_paint": "Pintura Customizada:",
        "intensity": "Intensidade:",
        "btn_apply_swap": "Aplicar Swap",
        "btn_restore": "Restaurar",
        # Extra strings in Backups Panel
        "no_backups": "Nenhum backup ativo encontrado.",
        "btn_restore_all": "Restaurar Todos",
        "backup_name": "Nome do Backup",
        "action": "Ação",
        # Extra strings in Combos Panel
        "select_combo": "Selecione um Combo predefinido",
        "btn_apply_combo": "Aplicar Combo",
        "combo_slots": "Slots do Combo",
        "search_combos": "Buscar Combos...",
        "credits_title": "Créditos do RL Forge",
        "credits_msg": "RL Forge - Utilitário de Swap de Itens Local\n\nDesenvolvido com estética premium e precisão absoluta.\nAgradecimentos especiais à comunidade e colaboradores.",
        # UI Titles
        "orig_picker_title": "ITEM QUE VOCÊ USA",
        "target_picker_title": "VISUAL QUE VOCÊ QUER",
        "sel_none": "Nenhum selecionado",
        "btn_swap_action": "⚡ SWAP",
        "btn_save_combo": "💾 Salvar Combo",
        "paint_section_title": "🎨 PINTURA",
        "btn_select_color": "Selecionar Cor",
        "btn_clear_color": "Limpar Cor",
        "flame_section_title": "🔥 FOGO DO ESCAPAMENTO",
        "flame_magnet_label": "🧲 Ímã",
        "btn_select_flame_color": "Selecionar Cor",
        "btn_clear_flame_color": "Limpar Cor",
        "intensity_label_fmt": "Brilho: {val}x",
        "combos_title": "PRESETS & COMBOS",
        "no_combos": "Nenhum combo personalizado salvo ainda.",
        "combo_name_placeholder": "Nome do Combo...",
        "combo_saved": "Combo salvo com sucesso!",
        "combo_applied": "Combo aplicado com sucesso!",
        "restore_completed": "Todos os backups foram restaurados com sucesso!",
        # Platform & Path Separation
        "platform_active_changed": "Plataforma activa alterada para: {platform}",
        "pkg_dir_configured": "📁 Pasta configurada: {folder}",
        "pkg_dir_autodetected": "📁 Auto-detectado: {folder}",
        "combos_header_title": "📦  Meus Combos Salvos",
        "backups_header_title": "💾  Backups Ativos",
        "no_backups_msg": "Nenhum swap ativo.\nFaça um swap na aba principal!",
        "no_combos_msg": "Nenhum combo salvo.\nClique em 'Salvar Combo' na aba Swap!",
        "btn_restore_all_title": "↺ Restaurar Tudo",
        "btn_refresh": "🔄 Atualizar",
        "btn_restore_one": "Restaurar",
        "btn_apply_preset": "▶ Aplicar Tudo",
        "console_header_title": "💻 TERMINAL DE EXECUÇÃO",
        "folder_not_configured_title": "⚠️  Pasta não configurada",
        "btn_credits_title": "ℹ️ Créditos",
        "credits_version_license": "Versão {version} — Sob Licença GNU GPL v3.0",
        "credits_main_text": "Desenvolvido por **TheDroid** com amor para a comunidade.\n\nEste projeto só é possível graças à comunidade de modding:\n\n• ShinyEmii (Toga-Files): Banco de dados de itens e chaves AES.\n• AltimorTASDK (RLUPKTool): Motor de descriptografia (MIT License).\n\nO código-fonte do RL Forge é aberto e livre sob a GNU GPL v3.0.",
        "console_ready": "Pronto.",
        # QoL & Base64 Presets Share
        "recent_colors_title": "CORES RECENTES",
        "btn_import_code": "📥 Importar Código",
        "btn_export_code_title": "📋 Exportar",
        "dialog_import_title": "Importar Combo",
        "dialog_import_msg": "Cole o código do combo abaixo:",
        "dialog_import_name_title": "Nome do Combo",
        "dialog_import_name_msg": "Dê um nome para o combo importado:",
        "import_invalid_code": "❌ Código de combo inválido.",
        "import_success": "✅ Combo '{name}' importado com sucesso!",
        "export_success": "📋 Código do combo copiado para a área de transferência!",
        "btn_autodetect": "🔍 Auto-Detectar",
        "autodetect_failed": "❌ Não foi possível auto-detectar a pasta do Rocket League. Selecione manualmente.",
        "autodetect_success": "📁 Pasta do Rocket League auto-detected com sucesso!",
        "backup_not_in_game_tooltip": "O arquivo modificado não foi encontrado na pasta do jogo (já restaurado ou removido).",
        "backup_not_readable_tooltip": "O arquivo de backup está ilegível ou corrompido.",
        # Platform mode toggle
        "platform_label": "Plataforma",
        "platform_epic": "Epic",
        "platform_steam": "Steam",
        "platform_switch_toast": "Plataforma: {platform}",
        "platform_folder_missing": "Nenhuma pasta configurada para {platform}. Selecione ou auto-detecte.",
        # Terminal & Safety Localization
        "log_restored": "✅ Restaurado: {name}",
        "log_restored_textures": "🎨 Restaurado texturas de: {name}",
        "log_no_backups": "ℹ️ Nenhum backup encontrado.",
        "log_using_original_from_backup": "[info] Usando arquivo original de {name} a partir do backup.",
        "log_original_saved": "[backup] Original salvo: {name}",
        "log_using_existing_backup": "[info] Usando backup original já existente.",
        "log_decrypting": "[1/4] Descriptografando {name}...",
        "log_altering_nametable": "[2/4] Alterando name table: {target} -> {orig}...",
        "log_material_mapping": "[info] Mapeamento de materiais: {target} -> {equipped}",
        "log_chassis_mapping": "[info] Mapeamento de chassis: {target} -> {equipped}",
        "log_applying_rgb": "🎨 Aplicando pintura customizada RGB...",
        "log_recrypting": "[3/4] Re-criptografando...",
        "log_saving_to": "[4/4] Salvando em {name}...",
        "log_starting_swap": "🔄 Iniciando swap do pacote principal...",
        "log_textures_detected": "🎨 Pacotes de textura detectados! Efetuando swap de texturas...",
        "log_swap_completed": "[OK] Swap concluido! {orig} agora parece {target}.",
        "log_wheel_paint_ignored": "[info] Pintura ignorada: rodas unpainted não suportam injeção estável de cor devido a overrides gráficos nativos do Rocket League.",
        "log_paint_ignored": "[info] Pintura ignorada: apenas chassis de carros e boosts suportam injeção de cor customizada devido a restrições do motor do jogo.",
        "err_item_not_found": "Item não encontrado.",
        "err_invalid_combo_code": "Código inválido.",
        "err_paint_blocking": "Swaps com pintura (RGB ou variante pintada) não são permitidos para o Octane ou rodas OEM como destino final, pois suas texturas residem no arquivo global Startup.upk.",
        "log_err_paint_blocking": "❌ Erro de Segurança: Swaps com pintura (RGB ou variante pintada) não são permitidos para o Octane ou rodas OEM como destino final, pois suas texturas residem no arquivo global Startup.upk.",
        "err_prefix": "❌ Erro: {error}",
        "err_game_running": "Não é possível modificar os arquivos do jogo enquanto o Rocket League estiver aberto. Feche o jogo e tente novamente.",
        "log_err_game_running": "❌ Erro de Segurança: O Rocket League está aberto! Feche o jogo antes de fazer swaps ou restaurações.",
        "modal_game_running_title": "⚠️ Rocket League Aberto",
        "modal_game_running_body": "Não é possível fazer swaps ou restaurações enquanto o Rocket League estiver aberto. Por favor, feche o jogo primeiro!",
        "btn_close_warning": "Entendi",
        "oem_disabled_msg": "Este item não pode ser modificado devido a limitações técnicas do jogo (Startup.upk).",
        "oem_badge_label": "⚠️ Indisponível",
        "gizmo_disabled_msg": "O Gizmo (Body_Spark) não pode ser feito swap devido a uma incompatibilidade na estrutura interna do arquivo que causa crash no jogo.",
        "gizmo_badge_label": "⚠️ Indisponível",
        "triton_disabled_msg": "A Triton (cannonboy) não pode ser feita swap devido a uma incompatibilidade na estrutura interna do seu arquivo SeekFree que causa crash no jogo ao renderizar a garagem.",
    }
}

def set_language(lang: str) -> None:
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang
        # Persist to config.json
        try:
            cfg = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                    cfg = json.load(f)
            cfg["language"] = lang
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

def get_language() -> str:
    return _current_lang

def t(key: str, default: str = None) -> str:
    lang = get_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, default or key)

def translate_slot_name(slot: str) -> str:
    """
    Translates a slot name to the active language, with a dynamic capitalization fallback
    for unmapped slots (e.g., 'underglow_neon' -> 'Underglow: Neon' in English or custom).
    """
    key = f"slot_{slot.lower().replace(' ', '_')}"
    translated = t(key, None)
    if translated != key:
        return translated
    
    # Fallback premium: e.g. underglow_neon -> Underglow: Neon
    import re
    parts = slot.replace("_", " ").split()
    if not parts:
        return slot.title()
    
    if len(parts) > 1:
        prefix = parts[0].capitalize()
        rest = " ".join(parts[1:]).title()
        return f"{prefix}: {rest}"
    else:
        rest = re.sub(r'(?<!^)(?=[A-Z])', ' ', parts[0])
        return rest.title()
