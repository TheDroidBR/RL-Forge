/**
 * RL Forge — Renderer App Logic
 * Pure JS, no framework. Communicates with Python backend via fetch().
 */

"use strict";

// ═══════════════════════════════════════════════════════════════
// 1. API LAYER
// ═══════════════════════════════════════════════════════════════
const api = {
  base: "",   // same origin — Flask serves this file

  async get(path, params = {}) {
    const qs  = new URLSearchParams(params).toString();
    const url = qs ? `${path}?${qs}` : path;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`GET ${url}: ${res.status}`);
    return res.json();
  },

  async post(path, body = {}) {
    const res = await fetch(path, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `POST ${path}: ${res.status}`);
    }
    return res.json();
  },

  config:           ()      => api.get("/api/config"),
  saveConfig:       (data)  => api.post("/api/config", data),
  products:         (p)     => api.get("/api/products", p),
  fetchProducts:    ()      => api.post("/api/products/fetch"),
  slots:            ()      => api.get("/api/slots"),
  swap:             (d)     => api.post("/api/swap", d),
  restore:          (d)     => api.post("/api/restore", d),
  restoreAll:       (d)     => api.post("/api/restore-all", d),
  backups:          (dir)   => api.get("/api/backups", { pkg_dir: dir }),
  colorVariants:    (name)  => api.get("/api/color-variants", { name }),
  autodetect:       (plat)  => api.get("/api/autodetect", { platform: plat }),
  encodeCombo:      (swaps) => api.post("/api/combos/encode", { swaps }),
  decodeCombo:      (code)  => api.post("/api/combos/decode", { code }),
  translations:     (lang)  => api.get("/api/translations", { lang }),
  paintColors:      ()      => api.get("/api/paint-colors"),
  gameRunning:      ()      => api.get("/api/game-running"),
  toggleFav:        (name)  => api.post("/api/favorites/toggle", { name }),
  imageUrl:         (name)  => `/api/images/${encodeURIComponent(name)}`,
};


// ═══════════════════════════════════════════════════════════════
// 2. GLOBAL STATE
// ═══════════════════════════════════════════════════════════════
const state = {
  lang:      "pt-BR",
  strings:   {},
  config:    {},
  paintColors: {},

  // All products loaded once — filtered client-side
  allProducts: [],

  // Pickers
  orig: {
    search: "", slot: "Todos", favOnly: false,
    selected: null, searchTimer: null,
  },
  target: {
    search: "", slot: "Todos", favOnly: false,
    selected: null, searchTimer: null,
  },

  // Paint
  customHex: null,
  intensity: 1.0,
  customHexFlame: null,
  flameMagnet: true,
  recentColors: [],

  // Combos
  combos: [],

  // UI
  activeTab: "swap",
};

const DEFAULT_FACTORY_COLORS = [
  "#FFFFFF","#FF0000","#00FF00","#0000FF",
  "#FFFF00","#FF00FF","#00FFFF","#FF8C00",
];

const SLOT_COLORS = {
  "Antenna":      "#ffa726",
  "Decal":        "#ab47bc",
  "Goal Explosion":"#ff7043",
  "Wheels":       "#66bb6a",
  "Topper":       "#ef5350",
  "Body":         "#fbc02d",
  "Trail":        "#26a69a",
  "Engine Audio": "#8d6e63",
  "Rocket Boost": "#00d4ff",
};
const SLOT_EMOTES = {
  "Antenna":"🚩","Decal":"🎨","Goal Explosion":"💥","Wheels":"🛞",
  "Topper":"🎩","Body":"🚗","Trail":"✨","Engine Audio":"🔊","Rocket Boost":"🔥",
};


// ═══════════════════════════════════════════════════════════════
// 3. TRANSLATIONS
// ═══════════════════════════════════════════════════════════════
function t(key, fallback) {
  return state.strings[key] || fallback || key;
}

async function loadTranslations(lang) {
  try {
    state.strings = await api.translations(lang);
  } catch {
    console.warn("Could not load translations for", lang);
  }
  applyTranslations();
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    if (state.strings[key]) el.textContent = state.strings[key];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (state.strings[key]) el.placeholder = state.strings[key];
  });

  // Translate custom colors dynamically based on language
  const nameEl = document.getElementById("color-name-label");
  if (nameEl) {
    nameEl.textContent = state.customHex 
      ? (state.lang === "en" ? "Custom" : "Personalizada")
      : (state.lang === "en" ? "None" : "Nenhuma");
  }
  const flameNameEl = document.getElementById("flame-color-name-label");
  if (flameNameEl) {
    flameNameEl.textContent = state.customHexFlame 
      ? (state.lang === "en" ? "Custom" : "Personalizada")
      : (state.lang === "en" ? "None" : "Nenhuma");
  }

  // Update Credits screen dynamically
  const creditsVerEl = document.getElementById("credits-version");
  if (creditsVerEl) {
    const licFmt = t("credits_version_license", "v{version} — Under GNU GPL v3.0 License");
    creditsVerEl.textContent = licFmt.replace("{version}", "2.0.0");
  }

  const creditsBodyEl = document.getElementById("credits-body");
  if (creditsBodyEl) {
    const rawText = t("credits_main_text", "");
    if (rawText) {
      // Simple parse of Markdown bold and bullet lists
      const htmlText = rawText
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/• (.*?)(?:\n|$)/g, '<li>$1</li>')
        .split("\n\n")
        .map(p => {
          if (p.includes("<li>")) {
            return `<ul>${p}</ul>`;
          }
          return `<p>${p.replace(/\n/g, "<br>")}</p>`;
        })
        .join("");
      creditsBodyEl.innerHTML = htmlText;
    }
  }
}


// ═══════════════════════════════════════════════════════════════
// 4. TOAST
// ═══════════════════════════════════════════════════════════════
function toast(msg, type = "info", duration = 3000) {
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = `${icons[type] || ""} ${msg}`;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => {
    el.classList.add("fadeout");
    el.addEventListener("animationend", () => el.remove());
  }, duration);
}


