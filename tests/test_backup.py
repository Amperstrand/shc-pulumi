"""Unit tests for SHCBackupProvider.

All SHC API calls are mocked via the ``mock_client`` fixture defined in
``conftest.py``.  These tests exercise the provider lifecycle logic
(create / read / delete / diff) without making any real network calls.
"""

from __future__ import annotations

from unittest.mock import patch

from shc_pulumi.backup import SHCBackupProvider


def test_backup_create(mock_client):
    with patch("shc_pulumi.backup.SHCClient", return_value=mock_client):
        provider = SHCBackupProvider(api_key="test")
        result = provider.create({
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        assert result.id == "bk-1"
        assert result.outs["backup_id"] == "bk-1"
        assert result.outs["service_id"] == 123
        assert result.outs["name"] == "test"
        mock_client.create_backup.assert_called_once_with(123, name="test")


def test_backup_read(mock_client):
    with patch("shc_pulumi.backup.SHCClient", return_value=mock_client):
        provider = SHCBackupProvider(api_key="test")
        result = provider.read("bk-1", {
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        assert result.id == "bk-1"
        assert result.outs["backup_id"] == "bk-1"
        assert result.outs["name"] == "test"
        mock_client.list_backups.assert_called_once_with(123)


def test_backup_delete(mock_client):
    with patch("shc_pulumi.backup.SHCClient", return_value=mock_client):
        provider = SHCBackupProvider(api_key="test")
        provider.delete("bk-1", {
            "service_id": 123,
            "api_key": "test",
            "name": "test",
        })
        mock_client.delete_backup.assert_called_once_with(123, "bk-1", confirm=True)


def test_backup_diff_replaces_service_id(mock_client):
    provider = SHCBackupProvider(api_key="test")
    result = provider.diff(
        "bk-1",
        {"service_id": 123, "name": "a"},
        {"service_id": 456, "name": "a"},
    )
    assert result.changes is True
    assert "service_id" in result.replaces


def test_backup_diff_no_changes(mock_client):
    provider = SHCBackupProvider(api_key="test")
    result = provider.diff(
        "bk-1",
        {"service_id": 123, "name": "a"},
        {"service_id": 123, "name": "a"},
    )
    assert result.changes is False
