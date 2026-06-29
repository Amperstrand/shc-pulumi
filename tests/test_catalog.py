"""Tests for the ``shc_pulumi.get_plan`` catalog helper.

The SHCClient used inside ``get_plan`` is patched so no real API call is
made; the canned catalog from ``conftest._build_mock_client`` is reused.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import shc_pulumi
from shc_pulumi import get_plan


def test_get_plan_returns_package_and_pricing(mock_client):
    """get_plan returns (package_id, pricing_id) for a known plan name."""
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        pkg_id, price_id = get_plan("NVMe VPS - Starter")
        assert pkg_id == 23
        assert price_id == 55


def test_get_plan_case_insensitive(mock_client):
    """Matching is case-insensitive substring on the package name."""
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        pkg_id, price_id = get_plan("nvme vps - standard")
        assert pkg_id == 81
        assert price_id == 245


def test_get_plan_substring_match(mock_client):
    """A unique substring is enough to select a package."""
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        pkg_id, price_id = get_plan("Starter")
        assert pkg_id == 23


def test_get_plan_monthly_period(mock_client):
    """Selecting a different period returns that period's pricing id."""
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        pkg_id, price_id = get_plan("Starter", period="month")
        assert pkg_id == 23
        assert price_id == 56


def test_get_plan_unknown_period_returns_none_pricing(mock_client):
    """When the period is unavailable, pricing_id is None but pkg returned."""
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        pkg_id, price_id = get_plan("Starter", period="year")
        assert pkg_id == 23
        assert price_id is None


def test_get_plan_unknown_raises(mock_client):
    """An unknown plan name raises a ValueError."""
    with patch("shc_toolkit.SHCClient", return_value=mock_client):
        with pytest.raises(ValueError, match="not found"):
            get_plan("Definitely Does Not Exist")


def test_get_plan_importable_from_package(mock_client):
    """``get_plan`` is exported from the top-level ``shc_pulumi`` module."""
    assert hasattr(shc_pulumi, "get_plan")
    assert callable(shc_pulumi.get_plan)
