"""Tests for provider input validation (check) and VM-lock retry logic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shc_pulumi.provider import SHCVMProvider
from shc_pulumi.snapshot import SHCSnapshotProvider
from shc_pulumi.firewall import SHCFirewallRuleProvider
from shc_pulumi.rdns import SHCrDNSProvider
from shc_toolkit.client import SHCError


# ---------------------------------------------------------------------------
# SHCVMProvider.check() validation
# ---------------------------------------------------------------------------


def test_check_rejects_invalid_package_id(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check({}, {"package_id": -1, "pricing_id": 245, "hostname": "vm"})
    assert len(result.failures) == 1
    assert result.failures[0].property == "package_id"


def test_check_rejects_zero_package_id(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check({}, {"package_id": 0, "pricing_id": 245, "hostname": "vm"})
    failures = [f for f in result.failures if f.property == "package_id"]
    assert len(failures) == 1


def test_check_rejects_invalid_pricing_id(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check({}, {"package_id": 81, "pricing_id": -5, "hostname": "vm"})
    failures = [f for f in result.failures if f.property == "pricing_id"]
    assert len(failures) == 1


def test_check_rejects_empty_hostname(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check({}, {"package_id": 81, "pricing_id": 245, "hostname": ""})
    failures = [f for f in result.failures if f.property == "hostname"]
    assert len(failures) == 1


def test_check_rejects_whitespace_hostname(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check({}, {"package_id": 81, "pricing_id": 245, "hostname": "  "})
    failures = [f for f in result.failures if f.property == "hostname"]
    assert len(failures) == 1


def test_check_rejects_invalid_power_state(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check(
            {},
            {"package_id": 81, "pricing_id": 245, "hostname": "vm", "power_state": "paused"},
        )
    failures = [f for f in result.failures if f.property == "power_state"]
    assert len(failures) == 1


def test_check_accepts_valid_inputs(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check(
            {},
            {"package_id": 81, "pricing_id": 245, "hostname": "vm", "power_state": "running"},
        )
    assert len(result.failures) == 0


def test_check_accepts_valid_stopped_power_state(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        result = provider.check(
            {},
            {"package_id": 81, "pricing_id": 245, "hostname": "vm", "power_state": "stopped"},
        )
    assert len(result.failures) == 0


def test_check_returns_inputs_unchanged(mock_client):
    with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
        provider = SHCVMProvider(api_key="test")
        news = {"package_id": 81, "pricing_id": 245, "hostname": "vm"}
        result = provider.check({}, news)
    assert result.inputs == news


# ---------------------------------------------------------------------------
# SHCSnapshotProvider.check() validation
# ---------------------------------------------------------------------------


def test_snapshot_check_rejects_invalid_service_id():
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.check({}, {"service_id": -1, "name": "snap"})
    failures = [f for f in result.failures if f.property == "service_id"]
    assert len(failures) == 1


def test_snapshot_check_rejects_empty_name():
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.check({}, {"service_id": 123, "name": ""})
    failures = [f for f in result.failures if f.property == "snapshot_name"]
    assert len(failures) == 1


def test_snapshot_check_accepts_valid_inputs():
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.check({}, {"service_id": 123, "name": "pre-deploy"})
    assert len(result.failures) == 0


# ---------------------------------------------------------------------------
# SHCFirewallRuleProvider.check() validation
# ---------------------------------------------------------------------------


def test_firewall_check_rejects_invalid_protocol():
    provider = SHCFirewallRuleProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "protocol": "gre", "port": "22"},
    )
    failures = [f for f in result.failures if f.property == "protocol"]
    assert len(failures) == 1


def test_firewall_check_rejects_invalid_port():
    provider = SHCFirewallRuleProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "protocol": "tcp", "port": "abc"},
    )
    failures = [f for f in result.failures if f.property == "port"]
    assert len(failures) == 1


def test_firewall_check_accepts_valid_inputs():
    provider = SHCFirewallRuleProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "protocol": "tcp", "port": "22,80,443"},
    )
    assert len(result.failures) == 0


def test_firewall_check_accepts_port_range():
    provider = SHCFirewallRuleProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "protocol": "udp", "port": "1000-2000"},
    )
    assert len(result.failures) == 0


# ---------------------------------------------------------------------------
# SHCrDNSProvider.check() validation
# ---------------------------------------------------------------------------


def test_rdns_check_rejects_invalid_ip():
    provider = SHCrDNSProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "ip": "not-an-ip", "hostname": "mail.example.com"},
    )
    failures = [f for f in result.failures if f.property == "ip"]
    assert len(failures) == 1


def test_rdns_check_rejects_empty_hostname():
    provider = SHCrDNSProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "ip": "1.2.3.4", "hostname": ""},
    )
    failures = [f for f in result.failures if f.property == "hostname"]
    assert len(failures) == 1


def test_rdns_check_accepts_valid_inputs():
    provider = SHCrDNSProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "ip": "1.2.3.4", "hostname": "mail.example.com"},
    )
    assert len(result.failures) == 0


def test_rdns_check_accepts_ipv6():
    provider = SHCrDNSProvider(api_key="test")
    result = provider.check(
        {},
        {"service_id": 123, "ip": "::1", "hostname": "mail.example.com"},
    )
    assert len(result.failures) == 0


# ---------------------------------------------------------------------------
# VM lock retry in delete() methods
# ---------------------------------------------------------------------------


def test_delete_retries_on_vm_locked(mock_client):
    call_count = 0

    def side_effect(sid, immediate=True):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise SHCError("upstream_failure", "VM is locked (backup)")

    mock_client.cancel_vm.side_effect = side_effect

    with patch("shc_pulumi.provider.time.sleep"):
        with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
            provider = SHCVMProvider(api_key="test")
            provider.delete("123", {"hostname": "vm", "api_key": "test"})

    assert call_count == 3
    mock_client.cancel_vm.assert_called_with(123, immediate=True)


def test_delete_raises_after_locked_retries(mock_client):
    mock_client.cancel_vm.side_effect = SHCError(
        "upstream_failure", "VM is locked (backup)"
    )

    with patch("shc_pulumi.provider.time.sleep"):
        with patch("shc_pulumi.provider.SHCClient", return_value=mock_client):
            provider = SHCVMProvider(api_key="test")
            with pytest.raises(RuntimeError, match="VM is locked by a running job"):
                provider.delete("123", {"hostname": "vm", "api_key": "test"})

    assert mock_client.cancel_vm.call_count == 4


def test_snapshot_delete_retries_on_vm_locked(mock_client):
    call_count = 0

    def side_effect(sid, snap_id):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise SHCError("upstream_failure", "VM is locked (snapshot)")

    mock_client.delete_snapshot.side_effect = side_effect

    with patch("shc_pulumi.snapshot.time.sleep"):
        with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
            provider = SHCSnapshotProvider(api_key="test")
            provider.delete("snap-1", {
                "service_id": 123,
                "api_key": "test",
                "name": "test",
            })

    assert call_count == 2


def test_firewall_delete_retries_on_vm_locked(mock_client):
    call_count = 0

    def side_effect(sid, position):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise SHCError("upstream_failure", "VM is locked")

    mock_client.delete_firewall_rule.side_effect = side_effect

    with patch("shc_pulumi.firewall.time.sleep"):
        with patch("shc_pulumi.firewall.SHCClient", return_value=mock_client):
            provider = SHCFirewallRuleProvider(api_key="test")
            provider.delete("123:5", {
                "service_id": 123,
                "api_key": "test",
                "position": 5,
            })

    assert call_count == 2


def test_rdns_delete_retries_on_vm_locked(mock_client):
    call_count = 0

    def side_effect(sid, ip=None):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise SHCError("upstream_failure", "VM is locked")

    mock_client.clear_rdns.side_effect = side_effect

    with patch("shc_pulumi.rdns.time.sleep"):
        with patch("shc_pulumi.rdns.SHCClient", return_value=mock_client):
            provider = SHCrDNSProvider(api_key="test")
            provider.delete("123:1.2.3.4", {
                "service_id": 123,
                "api_key": "test",
                "ip": "1.2.3.4",
                "hostname": "mail.example.com",
            })

    assert call_count == 2
