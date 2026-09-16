import os
import logging


class FileSystemTool:
    def __init__(self, safe_dir: str = None):
        if safe_dir is None:
            safe_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "sandbox")
            )
        self.safe_dir = safe_dir

        # Lock file writes to a specific directory to prevent OS damage
        os.makedirs(self.safe_dir, exist_ok=True)

    def write_file(self, relative_path: str, content: str) -> str:
        """Safely writes multi-line code to the local filesystem."""
        try:
            # Prevent directory traversal attacks (e.g., "../../windows/system32")
            safe_path = os.path.abspath(os.path.join(self.safe_dir, relative_path))
            if not safe_path.startswith(os.path.abspath(self.safe_dir)):
                return "[TOOL ERROR]: Security violation. Cannot write outside sandbox."

            # Ensure subdirectories exist
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)

            with open(safe_path, "w", encoding="utf-8") as f:
                # Strip out escaped newlines that the LLM might output improperly
                clean_content = content.replace("\\n", "\n")
                f.write(clean_content)

            logging.info(f"💾 File Written Successfully: {safe_path}")
            return f"[SUCCESS]: File written to {safe_path}"
        except Exception as e:
            return f"[TOOL ERROR]: Failed to write file. {str(e)}"
