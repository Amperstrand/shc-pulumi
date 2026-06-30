"""Pulumi dynamic resource for SHC VM reverse DNS (rDNS / PTR)."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import pulumi
from pulumi.dynamic import (
    CreateResult,
    DiffResult,
    ReadResult,
    ResourceProvider,
)
from shc_toolkit import SHCClient
from shc_toolkit.client import SHCError

logger = logging.getLogger(__name__)

# Changes to these props force a full replacement (clear + set).
_REPLACE_PROPS = frozenset({"service_id", "ip", "hostname"})


class SHCrDNSProvider(ResourceProvider):
    """Dynamic provider for a single SHC VM reverse DNS record."""

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

    def create(self, props: dict[str, Any]) -> CreateResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        ip = props["ip"]
        hostname = props["hostname"]

        result = client.set_rdns(service_id, ip=ip, ptr=hostname)
        job_id = result.get("job_id") or result.get("id", "")

        outs = {
            "service_id": service_id,
            "ip": ip,
            "hostname": hostname,
            "job_id": str(job_id) if job_id else "",
        }
        return CreateResult(id_=f"{service_id}:{ip}", outs=outs)

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        ip = props["ip"]
        try:
            records = client.list_rdns(service_id)
        except SHCError:
            return ReadResult(id_="", outs=None)

        for rec in records:
            if rec.get("ip") == ip:
                ptr = rec.get("ptr", rec.get("hostname", ""))
                outs = {
                    "service_id": service_id,
                    "ip": ip,
                    "hostname": ptr,
                    "job_id": props.get("job_id", ""),
                }
                return ReadResult(id_=id_, outs=outs)
        return ReadResult(id_="", outs=None)

    def delete(self, id_: str, props: dict[str, Any]) -> None:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        ip = props["ip"]
        try:
            client.clear_rdns(service_id, ip=ip)
        except SHCError as e:
            if "not_found" in e.code:
                return
            raise

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
        if replaces:
            return DiffResult(changes=True, replaces=replaces)
        return DiffResult(changes=False)


class SHCrDNSResource(pulumi.dynamic.Resource):
    """Pulumi resource representing a reverse DNS (PTR) record for an SHC VM IP.

    Example::

        rdns = SHCrDNSResource("vm-rdns",
            service_id=vm.service_id,
            api_key=pulumi.Config().require_secret("shc_api_key"),
            ip=vm.ip,
            hostname="mail.example.com",
        )
    """

    job_id: pulumi.Output[str]
    service_id: pulumi.Output[int]
    ip: pulumi.Output[str]
    hostname: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        service_id: pulumi.Input[int],
        api_key: pulumi.Input[str],
        ip: pulumi.Input[str],
        hostname: pulumi.Input[str],
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        provider = SHCrDNSProvider()
        props: dict[str, Any] = {
            "service_id": service_id,
            "api_key": pulumi.Output.secret(api_key) if api_key else "",
            "ip": ip,
            "hostname": hostname,
            "job_id": None,
        }
        super().__init__(provider, name, props, opts)
