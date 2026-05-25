# Changelog - RL Forge

All notable changes to RL Forge will be documented in this file.

---

## [2.0.0] - 2026-05-24

> **Complete rewrite.** Version 2.0.0 is a total refactoring of RL Forge — new architecture, new interface, new features, and radically superior performance. Users of 1.0.0 will experience a completely different product.

### 🏗️ Architecture

- **Migration to Hybrid Electron + Flask:** Complete departure from CustomTkinter in favor of a native desktop UI running on Electron (HTML5/CSS3/JS) with a headless Flask backend in Python. The interface loads instantly, is pixel-perfect, and utilizes GPU acceleration via Chromium.
- **Independent Steam and Epic Modes:** Each platform has its own game directory (`pkg_dir_epic` / `pkg_dir_steam`) and its own backups folder (`_RL_Forge_Backups_Epic` / `_RL_Forge_Backups_Steam`). A visual platform toggle pill in the title bar allows switching between modes with a single click, preserving all configurations for each platform.
- **Automatic Migration of Legacy Settings:** Upon opening for the first time after the update, the previous `pkg_dir` is automatically migrated to the active platform's configuration key without any data loss.

### ✨ New Features

- **Dynamic Painting System (RGB):** Full color picker allowing the application of any hexadecimal color to any in-game item.
- **Brightness/Intensity Control:** Slider to adjust the intensity of the applied color, enabling high-intensity neon and glow effects.
- **Self-Item Painting:** Allows selecting the same item on both sides to apply only the custom paint/color without changing the item's baseline model.
- **Recent Colors Grid (2×4):** The 8 most frequently used colors are saved and displayed as clickable swatches. Recent colors are only added after a successful swap using the chosen color — never upon mere selection.
- **Out-of-the-Box Color Preloading:** When launching the app for the first time, the grid comes pre-populated with vibrant and classic neon colors.
- **Color Variants in Picker:** When selecting an item on the right side, a bar of colored dots displays all available painted variants for quick selection.
- **Combo System (Presets):** Save, apply, and share entire swap combos. Supports exporting and importing via compressed, URL-safe Base64 codes.
- **Automatic Game Folder Detection:** An algorithm that reads the Windows Registry and Steam/Epic manifest files to auto-configure the directory in a single click, respecting the active platform.
- **Favorites System:** Mark items as favorites with ★ and filter to see only them in both pickers simultaneously.
- **Embedded Execution Console:** A collapsible panel at the footer displays all operation logs in real time, with visual distinction by type (error, success, info).
- **Internationalization (PT-BR / EN):** The entire interface is dynamically translated. Includes a language toggle in the title bar.
- **Real-Time Game Status:** An indicator in the title bar displays whether Rocket League is running, utilizing polling every 10 seconds.

### ⚡ Performance

- **Pre-computed Product Index:** When loading the catalog's 9,008 items, all search fields (`_labelL`, `_nameL`, `_slotL`) and display properties (`_slotName`, `_baseLabel`, `_slotColor`, `_emote`) are computed **only once** and cached. Subsequent searches are pure O(n) string comparisons without object allocation.
- **List Virtualization (Infinite Scroll):** Renders only 80 cards per batch. An `IntersectionObserver` monitors an invisible sentinel at the end of the list and automatically loads the next batch on scroll — no pagination, no buttons. The DOM never holds more than ~80–160 card nodes per list simultaneously.
- **Intelligent Debounce with `requestAnimationFrame`:** Searches with `< 2` characters are instantaneous; longer queries wait for a 250ms typing pause, and rendering is scheduled in the next animation frame to prevent blocking the input thread.
- **Global Constants:** `COLORS_SORTED` and `SEARCH_SHORTHANDS` are defined once at the module level — eliminating the recreation of arrays on every keystroke that occurred previously.
- **Result:** Search UI responsiveness went from a ~400ms freeze per keystroke to `< 16ms` (1 frame) on any search.

### 🐛 Bug Fixes

- **`Cannot read properties of null (reading 'style')` Crash in Backups:** Fixed a DOM lifecycle bug where the `#backups-empty` element was destroyed by `innerHTML = ""` and consequently returned `null` on subsequent `getElementById` calls. The element is now detached before clearing the container and always re-appended (even when hidden) at the end of each render path.
- **Complete Painting of Alpha Boost (Black/Dark):** Identified and corrected binary signatures for particle emission and ignition (`CarBoostGlowColor`, `SourceColor`, `ParameterValue`), allowing clean dark custom paint effects.
- **Automatic Texture Synchronization:** Implemented automatic detection and replacement of companion texture packages (`_T_SF.upk`), completely eliminating the "smooth/flat" chassis visual bug after swapping.
- **Seekfree Composite Package Resolution:** Fixed a game crash when swapping Dueling Dragons (`explosion_Dragon`) to Classic (`Explosion_Default`) by implementing a composite prefix scanner to dynamically detect and remap nested resource paths inside seekfree packages (e.g., skeletal meshes and particle systems).
- **Dynamic Casing Resolver:** Integrated case-insensitive lookup resolving generic lowercased replacements to their original capitalized strings (e.g., thumbnail assets and skeletal meshes) for stable asset binding.
- **Chain Swap Protection:** The swap engine prioritizes reading from original clean backups, preventing previous swaps from contaminating new swap operations.
- **Unicode (UTF-16) Support:** Unicode names now parse and encrypt correctly (e.g., Dieci Wheels).
- **Hidden `.upk` Extension in Backups List:** Backup file names are now displayed without their technical file extensions, resulting in a cleaner UI.
- **Recent Colors Behavior:** Colors are no longer added to the grid simply by clicking them — they are only added after a successful swap is completed with that color.

### 🔒 Security

- **Triton / Cannonboy Safety Block:** Explicitly disabled and blocked any swaps containing Triton wheels (internal name `cannonboy`) as source or target to avoid fatal UI/icon rendering crashes in the game's garage.
- **Painted Octane Blocking:** Swaps using RGB paint or painted variants on `Body_Octane` are explicitly blocked, as their materials reside in the global `Startup.upk`. Unpainted swaps remain allowed.
- **OEM / Startup.upk Safety Block:** Validation and blocking of swaps targeting OEM wheels (which are preloaded in the `Startup.upk` memory space), safeguarding the user's account from Easy Anti-Cheat (EAC) flag risks.
- **Active Game Detection:** Prevents swap operations while Rocket League is actively running.

---

## [1.0.0] - 2026-05-14

- Initial release of RL Forge.
- Basic Item Swapping system (UPK substitution).
- Support for Decals, Wheels, Cars, and Boosts.
- Modern dark mode interface (CustomTkinter).
- Automatic backup and restoration system.
