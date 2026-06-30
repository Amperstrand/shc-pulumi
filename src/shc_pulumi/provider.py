"""Pulumi dynamic resource provider for SHC VPS instances."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

import pulumi
from pulumi.dynamic import (
    CheckFailure,
    CheckResult,
    CreateResult,
    DiffResult,
    ReadResult,
    ResourceProvider,
    UpdateResult,
)
from shc_toolkit import SHCClient
from shc_toolkit.client import SHCError

from .sizes import resolve_size

logger = logging.getLogger(__name__)

_PROVISIONING_TIMEOUT = 300
_PROVISIONING_INTERVAL = 5

# Changes to these props force a full replacement (delete + recreate).
_REPLACE_PROPS = frozenset({"hostname", "ssh_key"})
# Changes to these props are detected and reported as updates but do NOT
# force replacement of the underlying VM.  ``package_id`` and ``pricing_id``
# trigger an in-place upgrade via the SHC upgrade API.
_UPDATE_PROPS = frozenset(
    {"auto_cancel", "api_key", "power_state", "package_id", "pricing_id", "size"}
)
# Output-only props that never trigger a diff.
_STABLE_PROPS = frozenset({"ip", "service_id", "os_user", "status"})


class SHCVMProvider(ResourceProvider):
    """Dynamic resource provider managing SHC VM lifecycle.

    The ``api_key`` may be a plain string or a Pulumi secret Output.
    When passed as an Output, the provider cannot build the client at
    construction time (Outputs are not yet resolved); instead it
    defers until ``create``/``read``/``delete`` receive the resolved
    value via ``props``.
    """

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.api_key = api_key
        self.client: SHCClient | None = (
            SHCClient(api_key=api_key) if api_key else None
        )

    def _get_client(self, props: dict[str, Any]) -> SHCClient:
        if self.client is not None:
            return self.client
        key = props.get("api_key", "")
        if not key or not isinstance(key, str):
            key = os.environ.get("SHC_API_KEY", "")
        if not key:
            raise ValueError(
                "api_key required: pass as a resource argument or export SHC_API_KEY"
            )
        self.client = SHCClient(api_key=key)
        return self.client

    # -- CRUD ---------------------------------------------------

    def check(self, olds: dict[str, Any], news: dict[str, Any]) -> CheckResult:
        failures: list[Any] = []

        size = news.get("size")
        if size:
            if not isinstance(size, str) or size.strip() == "":
                failures.append(
                    CheckFailure("size", "must be a non-empty string")
                )
            else:
                try:
                    pkg_id, price_id = resolve_size(size)
                    news["package_id"] = pkg_id
                    news["pricing_id"] = price_id
                except ValueError as exc:
                    failures.append(CheckFailure("size", str(exc)))
        else:
            package_id = news.get("package_id")
            if not isinstance(package_id, int) or package_id <= 0:
                failures.append(
                    CheckFailure(
                        "package_id",
                        "must be a positive integer",
                    )
                )

            pricing_id = news.get("pricing_id")
            if not isinstance(pricing_id, int) or pricing_id <= 0:
                failures.append(
                    CheckFailure(
                        "pricing_id",
                        "must be a positive integer",
                    )
                )

        hostname = news.get("hostname")
        if not hostname or not isinstance(hostname, str) or hostname.strip() == "":
            failures.append(
                CheckFailure(
                    "hostname",
                    "must be a non-empty string",
                )
            )

        power_state = news.get("power_state", "running")
        if power_state not in ("running", "stopped"):
            failures.append(
                CheckFailure(
                    "power_state",
                    f"must be 'running' or 'stopped', got: {power_state!r}",
                )
            )

        return CheckResult(news, failures)

    def create(self, props: dict[str, Any]) -> CreateResult:
        client = self._get_client(props)
        hostname = props["hostname"]
        package_id = props["package_id"]
        pricing_id = props["pricing_id"]

        result = client.submit_order(
            hostname=hostname,
            package_id=package_id,
            pricing_id=pricing_id,
        )

        service_ids = result.get("service_ids", [])
        service_id = (
            service_ids[0]
            if service_ids
            else result.get("service_id") or result.get("id")
        )
        if not service_id:
            raise RuntimeError(f"Order response missing service_id: {result}")
        sid = int(service_id)

        vm = self._wait_for_ready(client, sid)

        # Honor the requested power state: if the user wants the VM
        # stopped after provisioning, stop it now.
        if props.get("power_state", "running") == "stopped":
            try:
                client.stop_vm(sid)
            except Exception as exc:
                logger.warning(
                    "stop_vm failed for VM %s after creation: %s", sid, exc
                )

        ssh_key = props.get("ssh_key")
        if ssh_key:
            last_err: Exception | None = None
            for attempt in range(3):
                try:
                    client.apply_ssh_key_live(sid, ssh_key)
                    last_err = None
                    break
                except Exception as exc:
                    last_err = exc
                    logger.warning(
                        "SSH key apply attempt %d/3 for VM %s failed: %s",
                        attempt + 1,
                        sid,
                        exc,
                    )
                    time.sleep(5)
            if last_err is not None:
                raise RuntimeError(
                    f"Failed to apply SSH key to VM {sid} after 3 retries"
                ) from last_err

        if props.get("auto_cancel"):
            try:
                client.cancel_vm(sid, immediate=False)
            except (SHCError, Exception) as exc:
                logger.warning(
                    "auto_cancel failed for VM %s (VM was created successfully): %s",
                    sid,
                    exc,
                )

        for attempt in range(5):
            try:
                vm = client.get_vm(sid)
                break
            except Exception:
                time.sleep(3)
        else:
            vm = {"ips": [], "os_user": "debian"}

        ips = vm.get("ips", [])
        ip = ips[0]["ip"] if ips else ""
        os_user = vm.get("os_user", "debian")

        outs = {
            "ip": ip,
            "hostname": hostname,
            "service_id": sid,
            "os_user": os_user,
            "status": vm.get("provisioning_state", "ready"),
            "package_id": package_id,
            "pricing_id": pricing_id,
        }
        if props.get("size"):
            outs["size"] = props["size"]
        return CreateResult(id_=str(sid), outs=outs)

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        client = self._get_client(props)
        try:
            vm = client.get_vm(int(id_))
        except SHCError:
            return ReadResult(id_="", outs=None)

        ips = vm.get("ips", [])
        outs = {
            "ip": ips[0]["ip"] if ips else "",
            "hostname": vm.get("hostname", props.get("hostname", "")),
            "service_id": int(id_),
            "os_user": vm.get("os_user", "debian"),
            "status": vm.get("provisioning_state", "unknown"),
            "package_id": props.get("package_id"),
            "pricing_id": props.get("pricing_id"),
        }
        if props.get("size"):
            outs["size"] = props["size"]
        return ReadResult(id_=id_, outs=outs)

    def delete(self, id_: str, props: dict[str, Any]) -> None:
        client = self._get_client(props)
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                client.cancel_vm(int(id_), immediate=True)
                return
            except SHCError as e:
                if "not_found" in e.code or "already" in e.message.lower():
                    return
                if "locked" in e.message.lower():
                    last_exc = e
                    if attempt < 3:
                        time.sleep(5)
                        continue
                    break
                raise
        raise RuntimeError(
            "VM is locked by a running job. Wait for it to complete and try again."
        ) from last_exc

    def diff(
        self,
        id_: str,
        olds: dict[str, Any],
        news: dict[str, Any],
    ) -> DiffResult:
        replaces: list[str] = []
        for prop in _REPLACE_PROPS:
            if olds.get(prop) != news.get(prop):
                replaces.append(prop)

        # Detect changes to update-only props (auto_cancel, api_key).
        # These don't force replacement but should be reported so the
        # new values are saved in state.
        has_updates = any(
            olds.get(prop) != news.get(prop) for prop in _UPDATE_PROPS
        )

        if replaces:
            return DiffResult(
                changes=True,
                replaces=replaces,
                stables=list(_STABLE_PROPS),
            )
        if has_updates:
            return DiffResult(
                changes=True, replaces=[], stables=list(_STABLE_PROPS)
            )
        return DiffResult(changes=False, stables=list(_STABLE_PROPS))

    def update(
        self,
        id_: str,
        props: dict[str, Any],
        olds: dict[str, Any],
    ) -> UpdateResult:
        client = self._get_client(props)
        sid = int(id_)

        old_pricing = olds.get("pricing_id")
        new_pricing = props.get("pricing_id")

        # When size changes, resolve the new pricing_id from the static map.
        old_size = olds.get("size")
        new_size = props.get("size")
        if new_size and old_size != new_size:
            _, resolved_pricing = resolve_size(new_size)
            new_pricing = resolved_pricing

        if old_pricing and new_pricing and old_pricing != new_pricing:
            client.upgrade_vm(sid, pricing_ref=int(new_pricing))

        old_power = olds.get("power_state", "running")
        new_power = props.get("power_state", "running")
        if old_power != new_power:
            if new_power == "stopped":
                client.stop_vm(sid)
            elif new_power == "running":
                client.start_vm(sid)

        outs = dict(olds)
        outs.update({k: v for k, v in props.items() if k != "api_key"})
        return UpdateResult(outs=outs)

    # -- Helpers ------------------------------------------------

    @staticmethod
    def _wait_for_ready(client: SHCClient, sid: int) -> dict[str, Any]:
        deadline = time.time() + _PROVISIONING_TIMEOUT
        while time.time() < deadline:
            try:
                vm = client.get_vm(sid)
                prov = vm.get("provisioning_state", "unknown")
                if prov == "ready":
                    return vm
                if prov in ("failed", "error"):
                    raise RuntimeError(f"VM {sid} provisioning failed: {vm}")
            except RuntimeError:
                raise
            except Exception as exc:
                logger.debug(
                    "Transient error while waiting for VM %s: %s", sid, exc
                )
            time.sleep(_PROVISIONING_INTERVAL)
        raise TimeoutError(
            f"VM {sid} not ready after {_PROVISIONING_TIMEOUT}s"
        )


class SHCVMResource(pulumi.dynamic.Resource):
    """Pulumi resource representing an SHC VPS instance.

    Example::

        vm = SHCVMResource("my-vm",
            hostname="test-vm",
            size="standard",
            api_key=pulumi.Config().require_secret("shc_api_key"),
            ssh_key=open("~/.ssh/id_rsa.pub").read().strip(),
            auto_cancel=True,
        )
        pulumi.export("ip", vm.ip)
        pulumi.export("service_id", vm.service_id)
    """

    ip: pulumi.Output[str]
    hostname: pulumi.Output[str]
    service_id: pulumi.Output[int]
    os_user: pulumi.Output[str]
    status: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        hostname: pulumi.Input[str],
        api_key: pulumi.Input[str] = "",
        package_id: Optional[pulumi.Input[int]] = None,
        pricing_id: Optional[pulumi.Input[int]] = None,
        ssh_key: Optional[pulumi.Input[str]] = None,
        auto_cancel: bool = True,
        power_state: pulumi.Input[str] = "running",
        size: Optional[pulumi.Input[str]] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        if size is not None:
            package_id, pricing_id = resolve_size(size)
        elif package_id is None or pricing_id is None:
            raise ValueError(
                "Either 'size' or both 'package_id' and 'pricing_id' "
                "must be provided"
            )

        provider = SHCVMProvider()
        props: dict[str, Any] = {
            "hostname": hostname,
            "package_id": package_id,
            "pricing_id": pricing_id,
            "api_key": pulumi.Output.secret(api_key) if api_key else "",
            "ip": None,
            "service_id": None,
            "os_user": None,
            "status": None,
        }
        if size is not None:
            props["size"] = size
        if ssh_key is not None:
            props["ssh_key"] = ssh_key
        props["auto_cancel"] = auto_cancel
        props["power_state"] = power_state
        super().__init__(provider, name, props, opts)
