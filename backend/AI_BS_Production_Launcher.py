import os
import sys
import subprocess


class AI_BS_Production_Installer:
    def __init__(self):
        # Resolve the directory correctly whether running from source or as a compiled PyInstaller executable
        if getattr(sys, "frozen", False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # Define possible locations depending on where the user places the AI-BS.exe file
        possible_paths = [
            # Hardcoded ultimate fallbacks (guarantees it works even if AI-BS.exe is copied to the Desktop)
            r"G:\Stehouwer_Server\AI-BS\frontend\release\win-unpacked\AI-BS Setup.exe",
            # Relative paths
            os.path.abspath(
                os.path.join(
                    self.base_dir,
                    "..",
                    "..",
                    "frontend",
                    "release",
                    "win-unpacked",
                    "AI-BS Setup.exe",
                )
            ),
            os.path.abspath(
                os.path.join(
                    self.base_dir,
                    "frontend",
                    "release",
                    "win-unpacked",
                    "AI-BS Setup.exe",
                )
            ),
            os.path.abspath(
                os.path.join(
                    self.base_dir,
                    "AI-BS",
                    "frontend",
                    "release",
                    "win-unpacked",
                    "AI-BS Setup.exe",
                )
            ),
        ]

        self.frontend_exe = None
        for p in possible_paths:
            if os.path.exists(p):
                self.frontend_exe = p
                break

    def run(self):
        print("==================================================")
        print("    INITIALIZING AI-BS PRODUCTION ECOSYSTEM       ")
        print("==================================================")
        print("Launching the AI-BS Universal Application...")

        if self.frontend_exe:
            # Launch the electron frontend, which handles Ollama, ComfyUI, and the Backend automatically in logical order
            subprocess.Popen([self.frontend_exe])
            print(f"System launched successfully from: {self.frontend_exe}")
            print(
                "The AI-BS Interface is opening. You may safely close this terminal window."
            )
        else:
            print("[Error] Could not find the frontend application.")
            print("Searched locations relative to: ", self.base_dir)
            print("Please ensure the frontend has been built using electron-builder.")
            input("Press Enter to exit...")


if __name__ == "__main__":
    installer = AI_BS_Production_Installer()
    installer.run()
