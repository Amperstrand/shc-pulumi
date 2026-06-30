"""Pytest fixtures shared across the shc-pulumi test suite.

Every fixture here returns a fully-mocked SHCClient so that no test ever
reaches the real SHC API.  The ``mock_client`` fixture is the single source
of truth for the canned API responses used throughout the test suite.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _build_mock_client() -> MagicMock:
    """Return a MagicMock configured to look like an SHCClient."""
    client = MagicMock(name="SHCClient")

    # submit_order -> service_ids list (as returned by the SHC API)
    client.submit_order.return_value = {
        "service_ids": [123],
        "service_id": 123,
    }

    # get_vm -> an active, provisioned VM with one IPv4.
    client.get_vm.return_value = {
        "hostname": "test",
        "service_status": "active",
        "provisioning_state": "ready",
        "ips": [{"ip": "1.2.3.4"}],
        "os_user": "debian",
    }

    # cancel_vm -> canceled status.
    client.cancel_vm.return_value = {"service_status": "canceled"}

    # VM power management.
    client.start_vm.return_value = {"service_status": "active"}
    client.stop_vm.return_value = {"service_status": "stopped"}

    # apply_ssh_key_live -> no-op success.
    client.apply_ssh_key_live.return_value = {}

    # Snapshot lifecycle.
    client.list_snapshots.return_value = [{"id": "snap-1", "name": "test"}]
    client.create_snapshot.return_value = {"id": "snap-1", "name": "test"}
    client.delete_snapshot.return_value = {}

    # Firewall lifecycle.
    client.get_firewall.return_value = {
        "rules": [
            {
                "position": 5,
                "action": "accept",
                "protocol": "tcp",
                "dest_port": "22",
                "source": "0.0.0.0/0",
                "direction": "in",
                "name": "allow-ssh",
            },
        ],
    }
    client.create_firewall_rule.return_value = {"position": 5}
    client.delete_firewall_rule.return_value = {}

    # rDNS lifecycle.
    client.list_rdns.return_value = [
        {"ip": "1.2.3.4", "ptr": "mail.example.com"},
    ]
    client.set_rdns.return_value = {"job_id": "job-42"}
    client.clear_rdns.return_value = {}

    # Catalog (used by get_plan / test_catalog).
    client.get_catalog.return_value = [
        {
            "package_id": 23,
            "name": "NVMe VPS - Starter",
            "pricing": [
                {"period": "day", "pricing_id": 55},
                {"period": "month", "pricing_id": 56},
            ],
        },
        {
            "package_id": 81,
            "name": "NVMe VPS - Standard",
            "pricing": [
                {"period": "day", "pricing_id": 245},
                {"period": "month", "pricing_id": 246},
            ],
        },
    ]

    return client


@pytest.fixture()
def mock_client() -> MagicMock:
    """A MagicMock that behaves like SHCClient with canned responses.

    Each method's ``return_value`` matches the SHC API contract. Tests that
    need a non-default response simply set the attribute on the returned
    object (e.g. ``mock_client.get_vm.return_value = {...}``).
    """
    return _build_mock_client()
