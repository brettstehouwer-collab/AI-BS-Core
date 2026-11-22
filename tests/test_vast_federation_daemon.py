"""Unit tests for VastFederationDaemon."""

import pytest
from unittest.mock import patch, MagicMock
from backend.core.cluster.vast_federation_daemon import VastFederationDaemon, FederatedNode


@pytest.fixture
def federation_daemon():
    daemon = VastFederationDaemon()
    daemon.active_nodes.clear()
    return daemon


def test_initialization(federation_daemon):
    assert federation_daemon is not None
    assert isinstance(federation_daemon.active_nodes, dict)
    assert federation_daemon.max_hourly_rate_usd > 0


def test_search_spot_offers_simulated(federation_daemon):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"id": 12345, "gpu_name": "RTX 4090", "num_gpus": 1, "gpu_ram": 24576, "dph_total": 0.22, "cpu_cores": 16, "dlperf": 35.5, "inet_down": 500, "inet_up": 500, "reliability2": 0.99, "host_id": 999}]',
        )
        offers = federation_daemon.search_spot_offers(min_vram_gb=16.0, max_price_usd=0.30)
        assert len(offers) == 1
        assert offers[0]["offer_id"] == "12345"
        assert offers[0]["gpu_name"] == "RTX 4090"
        assert offers[0]["dph_usd"] == 0.22


def test_provision_simulated_zero_cost(federation_daemon):
    # Under default zero-cost mandate (cloud_burst_enabled=False), it should provision in simulated mode
    with patch.object(federation_daemon, "_get_burst_engine_policy", return_value={"cloud_burst_enabled": False}):
        res = federation_daemon.provision_federated_node(offer_id="test_offer_999", disk_gb=30)
        assert res["status"] == "PROVISIONED_SIMULATED"
        assert "Zero-Cost Mandate Active" in res["message"]
        node_id = res["node"]["node_id"]
        assert node_id in federation_daemon.active_nodes

        # Check cluster status
        status = federation_daemon.get_cluster_status()
        assert status["cluster_nodes_count"] == 1
        assert status["total_federated_vram_gb"] == 24.0
        assert status["total_hourly_burn_usd"] == 0.00

        # Terminate node
        term_res = federation_daemon.terminate_federated_node(node_id)
        assert term_res["status"] == "SUCCESS"
        assert node_id not in federation_daemon.active_nodes
