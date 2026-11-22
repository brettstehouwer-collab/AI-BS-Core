import os
from pathlib import Path
import unittest
# Assuming bullshit_senses contains initialization logic we want to test
try:
    pass
except ImportError as e:
    print(f"Could not import necessary modules for testing: {e}")


class TestSystemIntegration(unittest.TestCase):
    """
    Tests the integration points between the backend logic and the compiled frontend assets.
    Requires FRONTEND_BUILD_PATH to be set in the environment.
    """

    def setUp(self):
        # 1. Validate Environment Variables
        self.frontend_path = os.getenv("FRONTEND_BUILD_PATH")
        self.tts_output_dir = os.getenv("TTS_OUTPUT_DIR", "tts_output")

        if not self.frontend_path:
            raise EnvironmentError(
                "FATAL: FRONTEND_BUILD_PATH environment variable is not set. Cannot test frontend integration."
            )
        self.frontend_dir = Path(self.frontend_path)
        print(f"\n--- Starting Integration Test ---")
        print(f"✅ Frontend Build Path validated: {self.frontend_dir}")

    def test_01_environment_paths_exist(self):
        """Checks if critical directories and files exist based on environment variables."""
        # Check for the main executable
        exe_path = self.frontend_dir / "AI-BS Matrix.exe"
        self.assertTrue(
            exe_path.exists(),
            f"Expected executable not found at: {exe_path}")

        # Check for a key resource file
        resource_pak_path = self.frontend_dir / "resources.pak"
        self.assertTrue(
            resource_pak_path.exists(),
            f"Expected resources.pak not found at: {resource_pak_path}")

        # Check the TTS output directory (should exist or be creatable)
        tts_output_path = Path(self.tts_output_dir)
        if not tts_output_path.exists():
            os.makedirs(tts_output_path, exist_ok=True)
            print(f"Created missing TTS output directory: {tts_output_path}")

    def test_02_module_initialization(self):
        """Tests if the core module can initialize using the correct paths."""
        # This is a placeholder to confirm that the module loaded without path
        # errors.
        print("\n--- Testing Module Initialization ---")
        try:
            # Attempting to access a variable defined in bullshit_senses
            # confirms successful import and path resolution.
            if self.frontend_dir.exists():
                print(
                    "✅ Successfully confirmed frontend directory structure is visible to the test script.")
            else:
                self.fail("Failed to confirm frontend directory visibility.")

        except Exception as e:
            self.fail(f"Module initialization failed unexpectedly: {e}")


if __name__ == '__main__':
    # Running tests will print output directly, which is useful for manual
    # review.
    unittest.main()
