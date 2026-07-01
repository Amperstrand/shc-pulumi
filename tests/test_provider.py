"""Unit tests for SHCVMProvider and SHCSnapshotProvider.

All SHC API calls are mocked via the ``mock_client`` fixture defined in
``conftest.py``.  These tests exercise the provider lifecycle logic
(create / read / delete / diff) without making any real network calls.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from shc_pulumi.provider import SHCVMProvider
from shc_pulumi.snapshot import SHCSnapshotProvider


# ---------------------------------------------------------------------------
# SHCVMProvider lifecycle
# ---------------------------------------------------------------------------


def test_create_vm(mock_client):
    # Patch SHCClient creation to return mock_client
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.create({
            "hostname": "test-vm",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": False,
        })
        assert result.id == "123"
        assert result.outs["ip"] == "1.2.3.4"
        assert result.outs["hostname"] == "test-vm"


def test_read_vm(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.read("123", {
            "hostname": "test",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
        })
        assert result.outs["ip"] == "1.2.3.4"


def test_delete_vm(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        provider.delete("123", {"hostname": "test", "api_key": "test"})
        mock_client.cancel_vm.assert_called_once_with(123, immediate=True)


def test_diff_replaces_hostname(mock_client):
    provider = SHCVMProvider(api_key="test")
    result = provider.diff("123", {"hostname": "old"}, {"hostname": "new"})
    assert result.changes is True
    assert "hostname" in result.replaces


def test_diff_no_changes(mock_client):
    provider = SHCVMProvider(api_key="test")
    result = provider.diff(
        "123",
        {"hostname": "x", "package_id": 1, "pricing_id": 2},
        {"hostname": "x", "package_id": 1, "pricing_id": 2},
    )
    assert result.changes is False


def test_create_vm_submits_order_with_correct_args(mock_client):
    """The provider should forward hostname/package/pricing to submit_order."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        provider.create({
            "hostname": "my-vm",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": False,
        })
        mock_client.submit_order.assert_called_once_with(
            hostname="my-vm",
            package_id=81,
            pricing_id=245,
        )


def test_create_vm_auto_cancel_schedules_non_immediate(mock_client):
    """When auto_cancel is True, a non-immediate cancel must be scheduled."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        provider.create({
            "hostname": "my-vm",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": True,
        })
        mock_client.cancel_vm.assert_called_once_with(123, immediate=False)


def test_read_vm_returns_empty_when_not_found(mock_client):
    """A SHCError on get_vm should produce an empty ReadResult (resource gone)."""
    from shc_toolkit.client import SHCError

    mock_client.get_vm.side_effect = SHCError("not_found", "no such vm")
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.read("999", {"hostname": "x", "api_key": "test"})
        assert result.id == ""
        assert result.outs is None


def test_diff_package_id_triggers_update_not_replacement(mock_client):
    provider = SHCVMProvider(api_key="test")
    result = provider.diff(
        "1",
        {"hostname": "a", "package_id": 1, "pricing_id": 2},
        {"hostname": "a", "package_id": 2, "pricing_id": 2},
    )
    assert result.changes is True
    assert "package_id" not in result.replaces


# ---------------------------------------------------------------------------
# SHCSnapshotProvider lifecycle
# ---------------------------------------------------------------------------


def test_snapshot_create(mock_client):
    with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
        provider = SHCSnapshotProvider(api_key="test")
        result = provider.create({
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        assert result.id == "snap-1"
        assert result.outs["snapshot_id"] == "snap-1"
        assert result.outs["service_id"] == 123
        assert result.outs["name"] == "test"
        mock_client.create_snapshot.assert_called_once_with(123, name="test")


def test_snapshot_read(mock_client):
    with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
        provider = SHCSnapshotProvider(api_key="test")
        result = provider.read("snap-1", {
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        assert result.id == "snap-1"
        assert result.outs["snapshot_id"] == "snap-1"
        assert result.outs["name"] == "test"
        mock_client.list_snapshots.assert_called_once_with(123)


def test_snapshot_read_missing_returns_empty(mock_client):
    """When the snapshot id is not in list_snapshots, read returns empty."""
    with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
        provider = SHCSnapshotProvider(api_key="test")
        result = provider.read("snap-missing", {
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        assert result.id == ""
        assert result.outs is None


def test_snapshot_delete(mock_client):
    with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
        provider = SHCSnapshotProvider(api_key="test")
        provider.delete("snap-1", {
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        mock_client.delete_snapshot.assert_called_once_with(123, "snap-1")


def test_snapshot_diff_replaces_service_id(mock_client):
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.diff(
        "snap-1",
        {"service_id": 123, "name": "a"},
        {"service_id": 456, "name": "a"},
    )
    assert result.changes is True
    assert "service_id" in result.replaces


def test_snapshot_diff_no_changes(mock_client):
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.diff(
        "snap-1",
        {"service_id": 123, "name": "a"},
        {"service_id": 123, "name": "a"},
    )
    assert result.changes is False


# ---------------------------------------------------------------------------
# SHCVMProvider power management
# ---------------------------------------------------------------------------


def test_create_vm_with_power_state_stopped(mock_client):
    """When power_state is 'stopped', stop_vm must be called after VM is ready."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.create({
            "hostname": "test-vm",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": False,
            "power_state": "stopped",
        })
    assert result.id == "123"
    mock_client.stop_vm.assert_called_once_with(123)


