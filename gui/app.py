"""
RL Forge GUI — CustomTkinter dark mode interface.
"""

import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import sys
import os
from PIL import Image
import webbrowser
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

APP_VERSION = "1.0.0"

from core.swapper import (
    load_config, save_config, load_products, fetch_products_csv,
    filter_products, get_slots, swap, restore_item, restore_all, list_backups,
    get_color_variants, get_item_color, get_base_label, RL_PAINT_COLORS
)
from core.updater import start_update_thread
from core.utils import get_base_dir, get_data_dir

# Cache for item thumbnails to prevent disk thrashing
IMAGE_CACHE = {}
IMAGE_DIR = get_data_dir() / "data" / "images"


# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG        = "#0f1117"
SURFACE   = "#1a1d27"
CARD      = "#21263a"
ACCENT    = "#00d4ff"
ACCENT2   = "#0099cc"
SUCCESS   = "#00e676"
WARNING   = "#ffab40"
DANGER    = "#ff5252"
TEXT      = "#e8eaf6"
MUTED     = "#7986cb"
BORDER    = "#2a2f45"


class ItemCard(ctk.CTkFrame):
    """Clickable item card with image, info, and favorite button."""
    def __init__(self, master, item: dict, on_select, on_fav_toggle=None, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=8, border_width=1,
                         border_color=BORDER, **kwargs)
        self.item = item
        self.on_select = on_select
        self.on_fav_toggle = on_fav_toggle
        self.selected = False
        self.is_fav = False

        # Thumbnail Image
        self.img_label = ctk.CTkLabel(self, text="", width=48, height=48, corner_radius=6, fg_color="#333344")
        self.img_label.pack(side="left", padx=(8, 4), pady=8)

        # Info Frame
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=8, padx=4)

        self.slot_badge = ctk.CTkLabel(info_frame, text=" ? ", fg_color=MUTED,
                                       text_color="white", corner_radius=4,
                                       font=ctk.CTkFont("Consolas", 10, "bold"))
        self.slot_badge.pack(anchor="w", pady=(0, 4))

        self.name_label = ctk.CTkLabel(info_frame, text="",
                                        fg_color="transparent", text_color=TEXT,
                                        font=ctk.CTkFont("Segoe UI", 12),
                                        anchor="w", wraplength=180)
        self.name_label.pack(anchor="w")

        # Favorite Button
        self.fav_btn = ctk.CTkButton(self, text="☆", width=30, height=30, fg_color="transparent",
                                      hover_color=BORDER, text_color=MUTED,
                                      font=ctk.CTkFont("Segoe UI", 18),
                                      command=self._toggle_fav)
        self.fav_btn.pack(side="right", padx=8)

        # Bindings for selection
        for widget in (self, self.img_label, info_frame, self.slot_badge, self.name_label):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._hover_on)
            widget.bind("<Leave>", self._hover_off)

    def update_data(self, item: dict, on_select, is_fav: bool, on_fav_toggle):
        """Update existing card with new item data (for object pooling)."""
        self.item = item
        self.on_select = on_select
        self.on_fav_toggle = on_fav_toggle
        self.is_fav = is_fav
        
        # Text and Badges
        slot = item.get("Slot", "?")[:3].upper()
        slot_colors = {"BOO": "#00d4ff", "DEC": "#ab47bc", "GOA": "#ff7043",
                       "WHE": "#66bb6a", "ANT": "#ffa726", "TOP": "#ef5350",
                       "BOD": "#fbc02d", "TRA": "#26a69a", "ENG": "#8d6e63"}
        slot_color = slot_colors.get(slot, MUTED)
        
        self.slot_badge.configure(text=f" {slot} ", fg_color=slot_color)
        
        name_str = item.get("Label", item.get("Name", ""))
        self.name_label.configure(text=name_str)
        
        # Star icon
        if self.is_fav:
            self.fav_btn.configure(text="★", text_color=SUCCESS)
        else:
            self.fav_btn.configure(text="☆", text_color=MUTED)
        
        # Load Image if exists
        base = get_base_label(name_str)
        img_name = f"{base}.png"
        img_path = os.path.join(IMAGE_DIR, img_name)
        
        # Use cache
        if img_name in IMAGE_CACHE:
            self.img_label.configure(image=IMAGE_CACHE[img_name], text="")
        elif os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(48, 48))
                IMAGE_CACHE[img_name] = ctk_img
                self.img_label.configure(image=ctk_img, text="")
            except Exception:
                self.img_label.configure(image=None, text=slot[0], text_color=slot_color, font=ctk.CTkFont("Segoe UI", 24, "bold"))
        else:
            self.img_label.configure(image=None, text=slot[0], text_color=slot_color, font=ctk.CTkFont("Segoe UI", 24, "bold"))

        self.set_selected(False)

    def _toggle_fav(self):
        self.is_fav = not self.is_fav
        if self.is_fav:
            self.fav_btn.configure(text="★", text_color=SUCCESS)
        else:
            self.fav_btn.configure(text="☆", text_color=MUTED)
        if self.on_fav_toggle:
            self.on_fav_toggle(self.item, self.is_fav)

    def _click(self, _):
        self.on_select(self.item, self)

    def _hover_on(self, _):
        if not self.selected:
            self.configure(border_color=ACCENT2)

    def _hover_off(self, _):
        if not self.selected:
            self.configure(border_color=BORDER)

    def set_selected(self, val: bool):
        self.selected = val
        if val:
            self.configure(border_color=ACCENT, fg_color="#1e2a3a")
        else:
            self.configure(border_color=BORDER, fg_color=CARD)


