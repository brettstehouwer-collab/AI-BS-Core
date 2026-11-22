"""Tier 1 Feature 17: Vite Frontend Build & Dev Audit.

Requirement: Vite development server on port 5173 responding 200 OK and
production build compiling with 0 errors, generating dist/index.html and asset bundles.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import HttpClientHelper, PlatformPaths


@pytest.mark.tier1
@pytest.mark.feature(17)
@pytest.mark.feature_17
class TestF17ViteFrontendAudit:
    """Feature 17: Vite Frontend Build & Dev Audit Test Suite."""

    def test_f17_vite_dev_server_responds_200(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify Vite development server on port 5173 responds 200 OK with HTML."""
        url = platform_paths.frontend_url
        resp = http_client.get(url, timeout=5.0)
        resp.assert_ok(f"Vite dev server unreachable at {url}")

        body_lower = resp.text.lower()
        assert "<!doctype html" in body_lower or "<html" in body_lower, "Response is not an HTML document"
        assert "<div id=\"root\"" in body_lower or "root" in body_lower, "Vite index template root container missing"

    def test_f17_production_build_artifacts_exist(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify production build directory frontend/dist contains index.html and assets."""
        dist_dir = platform_paths.base_dir / "frontend" / "dist"
        assert dist_dir.exists(), f"Frontend dist directory missing: {dist_dir}"
        assert dist_dir.is_dir(), f"dist path is not a directory: {dist_dir}"

        index_file = dist_dir / "index.html"
        assert index_file.exists(), f"Production dist/index.html missing: {index_file}"
        assert index_file.stat().st_size > 500, "dist/index.html appears truncated or empty"

        content = index_file.read_text(encoding="utf-8", errors="replace")
        assert "<!doctype html" in content.lower() or "<html" in content.lower()

        assets_dir = dist_dir / "assets"
        assert assets_dir.exists(), f"Compiled assets directory missing: {assets_dir}"
        asset_files = list(assets_dir.glob("*"))
        assert len(asset_files) > 0, "No bundled JS/CSS assets found in frontend/dist/assets"

    def test_f17_package_json_scripts_contract(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify package.json registers all mandatory build, dev, and mirror scripts."""
        package_json = platform_paths.base_dir / "frontend" / "package.json"
        assert package_json.exists(), f"package.json missing: {package_json}"

        with open(package_json, "r", encoding="utf-8") as f:
            pkg = json.load(f)

        assert "scripts" in pkg, "package.json missing 'scripts' section"
        scripts = pkg["scripts"]

        assert "dev" in scripts, "Missing 'dev' script in package.json"
        assert "build" in scripts, "Missing 'build' script in package.json"
        assert "sync-mirrors" in scripts, "Missing 'sync-mirrors' script in package.json"
        assert "5173" in scripts["dev"], "Dev script must bind port 5173"

    def test_f17_vite_config_architecture(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify vite.config.js exists and configures build and development options."""
        vite_config = platform_paths.base_dir / "frontend" / "vite.config.js"
        assert vite_config.exists(), f"vite.config.js missing: {vite_config}"

        code = vite_config.read_text(encoding="utf-8", errors="replace")
        assert "defineConfig" in code or "export default" in code
        assert len(code) > 200, "vite.config.js content is unexpectedly brief"

    def test_f17_dev_server_serves_static_headers(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify dev server returns appropriate Content-Type header text/html."""
        url = f"{platform_paths.frontend_url}/"
        resp = http_client.get(url, timeout=5.0)
        resp.assert_ok()

        content_type = resp.headers.get("Content-Type") or resp.headers.get("content-type") or ""
        assert "text/html" in content_type, f"Expected text/html Content-Type, got '{content_type}'"

    def test_f17_m5_audit_vite_pass(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify Vite subsystem passed in M5 audit report with 0 failures."""
        report_json = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_json.exists(), f"M5 report missing: {report_json}"

        with open(report_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        vite_sub = data.get("subsystems", {}).get("vite", {})
        assert vite_sub.get("passed") is True, f"Vite audit failed: {vite_sub.get('failures')}"
        assert len(vite_sub.get("failures", [])) == 0, f"Unexpected failures in Vite audit: {vite_sub.get('failures')}"