def test_update_power_state(mock_client):
    """The update method must call stop_vm / start_vm when power_state changes."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")

        # running -> stopped: should call stop_vm
        result = provider.update(
            "123",
            {
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "power_state": "stopped",
                "service_id": 123,
            },
            {
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "power_state": "running",
                "service_id": 123,
            },
        )
    mock_client.stop_vm.assert_called_once_with(123)
    assert result.outs["power_state"] == "stopped"

    mock_client.reset_mock()
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.update(
            "123",
            {
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "power_state": "running",
                "service_id": 123,
            },
            {
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "power_state": "stopped",
                "service_id": 123,
            },
        )
    mock_client.start_vm.assert_called_once_with(123)
    assert result.outs["power_state"] == "running"


# ---------------------------------------------------------------------------
# SHCVMProvider in-place upgrade
# ---------------------------------------------------------------------------


def test_update_triggers_upgrade_when_pricing_changes(mock_client):
    """Changing pricing_id must call upgrade_vm with the new pricing_ref."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        provider.update(
            "123",
            {
                "hostname": "test",
                "package_id": 82,
                "pricing_id": 249,
                "api_key": "test",
            },
            {
                "hostname": "test",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
            },
        )
    mock_client.upgrade_vm.assert_called_once_with(123, pricing_ref=249)


