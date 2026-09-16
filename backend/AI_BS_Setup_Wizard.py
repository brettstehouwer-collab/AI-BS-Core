import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import subprocess
import time


class AI_BS_Setup_Wizard:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-BS Setup Wizard")
        self.root.geometry("520x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#121212")

        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use("default")

        # Custom Progressbar Style
        self.style.configure(
            "Colored.Horizontal.TProgressbar",
            troughcolor="#1e1e1e",
            background="#0078D7",
            thickness=8,
            borderwidth=0,
        )

        # Determine the bundled data path
        if hasattr(sys, "_MEIPASS"):
            self.bundled_exe_path = os.path.join(sys._MEIPASS, "AI-BS.exe")
        else:
            self.bundled_exe_path = os.path.join(
                os.path.dirname(__file__), "dist", "AI-BS.exe"
            )

        # Default install directory
        user_profile = os.environ.get("USERPROFILE", "C:\\")
        self.install_dir = tk.StringVar(
            value=os.path.join(user_profile, "AI-BS_Matrix")
        )

        self.build_ui()

    def build_ui(self):
        # Header Frame
        header_frame = tk.Frame(self.root, bg="#1e1e1e", height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="AI-BS Ecosystem Setup",
            font=("Segoe UI", 16, "bold"),
            fg="#ffffff",
            bg="#1e1e1e",
        ).pack(side=tk.LEFT, padx=20, pady=18)

        # Glowing accent border under header
        accent_line = tk.Frame(self.root, bg="#0078D7", height=2)
        accent_line.pack(fill=tk.X)

        # Body Frame
        body_frame = tk.Frame(self.root, bg="#121212", padx=25, pady=20)
        body_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body_frame,
            text="Welcome to the sovereign local multi-agent build system installation.",
            font=("Segoe UI", 10),
            fg="#b0b0b0",
            bg="#121212",
            wraplength=470,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 15))

        tk.Label(
            body_frame,
            text="Installation Path:",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#121212",
        ).pack(anchor=tk.W, pady=(10, 5))

        # Path Selection Frame
        path_frame = tk.Frame(body_frame, bg="#121212")
        path_frame.pack(fill=tk.X)

        # Custom Entry-like read-only Label to support dark theme styling
        # easily
        self.entry_var_label = tk.Label(
            path_frame,
            textvariable=self.install_dir,
            font=("Segoe UI", 10),
            fg="#e0e0e0",
            bg="#1e1e1e",
            anchor="w",
            padx=10,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#333333",
        )
        self.entry_var_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        self.browse_btn = tk.Button(
            path_frame,
            text="Browse...",
            font=("Segoe UI", 9, "bold"),
            bg="#333333",
            fg="#ffffff",
            activebackground="#444444",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=15,
            command=self.browse_dir,
        )
        self.browse_btn.pack(side=tk.RIGHT, padx=(10, 0), ipady=3)
        self.bind_hover(self.browse_btn, "#333333", "#444444")

        # Progress & Status
        tk.Label(
            body_frame,
            text="Deployment Status:",
            font=("Segoe UI", 9, "bold"),
            fg="#888888",
            bg="#121212",
        ).pack(anchor=tk.W, pady=(25, 2))

        self.status_text_var = tk.StringVar(value="Ready to deploy.")
        self.status_msg_label = tk.Label(
            body_frame,
            textvariable=self.status_text_var,
            font=("Segoe UI", 9, "italic"),
            fg="#0078D7",
            bg="#121212",
        )
        self.status_msg_label.pack(anchor=tk.W, pady=(0, 5))

        self.progress = ttk.Progressbar(
            body_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            style="Colored.Horizontal.TProgressbar",
        )
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Footer Frame
        footer_frame = tk.Frame(self.root, bg="#1e1e1e", pady=12, padx=25)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.install_btn = tk.Button(
            footer_frame,
            text="Install",
            font=("Segoe UI", 10, "bold"),
            width=12,
            bg="#0078D7",
            fg="#ffffff",
            activebackground="#005A9E",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            command=self.start_install_thread,
        )
        self.install_btn.pack(side=tk.RIGHT)
        self.bind_hover(self.install_btn, "#0078D7", "#005A9E")

        self.cancel_btn = tk.Button(
            footer_frame,
            text="Cancel",
            font=("Segoe UI", 10),
            width=10,
            bg="#2d2d2d",
            fg="#b0b0b0",
            activebackground="#3d3d3d",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            command=self.root.quit,
        )
        self.cancel_btn.pack(side=tk.RIGHT, padx=10)
        self.bind_hover(self.cancel_btn, "#2d2d2d", "#3d3d3d")

    def bind_hover(self, widget, normal_color, hover_color):
        widget.bind(
            "<Enter>",
            lambda e: (
                widget.config(bg=hover_color) if widget["state"] == tk.NORMAL else None
            ),
        )
        widget.bind(
            "<Leave>",
            lambda e: (
                widget.config(bg=normal_color) if widget["state"] == tk.NORMAL else None
            ),
        )

    def browse_dir(self):
        directory = filedialog.askdirectory(
            initialdir=self.install_dir.get(), title="Select Installation Folder"
        )
        if directory:
            self.install_dir.set(os.path.join(directory, "AI-BS_Matrix"))

    def create_desktop_shortcut(self, target_exe):
        try:
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut_path = os.path.join(desktop, "AI-BS.lnk")

            ps_script = f"""
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{target_exe}"
            $Shortcut.Description = "AI-BS Central Matrix"
            $Shortcut.Save()
            """
            subprocess.run(
                ["powershell", "-Command", ps_script],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        except Exception as e:
            print(f"Shortcut Error: {e}")
            return False

    def install_logic(self):
        target_dir = self.install_dir.get()
        target_exe = os.path.join(target_dir, "AI-BS.exe")

        try:
            # 1. Verify bundled exe
            self.status_text_var.set("Verifying installation package...")
            self.progress["value"] = 10
            time.sleep(0.5)

            if not os.path.exists(self.bundled_exe_path):
                messagebox.showerror(
                    "Installation Error",
                    "The bundled AI-BS.exe could not be found inside the setup package!",
                )
                self.reset_ui()
                return

            # 2. Create Directory
            self.status_text_var.set(f"Creating directory: {target_dir}")
            os.makedirs(target_dir, exist_ok=True)
            self.progress["value"] = 30
            time.sleep(0.5)

            # 3. Copy Executable
            self.status_text_var.set("Extracting and installing AI-BS ecosystem...")
            shutil.copy2(self.bundled_exe_path, target_exe)
            self.progress["value"] = 70
            time.sleep(1.0)  # Simulate extraction time for massive .exe

            # 4. Create Shortcut
            self.status_text_var.set("Generating Desktop Shortcut...")
            self.create_desktop_shortcut(target_exe)
            self.progress["value"] = 90
            time.sleep(0.5)

            # 5. Finish
            self.status_text_var.set("Installation Complete!")
            self.status_msg_label.config(fg="#4CAF50")
            self.progress["value"] = 100

            self.install_btn.config(text="Finish", command=self.root.quit, bg="#4CAF50")
            self.bind_hover(self.install_btn, "#4CAF50", "#45a049")
            self.cancel_btn.config(state=tk.DISABLED, bg="#1e1e1e")
            messagebox.showinfo(
                "Success", "AI-BS has been successfully installed to your system!"
            )

        except Exception as e:
            messagebox.showerror(
                "Fatal Error", f"An error occurred during installation:\n\n{
                    str(e)}"
            )
            self.reset_ui()

    def reset_ui(self):
        self.install_btn.config(state=tk.NORMAL, bg="#0078D7")
        self.status_text_var.set("Ready to deploy.")
        self.status_msg_label.config(fg="#0078D7")
        self.progress["value"] = 0

    def start_install_thread(self):
        self.install_btn.config(state=tk.DISABLED, bg="#1e1e1e")
        threading.Thread(target=self.install_logic, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = AI_BS_Setup_Wizard(root)
    root.mainloop()
