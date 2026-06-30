"""Pulumi dynamic provider for Sovereign Hybrid Compute (SHC) VPS."""

from .provider import SHCVMProvider, SHCVMResource
from .snapshot import SHCSnapshotProvider, SHCSnapshotResource
from .firewall import SHCFirewallRuleProvider, SHCFirewallRuleResource
from .rdns import SHCrDNSProvider, SHCrDNSResource


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
]