// ═══════════════════════════════════════════════════════════════
// 5. CONSOLE LOG
// ═══════════════════════════════════════════════════════════════
function logLine(msg, type = "") {
  const el = document.getElementById("console-lines");
  const line = document.createElement("span");
  line.className = `console-line ${type}`;
  line.textContent = msg;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function logLines(lines = []) {
  lines.forEach(l => {
    const type = l.startsWith("❌") ? "error"
               : l.startsWith("✅") || l.startsWith("[OK]") ? "success"
               : "";
    logLine(l, type);
  });
}



// Sorted longest-first so longer color names match before shorter ones
const COLORS_SORTED = [
  "Titanium White","Forest Green","Burnt Sienna","Sky Blue",
  "Black","White","Grey","Gray","Crimson","Pink","Cobalt",
  "Saffron","Yellow","Lime","Orange","Purple","Unpainted",
].sort((a, b) => b.length - a.length);

const SEARCH_SHORTHANDS = {
  tw: "titanium white", bs: "burnt sienna", fg: "forest green",
  sb: "sky blue", bk: "black", cr: "crimson", cb: "cobalt",
  sf: "saffron", lm: "lime",
};

function stripColor(label) {
  for (const c of COLORS_SORTED) {
    if (label.toLowerCase().endsWith(" " + c.toLowerCase())) {
      return label.slice(0, -(c.length + 1)).trim();
    }
  }
  return label;
}

function getItemColor(label) {
  for (const c of COLORS_SORTED) {
    if (label.toLowerCase().endsWith(" " + c.toLowerCase())) return c;
  }
  return null;
}




// ═══════════════════════════════════════════════════════════════
// 7. PRODUCT INDEX — pre-compute search strings once on load
// ═══════════════════════════════════════════════════════════════

/** Augments every product with cached lower-case fields used during search. */
function buildProductIndex() {
  state.allProducts.forEach(p => {
    const label    = p.Label || "";
    const slot     = p.Slot  || "";
    const slotKey  = `slot_${slot.toLowerCase().replace(/ /g, "_")}`;
    p._labelL      = label.toLowerCase();
    p._nameL       = (p.Name || "").toLowerCase();
    p._slotL       = slot.toLowerCase();
    p._slotName    = t(slotKey, slot);
    p._baseLabel   = stripColor(label);
    p._slotColor   = SLOT_COLORS[slot] || "#7986cb";
    p._emote       = SLOT_EMOTES[slot] || "📦";
  });
}


const VIRTUAL_PAGE = 80;  // cards rendered per scroll batch

async function loadAllProducts() {
  const list = document.getElementById("orig-list");
  list.innerHTML = `<div class="loading-cards"><div class="spinner"></div><span>Carregando itens...</span></div>`;
  document.getElementById("target-list").innerHTML = list.innerHTML;
  try {
    const data = await api.products({ per_page: 99999, page: 0 });
    const favorites = state.config.favorites || [];
    state.allProducts = data.items.map(item => ({
      ...item,
      is_fav: favorites.includes(item.Name),
    }));
    buildProductIndex();
    buildSlotOptions("orig");
    buildSlotOptions("target");
    refreshList("orig");
    refreshList("target");
  } catch (err) {
    const msg = `<div class="loading-cards"><span style="color:var(--danger)">❌ ${err.message}</span></div>`;
    document.getElementById("orig-list").innerHTML = msg;
    document.getElementById("target-list").innerHTML = msg;
  }
}


/** Build slot <select> from cached products */
function buildSlotOptions(side) {
  const selId = side === "orig" ? "orig-slot-select" : "target-slot-select";
  const sel   = document.getElementById(selId);
  if (!sel) return;
  // Remove old change listeners by cloning
  const fresh = sel.cloneNode(false);
  sel.parentNode.replaceChild(fresh, sel);

  const slots = ["Todos", ...new Set(state.allProducts.map(p => p.Slot || "").filter(Boolean)).values()].sort(
    (a, b) => a === "Todos" ? -1 : b === "Todos" ? 1 : a.localeCompare(b)
  );

  slots.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s;
    const key = `slot_${s.toLowerCase().replace(/ /g, "_")}`;
    opt.textContent = s === "Todos" ? t("all", "Todos") : t(key, s);
    fresh.appendChild(opt);
  });

  fresh.addEventListener("change", () => {
    state[side].slot = fresh.value;
    refreshList(side);
    if (side === "orig") {
      refreshList("target");
    }
  });
}

/** Client-side filter using pre-indexed fields — O(n) with no string ops */
function clientFilter(products, search, slot, favOnly, side) {
  let result = products;

  let targetSlot = slot;
  if (side === "target") {
    if (state.orig.selected) {
      targetSlot = state.orig.selected.Slot;
    } else {
      targetSlot = state.orig.slot;
    }
  }

  const slotL = (targetSlot && targetSlot !== "Todos" && targetSlot !== t("all", "Todos"))
    ? targetSlot.toLowerCase() : null;
  if (slotL) {
    result = result.filter(p => p._slotL === slotL);
  }

  if (search) {
    const terms = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
    result = result.filter(p => {
      const labelL = p._labelL;
      const nameL  = p._nameL;
      return terms.every(term => {
        const expanded = SEARCH_SHORTHANDS[term];
        if (expanded && (labelL.includes(expanded) || nameL.includes(expanded))) return true;
        return labelL.includes(term) || nameL.includes(term);
      });
    });
  }

  if (favOnly) result = result.filter(p => p.is_fav);

  return result;
}