def test_update_does_not_upgrade_when_pricing_unchanged(mock_client):
    """No upgrade call when pricing_id is the same."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        provider.update(
            "123",
            {
                "hostname": "test",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
            },
            {
                "hostname": "test",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
            },
        )
    mock_client.upgrade_vm.assert_not_called()


def test_diff_package_id_no_longer_forces_replacement(mock_client):
    """package_id/pricing_id changes should be updates, not replacements."""
    provider = SHCVMProvider(api_key="test")
    result = provider.diff(
        "123",
        {"hostname": "x", "package_id": 81, "pricing_id": 245},
        {"hostname": "x", "package_id": 82, "pricing_id": 249},
    )
    assert result.changes is True
    assert "package_id" not in result.replaces
    assert "pricing_id" not in result.replaces


# ---------------------------------------------------------------------------
# SHCVMProvider NoDNS integration
# ---------------------------------------------------------------------------


def test_create_vm_with_nodns(mock_client):
    """When nodns=True, provision_dns_for_vm must be called and fqdn/nsec set."""
    fake_dns = {
        "fqdn": "npub1abc.nodns.shop",
        "keypair": {"nsec": "nsec1fakekey", "npub": "npub1abc"},
        "success": True,
    }
    mock_nodns = MagicMock()
    mock_nodns.provision_dns_for_vm.return_value = fake_dns
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        with patch.dict(sys.modules, {"shc_toolkit.nodns": mock_nodns}):
            provider = SHCVMProvider(api_key="test")
            result = provider.create({
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "auto_cancel": False,
                "nodns": True,
                "nodns_zone": "dns4sats.xyz",
            })
    assert result.id == "123"
    assert result.outs["fqdn"] == "npub1abc.nodns.shop"
    assert result.outs["nodns_nsec"] == "nsec1fakekey"
    mock_nodns.provision_dns_for_vm.assert_called_once_with(
        ip="1.2.3.4", zone="dns4sats.xyz"
    )


def test_create_vm_with_nodns_defaults_zone(mock_client):
    """When nodns=True but nodns_zone is unset, defaults to nodns.shop."""
    fake_dns = {
        "fqdn": "npub1xyz.nodns.shop",
        "keypair": {"nsec": "nsec1other"},
        "success": True,
    }
    mock_nodns = MagicMock()
    mock_nodns.provision_dns_for_vm.return_value = fake_dns
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        with patch.dict(sys.modules, {"shc_toolkit.nodns": mock_nodns}):
            provider = SHCVMProvider(api_key="test")
            result = provider.create({
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "auto_cancel": False,
                "nodns": True,
            })
    assert result.outs["fqdn"] == "npub1xyz.nodns.shop"
    mock_nodns.provision_dns_for_vm.assert_called_once_with(
        ip="1.2.3.4", zone="nodns.shop"
    )


def test_create_vm_without_nodns_has_empty_fqdn(mock_client):
    """When nodns is not set, fqdn and nodns_nsec must be empty strings."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.create({
            "hostname": "test-vm",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": False,
        })
    assert result.outs["fqdn"] == ""
    assert result.outs["nodns_nsec"] == ""


def test_create_vm_with_nodns_import_error_skips(mock_client):
    """When nostr-sdk is not installed, NoDNS is skipped gracefully."""
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        with patch.dict(sys.modules, {"shc_toolkit.nodns": None}):
            provider = SHCVMProvider(api_key="test")
            result = provider.create({
                "hostname": "test-vm",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "auto_cancel": False,
                "nodns": True,
            })
    assert result.outs["fqdn"] == ""
    assert result.outs["nodns_nsec"] == ""


# ---------------------------------------------------------------------------
# Credit pre-check in create()
# ---------------------------------------------------------------------------


def test_create_vm_checks_credit_and_raises_when_low(mock_client):
    mock_client.get_available_credit.return_value = 0.05
    mock_client.estimate_daily_cost.return_value = 0.46
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        with pytest.raises(RuntimeError, match="Insufficient credit"):
            provider.create({
                "hostname": "test",
                "package_id": 81,
                "pricing_id": 245,
                "api_key": "test",
                "auto_cancel": False,
            })


def test_create_vm_proceeds_when_credit_sufficient(mock_client):
    mock_client.get_available_credit.return_value = 5.00
    mock_client.estimate_daily_cost.return_value = 0.46
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.create({
            "hostname": "test",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": False,
        })
        assert result.id == "123"


def test_create_vm_credit_check_fails_open_on_endpoint_error(mock_client):
    mock_client.estimate_daily_cost.side_effect = Exception("network error")
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.create({
            "hostname": "test",
            "package_id": 81,
            "pricing_id": 245,
            "api_key": "test",
            "auto_cancel": False,
        })
        assert result.id == "123"


# ---------------------------------------------------------------------------
# Credit warning in check()
# ---------------------------------------------------------------------------


def test_check_warns_on_low_credit(mock_client):
    mock_client.get_available_credit.return_value = 0.05
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check(
            {},
            {"package_id": 81, "pricing_id": 245, "hostname": "vm"},
        )
    credit_failures = [f for f in result.failures if f.property == "credit"]
    assert len(credit_failures) == 1
    assert "Low credit balance" in credit_failures[0].reason


def test_check_no_credit_warning_when_sufficient(mock_client):
    mock_client.get_available_credit.return_value = 5.00
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check(
            {},
            {"package_id": 81, "pricing_id": 245, "hostname": "vm"},
        )
    credit_failures = [f for f in result.failures if f.property == "credit"]
    assert len(credit_failures) == 0
