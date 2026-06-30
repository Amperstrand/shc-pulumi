"""Static size map for SHC VPS plans."""

SIZE_MAP = {
    "starter":          {"package_id": 23, "pricing_id": 55,  "cpu": 1,  "ram_mb": 4096,  "disk_gb": 8,   "line": "nvme"},
    "standard":         {"package_id": 26, "pricing_id": 56,  "cpu": 2,  "ram_mb": 8192,  "disk_gb": 16,  "line": "nvme"},
    "professional":     {"package_id": 29, "pricing_id": 57,  "cpu": 4,  "ram_mb": 16384, "disk_gb": 32,  "line": "nvme"},
    "business":         {"package_id": 32, "pricing_id": 58,  "cpu": 8,  "ram_mb": 32768, "disk_gb": 64,  "line": "nvme"},
    "enterprise":       {"package_id": 35, "pricing_id": 59,  "cpu": 16, "ram_mb": 65536, "disk_gb": 128, "line": "nvme"},
    "dev-starter":      {"package_id": 80, "pricing_id": 241, "cpu": 1,  "ram_mb": 4096,  "disk_gb": 8,   "line": "dev"},
    "dev-standard":     {"package_id": 81, "pricing_id": 245, "cpu": 2,  "ram_mb": 8192,  "disk_gb": 16,  "line": "dev"},
    "dev-professional": {"package_id": 82, "pricing_id": 249, "cpu": 4,  "ram_mb": 16384, "disk_gb": 32,  "line": "dev"},
    "dev-business":     {"package_id": 83, "pricing_id": 253, "cpu": 8,  "ram_mb": 32768, "disk_gb": 64,  "line": "dev"},
    "dev-enterprise":   {"package_id": 84, "pricing_id": 257, "cpu": 16, "ram_mb": 65536, "disk_gb": 128, "line": "dev"},
}

def resolve_size(size: str) -> tuple[int, int]:
    entry = SIZE_MAP.get(size.lower().strip())
    if not entry:
        raise ValueError(f"Unknown size '{size}'. Valid: {', '.join(SIZE_MAP.keys())}")
    return int(entry["package_id"]), int(entry["pricing_id"])

def resolve_specs(cpu: int | None = None, ram_mb: int | None = None, disk_gb: int | None = None) -> tuple[int, int]:
    candidates = []
    for entry in SIZE_MAP.values():
        if entry["line"] != "nvme": continue
        if cpu and entry["cpu"] < cpu: continue
        if ram_mb and entry["ram_mb"] < ram_mb: continue
        if disk_gb and entry["disk_gb"] < disk_gb: continue
        candidates.append(entry)
    if not candidates:
        raise ValueError(f"No NVMe plan matches: cpu>={cpu}, ram>={ram_mb}, disk>={disk_gb}")
    cheapest = min(candidates, key=lambda e: e["pricing_id"])
    return int(cheapest["package_id"]), int(cheapest["pricing_id"])