class ColorVariantBar(ctk.CTkFrame):
    """Horizontal row of paint color dots for variant selection."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=8, **kwargs)
        self._buttons: list[ctk.CTkButton] = []
        self._active: ctk.CTkButton | None = None

    def load(self, variants: list[dict], current_item: dict, on_select):
        for w in self.winfo_children():
            w.destroy()
        self._buttons.clear()
        self._active = None

        if len(variants) <= 1:
            self.pack_forget()
            return

        ctk.CTkLabel(self, text="Cor:", text_color=MUTED,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left", padx=(10, 6), pady=6)

        for v in variants:
            color_name = get_item_color(v.get("Label", ""))
            hex_color  = RL_PAINT_COLORS.get(color_name, "#555577") if color_name else "#aaaaaa"
            tip_text   = color_name if color_name else "Sem pintura"

            is_current = v["Name"] == current_item["Name"]

            btn = ctk.CTkButton(
                self, text="", width=22, height=22,
                corner_radius=11,
                fg_color=hex_color,
                hover_color=hex_color,
                border_width=2 if is_current else 0,
                border_color=ACCENT if is_current else hex_color,
                command=lambda item=v: on_select(item)
            )
            btn.pack(side="left", padx=3, pady=6)
            btn._variant = v
            if is_current:
                self._active = btn
            self._buttons.append(btn)

        self.pack(fill="x", padx=12, pady=(0, 6))

    def mark_active(self, item: dict):
        for btn in self._buttons:
            is_active = btn._variant["Name"] == item["Name"]
            btn.configure(border_width=2 if is_active else 0)


class ItemPicker(ctk.CTkFrame):
    """Left or right item picker panel with search + slot filter + color bar."""
    def __init__(self, master, title: str, label_color: str, **kwargs):
        super().__init__(master, fg_color=SURFACE, corner_radius=12, **kwargs)
        self.products_all = []
        self.selected_item = None
        self.selected_card = None
        self.on_change_cb = None
        self.on_fav_change_cb = None
        self.favorites: list[str] = []
        self._card_pool: list[ItemCard] = []

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=label_color).pack(side="left")
        self.sel_label = ctk.CTkLabel(header, text="Nenhum selecionado",
                                       font=ctk.CTkFont("Segoe UI", 11),
                                       text_color=MUTED)
        self.sel_label.pack(side="left", padx=8)

        # Search
        self._search_after_id = None
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._schedule_refresh())
        search = ctk.CTkEntry(self, textvariable=self.search_var,
                              placeholder_text="🔍  Pesquisar item...",
                              fg_color=CARD, border_color=BORDER,
                              text_color=TEXT, font=ctk.CTkFont("Segoe UI", 12),
                              corner_radius=8, height=36)
        search.pack(fill="x", padx=12, pady=(0, 6))

        # Slot filter
        self.slot_var = ctk.StringVar(value="Todos")
        self.slot_menu = ctk.CTkOptionMenu(self, variable=self.slot_var,
                                            values=["Todos"],
                                            fg_color=CARD, button_color=ACCENT2,
                                            button_hover_color=ACCENT,
                                            text_color=TEXT, corner_radius=8,
                                            command=lambda _: self._refresh())
        self.slot_menu.pack(fill="x", padx=12, pady=(0, 6))

        # Color variant bar (hidden until an item with variants is selected)
        self.color_bar = ColorVariantBar(self)

        # Scrollable card list
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                              scrollbar_button_color=BORDER)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def load(self, products: list[dict]):
        self.products_all = products
        slots = get_slots(products)
        self.slot_menu.configure(values=slots)
        self._refresh()

    def _schedule_refresh(self):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self._refresh)

    def _refresh(self):
        self.selected_card = None

        filtered = filter_products(
            self.products_all,
            self.search_var.get(),
            self.slot_var.get()
        )
        
        # Sort favorites to top
        filtered.sort(key=lambda p: p["Name"] not in self.favorites)
        filtered = filtered[:100]  # cap for performance

        # Ensure we have enough cards in the pool
        while len(self._card_pool) < len(filtered):
            card = ItemCard(self.scroll, {}, self._on_select, self._on_fav_toggle)
            self._card_pool.append(card)

        # Update and pack active cards
        for i, item in enumerate(filtered):
            card = self._card_pool[i]
            is_fav = item["Name"] in self.favorites
            card.update_data(item, self._on_select, is_fav, self._on_fav_toggle)
            
            if self.selected_item and self.selected_item["Name"] == item["Name"]:
                card.set_selected(True)
                self.selected_card = card
                
            card.pack(fill="x", pady=3)

        # Hide unused cards
        for i in range(len(filtered), len(self._card_pool)):
            self._card_pool[i].pack_forget()

    def _on_fav_toggle(self, item: dict, is_fav: bool):
        name = item["Name"]
        if is_fav and name not in self.favorites:
            self.favorites.append(name)
        elif not is_fav and name in self.favorites:
            self.favorites.remove(name)
            
        if self.on_fav_change_cb:
            self.on_fav_change_cb(self.favorites)
        # We don't trigger a full refresh here to avoid interrupting the user's scroll position


    def select_item(self, item: dict):
        """Programmatically select an item."""
        if self.selected_card:
            self.selected_card.set_selected(False)
        self.selected_card = None
        self.selected_item = item

        # If its card is visible, highlight it
        for card in self._card_pool:
            if card.winfo_ismapped() and card.item.get("Name") == item.get("Name"):
                card.set_selected(True)
                self.selected_card = card
                break

        base = get_base_label(item.get("Label", item.get("Name", "")))
        color_name = get_item_color(item.get("Label", ""))
        
        if color_name:
            self.sel_label.configure(text=f"{base} · {color_name}", text_color=ACCENT)
        else:
            self.sel_label.configure(text=base, text_color=ACCENT)

        variants = get_color_variants(self.products_all, item)
        self.color_bar.load(variants, item, self._on_color_select)

    def _on_select(self, item: dict, card: ItemCard):
        self.select_item(item)
        if self.on_change_cb:
            self.on_change_cb()

    def _on_color_select(self, item: dict):
        """Called when user clicks a color dot."""
        self.select_item(item)
        if self.on_change_cb:
            self.on_change_cb()


class BackupsPanel(ctk.CTkFrame):
    """Panel showing active swaps with restore buttons."""
    def __init__(self, master, get_pkg_dir, log_cb, **kwargs):
        super().__init__(master, fg_color=SURFACE, corner_radius=12, **kwargs)
        self.get_pkg_dir = get_pkg_dir
        self.log_cb = log_cb

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(header, text="💾  Backups Ativos",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkButton(header, text="↺ Restaurar Tudo", width=140, height=32,
                      fg_color=DANGER, hover_color="#cc3333",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._restore_all).pack(side="right")
        ctk.CTkButton(header, text="🔄 Atualizar", width=110, height=32,
                      fg_color=CARD, hover_color=BORDER,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self.refresh).pack(side="right", padx=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.empty_label = ctk.CTkLabel(self.scroll, text="Nenhum swap ativo.\nFaça um swap na aba principal!",
                                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 13))

    def refresh(self):
        self.empty_label.pack_forget()
        for w in self.scroll.winfo_children():
            if w != self.empty_label:
                w.destroy()
        pkg = self.get_pkg_dir()
        if not pkg:
            return
        backups = list_backups(pkg)
        if not backups:
            self.empty_label.pack(pady=40)
            return
        for b in backups:
            row = ctk.CTkFrame(self.scroll, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=b["name"], text_color=TEXT,
                          font=ctk.CTkFont("Segoe UI", 12)).pack(side="left", padx=12, pady=10)
            ctk.CTkButton(row, text="Restaurar", width=90, height=28,
                           fg_color=WARNING, hover_color="#cc8800", text_color="black",
                           font=ctk.CTkFont("Segoe UI", 11, "bold"),
                           command=lambda name=b["name"]: self._restore_one(name)
                           ).pack(side="right", padx=10)

    def _restore_one(self, name: str):
        pkg = self.get_pkg_dir()
        if not pkg:
            return
        try:
            restore_item(name, pkg, self.log_cb)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _restore_all(self):
        pkg = self.get_pkg_dir()
        if not pkg:
            return
        if not messagebox.askyesno("Restaurar Tudo",
                                    "Restaurar todos os itens originais?"):
            return
        restore_all(pkg, self.log_cb)
        self.refresh()


class CombosPanel(ctk.CTkFrame):
    """Panel showing saved combos (presets) of items."""
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, fg_color=SURFACE, corner_radius=12, **kwargs)
        self.app = app_ref

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(header, text="📦  Meus Combos Salvos",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=TEXT).pack(side="left")
                     
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        
        self.empty_label = ctk.CTkLabel(self.scroll, text="Nenhum combo salvo.\nClique em 'Salvar Combo' na aba Swap!",
                                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 13))

    def refresh(self):
        self.empty_label.pack_forget()
        for w in self.scroll.winfo_children():
            if w != self.empty_label:
                w.destroy()
            
        presets = self.app.cfg.get("presets", {})
        if not presets:
            self.empty_label.pack(pady=40)
            return
            
        for name, swaps in presets.items():
            card = ctk.CTkFrame(self.scroll, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", pady=6)
            
            # Header
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(header, text=name, text_color=ACCENT, font=ctk.CTkFont("Segoe UI", 14, "bold")).pack(side="left")
            
            ctk.CTkButton(header, text="🗑️", width=30, height=30, fg_color="transparent", hover_color=DANGER,
                          command=lambda n=name: self._delete(n)).pack(side="right")
                          
            ctk.CTkButton(header, text="▶ Aplicar Tudo", height=30, fg_color=SUCCESS, hover_color="#00c853", text_color="black",
                          font=ctk.CTkFont("Segoe UI", 12, "bold"),
                          command=lambda s=swaps: self._apply_combo(s)).pack(side="right", padx=8)
                          
            # List swaps
            for s in swaps:
                lbl = f"• {s.get('slot', '?')}: {get_base_label(s['orig_name'])} → {get_base_label(s['target_name'])}"
                ctk.CTkLabel(card, text=lbl, text_color=TEXT, font=ctk.CTkFont("Segoe UI", 12)).pack(anchor="w", padx=12, pady=(0, 4))
            
            # spacing bottom
            ctk.CTkFrame(card, height=4, fg_color="transparent").pack()

    def _delete(self, name: str):
        if messagebox.askyesno("Excluir", f"Excluir o combo '{name}'?"):
            del self.app.cfg["presets"][name]
            save_config(self.app.cfg)
            self.refresh()

    def _apply_combo(self, swaps: list):
        pkg = self.app._get_pkg_dir()
        if not pkg:
            messagebox.showwarning("Sem pasta", "Configure a pasta primeiro.")
            return
            
        # We need to run them sequentially
        def run():
            success = 0
            for i, s in enumerate(swaps):
                orig = next((p for p in self.app.products if p["Name"] == s["orig_name"]), None)
                target = next((p for p in self.app.products if p["Name"] == s["target_name"]), None)
                if not orig or not target:
                    self.app._log(f"⚠️ Item {s['orig_name']} ou {s['target_name']} não encontrado.")
                    continue
                
                self.app.after(0, lambda p=int((i/len(swaps))*100): self.app.progress_bar.set(p/100))
                try:
                    self.app._log(f"[{i+1}/{len(swaps)}] Swapping {orig['Label']} -> {target['Label']}...")
                    swap(orig, target, pkg, None)
                    success += 1
                except Exception as e:
                    self.app._log(f"❌ Erro no {orig['Label']}: {e}")
            
            self.app._log(f"✅ Combo aplicado: {success}/{len(swaps)} itens trocados.")
            self.app.after(0, lambda: self.app.backups_panel.refresh())
            
        self.app.progress_bar.set(0)
        self.app.progress_bar.pack(pady=4)
        threading.Thread(target=run, daemon=True).start()

class RLSwapperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"RL Forge v{APP_VERSION}")
        self.geometry("1000x700")
        self.minsize(900, 600)
        self.configure(fg_color=BG)
        self.resizable(True, True)
        
        try:
            icon_path = get_base_dir() / "data" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Icon warning: {e}")

        self.cfg = load_config()
        self.products = []

        self._build_ui()
        self._load_data_async()
        self._check_updates()

    def _check_updates(self):
        def run():
            try:
                import urllib3
                urllib3.disable_warnings()
                res = requests.get("https://api.github.com/repos/TheDroidBR/RL-Forge/releases/latest", timeout=5, verify=False)
                if res.status_code == 200:
                    data = res.json()
                    latest_ver = data.get("tag_name", "").replace("v", "")
                    if latest_ver and latest_ver != APP_VERSION:
                        # Find EXE asset
                        assets = data.get("assets", [])
                        exe_url = None
                        for asset in assets:
                            if asset.get("name", "").endswith(".exe"):
                                exe_url = asset.get("browser_download_url")
                                break
                                
                        try:
                            cur_parts = [int(x) for x in APP_VERSION.split(".")]
                            new_parts = [int(x) for x in latest_ver.split(".")]
                            if new_parts > cur_parts:
                                self.after(0, lambda: self._show_update_button(latest_ver, exe_url, data.get("html_url")))
                        except Exception:
                            if latest_ver > APP_VERSION:
                                self.after(0, lambda: self._show_update_button(latest_ver, exe_url, data.get("html_url")))
            except Exception as e:
                print(f"Update check failed: {e}")
                pass
                
        threading.Thread(target=run, daemon=True).start()

    def _show_update_button(self, new_version, exe_url, html_url):
        self.btn_update.configure(
            text=f"🟢 Atualizar (v{new_version})",
            command=lambda: self._show_update_dialog(new_version, exe_url, html_url)
        )
        self.btn_update.pack(side="right", padx=8)

    def _show_update_dialog(self, new_version, exe_url, html_url):
        if not exe_url:
            # Fallback to manual download if no exe is attached
            if messagebox.askyesno("Nova Versão", f"RL Forge v{new_version} disponível!\nDeseja baixar no navegador?"):
                webbrowser.open(html_url)
            return

        if messagebox.askyesno("Atualização Disponível", 
                               f"Uma nova versão (v{new_version}) do RL Forge está disponível!\n\n"
                               "Deseja atualizar agora automaticamente?"):
            self._start_native_update(exe_url)

    def _start_native_update(self, url):
        popup = ctk.CTkToplevel(self)
        popup.title("Atualizando RL Forge")
        popup.geometry("400x150")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        
        lbl = ctk.CTkLabel(popup, text="Preparando...", font=ctk.CTkFont("Segoe UI", 14))
        lbl.pack(pady=(20, 10))
        
        bar = ctk.CTkProgressBar(popup, width=300, progress_color=SUCCESS)
        bar.set(0)
        bar.pack(pady=10)
        
        def on_progress(pct, text):
            self.after(0, lambda: lbl.configure(text=text))
            self.after(0, lambda: bar.set(pct / 100.0))
            
        def on_complete():
            self.after(0, self.destroy) # Close main app so the updater can replace files
            
        def on_error(err):
            self.after(0, lambda: lbl.configure(text="Erro ao atualizar.", text_color=DANGER))
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha na atualização:\n{err}", parent=popup))
            self.after(0, popup.destroy)
            
        start_update_thread(url, on_progress, on_complete, on_error)

    # ── UI Builder ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color=SURFACE, height=56, corner_radius=0)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        title_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        title_frame.pack(side="left", padx=20)
        
        ctk.CTkLabel(title_frame, text="🚀 RL Forge",
                     font=ctk.CTkFont("Segoe UI", 18, "bold"),
                     text_color=ACCENT).pack(side="left")
                     
        ctk.CTkLabel(title_frame, text=f"v{APP_VERSION}",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     fg_color=ACCENT2, text_color="white", corner_radius=4,
                     width=40, height=18).pack(side="left", padx=(8, 0), pady=(4, 0))

        self.pkg_label = ctk.CTkLabel(topbar, text=self._pkg_display(),
                                       font=ctk.CTkFont("Consolas", 11),
                                       text_color=MUTED)
        self.pkg_label.pack(side="left", padx=8)

        ctk.CTkButton(topbar, text="📁 Pasta do Jogo", width=130, height=32,
                      fg_color=CARD, hover_color=BORDER, text_color=TEXT,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self._pick_folder).pack(side="left", padx=4)

        ctk.CTkButton(topbar, text="☁️ Atualizar Itens", width=130, height=32,
                      fg_color=CARD, hover_color=BORDER, text_color=TEXT,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self._update_csv).pack(side="left", padx=4)
                      
        ctk.CTkButton(topbar, text="ℹ️ Créditos", width=100, height=32,
                      fg_color="transparent", hover_color=BORDER, text_color=MUTED,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self._show_credits).pack(side="right", padx=16)

        self.btn_update = ctk.CTkButton(topbar, text="🟢 Atualizar", width=130, height=32,
                      fg_color=SUCCESS, hover_color="#28a745", text_color="white",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"))
        # self.btn_update is packed ONLY when an update is found via _show_update_button

        # ── Tab view ─────────────────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(self, fg_color=BG,
                                    segmented_button_fg_color=SURFACE,
                                    segmented_button_selected_color=ACCENT2,
                                    segmented_button_selected_hover_color=ACCENT,
                                    segmented_button_unselected_color=SURFACE,
                                    text_color=TEXT)
        self.tabs.pack(fill="both", expand=True, padx=0, pady=0)

        self.tabs.add("⚡  Swap")
        self.tabs.add("📦  Combos")
        self.tabs.add("💾  Backups")

        self._build_swap_tab()
        self._build_combos_tab()
        self._build_backup_tab()

        # Favorites
        self.favorites = self.cfg.get("favorites", [])
        self.orig_picker.favorites = self.favorites
        self.target_picker.favorites = self.favorites
        
        self.orig_picker.on_fav_change_cb = self._on_fav_changed
        self.target_picker.on_fav_change_cb = self._on_fav_changed

        # ── Log bar ───────────────────────────────────────────────────────────
        logbar = ctk.CTkFrame(self, fg_color=SURFACE, height=38, corner_radius=0)
        logbar.pack(fill="x", side="bottom")
        logbar.pack_propagate(False)
        
        self.log_label = ctk.CTkLabel(logbar, text="Pronto.", text_color=MUTED,
                                       font=ctk.CTkFont("Consolas", 11), anchor="w")
        self.log_label.pack(side="left", fill="x", expand=True, padx=16, pady=8)

    def _on_fav_changed(self, new_favs: list[str]):
        """Called when a favorite is toggled in any picker."""
        self.favorites = new_favs
        self.orig_picker.favorites = new_favs
        self.target_picker.favorites = new_favs
        self.cfg["favorites"] = new_favs
        save_config(self.cfg)
        
        # We need to refresh the other picker so its stars sync
        # We don't need to do a full search refresh immediately, 
        # but to keep it simple, we can just call _refresh()
        # To avoid lag during clicking, we only update the stars.
        for picker in (self.orig_picker, self.target_picker):
            for card in picker._card_pool:
                if card.winfo_ismapped() and card.item:
                    is_fav = card.item["Name"] in self.favorites
                    card.is_fav = is_fav
                    if is_fav:
                        card.fav_btn.configure(text="★", text_color=SUCCESS)
                    else:
                        card.fav_btn.configure(text="☆", text_color=MUTED)

    def _build_swap_tab(self):
        tab = self.tabs.tab("⚡  Swap")

        # Pickers row
        pickers = ctk.CTkFrame(tab, fg_color="transparent")
        pickers.pack(fill="both", expand=True, padx=12, pady=12)
        pickers.columnconfigure(0, weight=1)
        pickers.columnconfigure(2, weight=1)
        pickers.rowconfigure(0, weight=1)

        self.orig_picker = ItemPicker(pickers, "ITEM QUE VOCÊ USA", SUCCESS)
        self.orig_picker.grid(row=0, column=0, sticky="nsew")
        self.orig_picker.on_change_cb = self._update_swap_btn

        # Center column
        center = ctk.CTkFrame(pickers, fg_color="transparent", width=120)
        center.grid(row=0, column=1, padx=8, sticky="ns")
        center.pack_propagate(False)

        ctk.CTkLabel(center, text="→", font=ctk.CTkFont("Segoe UI", 36, "bold"),
                     text_color=ACCENT).pack(expand=True)

        self.swap_btn = ctk.CTkButton(center, text="⚡ SWAP", height=50, width=110,
                                       font=ctk.CTkFont("Segoe UI", 15, "bold"),
                                       fg_color=ACCENT2, hover_color=ACCENT,
                                       text_color="white", corner_radius=10,
                                       state="disabled", command=self._do_swap)
        self.swap_btn.pack(pady=8)

        self.progress_bar = ctk.CTkProgressBar(center, width=110, height=8,
                                                progress_color=SUCCESS,
                                                fg_color=CARD)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=4)
        self.progress_bar.pack_forget()  # Hide initially
        
        self.save_preset_btn = ctk.CTkButton(center, text="💾 Salvar Combo", height=28, width=110,
                                             fg_color="transparent", hover_color=BORDER, text_color=MUTED,
                                             command=self._save_combo)
        self.save_preset_btn.pack(pady=0)

        self.target_picker = ItemPicker(pickers, "VISUAL QUE VOCÊ QUER", ACCENT)
        self.target_picker.grid(row=0, column=2, sticky="nsew")
        self.target_picker.on_change_cb = self._update_swap_btn

    def _build_combos_tab(self):
        tab = self.tabs.tab("📦  Combos")
        self.combos_panel = CombosPanel(tab, self)
        self.combos_panel.pack(fill="both", expand=True, padx=12, pady=12)

    def _build_backup_tab(self):
        tab = self.tabs.tab("💾  Backups")
        self.backups_panel = BackupsPanel(tab, self._get_pkg_dir, self._log)
        self.backups_panel.pack(fill="both", expand=True, padx=12, pady=12)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_data_async(self):
        def run():
            from core.swapper import CSV_FILE
            if not CSV_FILE.exists():
                self._log("⬇️  Baixando lista de itens...")
                try:
                    fetch_products_csv(self._log)
                except Exception as e:
                    self._log(f"⚠️  Falha ao baixar: {e}")
            self.products = load_products()
            self.after(0, self._on_products_loaded)
        threading.Thread(target=run, daemon=True).start()

    def _on_products_loaded(self):
        if not self.products:
            self._log("⚠️  Sem itens. Clique em '☁️ Atualizar Itens'.")
            return
        self.orig_picker.load(self.products)
        self.target_picker.load(self.products)
        
        # Load smart memory (last selected items)
        last_orig = self.cfg.get("last_orig_name")
        last_target = self.cfg.get("last_target_name")
        
        if last_orig:
            item = next((p for p in self.products if p["Name"] == last_orig), None)
            if item: self.orig_picker.select_item(item)
            
        if last_target:
            item = next((p for p in self.products if p["Name"] == last_target), None)
            if item: self.target_picker.select_item(item)
            
        self._update_swap_btn()
        self.combos_panel.refresh()
        self._log(f"✅ {len(self.products)} itens carregados.")

    def _update_csv(self):
        def run():
            self._log("⬇️  Atualizando lista de itens...")
            try:
                fetch_products_csv(self._log)
                self.products = load_products()
                self.after(0, self._on_products_loaded)
            except Exception as e:
                self._log(f"❌ Erro: {e}")
        threading.Thread(target=run, daemon=True).start()

    # ── Swap ──────────────────────────────────────────────────────────────────

    def _update_swap_btn(self):
        ok = self.orig_picker.selected_item and self.target_picker.selected_item
        self.swap_btn.configure(state="normal" if ok else "disabled")
        
        # Save smart memory on every selection change
        if self.orig_picker.selected_item:
            self.cfg["last_orig_name"] = self.orig_picker.selected_item["Name"]
        if self.target_picker.selected_item:
            self.cfg["last_target_name"] = self.target_picker.selected_item["Name"]
        save_config(self.cfg)

    def _save_combo(self):
        orig = self.orig_picker.selected_item
        target = self.target_picker.selected_item
        if not orig or not target:
            return
            
        dialog = ctk.CTkInputDialog(text="Digite um nome para este Combo\n(ex: 'Meu Preset Alpha', 'Carro Azul'):", title="Salvar Combo")
        name = dialog.get_input()
        if not name or not name.strip():
            return
        name = name.strip()
            
        presets = self.cfg.get("presets", {})
        if name not in presets:
            presets[name] = []
            
        # Overwrite if same slot
        slot = orig.get("Slot")
        presets[name] = [p for p in presets[name] if p.get("slot") != slot]
        
        presets[name].append({
            "orig_name": orig["Name"],
            "target_name": target["Name"],
            "slot": slot
        })
        self.cfg["presets"] = presets
        save_config(self.cfg)
        self._log(f"✅ Combo '{name}' atualizado/salvo!")
        self.combos_panel.refresh()

    def _do_swap(self):
        pkg = self._get_pkg_dir()
        if not pkg:
            messagebox.showwarning("Sem pasta", "Configure a pasta CookedPCConsole primeiro.")
            return
        orig   = self.orig_picker.selected_item
        target = self.target_picker.selected_item
        if not orig or not target:
            return

        self.swap_btn.configure(state="disabled", text="Aguarde...")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=4)

        def run():
            try:
                swap(orig, target, pkg, self._log)
                self.after(0, lambda: self.backups_panel.refresh())
                self.after(0, lambda: self.swap_btn.configure(
                    state="normal", text="⚡ SWAP"))
                self.after(1000, lambda: self.progress_bar.pack_forget())
            except Exception as e:
                self._log(f"❌ Erro: {e}")
                self.after(0, lambda: self.swap_btn.configure(
                    state="normal", text="⚡ SWAP"))
                self.after(0, lambda: self.progress_bar.pack_forget())
                self.after(0, lambda: messagebox.showerror("Erro no Swap", str(e)))

        threading.Thread(target=run, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_pkg_dir(self) -> str:
        return self.cfg.get("pkg_dir", "")

    def _pkg_display(self) -> str:
        d = self.cfg.get("pkg_dir", "")
        if d:
            # Show shortened path
            parts = d.replace("\\", "/").split("/")
            return "/".join(parts[-3:]) if len(parts) > 3 else d
        return "⚠️  Pasta não configurada"

    def _pick_folder(self):
        initial = self.cfg.get("pkg_dir", "D:\\")
        folder = filedialog.askdirectory(title="Selecione a pasta CookedPCConsole",
                                          initialdir=initial)
        if not folder:
            return
        import os
        # Auto-navigate to CookedPCConsole if user picked game root or TAGame
        cooked = os.path.join(folder, "TAGame", "CookedPCConsole")
        cooked2 = os.path.join(folder, "CookedPCConsole")
        if os.path.isdir(cooked):
            folder = cooked
            self._log(f"📁 Auto-detectado: {folder}")
        elif os.path.isdir(cooked2):
            folder = cooked2
            self._log(f"📁 Auto-detectado: {folder}")
        self.cfg["pkg_dir"] = folder
        save_config(self.cfg)
        self.pkg_label.configure(text=self._pkg_display())
        self._log(f"📁 Pasta configurada: {folder}")

    def _log(self, msg: str):
        self.after(0, lambda: self.log_label.configure(text=msg))
        
        # Intercept progress steps [1/4]
        if msg.startswith("["):
            try:
                part = msg[1:4]
                if "/" in part:
                    curr, tot = part.split("/")
                    pct = int(curr) / int(tot)
                    self.after(0, lambda: self.progress_bar.set(pct))
            except:
                pass
        
        if "[OK]" in msg or "concluido" in msg.lower():
            self.after(0, lambda: self.progress_bar.set(1.0))

    def _show_credits(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Créditos e Licenças")
        popup.geometry("500x380")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        
        lbl = ctk.CTkLabel(popup, text="RL Forge", font=ctk.CTkFont("Segoe UI", 20, "bold"), text_color=ACCENT)
        lbl.pack(pady=(20, 5))
        
        sub = ctk.CTkLabel(popup, text=f"Versão {APP_VERSION} — Sob Licença GNU GPL v3.0", font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED)
        sub.pack(pady=(0, 20))
        
        frame = ctk.CTkFrame(popup, fg_color=CARD)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        txt = ("Este projeto só é possível graças à comunidade de modding:\n\n"
               "• ShinyEmii (Toga-Files): Banco de dados de itens e chaves AES.\n"
               "• AltimorTASDK (RLUPKTool): Motor de descriptografia (MIT License).\n\n"
               "O código-fonte do RL Forge é aberto e livre sob a GNU GPL v3.0. Obrigado por usar!")
               
        msg = ctk.CTkLabel(frame, text=txt, font=ctk.CTkFont("Segoe UI", 13), text_color=TEXT, justify="left", wraplength=400)
        msg.pack(padx=20, pady=20, fill="both", expand=True)
