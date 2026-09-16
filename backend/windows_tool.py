import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Windows Tool] %(message)s")


class WindowsIntegrationTool:
    def __init__(self, workspace_path: str = "C:\\AI-BS"):
        self.workspace_path = workspace_path
        # Optional: Add a blacklist of catastrophic commands (e.g., format C:)
        self.banned_commands = [
            "format",
            "del /f /s /q c:\\",
            "Remove-Item -Recurse C:\\",
        ]

    def execute(self, command: str) -> str:
        """Executes a Windows command and returns the terminal output."""
        # 1. Safety Screen
        for banned in self.banned_commands:
            if banned.lower() in command.lower():
                return f"[TOOL ERROR]: Command '{banned}' is blacklisted for safety."

        logging.info(f"🤖 AI-BS executing command: {command}")

        # 2. Execute via PowerShell for maximum native IDE compatibility
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=10,  # Hard 10-second kill switch
            )

            output = result.stdout.strip()
            error = result.stderr.strip()

            if result.returncode != 0:
                return f"[COMMAND FAILED] Exit Code: {result.returncode}\nStderr: {error}\nStdout: {output}"

            return (
                output if output else "[Command executed successfully with no output]"
            )

        except subprocess.TimeoutExpired:
            return "[TOOL ERROR]: Command timed out after 10 seconds. (Did you run a blocking process?)"
        except Exception as e:
            return f"[TOOL ERROR]: {str(e)}"
