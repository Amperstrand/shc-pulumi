"""Pulumi dynamic provider for Sovereign Hybrid Compute (SHC) VPS."""

from .provider import SHCVMProvider, SHCVMResource
from .snapshot import SHCSnapshotProvider, SHCSnapshotResource
from .firewall import SHCFirewallRuleProvider, SHCFirewallRuleResource
from .rdns import SHCrDNSProvider, SHCrDNSResource
from .sizes import SIZE_MAP, resolve_size, resolve_specs


def get_plan(name: str, period: str = "day"):
    """Query the SHC catalog and return (package_id, pricing_id) for a plan name.

    ``name`` is matched case-insensitively as a substring of the package
    name returned by :meth:`SHCClient.get_catalog`.  When ``period`` is
    given (default ``"day"``) the pricing entry with that period is selected;
    otherwise the first matching package's first pricing entry is returned
    with ``None`` as the pricing id.

    Example::

        pkg_id, price_id = get_plan("NVMe VPS - Standard")

    Returns:
        tuple[int | None, int | None]: ``(package_id, pricing_id)``.

    Raises:
        ValueError: if no package matches ``name``.
    """
    from shc_toolkit import SHCClient

    c = SHCClient()
    for pkg in c.get_catalog():
        if name.lower() in pkg.get("name", "").lower():
            for pricing in pkg.get("pricing", []):
                if pricing.get("period") == period:
                    return pkg["package_id"], pricing.get(
                        "pricing_id", pricing.get("id")
                    )
            return pkg["package_id"], None
    raise ValueError(f"Plan '{name}' not found in catalog")


def get_templates():
    """List available OS templates."""
    from shc_toolkit import SHCClient

    c = SHCClient()
    return c.list_templates()


def get_machine_types():
    """List available VPS plans with specs and pricing."""
    from shc_toolkit import SHCClient

    c = SHCClient()
    result = []
    for pkg in c.get_catalog():
        daily = next((p for p in pkg.get("pricing", []) if p.get("period") == "day"), {})
        result.append({
            "name": pkg.get("name", ""),
            "package_id": pkg.get("package_id"),
            "cpu": pkg.get("cpu"),
            "memory_mb": pkg.get("memory_mb"),
            "disk_gb": pkg.get("disk_gb"),
            "price_daily": daily.get("price"),
        })
    return result


__all__ = [
    "SHCVMProvider",
    "SHCVMResource",
    "SHCSnapshotProvider",
    "SHCSnapshotResource",
    "SHCFirewallRuleProvider",
    "SHCFirewallRuleResource",
    "SHCrDNSProvider",
    "SHCrDNSResource",
    "get_plan",
    "get_templates",
    "get_machine_types",
    "SIZE_MAP",
    "resolve_size",
    "resolve_specs",
]
