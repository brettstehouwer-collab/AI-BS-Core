"""Tier 3 Pairwise Test P06: Distributed Training Driver (F08) + Dataproc Template (F09).

Validates that Dataproc Serverless template specifies runtime configs and dynamic executor
allocations compatible with the distributed PyTorch and MLlib drivers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths


@pytest.mark.tier3
class TestP06DriverDataprocTemplate:
    """Pairwise F08 x F09: Distributed Training Driver and Dataproc Serverless Template."""

    def test_p06_dataproc_template_runtime_and_executors(self, platform_paths: PlatformPaths) -> None:
        """Verify Dataproc session template defines dynamic executor scaling and runtime 2.2."""
        template_file = platform_paths.distributed_training_dir / "dataproc_serverless_session_template.json"
        assert template_file.exists(), f"Dataproc template missing at {template_file}"

        with open(template_file, "r", encoding="utf-8") as f:
            tpl = json.load(f)

        assert "runtimeConfig" in tpl
        rc = tpl["runtimeConfig"]
        assert rc.get("version") == "2.2"

        props = rc.get("properties", {})
        assert props.get("spark.dynamicAllocation.enabled") == "true"
        assert int(props.get("spark.dynamicAllocation.maxExecutors", 0)) >= 8

    def test_p06_dataproc_template_environment_and_service_account(self, platform_paths: PlatformPaths) -> None:
        """Verify environmentConfig defines staging bucket, service account, and TTL."""
        template_file = platform_paths.distributed_training_dir / "dataproc_serverless_session_template.json"
        with open(template_file, "r", encoding="utf-8") as f:
            tpl = json.load(f)

        assert "environmentConfig" in tpl
        ec = tpl["environmentConfig"]
        exec_cfg = ec.get("executionConfig", {})
        assert "serviceAccount" in exec_cfg
        assert "stagingBucket" in exec_cfg
        assert "ttl" in exec_cfg
