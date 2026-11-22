"""Tier 1 Feature Coverage Tests: Feature 9 - Dataproc Serverless Template.

Tests schema compliance of dataproc_serverless_session_template.json against
Google Cloud Dataproc v1 REST API specifications, execution config,
dynamic allocation properties, and Jupyter session configurations.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Ensure tests/e2e root is on sys.path
E2E_ROOT = Path(__file__).resolve().parent.parent
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

import pytest
from conftest import PlatformPaths


@pytest.mark.tier1
@pytest.mark.feature_9
@pytest.mark.feature(9)
class TestF09DataprocServerlessTemplate:
    """Test suite for Feature 9: Dataproc Serverless Session Template."""

    @pytest.fixture(scope="class")
    def template_data(self, platform_paths: PlatformPaths) -> dict:
        """Load and parse the Dataproc Serverless session template JSON."""
        template_file = platform_paths.distributed_training_dir / "dataproc_serverless_session_template.json"
        assert template_file.exists(), f"Session template file missing: {template_file}"
        with open(template_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_f09_template_json_exists_and_valid(self, template_data: dict) -> None:
        """Verify session template exists, parses as valid JSON dictionary."""
        assert isinstance(template_data, dict), "Template JSON must parse as a dictionary"
        assert "name" in template_data, "Template JSON missing 'name' attribute"

    def test_f09_resource_name_conforms_to_dataproc_rest_uri(self, template_data: dict) -> None:
        """Verify template resource name conforms to Dataproc v1 REST URI pattern."""
        name = template_data.get("name", "")
        pattern = r"^projects/[a-zA-Z0-9-_]+/locations/[a-zA-Z0-9-_]+/sessionTemplates/[a-zA-Z0-9-_]+$"
        assert re.match(pattern, name), f"Invalid Dataproc SessionTemplate name: {name}"

    def test_f09_labels_specification(self, template_data: dict) -> None:
        """Verify labels dictionary contains required operational tags."""
        labels = template_data.get("labels", {})
        assert labels.get("workload") == "distributed-training"
        assert labels.get("framework") == "pyspark-pytorch"
        assert labels.get("managed-by") == "ai-bs-system"
        assert "tier" in labels

    def test_f09_execution_config_contract(self, template_data: dict) -> None:
        """Verify executionConfig contains valid serviceAccount, stagingBucket, TTL, and network tags."""
        env_config = template_data.get("environmentConfig", {})
        assert "executionConfig" in env_config, "Missing environmentConfig.executionConfig"
        exec_config = env_config["executionConfig"]

        sa = exec_config.get("serviceAccount", "")
        assert "@" in sa and sa.endswith(".iam.gserviceaccount.com"), f"Invalid service account format: {sa}"

        staging_bucket = exec_config.get("stagingBucket", "")
        assert staging_bucket.startswith("gs://"), f"Invalid staging bucket URI: {staging_bucket}"

        ttl = exec_config.get("ttl", "")
        assert re.match(r"^\d+s$", ttl), f"Invalid TTL duration format: {ttl}"

        tags = exec_config.get("networkTags", [])
        assert isinstance(tags, list) and len(tags) > 0, "networkTags must be non-empty list"

    def test_f09_runtime_dynamic_allocation_properties(self, template_data: dict) -> None:
        """Verify runtime version and Spark dynamic allocation properties [2..32]."""
        runtime = template_data.get("runtimeConfig", {})
        assert runtime.get("version") == "2.2", f"Unexpected runtime version: {runtime.get('version')}"

        props = runtime.get("properties", {})
        assert props.get("spark.dynamicAllocation.enabled") == "true"
        assert int(props.get("spark.dynamicAllocation.minExecutors", 0)) == 2
        assert int(props.get("spark.dynamicAllocation.maxExecutors", 0)) == 32
        assert int(props.get("spark.dynamicAllocation.initialExecutors", 0)) >= 2

    def test_f09_executor_and_driver_compute_specs(self, template_data: dict) -> None:
        """Verify 4 cores and 16g memory configured for both driver and executors."""
        props = template_data.get("runtimeConfig", {}).get("properties", {})
        assert props.get("spark.executor.cores") == "4"
        assert props.get("spark.executor.memory") == "16g"
        assert props.get("spark.driver.cores") == "4"
        assert props.get("spark.driver.memory") == "16g"

    def test_f09_jupyter_session_and_pip_packages(self, template_data: dict) -> None:
        """Verify Jupyter kernel is PYTHON and driver PIP_PACKAGES includes ML libraries."""
        jupyter = template_data.get("jupyterSession", {})
        assert jupyter.get("kernel") == "PYTHON"
        assert len(jupyter.get("displayName", "")) > 0

        props = template_data.get("runtimeConfig", {}).get("properties", {})
        pip_pkgs = props.get("spark.dataproc.driverEnv.PIP_PACKAGES", "")
        for pkg in ["torch", "scikit-learn", "numpy", "pandas", "pyarrow"]:
            assert pkg in pip_pkgs, f"Missing required ML pip package in template: {pkg}"
