"""Tests for the static size abstraction (sizes.py)."""

from __future__ import annotations

import pytest

from shc_pulumi.sizes import resolve_size, resolve_specs


def test_resolve_size_standard():
    assert resolve_size("standard") == (26, 56)


def test_resolve_size_invalid():
    with pytest.raises(ValueError, match="Unknown size"):
        resolve_size("nonexistent")


def test_resolve_specs_cpu2():
    assert resolve_specs(cpu=2) == (26, 56)


def test_resolve_specs_no_match():
    with pytest.raises(ValueError, match="No NVMe plan matches"):
        resolve_specs(cpu=999)
