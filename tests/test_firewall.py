"""Unit tests for SHCFirewallRuleProvider.

All SHC API calls are mocked via the ``mock_client`` fixture defined in
``conftest.py``.  These tests exercise the provider lifecycle logic
(create / read / delete / diff) without making any real network calls.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shc_pulumi.firewall import SHCFirewallRuleProvider


# ---------------------------------------------------------------------------
# SHCFirewallRuleProvider lifecycle
# ---------------------------------------------------------------------------


def test_create_firewall_rule(mock_client):
    mock_client.create_firewall_rule.return_value = {"position": 5}
    with patch("shc_pulumi.firewall.SHCClient", return_value=mock_client):
        provider = SHCFirewallRuleProvider(api_key="test")
        result = provider.create({
            "service_id": 123,
            "api_key": "test",
            "action": "accept",
            "protocol": "tcp",
            "port": "22",
            "source": "0.0.0.0/0",
            "direction": "in",
            "name": "allow-ssh",
        })
    assert result.id == "123:5"
    assert result.outs["position"] == 5
    assert result.outs["action"] == "accept"
    assert result.outs["protocol"] == "tcp"
    mock_client.create_firewall_rule.assert_called_once_with(
        123,
        action="accept",
        protocol="tcp",
        dest_port="22",
        source="0.0.0.0/0",
        direction="in",
        name="allow-ssh",
    )


def test_read_firewall_rule(mock_client):
    mock_client.get_firewall.return_value = {
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
    with patch("shc_pulumi.firewall.SHCClient", return_value=mock_client):
        provider = SHCFirewallRuleProvider(api_key="test")
        result = provider.read("123:5", {
            "service_id": 123,
            "api_key": "test",
            "position": 5,
        })
    assert result.id == "123:5"
    assert result.outs["position"] == 5
    assert result.outs["action"] == "accept"
    assert result.outs["port"] == "22"
    mock_client.get_firewall.assert_called_once_with(123)


def test_delete_firewall_rule(mock_client):
    with patch("shc_pulumi.firewall.SHCClient", return_value=mock_client):
        provider = SHCFirewallRuleProvider(api_key="test")
        provider.delete("123:5", {
            "service_id": 123,
            "api_key": "test",
            "position": 5,
        })
    mock_client.delete_firewall_rule.assert_called_once_with(123, 5)


def test_diff_replaces_protocol(mock_client):
    provider = SHCFirewallRuleProvider(api_key="test")
    result = provider.diff(
        "123:5",
        {"service_id": 123, "action": "accept", "protocol": "tcp",
         "port": "22", "source": "0.0.0.0/0"},
        {"service_id": 123, "action": "accept", "protocol": "udp",
         "port": "22", "source": "0.0.0.0/0"},
    )
    assert result.changes is True
    assert "protocol" in result.replaces
