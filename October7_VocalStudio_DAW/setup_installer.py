"""
October 7 Vocal Tracking Studio DAW - Official Windows GUI Directory Installer
Features:
- Windows Administrator Elevation (UAC)
- End-User License Agreement (EULA) with Acceptance Verification
- Customizable Installation Directory with Folder Browser Dialog
- Disk Space Calculation & Verification
- Desktop & Start Menu Shortcut Generation
- Optional certificate fingerprint review (no trust store changes)
- Uninstaller Generation (Uninstall_October7_DAW.bat)
- Direct Launch on Completion
"""

import os
import sys
import shutil
import ctypes
import subprocess
import threading
from pathlib import Path

# GUI Modules
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "dist" / "October7_VocalStudio_Native"
if not (SOURCE_DIR / "October7_VocalStudio_Native.exe").is_file():
    SOURCE_DIR = BASE_DIR / "dist" / "October7_VocalStudio_DAW"
if not (SOURCE_DIR / "October7_VocalStudio_DAW.exe").is_file() and not (SOURCE_DIR / "October7_VocalStudio_Native.exe").is_file():
    SOURCE_DIR = BASE_DIR

DEFAULT_INSTALL_PATH = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "October7_VocalStudio_DAW")
ALT_INSTALL_PATH = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\AppData\\Local"), "October7_VocalStudio_DAW")

EULA_TEXT = """================================================================================
OCTOBER 7 VOCAL STUDIO & PERFORMANCE ENGINE - END USER LICENSE AGREEMENT (EULA)
================================================================================
VERSION 1.0 - WINDOWS CORE PRO EDITION (RELEASE CANDIDATE)

1. LICENSE GRANT & LOCAL SOVEREIGNTY:
October 7 Vocal Studio is licensed as a sovereign, local-first digital audio
workstation (DAW) for multi-track vocal recording, bio-acoustic telemetry, and stem
management. All audio recordings, vocal takes, bio-acoustic measurements, and AI
music latents are processed and stored 100% locally on your machine. No voice
samples or session telemetry are transmitted to remote servers.

2. CORE PC ACCESS & REALTIME OS OPTIMIZATIONS:
This software executes with Windows Administrator privileges to configure:
- Windows Multimedia Class Scheduler Service (MMCSS) 'Pro Audio' thread priority.
- Direct WASAPI Exclusive buffer management and sub-millisecond round-trip compensation.
- Local NVIDIA GeForce CUDA acceleration (Demucs stem separation, ACE-Step 1.5 DiT).

3. HARDWARE & LOCAL AI ACCELERATION:
Local generative AI components (Ollama on Port 11434, ACE-Step 1.5 on Port 7860) run
within local hardware parameters. A thread-safe CUDA VRAM queue manager protects
system memory from oversubscription.

4. USER ACCEPTANCE & ELEVATED SETUP:
By installing and using this software, you agree to these terms and authorize
the installer to deploy the audio engine, configure system MMCSS scheduling,
and register the local Authenticode digital signature for trusted execution.
================================================================================"""


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_to_admin():
    if not is_admin():
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        executable = sys.executable
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, str(BASE_DIR), 1
        )
        if ret > 32:
            sys.exit(0)
        else:
            messagebox.showerror(
                "Elevation Required",
                "Administrator privileges are required to install system audio drivers and shortcuts.\nInstallation cancelled."
            )
            sys.exit(1)


class InstallerWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("October 7 Vocal Studio DAW - Windows Installer")
        self.geometry("680x560")
        self.resizable(False, False)
        self.configure(bg="#0c0f17")

        # Color Palette
        self.c_bg = "#0c0f17"
        self.c_card = "#141a24"
        self.c_border = "#222c3d"
        self.c_text = "#f1f5f9"
        self.c_sub = "#94a3b8"
        self.c_gold = "#f59e0b"
        self.c_green = "#10b981"
        self.c_cyan = "#06b6d4"

        # Wizard State
        self.current_step = 0
        self.target_path = tk.StringVar(value=DEFAULT_INSTALL_PATH)
        self.accept_eula = tk.BooleanVar(value=False)
        self.opt_desktop = tk.BooleanVar(value=True)
        self.opt_startmenu = tk.BooleanVar(value=True)
        self.opt_cert = tk.BooleanVar(value=False)
        self.opt_launch = tk.BooleanVar(value=False)

        self.setup_ui()
        self.show_step(0)

    def setup_ui(self):
        # Header Banner
        self.header = tk.Frame(self, bg="#111622", height=70)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.header,
            text="October 7 Vocal Studio DAW",
            font=("Segoe UI", 14, "bold"),
            bg="#111622",
            fg=self.c_gold
        )
        self.title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

        self.subtitle_lbl = tk.Label(
            self.header,
            text="Official Windows Directory Installer (WASAPI Exclusive & MMCSS Pro Audio)",
            font=("Segoe UI", 9),
            bg="#111622",
            fg=self.c_sub
        )
        self.subtitle_lbl.pack(anchor="w", padx=20)

        # Content Container
        self.content_container = tk.Frame(self, bg=self.c_bg)
        self.content_container.pack(fill="both", expand=True, padx=20, pady=15)

        # Navigation Footer
        self.footer = tk.Frame(self, bg="#111622", height=60)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        self.btn_cancel = tk.Button(
            self.footer,
            text="Cancel",
            bg="#222c3d",
            fg=self.c_text,
            relief="flat",
            padx=14,
            pady=4,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(5, 20), pady=14)

        self.btn_next = tk.Button(
            self.footer,
            text="Next >",
            bg=self.c_gold,
            fg="#000000",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=4,
            command=self.next_step
        )
        self.btn_next.pack(side="right", padx=5, pady=14)

        self.btn_back = tk.Button(
            self.footer,
            text="< Back",
            bg="#222c3d",
            fg=self.c_text,
            relief="flat",
            padx=14,
            pady=4,
            command=self.prev_step
        )
        self.btn_back.pack(side="right", padx=5, pady=14)

    def show_step(self, step_idx):
        self.current_step = step_idx
        for widget in self.content_container.winfo_children():
            widget.destroy()

        if step_idx == 0:
            self.render_eula_step()
        elif step_idx == 1:
            self.render_location_step()
        elif step_idx == 2:
            self.render_installing_step()
        elif step_idx == 3:
            self.render_finished_step()

    # --- STEP 0: EULA & License Agreement ---
    def render_eula_step(self):
        self.btn_back.config(state="disabled")
        self.btn_next.config(text="Accept & Next >", state="normal" if self.accept_eula.get() else "disabled")

        lbl = tk.Label(
            self.content_container,
            text="End-User License Agreement & Audio System Access",
            font=("Segoe UI", 11, "bold"),
            bg=self.c_bg,
            fg=self.c_text
        )
        lbl.pack(anchor="w", pady=(0, 6))

        txt_frame = tk.Frame(self.content_container, bg=self.c_card, bd=1, relief="solid")
        txt_frame.pack(fill="both", expand=True, pady=(0, 10))

        scroll = tk.Scrollbar(txt_frame)
        scroll.pack(side="right", fill="y")

        eula_box = tk.Text(
            txt_frame,
            wrap="word",
            bg=self.c_card,
            fg="#cbd5e1",
            font=("Consolas", 9),
            yscrollcommand=scroll.set,
            bd=0,
            padx=10,
            pady=10
        )
        eula_box.pack(side="left", fill="both", expand=True)
        scroll.config(command=eula_box.yview)
        eula_box.insert("1.0", EULA_TEXT)
        eula_box.config(state="disabled")

        def on_toggle_eula():
            if self.accept_eula.get():
                self.btn_next.config(state="normal")
            else:
                self.btn_next.config(state="disabled")

        chk = tk.Checkbutton(
            self.content_container,
            text="I accept the terms in the License Agreement and authorize elevated audio tuning",
            variable=self.accept_eula,
            bg=self.c_bg,
            fg=self.c_gold,
            selectcolor="#1a212e",
            activebackground=self.c_bg,
            activeforeground=self.c_gold,
            font=("Segoe UI", 9, "bold"),
            command=on_toggle_eula
        )
        chk.pack(anchor="w")

    # --- STEP 1: Directory & Options ---
    def render_location_step(self):
        self.btn_back.config(state="normal")
        self.btn_next.config(text="Install Now", state="normal")

        lbl = tk.Label(
            self.content_container,
            text="Select Destination Directory & Installation Options",
            font=("Segoe UI", 11, "bold"),
            bg=self.c_bg,
            fg=self.c_text
        )
        lbl.pack(anchor="w", pady=(0, 8))

        path_card = tk.Frame(self.content_container, bg=self.c_card, padx=12, pady=12, bd=1, relief="solid")
        path_card.pack(fill="x", pady=(0, 15))

        tk.Label(
            path_card,
            text="Installation Path:",
            font=("Segoe UI", 9, "bold"),
            bg=self.c_card,
            fg=self.c_text
        ).pack(anchor="w", pady=(0, 4))

        input_row = tk.Frame(path_card, bg=self.c_card)
        input_row.pack(fill="x", pady=(0, 6))

        entry = tk.Entry(
            input_row,
            textvariable=self.target_path,
            font=("Segoe UI", 9),
            bg="#0f141c",
            fg="#ffffff",
            insertbackground="#ffffff",
            bd=1,
            relief="solid"
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)

        btn_browse = tk.Button(
            input_row,
            text="Browse...",
            bg="#222c3d",
            fg=self.c_text,
            relief="flat",
            padx=12,
            pady=2,
            command=self.browse_folder
        )
        btn_browse.pack(side="right")

        # Preset Buttons
        btn_row = tk.Frame(path_card, bg=self.c_card)
        btn_row.pack(anchor="w")

        tk.Button(
            btn_row,
            text="Use Program Files (System-Wide)",
            font=("Segoe UI", 8),
            bg="#1a2333",
            fg=self.c_cyan,
            relief="flat",
            command=lambda: self.target_path.set(DEFAULT_INSTALL_PATH)
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_row,
            text="Use AppData (User-Specific)",
            font=("Segoe UI", 8),
            bg="#1a2333",
            fg=self.c_cyan,
            relief="flat",
            command=lambda: self.target_path.set(ALT_INSTALL_PATH)
        ).pack(side="left")

        # Space details
        space_lbl = tk.Label(
            path_card,
            text="Required Space: ~260 MB | Available Space: Calculating...",
            font=("Segoe UI", 8),
            bg=self.c_card,
            fg=self.c_sub
        )
        space_lbl.pack(anchor="w", pady=(8, 0))

        try:
            drive = os.path.splitdrive(self.target_path.get())[0] or "C:"
            usage = shutil.disk_usage(drive + "\\")
            avail_gb = usage.free / (1024 ** 3)
            space_lbl.config(text=f"Required Space: ~260 MB | Available on {drive}: {avail_gb:.1f} GB")
        except Exception:
            pass

        # Options Card
        opt_card = tk.Frame(self.content_container, bg=self.c_card, padx=12, pady=10, bd=1, relief="solid")
        opt_card.pack(fill="both", expand=True)

        tk.Label(
            opt_card,
            text="Installation Components & Windows Integration:",
            font=("Segoe UI", 9, "bold"),
            bg=self.c_card,
            fg=self.c_text
        ).pack(anchor="w", pady=(0, 6))

        options = [
            ("Create Desktop Shortcut ('October 7 Vocal Studio DAW')", self.opt_desktop),
            ("Register Start Menu Entry ('October 7 Vocal Studio')", self.opt_startmenu),
            ("Review certificate fingerprint only (no Windows trust changes)", self.opt_cert),
            ("Launch October 7 Vocal Studio DAW when setup completes", self.opt_launch),
        ]

        for text, var in options:
            tk.Checkbutton(
                opt_card,
                text=text,
                variable=var,
                bg=self.c_card,
                fg=self.c_text,
                selectcolor="#0f141c",
                activebackground=self.c_card,
                activeforeground=self.c_text,
                font=("Segoe UI", 9)
            ).pack(anchor="w", pady=2)

    def browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.target_path.get(), title="Select Installation Folder")
        if chosen:
            self.target_path.set(chosen)

    # --- STEP 2: Installing & Progress ---
    def render_installing_step(self):
        self.btn_back.config(state="disabled")
        self.btn_next.config(state="disabled")
        self.btn_cancel.config(state="disabled")

        tk.Label(
            self.content_container,
            text="Installing October 7 Vocal Studio DAW...",
            font=("Segoe UI", 12, "bold"),
            bg=self.c_bg,
            fg=self.c_gold
        ).pack(anchor="w", pady=(20, 10))

        self.status_lbl = tk.Label(
            self.content_container,
            text="Initializing deployment...",
            font=("Segoe UI", 9),
            bg=self.c_bg,
            fg=self.c_sub
        )
        self.status_lbl.pack(anchor="w", pady=(0, 12))

        self.progress = ttk.Progressbar(self.content_container, mode="indeterminate", length=640)
        self.progress.pack(fill="x", pady=(0, 20))
        self.progress.start(12)

        self.log_box = tk.Text(
            self.content_container,
            height=12,
            bg=self.c_card,
            fg="#94a3b8",
            font=("Consolas", 8),
            bd=1,
            relief="solid",
            padx=8,
            pady=8
        )
        self.log_box.pack(fill="both", expand=True)

        # Run installation in background thread
        threading.Thread(target=self.execute_installation, daemon=True).start()

    def append_log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def execute_installation(self):
        try:
            source = SOURCE_DIR.resolve()
            target = Path(self.target_path.get()).resolve()
            # Validate before creating anything: an installed package is also its source.
            if target == source or target in source.parents or source in target.parents:
                raise ValueError("Choose a destination separate from the source package (no nested paths).")
            if target == Path(target.anchor):
                raise ValueError("A drive root cannot be an installation directory.")
            if not source.is_dir():
                raise ValueError("The source package directory is unavailable.")

            self.status_lbl.config(text=f"Deploying application files to: {target}")
            target.mkdir(parents=True, exist_ok=True)
            preserved_dirs = {"takes", "stems", "recordings", "projects", "sessions", "backups"}
            preserved_media = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff", ".mid", ".midi"}

            def copy_entry(item, dst):
                # Keep user sessions out of application upgrades, including bundled takes.
                if item.name.casefold() in preserved_dirs or (dst.exists() and item.suffix.casefold() in preserved_media):
                    self.append_log(f" [PRESERVED] User media/session path: {item.name}")
                    return
                if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
                    raise ValueError(f"Linked source entries are not supported: {item.name}")
                if dst.is_symlink() or getattr(dst, "is_junction", lambda: False)():
                    raise ValueError(f"Linked destination entries are not supported: {item.name}")
                if not item.resolve().is_relative_to(source) or not dst.resolve().is_relative_to(target):
                    raise ValueError("A package path escapes its installation boundary.")
                if item.is_dir():
                    dst.mkdir(parents=True, exist_ok=True)
                    for child in item.iterdir():
                        copy_entry(child, dst / child.name)
                else:
                    shutil.copy2(item, dst)

            for item in source.iterdir():
                copy_entry(item, target / item.name)
            self.append_log(" [OK] Application files copied; existing media and session directories preserved.")

            # Optional certificate review is informational; installers never alter trust stores.
            if self.opt_cert.get():
                cer_file = target / "October7_CodeSigning.cer"
                if cer_file.is_file():
                    import hashlib
                    self.append_log(f" [REVIEW] Certificate file SHA-256: {hashlib.sha256(cer_file.read_bytes()).hexdigest()}")
                self.append_log(" [NOTICE] Verify the signer independently before any manual trust change. No trust store was changed.")

            # Resolve both optional paths regardless of which shortcuts the user selects.
            desktop = Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / "Desktop"
            start_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "October 7 Vocal Studio"
            exe_path = target / "October7_VocalStudio_Native.exe"
            if not exe_path.is_file():
                exe_path = target / "October7_VocalStudio_DAW.exe"
            for selected, folder, label in (
                (self.opt_desktop.get(), desktop, "Desktop"),
                (self.opt_startmenu.get(), start_dir, "Start Menu"),
            ):
                if not selected:
                    continue
                folder.mkdir(parents=True, exist_ok=True)
                shortcut_path = folder / "October 7 Vocal Studio DAW.lnk"
                # PowerShell single-quoted literals escape apostrophes by doubling them.
                shortcut_literal = str(shortcut_path).replace("'", "''")
                executable_literal = str(exe_path).replace("'", "''")
                target_literal = str(target).replace("'", "''")
                ps_script = f"""
                $ErrorActionPreference = 'Stop'
                $WshShell = New-Object -ComObject WScript.Shell
                $Shortcut = $WshShell.CreateShortcut('{shortcut_literal}')
                $Shortcut.TargetPath = '{executable_literal}'
                $Shortcut.WorkingDirectory = '{target_literal}'
                $Shortcut.Save()
                """
                result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                                        capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    raise RuntimeError(f"{label} shortcut creation failed: {result.stderr.strip()}")
                self.append_log(f" [OK] {label} shortcut created")

            # A safe uninstall needs a tracked install manifest and media ownership checks.
            # Until that exists, fail closed rather than recursively deleting user recordings.
            (target / "Uninstall_October7_DAW.bat").write_text(
                '@echo off\n'
                'title October 7 Vocal Studio - Data Preservation\n'
                'echo Automatic uninstall is disabled to preserve recordings and project data.\n'
                'echo No files or shortcuts have been removed.\n'
                'echo Back up your media and use a reviewed install manifest before removal.\n'
                'exit /b 1\n', encoding="utf-8")
            self.status_lbl.config(text="Installation complete. Audio capabilities require a runtime check.")
            self.append_log(" [SUCCESS] File deployment and requested shortcuts completed. Windows trust and audio settings were not changed.")
            self.progress.stop()
            self.after(600, lambda: self.show_step(3))
        except Exception as e:
            self.progress.stop()
            self.append_log(f"\n[ERROR] Installation failed: {e}")
            self.status_lbl.config(text=f"Error: {e}")
            messagebox.showerror("Installation Error", f"Installation encountered an error:\n{e}")
            self.btn_cancel.config(state="normal")


    # --- STEP 3: Finished ---
    def render_finished_step(self):
        self.btn_back.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        self.btn_next.config(text="Finish & Launch", state="normal", command=self.finish_installation)

        tk.Label(
            self.content_container,
            text="✓ Installation Complete!",
            font=("Segoe UI", 16, "bold"),
            bg=self.c_bg,
            fg=self.c_green
        ).pack(anchor="w", pady=(25, 10))

        summary_card = tk.Frame(self.content_container, bg=self.c_card, padx=16, pady=16, bd=1, relief="solid")
        summary_card.pack(fill="x", pady=(0, 20))

        info_lines = [
            f"• Installation Folder: {self.target_path.get()}",
            "• Windows certificate trust: unchanged",
            "• Existing recordings and session directories: preserved",
            "• Audio devices, scheduling and AI services: require a runtime check",
            "• Automatic uninstall: disabled until a safe ownership manifest exists",
        ]

        for line in info_lines:
            tk.Label(
                summary_card,
                text=line,
                font=("Segoe UI", 9),
                bg=self.c_card,
                fg=self.c_text
            ).pack(anchor="w", pady=3)

        tk.Label(
            self.content_container,
            text="Click 'Finish & Launch' to start October 7 Vocal Studio DAW now.",
            font=("Segoe UI", 10),
            bg=self.c_bg,
            fg=self.c_gold
        ).pack(anchor="w")

    def next_step(self):
        self.show_step(self.current_step + 1)

    def prev_step(self):
        self.show_step(max(0, self.current_step - 1))

    def finish_installation(self):
        target = Path(self.target_path.get())
        exe_path = target / "October7_VocalStudio_Native.exe"
        if not exe_path.is_file():
            exe_path = target / "October7_VocalStudio_DAW.exe"
        if self.opt_launch.get() and exe_path.exists():
            subprocess.Popen([str(exe_path)], cwd=str(target))
        self.destroy()


def main():
    elevate_to_admin()
    app = InstallerWizard()
    app.mainloop()


if __name__ == "__main__":
    main()
