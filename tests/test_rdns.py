"""Unit tests for SHCrDNSProvider.

All SHC API calls are mocked via the ``mock_client`` fixture defined in
``conftest.py``.  These tests exercise the provider lifecycle logic
(create / read / delete / diff) without making any real network calls.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shc_pulumi.rdns import SHCrDNSProvider


# ---------------------------------------------------------------------------
# SHCrDNSProvider lifecycle
# ---------------------------------------------------------------------------


def test_create_rdns(mock_client):
    mock_client.set_rdns.return_value = {"job_id": "job-42"}
    with patch("shc_pulumi.rdns.SHCClient", return_value=mock_client):
        provider = SHCrDNSProvider(api_key="test")
        result = provider.create({
            "service_id": 123,
            "api_key": "test",
            "ip": "1.2.3.4",
            "hostname": "mail.example.com",
        })
    assert result.id == "123:1.2.3.4"
    assert result.outs["job_id"] == "job-42"
    assert result.outs["hostname"] == "mail.example.com"
    mock_client.set_rdns.assert_called_once_with(
        123, ip="1.2.3.4", ptr="mail.example.com"
    )


def test_read_rdns(mock_client):
    mock_client.list_rdns.return_value = [
        {"ip": "1.2.3.4", "ptr": "mail.example.com"},
        {"ip": "5.6.7.8", "ptr": "other.example.com"},
    ]
    with patch("shc_pulumi.rdns.SHCClient", return_value=mock_client):
        provider = SHCrDNSProvider(api_key="test")
        result = provider.read("123:1.2.3.4", {
            "service_id": 123,
            "api_key": "test",
            "ip": "1.2.3.4",
            "hostname": "mail.example.com",
        })
    assert result.id == "123:1.2.3.4"
    assert result.outs["hostname"] == "mail.example.com"
    assert result.outs["ip"] == "1.2.3.4"
    mock_client.list_rdns.assert_called_once_with(123)


def test_delete_rdns(mock_client):
    with patch("shc_pulumi.rdns.SHCClient", return_value=mock_client):
        provider = SHCrDNSProvider(api_key="test")
        provider.delete("123:1.2.3.4", {
            "service_id": 123,
            "api_key": "test",
            "ip": "1.2.3.4",
            "hostname": "mail.example.com",
        })
    mock_client.clear_rdns.assert_called_once_with(123, ip="1.2.3.4")