/** Build a single card using pre-indexed metadata — no string recomputation */
function buildCard(item, side) {
  const isFav = item.is_fav || false;

  const card = document.createElement("div");
  card.className = "item-card";
  card.dataset.name = item.Name;

  // Thumbnail (lazy — emote shown first, image replaces it on load)
  const thumb = document.createElement("div");
  thumb.className = "card-thumb";
  thumb.textContent = item._emote;

  const imgEl = new Image();
  imgEl.src = api.imageUrl(`${item._baseLabel}.png`);
  imgEl.onload = () => { thumb.textContent = ""; thumb.appendChild(imgEl); };

  // Info
  const info = document.createElement("div");
  info.className = "card-info";

  const badge = document.createElement("span");
  badge.className = "card-badge";
  badge.style.background = item._slotColor;
  badge.textContent = item._slotName;

  const name = document.createElement("div");
  name.className = "card-name";
  name.textContent = item.Label || item.Name || "";

  info.append(badge, name);

  const isOem = item.Name === "WHEEL_Star" || (item.Label === "OEM" && item.Slot === "Wheels");
  const isGizmo = item.Name === "Body_Spark";
  const isBlocked = isOem || isGizmo;

  if (isBlocked) {
    card.classList.add("disabled-oem");
    const blockedBadge = document.createElement("span");
    blockedBadge.className = "oem-disabled-badge";
    if (isGizmo) {
      blockedBadge.textContent = t("gizmo_badge_label", "⚠️ Indisponível");
      blockedBadge.title = t("gizmo_disabled_msg", "O Gizmo não pode ser feito swap por causar crash no jogo.");
    } else {
      blockedBadge.textContent = t("oem_badge_label", "⚠️ Indisponível");
      blockedBadge.title = t("oem_disabled_msg", "Este item não pode ser modificado devido a limitações técnicas do jogo (Startup.upk).");
    }
    card.append(thumb, info, blockedBadge);
  } else {
    // Fav button
    const favBtn = document.createElement("button");
    favBtn.className = `card-fav ${isFav ? "fav" : ""}`;
    favBtn.textContent = isFav ? "★" : "☆";
    favBtn.title = "Favorito";
    favBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        const res = await api.toggleFav(item.Name);
        item.is_fav = res.is_fav;
        const cached = state.allProducts.find(p => p.Name === item.Name);
        if (cached) cached.is_fav = res.is_fav;
        favBtn.textContent = res.is_fav ? "★" : "☆";
        favBtn.classList.toggle("fav", res.is_fav);
      } catch (err) {
        toast(err.message, "error");
      }
    });
    card.append(thumb, info, favBtn);
  }

  card.addEventListener("click", () => {
    if (isGizmo) {
      toast(t("gizmo_disabled_msg", "O Gizmo não pode ser feito swap por causar crash no jogo."), "error");
      return;
    }
    if (isOem) {
      toast(t("oem_disabled_msg", "Este item não pode ser modificado devido a limitações técnicas do jogo (Startup.upk)."), "error");
      return;
    }
    selectItem(side, item, card);
  });
  return card;
}

/**
 * Re-render a picker with virtualized output.
 * Renders the first VIRTUAL_PAGE cards immediately;
 * an IntersectionObserver sentinel triggers more batches on scroll.
 */
function refreshList(side) {
  const s      = state[side];
  const listId = side === "orig" ? "orig-list" : "target-list";
  const list   = document.getElementById(listId);

  // Disconnect any previous scroll sentinel
  if (s._observer) { s._observer.disconnect(); s._observer = null; }

  const items = clientFilter(state.allProducts, s.search, s.slot, s.favOnly, side);
  s._filtered = items;   // cache for sentinel batches
  s._rendered = 0;

  list.innerHTML = "";

  if (items.length === 0) {
    list.innerHTML = `<div class="loading-cards"><span style="font-size:24px;">😶</span><span>Nenhum item encontrado</span></div>`;
    return;
  }

  // Render first batch
  _renderBatch(side, list, items);

  // Re-apply selection highlight if item still visible
  if (s.selected) {
    const card = list.querySelector(`.item-card[data-name="${CSS.escape(s.selected.Name)}"]`);
    if (card) card.classList.add("selected");
  }
}

/** Appends the next VIRTUAL_PAGE cards and (re)attaches the sentinel. */
function _renderBatch(side, list, items) {
  const s     = state[side];
  const start = s._rendered;
  const end   = Math.min(start + VIRTUAL_PAGE, items.length);

  const frag = document.createDocumentFragment();
  for (let i = start; i < end; i++) {
    frag.appendChild(buildCard(items[i], side));
  }
  s._rendered = end;

  // Remove old sentinel before appending new cards
  const old = list.querySelector(".virt-sentinel");
  if (old) old.remove();

  list.appendChild(frag);

  // If there are more items, attach a scroll sentinel
  if (s._rendered < items.length) {
    const sentinel = document.createElement("div");
    sentinel.className = "virt-sentinel";
    sentinel.style.cssText = "height:1px;flex-shrink:0;";
    list.appendChild(sentinel);

    const obs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        obs.disconnect();
        s._observer = null;
        requestAnimationFrame(() => _renderBatch(side, list, items));
      }
    }, { root: list, rootMargin: "200px" });
    obs.observe(sentinel);
    s._observer = obs;
  }
}



function scheduleSearch(side) {
  const s = state[side];
  if (s.searchTimer) clearTimeout(s.searchTimer);
  // Short queries feel instant at 0ms; longer queries wait for typing to pause
  const delay = s.search.length < 2 ? 0 : 250;
  s.searchTimer = setTimeout(() => requestAnimationFrame(() => refreshList(side)), delay);
}


// Select an item in a picker
async function selectItem(side, item, cardEl) {
  // Deselect previous
  const listId = side === "orig" ? "orig-list" : "target-list";
  document.querySelectorAll(`#${listId} .item-card.selected`).forEach(c => c.classList.remove("selected"));
  cardEl.classList.add("selected");

  state[side].selected = item;

  const selLblId = side === "orig" ? "orig-sel-label" : "target-sel-label";
  document.getElementById(selLblId).textContent = stripColor(item.Label || item.Name || "");

  if (side === "orig") {
    // Limpeza inteligente se o slot do destino for incompatível
    if (state.target.selected && state.target.selected.Slot !== item.Slot) {
      state.target.selected = null;
      document.getElementById("target-sel-label").textContent =
        state.lang === "en" ? "None" : "Nenhuma";
      document.querySelectorAll("#target-list .item-card.selected").forEach(c => c.classList.remove("selected"));
    }
    // Re-filtra o destino para mostrar somente itens compatíveis com o item de origem
    refreshList("target");
  }

  updateSwapBtn();
}



// ═══════════════════════════════════════════════════════════════
// 8. PAINT / CUSTOM COLOR
// ═══════════════════════════════════════════════════════════════
function updateColorUI(hex) {
  state.customHex = hex;
  const swatch = document.getElementById("color-swatch");
  const nameEl = document.getElementById("color-name-label");
  const hexEl  = document.getElementById("color-hex-label");
  const clearBtn = document.getElementById("btn-clear-color");

  swatch.style.background = hex || "#555577";
  hexEl.textContent = hex || "#555577";

  if (hex) {
    nameEl.textContent = state.lang === "en" ? "Custom" : "Personalizada";
    clearBtn.style.display = "block";
  } else {
    nameEl.textContent = state.lang === "en" ? "None" : "Nenhuma";
    clearBtn.style.display = "none";
  }

  if (state.flameMagnet) {
    updateFlameColorUI(hex);
  }

  updateSwapBtn();
}

