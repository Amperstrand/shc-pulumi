"""VM size catalog for SHC, auto-generated from GET /ordering/catalog.

Spec-encoding names follow the {line}-{cpu}c-{ram}gb convention:
    nvme-2c-8gb, ssd-1c-4gb, hdd-4c-16gb, dev-2c-8gb

The static SIZE_MAP is the default fast path (no network, no auth).
"""

from __future__ import annotations

SIZE_MAP: dict[str, dict] = {
    "nvme-1c-4gb":   {"package_id": 23, "pricing_id": 55,  "cpu": 1,  "ram_mb": 4096,  "disk_gb": 8,   "line": "nvme", "name": "NVMe VPS - Starter"},
    "nvme-2c-8gb":   {"package_id": 26, "pricing_id": 56,  "cpu": 2,  "ram_mb": 8192,  "disk_gb": 16,  "line": "nvme", "name": "NVMe VPS - Standard"},
    "nvme-4c-16gb":  {"package_id": 29, "pricing_id": 57,  "cpu": 4,  "ram_mb": 16384, "disk_gb": 32,  "line": "nvme", "name": "NVMe VPS - Professional"},
    "nvme-8c-32gb":  {"package_id": 32, "pricing_id": 58,  "cpu": 8,  "ram_mb": 32768, "disk_gb": 64,  "line": "nvme", "name": "NVMe VPS - Business"},
    "nvme-16c-64gb": {"package_id": 35, "pricing_id": 59,  "cpu": 16, "ram_mb": 65536, "disk_gb": 128, "line": "nvme", "name": "NVMe VPS - Enterprise"},
    "ssd-1c-4gb":    {"package_id": 56, "pricing_id": 147, "cpu": 1,  "ram_mb": 4096,  "disk_gb": 8,   "line": "ssd",  "name": "SSD VPS - Starter"},
    "ssd-2c-8gb":    {"package_id": 57, "pricing_id": 151, "cpu": 2,  "ram_mb": 8192,  "disk_gb": 16,  "line": "ssd",  "name": "SSD VPS - Standard"},
    "ssd-4c-16gb":   {"package_id": 58, "pricing_id": 155, "cpu": 4,  "ram_mb": 16384, "disk_gb": 32,  "line": "ssd",  "name": "SSD VPS - Professional"},
    "ssd-8c-32gb":   {"package_id": 59, "pricing_id": 159, "cpu": 8,  "ram_mb": 32768, "disk_gb": 64,  "line": "ssd",  "name": "SSD VPS - Business"},
    "ssd-16c-64gb":  {"package_id": 60, "pricing_id": 163, "cpu": 16, "ram_mb": 65536, "disk_gb": 128, "line": "ssd",  "name": "SSD VPS - Enterprise"},
    "hdd-1c-4gb":    {"package_id": 36, "pricing_id": 67,  "cpu": 1,  "ram_mb": 4096,  "disk_gb": 8,   "line": "hdd",  "name": "HDD VPS - Starter"},
    "hdd-2c-8gb":    {"package_id": 37, "pricing_id": 71,  "cpu": 2,  "ram_mb": 8192,  "disk_gb": 16,  "line": "hdd",  "name": "HDD VPS - Standard"},
    "hdd-4c-16gb":   {"package_id": 38, "pricing_id": 75,  "cpu": 4,  "ram_mb": 16384, "disk_gb": 32,  "line": "hdd",  "name": "HDD VPS - Professional"},
    "hdd-8c-32gb":   {"package_id": 39, "pricing_id": 79,  "cpu": 8,  "ram_mb": 32768, "disk_gb": 64,  "line": "hdd",  "name": "HDD VPS - Business"},
    "hdd-16c-64gb":  {"package_id": 40, "pricing_id": 83,  "cpu": 16, "ram_mb": 65536, "disk_gb": 128, "line": "hdd",  "name": "HDD VPS - Enterprise"},
    "dev-1c-4gb":    {"package_id": 80, "pricing_id": 241, "cpu": 1,  "ram_mb": 4096,  "disk_gb": 8,   "line": "dev",  "name": "Dev VPS - Starter"},
    "dev-2c-8gb":    {"package_id": 81, "pricing_id": 245, "cpu": 2,  "ram_mb": 8192,  "disk_gb": 16,  "line": "dev",  "name": "Dev VPS - Standard"},
    "dev-4c-16gb":   {"package_id": 82, "pricing_id": 249, "cpu": 4,  "ram_mb": 16384, "disk_gb": 32,  "line": "dev",  "name": "Dev VPS - Professional"},
    "dev-8c-32gb":   {"package_id": 83, "pricing_id": 253, "cpu": 8,  "ram_mb": 32768, "disk_gb": 64,  "line": "dev",  "name": "Dev VPS - Business"},
    "dev-16c-64gb":  {"package_id": 84, "pricing_id": 257, "cpu": 16, "ram_mb": 65536, "disk_gb": 128, "line": "dev",  "name": "Dev VPS - Enterprise"},
}

_DAILY_PRICES = {p: float(v) for p, v in {
    23: 0.26, 26: 0.49, 29: 0.96, 32: 1.91, 35: 3.79,
    56: 0.24, 57: 0.46, 58: 0.90, 59: 1.78, 60: 3.54,
    36: 0.24, 37: 0.46, 38: 0.90, 39: 1.78, 40: 3.53,
    80: 0.24, 81: 0.46, 82: 0.90, 83: 1.78, 84: 3.54,
}.items()}

_LINE_RANK = {"nvme": 0, "ssd": 1, "hdd": 2, "dev": 3}


def resolve_size(size: str) -> tuple[int, int]:
    entry = SIZE_MAP.get(size.lower().strip())
    if not entry:
        valid = ", ".join(SIZE_MAP.keys())
        raise ValueError(f"Unknown size '{size}'. Valid: {valid}")
    return int(entry["package_id"]), int(entry["pricing_id"])


def resolve_specs(
    cpu: int | None = None,
    ram_mb: int | None = None,
    disk_gb: int | None = None,
    *,
    line: str | None = None,
) -> tuple[int, int]:
    candidates = []
    for entry in SIZE_MAP.values():
        if line and entry["line"] != line:
            continue
        if cpu and entry["cpu"] < cpu:
            continue
        if ram_mb and entry["ram_mb"] < ram_mb:
            continue
        if disk_gb and entry["disk_gb"] < disk_gb:
            continue
        candidates.append(entry)
    if not candidates:
        raise ValueError(f"No plan matches: cpu>={cpu}, ram>={ram_mb}, disk>={disk_gb}, line={line}")
    cheapest = min(candidates, key=lambda e: (_DAILY_PRICES[e["package_id"]], _LINE_RANK[e["line"]]))
    return int(cheapest["package_id"]), int(cheapest["pricing_id"])
