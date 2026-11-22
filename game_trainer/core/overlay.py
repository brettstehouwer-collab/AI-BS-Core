"""
AI-BS Game Trainer Suite: Transparent Interactive HUD Overlay
Standard library Tkinter + Win32 ctypes layered window.
Provides translucent, always-on-top HUD with segmented tabs, 
click-to-toggle cheats, and interactive variables.
"""

import sys
import os
import ctypes
from ctypes import wintypes
import threading
import time
import tkinter as tk
from typing import Optional, List, Dict, Any, Callable

# Win32 Window Styles & API for Click-Through Transparent Pass-Through
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008

try:
    user32 = ctypes.windll.user32
    SetWindowLongPtr = user32.SetWindowLongPtrW
    SetWindowLongPtr.restype = ctypes.c_void_p
    SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]

    GetWindowLongPtr = user32.GetWindowLongPtrW
    GetWindowLongPtr.restype = ctypes.c_void_p
    GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
except Exception:
    user32 = None


class TrainerOverlay:
    """
    Translucent on-screen HUD overlay for games.
    Runs in a dedicated background UI thread, maintaining live sync with the trainer state.
    """

    def __init__(self, trainer_instance, title: str = "AI-BS TRAINER HUD", initial_x: int = 40, initial_y: int = 40):
        self.trainer = trainer_instance
        self.title_text = title
        self.initial_x = initial_x
        self.initial_y = initial_y

        self.root = None
        self.hwnd = None
        self.visible = True
        self.click_through = False
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._feature_rows: Dict[str, Dict[str, Any]] = {}
        self._variable_labels: Dict[str, Dict[str, Any]] = {}
        self.tabs: Dict[str, Dict[str, Any]] = {}
        self.active_tab = "Launch Game"
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_ui, daemon=True, name="TrainerOverlayThread")
        self._thread.start()

    def stop(self):
        self._running = False
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass

    def toggle_visibility(self):
        self.visible = not self.visible
        if not self.root:
            return
        try:
            if self.visible:
                self.root.after(0, self.root.deiconify)
            else:
                self.root.after(0, self.root.withdraw)
        except Exception:
            pass

    def toggle_click_through(self):
        """Toggles click-through pass-through so clicks hit the game canvas beneath."""
        if not self.hwnd or not user32:
            return
        self.click_through = not self.click_through
        try:
            current_style = GetWindowLongPtr(self.hwnd, GWL_EXSTYLE)
            if self.click_through:
                new_style = current_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                new_style = current_style & ~WS_EX_TRANSPARENT
            SetWindowLongPtr(self.hwnd, GWL_EXSTYLE, new_style)
            if self.mode_lbl:
                self.mode_lbl.configure(text="👻 Pass-Through", bg="#4c1d95")
        except Exception as e:
            print(f"[Overlay] Failed setting click-through: {e}")

    def set_interactive_mode(self):
        """Forces interactive mode (clicks are captured)."""
        if self.click_through:
            self.toggle_click_through()
            if self.mode_lbl:
                self.mode_lbl.configure(text="🖱️ Interactive", bg="#1e3a8a")

    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event):
        if self.click_through:
            return
        deltax = event.x - self._drag_start_x
        deltay = event.y - self._drag_start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def _switch_tab(self, tab_name: str):
        self.active_tab = tab_name
        for name, data in self.tabs.items():
            if name == tab_name:
                data["button"].configure(bg="#2563eb", fg="#ffffff")
                data["frame"].pack(fill="both", expand=True, padx=10, pady=8)
            else:
                data["button"].configure(bg="#1f2937", fg="#94a3b8")
                data["frame"].pack_forget()

    def _launch_game(self):
        try:
            os.startfile("steam://rungameid/960090")
            print("[+] Triggered game launch via Steam URI.")
        except Exception as e:
            print(f"[Overlay] Launch failed: {e}")

    def _run_ui(self):
        self.root = tk.Tk()
        self.root.title(self.title_text)
        self.root.geometry(f"360x470+{self.initial_x}+{self.initial_y}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.configure(bg="#0b0f19")

        self.root.update_idletasks()
        try:
            self.hwnd = int(self.root.frame(), 16)
        except Exception:
            self.hwnd = None

        container = tk.Frame(self.root, bg="#0b0f19", bd=1, relief="solid", highlightbackground="#2563eb", highlightthickness=1)
        container.pack(fill="both", expand=True)

        # Header Bar
        header = tk.Frame(container, bg="#111827", height=32)
        header.pack(fill="x", padx=2, pady=2)
        header.bind("<Button-1>", self._on_drag_start)
        header.bind("<B1-Motion>", self._on_drag_motion)

        title_lbl = tk.Label(header, text=f"⚡ {self.title_text}", bg="#111827", fg="#38bdf8", font=("Segoe UI", 9, "bold"))
        title_lbl.pack(side="left", padx=8, pady=4)
        title_lbl.bind("<Button-1>", self._on_drag_start)
        title_lbl.bind("<B1-Motion>", self._on_drag_motion)

        # Mode Switcher
        self.mode_lbl = tk.Label(header, text="🖱️ Interactive", bg="#1e3a8a", fg="#ffffff", font=("Segoe UI", 7, "bold"), cursor="hand2", padx=6, pady=2)
        self.mode_lbl.pack(side="right", padx=6, pady=4)
        self.mode_lbl.bind("<Button-1>", lambda e: self.toggle_click_through())

        self.proc_status_lbl = tk.Label(header, text="WAITING", bg="#374151", fg="#f3f4f6", font=("Segoe UI", 7, "bold"), padx=6, pady=1)
        self.proc_status_lbl.pack(side="right", padx=6, pady=4)

        # Navigation Tabs
        nav_frame = tk.Frame(container, bg="#111827", height=28)
        nav_frame.pack(fill="x")
        
        tab_names = ["Launch Game", "Cheats", "Variables", "Scanner"]
        for tab_name in tab_names:
            btn = tk.Label(nav_frame, text=tab_name, bg="#1f2937", fg="#94a3b8", font=("Segoe UI", 8, "bold"), cursor="hand2", padx=6, pady=4)
            btn.pack(side="left", fill="x", expand=True, padx=1)
            btn.bind("<Button-1>", lambda e, name=tab_name: self._switch_tab(name))
            self.tabs[tab_name] = {"button": btn, "frame": tk.Frame(container, bg="#0b0f19")}

        # Build Tabs
        self._build_launch_tab()
        self._build_cheats_tab()
        self._build_variables_tab()
        self._build_scanner_tab()
        
        self._switch_tab("Launch Game")

        # Footer
        footer = tk.Frame(container, bg="#0f172a", height=24)
        footer.pack(fill="x", side="bottom")
        hint_lbl = tk.Label(footer, text="[F6] Hide/Show | [F10] Reset | Click variables to set", bg="#0f172a", fg="#64748b", font=("Segoe UI", 7))
        hint_lbl.pack(side="left", padx=8, pady=3)

        self._sync_tick()

        try:
            self.root.mainloop()
        except Exception:
            pass

    def _build_launch_tab(self):
        f = self.tabs["Launch Game"]["frame"]
        tk.Label(f, text="Start your game via AI-BS Trainer", bg="#0b0f19", fg="#f1f5f9", font=("Segoe UI", 10, "bold")).pack(pady=(20, 10))
        btn_start = tk.Label(f, text="▶ START GAME", bg="#16a34a", fg="#ffffff", font=("Segoe UI", 12, "bold"), cursor="hand2", padx=16, pady=8)
        btn_start.pack(pady=5)
        btn_start.bind("<Button-1>", lambda e: self._launch_game())
        
        tk.Label(f, text='(Optional) Use "Prepare" to enable cheats', bg="#0b0f19", fg="#64748b", font=("Segoe UI", 9)).pack(pady=10)
        tk.Label(f, text="Have fun with AI-BS Trainer", bg="#0b0f19", fg="#38bdf8", font=("Segoe UI", 10, "bold")).pack(pady=(5, 10))

    def _build_cheats_tab(self):
        f = self.tabs["Cheats"]["frame"]
        unique_feats = self.trainer.get_unique_features()
        for feat in unique_feats:
            row = tk.Frame(f, bg="#131d31", bd=0, padx=6, pady=4, cursor="hand2")
            row.pack(fill="x", pady=2)
            
            def on_click(e, f_obj=feat):
                f_obj.toggle()
            
            row.bind("<Button-1>", on_click)
            
            key_lbl = tk.Label(row, text=feat.get_key_label(), bg="#1e293b", fg="#38bdf8", font=("Consolas", 8, "bold"), width=13, anchor="w", padx=4)
            key_lbl.pack(side="left")
            key_lbl.bind("<Button-1>", on_click)
            
            # Special highlighting for "Prepare"
            name_color = "#fcd34d" if "Prepare" in feat.name else "#f1f5f9"
            name_lbl = tk.Label(row, text=feat.name[:25], bg="#131d31", fg=name_color, font=("Segoe UI", 8, "bold" if "Prepare" in feat.name else "normal"), anchor="w", padx=4)
            name_lbl.pack(side="left", fill="x", expand=True)
            name_lbl.bind("<Button-1>", on_click)
            
            status_lbl = tk.Label(row, text="OFF", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 7, "bold"), width=6, padx=3)
            status_lbl.pack(side="right")
            status_lbl.bind("<Button-1>", on_click)
            
            self._feature_rows[feat.name] = {"feature": feat, "status_lbl": status_lbl, "row": row}
            
            def on_enter(e, r=row, n=name_lbl):
                r.configure(bg="#1e293b")
                n.configure(bg="#1e293b")
            def on_leave(e, r=row, n=name_lbl):
                r.configure(bg="#131d31")
                n.configure(bg="#131d31")
                
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)
            name_lbl.bind("<Enter>", on_enter)
            name_lbl.bind("<Leave>", on_leave)

    def _build_variables_tab(self):
        f = self.tabs["Variables"]["frame"]
        vars_list = self.trainer.get_variables()
        for var in vars_list:
            card = tk.Frame(f, bg="#131d31", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1, padx=6, pady=4)
            card.pack(fill="x", pady=4, padx=2)
            
            top_row = tk.Frame(card, bg="#131d31")
            top_row.pack(fill="x")
            tk.Label(top_row, text=var.name, bg="#131d31", fg="#38bdf8", font=("Segoe UI", 9, "bold")).pack(side="left")
            val_lbl = tk.Label(top_row, text="", bg="#131d31", fg="#f1f5f9", font=("Consolas", 9))
            val_lbl.pack(side="right")
            
            preset_row = tk.Frame(card, bg="#131d31")
            preset_row.pack(fill="x", pady=4)
            for p in var.presets:
                def set_p(e, v=var, val=p):
                    v.set_val(val)
                p_text = f"{var.unit_prefix}{p:g}{var.unit_suffix}"
                lbl = tk.Label(preset_row, text=p_text, bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 7), cursor="hand2", padx=4, bd=1, relief="raised")
                lbl.pack(side="left", padx=2)
                lbl.bind("<Button-1>", set_p)
                
            inp_row = tk.Frame(card, bg="#131d31")
            inp_row.pack(fill="x")
            
            entry = tk.Entry(inp_row, bg="#0f172a", fg="#f1f5f9", font=("Consolas", 8), width=10, insertbackground="#f1f5f9")
            entry.pack(side="left", padx=2)
            
            def set_custom(e, v=var, ent=entry):
                try:
                    val = float(ent.get()) if v.var_type == "float" else int(ent.get())
                    v.set_val(val)
                    ent.delete(0, 'end')
                except ValueError:
                    pass
            
            btn_set = tk.Label(inp_row, text="Set", bg="#2563eb", fg="#ffffff", font=("Segoe UI", 7, "bold"), cursor="hand2", padx=6)
            btn_set.pack(side="left", padx=4)
            btn_set.bind("<Button-1>", set_custom)
            
            self._variable_labels[var.key] = {"var": var, "lbl": val_lbl}

    def _build_scanner_tab(self):
        f = self.tabs["Scanner"]["frame"]
        
        # Header
        tk.Label(f, text="In-Game Memory Calibration", bg="#0b0f19", fg="#38bdf8", font=("Segoe UI", 10, "bold")).pack(pady=(4, 2))
        tk.Label(f, text="First Scan initial value, change in-game, then Next Scan.", bg="#0b0f19", fg="#94a3b8", font=("Segoe UI", 7)).pack(pady=(0, 4))

        # --- Match Cash Card ---
        cash_card = tk.Frame(f, bg="#131d31", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1, padx=6, pady=4)
        cash_card.pack(fill="x", pady=3, padx=2)

        tk.Label(cash_card, text="💵 Match Cash (In-Game Display)", bg="#131d31", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack(anchor="w")

        # Quick preset pills
        pills_frame = tk.Frame(cash_card, bg="#131d31")
        pills_frame.pack(fill="x", pady=(2, 2))
        for p in [650.0, 850.0, 450.0, 1750.0]:
            lbl = tk.Label(pills_frame, text=f"${p:g}", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 7), cursor="hand2", padx=3, pady=1)
            lbl.pack(side="left", padx=1)
            lbl.bind("<Button-1>", lambda e, val=p: (self.cash_entry.delete(0, 'end'), self.cash_entry.insert(0, str(int(val)))))

        # Cash Input Row
        inp_f = tk.Frame(cash_card, bg="#131d31")
        inp_f.pack(fill="x", pady=2)
        self.cash_entry = tk.Entry(inp_f, bg="#0f172a", fg="#f1f5f9", font=("Consolas", 9), width=8, insertbackground="#f1f5f9")
        self.cash_entry.insert(0, "650")
        self.cash_entry.pack(side="left", padx=2)

        def do_first_scan_cash(e=None):
            try:
                val = float(self.cash_entry.get())
                if hasattr(self.trainer, 'first_scan_cash'):
                    self.trainer.first_scan_cash(val)
                elif hasattr(self.trainer, 'auto_scan_cash'):
                    self.trainer.auto_scan_cash(val)
            except ValueError:
                pass

        def do_next_scan_cash(e=None):
            try:
                val = float(self.cash_entry.get())
                if hasattr(self.trainer, 'next_scan_cash'):
                    self.trainer.next_scan_cash(val)
            except ValueError:
                pass

        btn_first = tk.Label(inp_f, text="🔍 First Scan", bg="#2563eb", fg="#ffffff", font=("Segoe UI", 7, "bold"), cursor="hand2", padx=5, pady=2)
        btn_first.pack(side="left", padx=2)
        btn_first.bind("<Button-1>", do_first_scan_cash)

        btn_next = tk.Label(inp_f, text="🎯 Next Scan", bg="#16a34a", fg="#ffffff", font=("Segoe UI", 7, "bold"), cursor="hand2", padx=5, pady=2)
        btn_next.pack(side="left", padx=2)
        btn_next.bind("<Button-1>", do_next_scan_cash)

        self.cash_scan_status_lbl = tk.Label(cash_card, text="Status: Not Scanned", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 7), padx=4, pady=1)
        self.cash_scan_status_lbl.pack(fill="x", pady=(2, 0))

        # --- Monkey Money Card ---
        coin_card = tk.Frame(f, bg="#131d31", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1, padx=6, pady=4)
        coin_card.pack(fill="x", pady=3, padx=2)

        tk.Label(coin_card, text="🪙 Monkey Money (Coins)", bg="#131d31", fg="#f59e0b", font=("Segoe UI", 8, "bold")).pack(anchor="w")

        coin_inp_f = tk.Frame(coin_card, bg="#131d31")
        coin_inp_f.pack(fill="x", pady=2)
        self.coin_entry = tk.Entry(coin_inp_f, bg="#0f172a", fg="#f1f5f9", font=("Consolas", 9), width=8, insertbackground="#f1f5f9")
        self.coin_entry.pack(side="left", padx=2)

        def do_first_scan_coins(e=None):
            try:
                val = int(self.coin_entry.get())
                if hasattr(self.trainer, 'first_scan_coins'):
                    self.trainer.first_scan_coins(val)
                elif hasattr(self.trainer, 'auto_scan_coins'):
                    self.trainer.auto_scan_coins(val)
            except ValueError:
                pass

        def do_next_scan_coins(e=None):
            try:
                val = int(self.coin_entry.get())
                if hasattr(self.trainer, 'next_scan_coins'):
                    self.trainer.next_scan_coins(val)
            except ValueError:
                pass

        btn_c_first = tk.Label(coin_inp_f, text="🔍 First Scan", bg="#b45309", fg="#ffffff", font=("Segoe UI", 7, "bold"), cursor="hand2", padx=5, pady=2)
        btn_c_first.pack(side="left", padx=2)
        btn_c_first.bind("<Button-1>", do_first_scan_coins)

        btn_c_next = tk.Label(coin_inp_f, text="🎯 Next Scan", bg="#059669", fg="#ffffff", font=("Segoe UI", 7, "bold"), cursor="hand2", padx=5, pady=2)
        btn_c_next.pack(side="left", padx=2)
        btn_c_next.bind("<Button-1>", do_next_scan_coins)

        self.coin_scan_status_lbl = tk.Label(coin_card, text="Status: Not Scanned", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 7), padx=4, pady=1)
        self.coin_scan_status_lbl.pack(fill="x", pady=(2, 0))

    def _sync_tick(self):
        if not self._running or not self.root:
            return

        try:
            # Update connection status
            attached = self.trainer.mem.is_alive()
            if attached:
                self.proc_status_lbl.configure(text="ATTACHED", bg="#15803d", fg="#ffffff")
            else:
                self.proc_status_lbl.configure(text="SEARCHING", bg="#b45309", fg="#ffffff")
                
            # Auto-switch from Launch Game to Cheats tab when attached
            if attached and self.active_tab == "Launch Game":
                self._switch_tab("Cheats")

            # Update feature statuses
            for feat_name, widgets in self._feature_rows.items():
                feat = widgets["feature"]
                lbl = widgets["status_lbl"]
                if not feat.is_toggle:
                    lbl.configure(text="READY", bg="#0284c7", fg="#ffffff")
                elif feat.enabled:
                    lbl.configure(text="ACTIVE", bg="#16a34a", fg="#ffffff")
                else:
                    lbl.configure(text="OFF", bg="#1e293b", fg="#94a3b8")
                    
            # Update variable displays
            for key, widgets in self._variable_labels.items():
                var = widgets["var"]
                lbl = widgets["lbl"]
                val = var.get_val()
                fmt_val = f"{val:g}" if isinstance(val, float) else f"{val}"
                lbl.configure(text=f"{var.unit_prefix}{fmt_val}{var.unit_suffix}")

            # Update scanner feedback labels
            if hasattr(self, 'cash_scan_status_lbl'):
                c_locked = len(getattr(self.trainer, 'cash_addresses', []))
                c_cand = len(getattr(self.trainer, 'cash_candidates', []))
                if c_locked > 0:
                    self.cash_scan_status_lbl.configure(text=f"Locked: {c_locked} addr ({hex(self.trainer.cash_addresses[0])[:12]}...)", bg="#15803d", fg="#ffffff")
                elif c_cand > 0:
                    self.cash_scan_status_lbl.configure(text=f"Candidates: {c_cand} (Change cash & Next Scan)", bg="#854d0e", fg="#ffffff")
                else:
                    self.cash_scan_status_lbl.configure(text="Status: Ready to scan", bg="#1e293b", fg="#94a3b8")

            if hasattr(self, 'coin_scan_status_lbl'):
                coins_locked = len(getattr(self.trainer, 'coins_addresses', []))
                coins_cand = len(getattr(self.trainer, 'coins_candidates', []))
                if coins_locked > 0:
                    self.coin_scan_status_lbl.configure(text=f"Locked: {coins_locked} addr", bg="#15803d", fg="#ffffff")
                elif coins_cand > 0:
                    self.coin_scan_status_lbl.configure(text=f"Candidates: {coins_cand} (Change coins & Next Scan)", bg="#854d0e", fg="#ffffff")
                else:
                    self.coin_scan_status_lbl.configure(text="Status: Ready to scan", bg="#1e293b", fg="#94a3b8")
                
        except Exception:
            pass

        if self._running and self.root:
            self.root.after(150, self._sync_tick)
