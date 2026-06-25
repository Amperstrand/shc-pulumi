"""Pulumi dynamic resource for SHC VM snapshots."""

from __future__ import annotations

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

_REPLACE_PROPS = frozenset({"service_id", "name"})


class SHCSnapshotProvider(ResourceProvider):
    """Dynamic provider for SHC VM snapshot lifecycle."""

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
        if not key:
            raise ValueError("api_key required for SHCSnapshotResource")
        self.client = SHCClient(api_key=key)
        return self.client

    def create(self, props: dict[str, Any]) -> CreateResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        name = props.get("name")

        result = client.create_snapshot(service_id, name=name)
        snapshot_id = result.get("snapshot_id") or result.get("id", "")

        return CreateResult(
            id_=str(snapshot_id),
            outs={
                "snapshot_id": str(snapshot_id),
                "service_id": service_id,
                "name": name or "",
            },
        )

    def read(self, id: str, props: dict[str, Any]) -> ReadResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        try:
            snapshots = client.list_snapshots(service_id)
        except SHCError:
            return ReadResult(id_="", outs=None)

        for snap in snapshots:
            sid = snap.get("snapshot_id") or snap.get("id", "")
            if str(sid) == id:
                return ReadResult(
                    id_=id,
                    outs={
                        "snapshot_id": str(sid),
                        "service_id": service_id,
                        "name": snap.get("name", props.get("name", "")),
                    },
                )
        return ReadResult(id_="", outs=None)

    def delete(self, id: str, props: dict[str, Any]) -> None:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        try:
            client.delete_snapshot(service_id, id)
        except SHCError as e:
            if "not_found" in e.code:
                return
            raise

    def diff(
        self,
        id: str,
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


class SHCSnapshotResource(pulumi.dynamic.Resource):
    """Pulumi resource representing an SHC VM snapshot.

    Example::

        snap = SHCSnapshotResource("pre-deploy",
            service_id=vm.service_id,
            name="pre-deploy",
            api_key=pulumi.Config().require_secret("shc_api_key"),
        )
    """

    snapshot_id: pulumi.Output[str]
    service_id: pulumi.Output[int]
    name: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        service_id: pulumi.Input[int],
        api_key: pulumi.Input[str],
        snapshot_name: Optional[pulumi.Input[str]] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        provider = SHCSnapshotProvider()
        props: dict[str, Any] = {
            "service_id": service_id,
            "api_key": pulumi.Output.secret(api_key) if api_key else "",
            "name": snapshot_name or name,
            "snapshot_id": None,
        }
        super().__init__(provider, name, props, opts)
