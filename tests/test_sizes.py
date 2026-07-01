"""Tests for the spec-encoding size abstraction (sizes.py)."""

from __future__ import annotations

import pytest

from shc_pulumi.sizes import resolve_size, resolve_specs, SIZE_MAP


def test_size_map_has_20_entries():
    assert len(SIZE_MAP) == 20


def test_size_map_covers_all_four_lines():
    lines = {e["line"] for e in SIZE_MAP.values()}
    assert lines == {"nvme", "ssd", "hdd", "dev"}


def test_resolve_size_nvme():
    assert resolve_size("nvme-2c-8gb") == (26, 56)


def test_resolve_size_hdd():
    assert resolve_size("hdd-1c-4gb") == (36, 67)


def test_resolve_size_dev():
    assert resolve_size("dev-4c-16gb") == (82, 249)


def test_resolve_size_case_insensitive():
    assert resolve_size("NVME-2C-8GB") == (26, 56)


def test_resolve_size_legacy_alias_rejected():
    with pytest.raises(ValueError, match="Unknown size"):
        resolve_size("standard")


def test_resolve_size_invalid():
    with pytest.raises(ValueError, match="Unknown size"):
        resolve_size("nonexistent")


def test_resolve_specs_all_lines_cheapest():
    pkg, _ = resolve_specs(cpu=4, ram_mb=16384)
    assert pkg == 58


def test_resolve_specs_nvme_only():
    pkg, price = resolve_specs(cpu=2, ram_mb=8192, line="nvme")
    assert pkg == 26
    assert price == 56


def test_resolve_specs_ssd_only():
    pkg, _ = resolve_specs(cpu=2, line="ssd")
    assert pkg == 57


def test_resolve_specs_no_match():
    with pytest.raises(ValueError, match="No plan matches"):
        resolve_specs(cpu=999)