function updateFlameColorUI(hex) {
  state.customHexFlame = hex;
  const swatch = document.getElementById("flame-color-swatch");
  const nameEl = document.getElementById("flame-color-name-label");
  const hexEl  = document.getElementById("flame-color-hex-label");
  const clearBtn = document.getElementById("btn-clear-flame-color");

  if (swatch) swatch.style.background = hex || "#555577";
  if (hexEl) hexEl.textContent = hex || "#555577";

  if (hex) {
    if (nameEl) nameEl.textContent = state.lang === "en" ? "Custom" : "Personalizada";
    if (clearBtn) clearBtn.style.display = "block";
  } else {
    if (nameEl) nameEl.textContent = state.lang === "en" ? "None" : "Nenhuma";
    if (clearBtn) clearBtn.style.display = "none";
  }
}

function setFlameMagnet(active) {
  state.flameMagnet = active;
  const wrapper = document.getElementById("flame-controls-wrapper");
  const checkbox = document.getElementById("flame-magnet-checkbox");
  
  if (checkbox) checkbox.checked = active;
  if (wrapper) {
    if (active) {
      wrapper.classList.add("disabled");
      updateFlameColorUI(state.customHex);
    } else {
      wrapper.classList.remove("disabled");
    }
  }
}

function updatePaintSectionVisibility() {
  const paintSection = document.getElementById("paint-section");
  const recentSection = document.getElementById("recent-colors-section");
  
  const selected = state.target.selected || state.orig.selected;
  const isPaintable = selected && (selected.Slot === "Body" || selected.Slot === "Rocket Boost" || selected.Slot === "Wheels");
  
  if (paintSection) {
    paintSection.style.display = isPaintable ? "block" : "none";
  }
  if (recentSection) {
    recentSection.style.display = isPaintable ? "block" : "none";
  }
}

function updateFlameSectionVisibility() {
  const section = document.getElementById("boost-flame-section");
  const isBoost = state.target.selected && state.target.selected.Slot === "Rocket Boost";
  if (section) {
    section.style.display = isBoost ? "flex" : "none";
  }
  updatePaintSectionVisibility();
}

function addRecentColor(hex) {
  const rc = state.recentColors;
  const idx = rc.indexOf(hex);
  if (idx !== -1) rc.splice(idx, 1);
  rc.unshift(hex);
  if (rc.length > 8) rc.pop();
  state.recentColors = rc;
  renderRecentColors();
  // Persist
  state.config.recent_colors = rc;
  api.saveConfig({ recent_colors: rc }).catch(() => {});
}

function renderRecentColors() {
  const grid = document.getElementById("recent-colors-grid");
  grid.innerHTML = "";
  state.recentColors.forEach(hex => {
    const btn = document.createElement("div");
    btn.className = "recent-color-btn";
    btn.style.background = hex;
    btn.title = hex;
    btn.addEventListener("click", () => {
      document.getElementById("native-color-picker").value = hex;
      updateColorUI(hex);
    });
    grid.appendChild(btn);
  });
}


// ═══════════════════════════════════════════════════════════════
// 9. SWAP BUTTON
// ═══════════════════════════════════════════════════════════════
function updateSwapBtn() {
  const btn = document.getElementById("btn-swap");
  const canSwap = state.orig.selected && state.target.selected && state.config.pkg_dir;
  btn.disabled = !canSwap;
  updateFlameSectionVisibility();
}

async function doSwap() {
  if (await checkGameRunningAndWarn()) return;

  const orig   = state.orig.selected;
  const target = state.target.selected;
  const pkgDir = state.config.pkg_dir;

  if (!orig || !target || !pkgDir) {
    toast(t("folder_not_configured_title", "⚠️ Pasta não configurada"), "error");
    return;
  }

  const btn = document.getElementById("btn-swap");
  btn.disabled = true;
  btn.textContent = "⏳ Swappando...";

  logLine("─".repeat(40));
  logLine(`🔄 Swap: ${orig.Name} ← ${target.Name}`);

  try {
    const payload = {
      orig_name:     orig.Name,
      target_name:   target.Name,
      pkg_dir:       pkgDir,
      hex_color:     state.customHex || null,
      rgb_intensity: state.intensity,
      hex_color_flame: state.flameMagnet ? (state.customHex || null) : (state.customHexFlame || null),
    };
    const res = await api.swap(payload);
    logLines(res.logs || []);
    if (res.ok) {
      toast(t("combo_applied", "Swap realizado com sucesso!"), "success");
      // Add color to recent colors if a custom hex was selected and swap succeeded
      if (state.customHex) {
        addRecentColor(state.customHex);
      }
    } else {
      toast(res.error || "Erro desconhecido", "error");
    }
  } catch (err) {
    logLine(`❌ ${err.message}`, "error");
    const isGameRunningErr = err.message.includes("Rocket League") || err.message.includes("game files") || err.message.includes("arquivos do jogo");
    if (isGameRunningErr) {
      await showModal({
        title: t("modal_game_running_title", "⚠️ Rocket League Aberto"),
        body: t("modal_game_running_body", "Não é possível fazer swaps ou restaurações enquanto o Rocket League estiver aberto. Por favor, feche o jogo primeiro!"),
        confirm: t("btn_close_warning", "Entendi"),
        hideCancel: true,
      });
    } else {
      toast(err.message, "error");
    }
  } finally {
    btn.disabled = false;
    btn.textContent = t("btn_swap_action", "⚡ SWAP");
    updateSwapBtn();
  }
}


// ═══════════════════════════════════════════════════════════════
// 10. COMBOS
// ═══════════════════════════════════════════════════════════════
function loadCombos() {
  state.combos = state.config.combos || [];
  renderCombos();
}

