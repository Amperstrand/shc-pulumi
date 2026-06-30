"""Tests for get_templates, get_machine_types, and snapshot restore."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import shc_pulumi
from shc_pulumi import get_machine_types, get_templates
from shc_pulumi.snapshot import SHCSnapshotProvider


# ---------------------------------------------------------------------------
# get_templates
# ---------------------------------------------------------------------------


def test_get_templates_returns_list(mock_client):
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        templates = get_templates()
    assert len(templates) == 2
    assert templates[0]["name"] == "debian13-cloud"
    assert templates[0]["family"] == "debian"
    assert templates[0]["arch"] == "x86_64"
    assert templates[0]["status"] == "active"


def test_get_templates_calls_list_templates(mock_client):
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        get_templates()
    mock_client.list_templates.assert_called_once()


def test_get_templates_importable_from_package():
    assert hasattr(shc_pulumi, "get_templates")
    assert callable(shc_pulumi.get_templates)


# ---------------------------------------------------------------------------
# get_machine_types
# ---------------------------------------------------------------------------


def test_get_machine_types_returns_specs_and_pricing(mock_client):
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        machine_types = get_machine_types()
    assert len(machine_types) == 2

    starter = machine_types[0]
    assert starter["name"] == "NVMe VPS - Starter"
    assert starter["package_id"] == 23
    assert starter["cpu"] == 1
    assert starter["memory_mb"] == 2048
    assert starter["disk_gb"] == 25
    assert starter["price_daily"] == "0.50"


def test_get_machine_types_missing_daily_price(mock_client):
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        machine_types = get_machine_types()
    standard = machine_types[1]
    assert standard["name"] == "NVMe VPS - Standard"
    assert standard["package_id"] == 81
    assert standard["price_daily"] == "1.00"


def test_get_machine_types_importable_from_package():
    assert hasattr(shc_pulumi, "get_machine_types")
    assert callable(shc_pulumi.get_machine_types)


# ---------------------------------------------------------------------------
# Snapshot restore
# ---------------------------------------------------------------------------


def test_snapshot_diff_detects_restore(mock_client):
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.diff(
        "snap-1",
        {"service_id": 123, "name": "test", "restore": False},
        {"service_id": 123, "name": "test", "restore": True},
    )
    assert result.changes is True
    assert not result.replaces


def test_snapshot_diff_no_restore_when_false(mock_client):
    provider = SHCSnapshotProvider(api_key="test")
    result = provider.diff(
        "snap-1",
        {"service_id": 123, "name": "test", "restore": False},
        {"service_id": 123, "name": "test", "restore": False},
    )
    assert result.changes is False


def test_snapshot_update_calls_restore(mock_client):
    with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
        provider = SHCSnapshotProvider(api_key="test")
        result = provider.update(
            "snap-1",
            {"service_id": 123, "name": "test", "restore": False, "api_key": "test"},
            {"service_id": 123, "name": "test", "restore": True, "api_key": "test"},
        )
    mock_client.restore_snapshot.assert_called_once_with(123, "snap-1")
    assert result.outs["restore"] is False
    assert result.outs["snapshot_id"] == "snap-1"


def test_snapshot_update_no_restore_when_not_triggered(mock_client):
    with patch("shc_pulumi.snapshot.SHCClient", return_value=mock_client):
        provider = SHCSnapshotProvider(api_key="test")
        result = provider.update(
            "snap-1",
            {"service_id": 123, "name": "test", "restore": False, "api_key": "test"},
            {"service_id": 123, "name": "test", "restore": False, "api_key": "test"},
        )
    mock_client.restore_snapshot.assert_not_called()
    assert result.outs["restore"] is False