function renderCombos(filter = "") {
  const list  = document.getElementById("combo-list");
  const empty = document.getElementById("combos-empty");
  const combos = state.combos.filter(c =>
    !filter || c.name.toLowerCase().includes(filter.toLowerCase())
  );

  list.innerHTML = "";
  if (combos.length === 0) {
    list.appendChild(empty);
    empty.style.display = "flex";
    return;
  }
  empty.style.display = "none";

  combos.forEach((combo, idx) => {
    const card = document.createElement("div");
    card.className = "combo-card";

    const info = document.createElement("div");
    info.className = "combo-card-info";

    const nameEl = document.createElement("div");
    nameEl.className = "combo-card-name";
    nameEl.textContent = combo.name;

    const slotsEl = document.createElement("div");
    slotsEl.className = "combo-card-slots";
    slotsEl.textContent = (combo.swaps || []).map(s => s.slot || "?").join(", ");

    info.append(nameEl, slotsEl);

    const actions = document.createElement("div");
    actions.className = "combo-card-actions";

    const applyBtn = document.createElement("button");
    applyBtn.className = "btn-success";
    applyBtn.textContent = t("btn_apply_preset", "▶ Aplicar");
    applyBtn.dataset.i18n = "btn_apply_preset";
    applyBtn.addEventListener("click", () => applyCombo(combo));

    const exportBtn = document.createElement("button");
    exportBtn.className = "btn-ghost";
    exportBtn.textContent = "📋";
    exportBtn.title = t("btn_export_code_title", "Exportar");
    exportBtn.addEventListener("click", () => exportCombo(combo));

    const delBtn = document.createElement("button");
    delBtn.className = "btn-ghost";
    delBtn.style.color = "var(--danger)";
    delBtn.textContent = "🗑";
    delBtn.title = "Remover";
    delBtn.addEventListener("click", () => {
      state.combos.splice(idx, 1);
      state.config.combos = state.combos;
      api.saveConfig({ combos: state.combos });
      renderCombos(filter);
    });

    actions.append(applyBtn, exportBtn, delBtn);
    card.append(info, actions);
    list.appendChild(card);
  });
}

async function saveCurrentCombo(name) {
  if (!state.orig.selected || !state.target.selected) {
    toast("Selecione itens nos dois painéis primeiro.", "error");
    return;
  }
  const swapEntry = {
    orig_name:   state.orig.selected.Name,
    target_name: state.target.selected.Name,
    slot:        state.orig.selected.Slot || "?",
    hex_color:   state.customHex,
    intensity:   state.intensity,
    hex_color_flame: state.flameMagnet ? null : state.customHexFlame,
    magnet:      state.flameMagnet,
  };
  state.combos.push({ name, swaps: [swapEntry] });
  state.config.combos = state.combos;
  await api.saveConfig({ combos: state.combos });
  renderCombos();
  toast(t("combo_saved", "Combo salvo!"), "success");
}

async function applyCombo(combo) {
  if (await checkGameRunningAndWarn()) return;

  const pkgDir = state.config.pkg_dir;
  if (!pkgDir) { toast(t("folder_not_configured_title", "⚠️ Pasta não configurada"), "error"); return; }

  for (const sw of (combo.swaps || [])) {
    logLine(`▶ Aplicando: ${sw.orig_name} ← ${sw.target_name}`);
    try {
      const res = await api.swap({
        orig_name:     sw.orig_name,
        target_name:   sw.target_name,
        pkg_dir:       pkgDir,
        hex_color:     sw.hex_color || null,
        rgb_intensity: sw.intensity || 1.0,
        hex_color_flame: sw.magnet ? (sw.hex_color || null) : (sw.hex_color_flame || null),
      });
      logLines(res.logs || []);
      if (!res.ok) toast(`❌ ${res.error}`, "error");
    } catch (err) {
      logLine(`❌ ${err.message}`, "error");
      const isGameRunningErr = err.message.includes("Rocket League") || err.message.includes("game files") || err.message.includes("arquivos do jogo");
      if (isGameRunningErr) {
        await showModal({
          title: t("modal_game_running_title", "⚠️ Rocket League Aberto"),
          body: t("modal_game_running_body", "Não é possível fazer swaps ou restaurações enquanto o Rocket League estiver aberto. Por favor, feche o jogo primeiro!"),
          confirm: t("btn_close_warning", "Entendi"),
          hideCancel: true,
        });
        return; // interrompe a aplicação de novos swaps
      } else {
        toast(err.message, "error");
      }
    }
  }
  toast(t("combo_applied", "Combo aplicado!"), "success");
}

async function exportCombo(combo) {
  try {
    const res = await api.encodeCombo(combo.swaps || []);
    if (!res.ok) throw new Error(res.error);
    await navigator.clipboard.writeText(res.code);
    toast(t("export_success", "📋 Código copiado!"), "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function importCombo() {
  const code = await showModal({
    title:     t("dialog_import_title", "Importar Combo"),
    body:      t("dialog_import_msg", "Cole o código do combo abaixo:"),
    showInput: true,
    inputType: "textarea",
    confirm:   "Decodificar",
  });
  if (!code) return;

  try {
    const res = await api.decodeCombo(code.trim());
    if (!res.ok) { toast(t("import_invalid_code", "❌ Código inválido"), "error"); return; }

    const name = await showModal({
      title:     t("dialog_import_name_title", "Nome do Combo"),
      body:      t("dialog_import_name_msg", "Dê um nome para o combo importado:"),
      showInput: true,
      inputType: "line",
      confirm:   "Salvar",
    });
    if (!name) return;

    state.combos.push({ name, swaps: res.swaps });
    state.config.combos = state.combos;
    await api.saveConfig({ combos: state.combos });
    renderCombos();
    toast(t("import_success", "✅ Combo importado!").replace("{name}", name), "success");
  } catch (err) {
    toast(err.message, "error");
  }
}


// ═══════════════════════════════════════════════════════════════
// 11. BACKUPS
// ═══════════════════════════════════════════════════════════════
async function loadBackups() {
  const pkgDir = state.config.pkg_dir;
  const list   = document.getElementById("backup-list");

  // Detach empty before wiping innerHTML so the reference survives.
  // CRITICAL: must re-append it at every exit path so getElementById
  // can find it again on the next call — otherwise it returns null.
  const empty = document.getElementById("backups-empty")
    || list.querySelector(".empty-state");
  if (empty && empty.parentNode) empty.parentNode.removeChild(empty);

  list.innerHTML = `<div class="loading-cards"><div class="spinner"></div></div>`;

  if (!pkgDir) {
    list.innerHTML = "";
    if (empty) { list.appendChild(empty); empty.style.display = "flex"; }
    return;
  }

  try {
    const { backups } = await api.backups(pkgDir);
    list.innerHTML = "";

    // Always re-append empty so the DOM reference is never lost
    if (empty) list.appendChild(empty);

    if (backups.length === 0) {
      if (empty) empty.style.display = "flex";
      return;
    }

    if (empty) empty.style.display = "none";

    backups.forEach(b => {
      const card = document.createElement("div");
      card.className = "backup-card";

      const name = document.createElement("span");
      name.className = "backup-card-name";
      const displayName = (b.display_name || b.name).replace(/\.upk$/i, "");
      name.textContent = displayName;

      const btn = document.createElement("button");
      btn.className = "btn-outline";
      btn.textContent = t("btn_restore_one", "Restaurar");
      btn.dataset.i18n = "btn_restore_one";

      if (b.exists_in_game === false) {
        btn.disabled = true;
        btn.classList.add("disabled");
        btn.title = t("backup_not_in_game_tooltip", "O arquivo modificado correspondente não está na pasta do jogo.");
        card.classList.add("disabled");
      } else if (b.is_readable === false) {
        btn.disabled = true;
        btn.classList.add("disabled");
        btn.title = t("backup_not_readable_tooltip", "O arquivo de backup está ilegível ou corrompido.");
        card.classList.add("disabled");
      } else {
        btn.addEventListener("click", async () => {
          if (await checkGameRunningAndWarn()) return;
          try {
            const res = await api.restore({ item_name: b.name, pkg_dir: pkgDir });
            logLines(res.logs || []);
            if (res.ok) {
              const dn = (b.display_name || b.name).replace(/\.upk$/i, "");
              toast(`✅ ${dn} restaurado!`, "success");
              loadBackups();
            }
          } catch (err) {
            const isGameRunningErr = err.message.includes("Rocket League") || err.message.includes("game files") || err.message.includes("arquivos do jogo");
            if (isGameRunningErr) {
              await showModal({
                title: t("modal_game_running_title", "⚠️ Rocket League Aberto"),
                body: t("modal_game_running_body", "Não é possível fazer swaps ou restaurações enquanto o Rocket League estiver aberto. Por favor, feche o jogo primeiro!"),
                confirm: t("btn_close_warning", "Entendi"),
                hideCancel: true,
              });
            } else {
              toast(err.message, "error");
            }
          }
        });
      }

      card.append(name, btn);
      list.appendChild(card);
    });
  } catch (err) {
    list.innerHTML = `<div class="loading-cards"><span style="color:var(--danger)">❌ ${err.message}</span></div>`;
    // Re-append empty even in error path so it stays in the DOM
    if (empty) list.appendChild(empty);
  }
}

async function restoreAll() {
  if (await checkGameRunningAndWarn()) return;

  const pkgDir = state.config.pkg_dir;
  if (!pkgDir) { toast(t("folder_not_configured_title", "⚠️ Pasta não configurada"), "error"); return; }

  try {
    const res = await api.restoreAll({ pkg_dir: pkgDir });
    logLines(res.logs || []);
    if (res.ok) {
      toast(t("restore_completed", "Todos os backups restaurados!"), "success");
      loadBackups();
    } else {
      toast(res.error || "Erro", "error");
    }
  } catch (err) {
    const isGameRunningErr = err.message.includes("Rocket League") || err.message.includes("game files") || err.message.includes("arquivos do jogo");
    if (isGameRunningErr) {
      await showModal({
        title: t("modal_game_running_title", "⚠️ Rocket League Aberto"),
        body: t("modal_game_running_body", "Não é possível fazer swaps ou restaurações enquanto o Rocket League estiver aberto. Por favor, feche o jogo primeiro!"),
        confirm: t("btn_close_warning", "Entendi"),
        hideCancel: true,
      });
    } else {
      toast(err.message, "error");
    }
  }
}


// ═══════════════════════════════════════════════════════════════
// 12. MODAL HELPER
// ═══════════════════════════════════════════════════════════════
function showModal({ title, body, showInput = false, inputType = "textarea", confirm = "Confirmar", hideCancel = false }) {
  return new Promise((resolve) => {
    const overlay = document.getElementById("modal-overlay");
    const wrap    = document.getElementById("modal-input-wrap");
    const cancelBtn = document.getElementById("modal-cancel");

    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-body").textContent  = body;
    document.getElementById("modal-confirm").textContent = confirm;

    if (cancelBtn) {
      cancelBtn.style.display = hideCancel ? "none" : "block";
    }

    if (showInput) {
      if (inputType === "textarea") {
        wrap.innerHTML = `<textarea id="modal-input" class="modal-input" rows="3" placeholder="..."></textarea>`;
      } else {
        wrap.innerHTML = `<input type="text" id="modal-input" class="modal-input-line" placeholder="..." />`;
      }
      wrap.style.display = "block";
    } else {
      wrap.style.display = "none";
    }

    overlay.classList.remove("hidden");
    setTimeout(() => document.getElementById("modal-input")?.focus(), 50);

    const cleanup = () => overlay.classList.add("hidden");

    document.getElementById("modal-confirm").onclick = () => {
      const val = document.getElementById("modal-input")?.value?.trim() || null;
      cleanup();
      resolve(showInput ? val : true);
    };
    document.getElementById("modal-cancel").onclick = () => {
      cleanup();
      resolve(null);
    };
  });
}

async function checkGameRunningAndWarn() {
  try {
    const { running } = await api.gameRunning();
    if (running) {
      await showModal({
        title: t("modal_game_running_title", "⚠️ Rocket League Aberto"),
        body: t("modal_game_running_body", "Não é possível fazer swaps ou restaurações enquanto o Rocket League estiver aberto. Por favor, feche o jogo primeiro!"),
        confirm: t("btn_close_warning", "Entendi"),
        hideCancel: true,
      });
      return true;
    }
  } catch (err) {
    console.error("Falha ao checar se jogo está aberto:", err);
  }
  return false;
}


// ═══════════════════════════════════════════════════════════════
// 13. TABS
// ═══════════════════════════════════════════════════════════════
function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach(p => {
    p.classList.toggle("active", p.id === `tab-${tab}`);
  });
  if (tab === "backups") loadBackups();
  if (tab === "combos") renderCombos();
}


// ═══════════════════════════════════════════════════════════════
// 14. GAME STATUS POLLING
// ═══════════════════════════════════════════════════════════════
function startGameStatusPolling() {
  const el   = document.getElementById("game-status");
  const dot  = el.querySelector(".status-dot");
  const text = el.querySelector(".status-text");

  async function poll() {
    try {
      const { running } = await api.gameRunning();
      el.classList.toggle("online", running);
      text.textContent = running ? "RL ✓" : "RL";
    } catch {}
  }

  poll();
  setInterval(poll, 10000);
}


// ═══════════════════════════════════════════════════════════════
// 15. FOLDER / AUTO-DETECT / PLATFORM
// ═══════════════════════════════════════════════════════════════

/** Return the per-platform pkg_dir key stored in config. */
function pkgDirKey(platform) {
  return platform === "steam" ? "pkg_dir_steam" : "pkg_dir_epic";
}

/**
 * Switch the active platform and update all state/UI accordingly.
 * Each platform has its own saved folder and its own backup dir.
 */
async function setPlatform(platform) {
  if (state.config.active_platform === platform) return;

  state.config.active_platform = platform;

  // Resolve the folder for the new platform
  const dirKey = pkgDirKey(platform);
  const dir    = state.config[dirKey] || "";
  state.config.pkg_dir = dir;

  // Persist both active_platform and pkg_dir
  await api.saveConfig({ active_platform: platform, pkg_dir: dir });

  // Update folder display
  const folderInput = document.getElementById("folder-display");
  folderInput.value = dir || "";
  if (!dir) {
    folderInput.placeholder = t(
      "platform_folder_missing",
      "Nenhuma pasta configurada. Selecione ou auto-detecte."
    ).replace("{platform}", platform === "steam" ? "Steam" : "Epic");
  }

  // Update toggle button states
  document.getElementById("btn-platform-epic").classList.toggle("active", platform === "epic");
  document.getElementById("btn-platform-steam").classList.toggle("active", platform === "steam");

  // Notify user
  const label = platform === "steam" ? "Steam" : "Epic";
  toast(t("platform_switch_toast", "Plataforma: {platform}").replace("{platform}", label), "success");

  updateSwapBtn();

  // Refresh backups if that tab is visible
  if (state.activeTab === "backups") loadBackups();
}

function setFolder(path) {
  state.config.pkg_dir = path;
  document.getElementById("folder-display").value = path;

  // Persist per-platform dir AND the active pkg_dir
  const dirKey = pkgDirKey(state.config.active_platform || "epic");
  state.config[dirKey] = path;
  api.saveConfig({ pkg_dir: path, [dirKey]: path });
  updateSwapBtn();
}


async function doAutodetect() {
  const platform = state.config.active_platform || "epic";
  const btn      = document.getElementById("btn-autodetect");
  btn.disabled   = true;
  try {
    const res = await api.autodetect(platform);
    if (res.ok && res.path) {
      setFolder(res.path);
      toast(t("autodetect_success", "📁 Pasta detectada!"), "success");
    } else {
      toast(t("autodetect_failed", "❌ Não foi possível auto-detectar."), "error");
    }
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}


// ═══════════════════════════════════════════════════════════════
// 16. SAVE COMBO MODAL
// ═══════════════════════════════════════════════════════════════
function showSaveComboModal() {
  const overlay  = document.getElementById("save-combo-modal");
  const nameInput = document.getElementById("save-combo-name");
  overlay.classList.remove("hidden");
  setTimeout(() => nameInput.focus(), 50);

  document.getElementById("save-combo-confirm").onclick = async () => {
    const name = nameInput.value.trim();
    if (!name) { toast("Digite um nome!", "error"); return; }
    overlay.classList.add("hidden");
    nameInput.value = "";
    await saveCurrentCombo(name);
  };
  document.getElementById("save-combo-cancel").onclick = () => {
    overlay.classList.add("hidden");
    nameInput.value = "";
  };
}


// ═══════════════════════════════════════════════════════════════
// 17. INIT
// ═══════════════════════════════════════════════════════════════
async function init() {
  // Load config
  try {
    state.config = await api.config();
  } catch {
    state.config = {};
  }

  // Language
  state.lang = state.config.language || "pt-BR";
  await loadTranslations(state.lang);

  // Paint colors
  try {
    state.paintColors = await api.paintColors();
  } catch {}

  // Folder — restore active platform first
  const savedPlatform = state.config.active_platform || "epic";
  state.config.active_platform = savedPlatform;

  // Resolve pkg_dir from the per-platform key if available
  const savedDirKey = pkgDirKey(savedPlatform);
  if (!state.config[savedDirKey] && state.config.pkg_dir) {
    // Migrate legacy single pkg_dir to the platform-specific key
    state.config[savedDirKey] = state.config.pkg_dir;
  }
  if (state.config[savedDirKey]) {
    state.config.pkg_dir = state.config[savedDirKey];
  }

  if (state.config.pkg_dir) {
    document.getElementById("folder-display").value = state.config.pkg_dir;
  }

  // Reflect active platform in toggle buttons
  document.getElementById("btn-platform-epic").classList.toggle("active", savedPlatform === "epic");
  document.getElementById("btn-platform-steam").classList.toggle("active", savedPlatform === "steam");

  // Recent colors
  state.recentColors = state.config.recent_colors && state.config.recent_colors.length
    ? state.config.recent_colors
    : [...DEFAULT_FACTORY_COLORS];
  renderRecentColors();

  // Combos
  loadCombos();

  // Load ALL products (client-side filtering from here on)
  await loadAllProducts();

  // Restore color UI
  updateColorUI(null);
  updateFlameSectionVisibility();

  // Window controls
  document.getElementById("btn-minimize").addEventListener("click", () => window.electronAPI?.minimize());
  document.getElementById("btn-maximize").addEventListener("click", () => window.electronAPI?.maximize());
  document.getElementById("btn-close").addEventListener("click",    () => window.electronAPI?.close());

  // Folder browse
  document.getElementById("btn-browse").addEventListener("click", async () => {
    const path = await window.electronAPI?.openFolderDialog();
    if (path) setFolder(path);
  });

  // Auto-detect
  document.getElementById("btn-autodetect").addEventListener("click", doAutodetect);

  // Platform toggle
  document.getElementById("btn-platform-epic").addEventListener("click",  () => setPlatform("epic"));
  document.getElementById("btn-platform-steam").addEventListener("click", () => setPlatform("steam"));

  // Update items
  document.getElementById("btn-update-items").addEventListener("click", async () => {
    const btn = document.getElementById("btn-update-items");
    btn.disabled = true;
    try {
      await api.fetchProducts();
      await loadAllProducts();
      toast("✅ Itens atualizados!", "success");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      btn.disabled = false;
    }
  });

  // Language toggle
  document.getElementById("btn-lang-pt").addEventListener("click", async () => {
    await switchLang("pt-BR");
    document.getElementById("btn-lang-pt").classList.add("active");
    document.getElementById("btn-lang-en").classList.remove("active");
  });
  document.getElementById("btn-lang-en").addEventListener("click", async () => {
    await switchLang("en");
    document.getElementById("btn-lang-en").classList.add("active");
    document.getElementById("btn-lang-pt").classList.remove("active");
  });

  // Apply initial lang button state
  if (state.lang === "en") {
    document.getElementById("btn-lang-en").classList.add("active");
    document.getElementById("btn-lang-pt").classList.remove("active");
  }

  // Tab bar
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  // Picker: search
  document.getElementById("orig-search").addEventListener("input", (e) => {
    state.orig.search = e.target.value;
    scheduleSearch("orig");
  });
  document.getElementById("target-search").addEventListener("input", (e) => {
    state.target.search = e.target.value;
    scheduleSearch("target");
  });

  // Picker: fav only
  document.getElementById("orig-fav-only").addEventListener("change", (e) => {
    state.orig.favOnly = e.target.checked;
    refreshList("orig");
  });
  document.getElementById("target-fav-only").addEventListener("change", (e) => {
    state.target.favOnly = e.target.checked;
    refreshList("target");
  });

  // Color picker
  const nativePicker = document.getElementById("native-color-picker");
  nativePicker.addEventListener("input", (e) => updateColorUI(e.target.value));

  document.getElementById("btn-select-color").addEventListener("click", () => {
    nativePicker.value = state.customHex || "#ff0000";
    nativePicker.click();
  });
  document.getElementById("color-swatch").addEventListener("click", () => {
    if (state.customHex) {
      nativePicker.value = state.customHex;
      nativePicker.click();
    }
  });
  document.getElementById("btn-clear-color").addEventListener("click", () => updateColorUI(null));

  // Flame color picker and magnet controls
  const flameMagnetCheckbox = document.getElementById("flame-magnet-checkbox");
  if (flameMagnetCheckbox) {
    flameMagnetCheckbox.addEventListener("change", (e) => {
      setFlameMagnet(e.target.checked);
    });
  }

  const nativeFlamePicker = document.getElementById("native-flame-color-picker");
  if (nativeFlamePicker) {
    nativeFlamePicker.addEventListener("input", (e) => {
      if (!state.flameMagnet) {
        updateFlameColorUI(e.target.value);
      }
    });
  }

  const btnSelectFlameColor = document.getElementById("btn-select-flame-color");
  if (btnSelectFlameColor) {
    btnSelectFlameColor.addEventListener("click", () => {
      if (!state.flameMagnet && nativeFlamePicker) {
        nativeFlamePicker.value = state.customHexFlame || "#ff0000";
        nativeFlamePicker.click();
      }
    });
  }

  const flameColorSwatch = document.getElementById("flame-color-swatch");
  if (flameColorSwatch) {
    flameColorSwatch.addEventListener("click", () => {
      if (!state.flameMagnet && state.customHexFlame && nativeFlamePicker) {
        nativeFlamePicker.value = state.customHexFlame;
        nativeFlamePicker.click();
      }
    });
  }

  const btnClearFlameColor = document.getElementById("btn-clear-flame-color");
  if (btnClearFlameColor) {
    btnClearFlameColor.addEventListener("click", () => {
      if (!state.flameMagnet) {
        updateFlameColorUI(null);
      }
    });
  }

  // Restore initial flame magnet UI state
  setFlameMagnet(true);

  // Swap btn
  document.getElementById("btn-swap").addEventListener("click", doSwap);

  // Save combo
  document.getElementById("btn-save-combo").addEventListener("click", showSaveComboModal);

  // Combo tab: import
  document.getElementById("btn-import-code").addEventListener("click", importCombo);

  // Combo search
  document.getElementById("combo-search").addEventListener("input", (e) => {
    renderCombos(e.target.value);
  });

  // Backups
  document.getElementById("btn-restore-all").addEventListener("click", restoreAll);
  document.getElementById("btn-refresh-backups").addEventListener("click", loadBackups);

  // Console clear
  document.getElementById("btn-clear-console").addEventListener("click", () => {
    document.getElementById("console-lines").innerHTML =
      `<span class="console-line muted" data-i18n="console_ready">${t("console_ready", "Pronto.")}</span>`;
  });

  // Credits changelog button
  document.getElementById("btn-changelog").addEventListener("click", () => {
    window.electronAPI?.openExternal("https://github.com/TheDroidBR/RL-Forge/blob/main/CHANGELOG.md");
  });

  // Discord button
  document.getElementById("btn-discord").addEventListener("click", () => {
    window.electronAPI?.openExternal("https://discord.gg/hR8nQZhDgf");
  });

  // Game status polling
  startGameStatusPolling();
}

async function switchLang(lang) {
  state.lang = lang;
  state.config.language = lang;
  api.saveConfig({ language: lang });
  await loadTranslations(lang);
  // Re-render slots and lists with new translations
  buildSlotOptions("orig");
  buildSlotOptions("target");
  refreshList("orig");
  refreshList("target");
  renderCombos();
  if (state.activeTab === "backups") {
    loadBackups();
  }
}

// ── Boot ─────────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", init);
