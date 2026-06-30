"""Pulumi dynamic resource for SHC VM backups."""

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

logger = logging.getLogger(__name__)

_REPLACE_PROPS = frozenset({"service_id", "name"})


def _raise_on_unsupported_storage(e: SHCError, operation: str) -> None:
    """Re-raise with a clear message if the plan lacks storage features.

    Dev VPS plans (pkg 80-84) do not include snapshot/backup support.
    The SHC API returns an ``upstream_failure`` or storage-related error
    code in that case.  This helper translates the opaque API error into
    an actionable message.
    """
    code = (e.code or "").lower()
    msg = (e.message or "").lower()
    if "upstream_failure" in code or "storage" in code or "storage" in msg:
        raise RuntimeError(
            f"Failed to {operation}: this SHC plan may not support "
            "snapshots/backups. Dev VPS plans (pkg 80-84) do not include "
            f"storage features. Original error: {e}"
        ) from e


class SHCBackupProvider(ResourceProvider):
    """Dynamic provider for SHC VM backup lifecycle."""

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

        service_id = news.get("service_id")
        if not isinstance(service_id, int) or service_id <= 0:
            failures.append(
                CheckFailure("service_id", "must be a positive integer")
            )

        name = news.get("name")
        if not name or not isinstance(name, str) or name.strip() == "":
            failures.append(
                CheckFailure("backup_name", "must be a non-empty string")
            )

        return CheckResult(news, failures)

    def create(self, props: dict[str, Any]) -> CreateResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        name = props.get("name")

        if props.get("restore"):
            try:
                client.restore_backup(service_id, str(name))
            except SHCError as e:
                _raise_on_unsupported_storage(e, "restore backup")
                raise
            backup_id = str(name)
        else:
            try:
                result = client.create_backup(service_id, name=name)
            except SHCError as e:
                _raise_on_unsupported_storage(e, "create backup")
                raise
            backup_id = result.get("backup_id") or result.get("id", "")

        return CreateResult(
            id_=str(backup_id),
            outs={
                "backup_id": str(backup_id),
                "service_id": service_id,
                "name": name or "",
            },
        )

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        try:
            backups = client.list_backups(service_id)
        except SHCError as e:
            _raise_on_unsupported_storage(e, "list backups")
            return ReadResult(id_="", outs=None)

        for bk in backups:
            bid = bk.get("backup_id") or bk.get("id", "")
            if str(bid) == id_:
                return ReadResult(
                    id_=id_,
                    outs={
                        "backup_id": str(bid),
                        "service_id": service_id,
                        "name": bk.get("name", props.get("name", "")),
                    },
                )
        return ReadResult(id_="", outs=None)

    def delete(self, id_: str, props: dict[str, Any]) -> None:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                client.delete_backup(service_id, id_, confirm=True)
                return
            except SHCError as e:
                if "not_found" in e.code:
                    return
                if "locked" in e.message.lower():
                    last_exc = e
                    if attempt < 3:
                        time.sleep(5)
                        continue
                    break
                _raise_on_unsupported_storage(e, "delete backup")
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
        if replaces:
            return DiffResult(changes=True, replaces=replaces)
        if news.get("restore") and not olds.get("restore"):
            return DiffResult(changes=True)
        return DiffResult(changes=False)

    def update(self, id_: str, olds: dict[str, Any], news: dict[str, Any]) -> UpdateResult:
        client = self._get_client(news)
        service_id = int(news["service_id"])

        if news.get("restore") and not olds.get("restore"):
            try:
                client.restore_backup(service_id, id_, confirm=True)
            except SHCError as e:
                _raise_on_unsupported_storage(e, "restore backup")
                raise

        return UpdateResult(
            outs={
                "backup_id": id_,
                "service_id": service_id,
                "name": news.get("name", olds.get("name", "")),
                "restore": False,
            }
        )


class SHCBackupResource(pulumi.dynamic.Resource):
    """Pulumi resource representing an SHC VM backup.

    Example::

        backup = SHCBackupResource("weekly",
            service_id=vm.service_id,
            api_key=pulumi.Config().require_secret("shc_api_key"),
        )
    """

    backup_id: pulumi.Output[str]
    service_id: pulumi.Output[int]
    name: pulumi.Output[str]
    restore: pulumi.Output[bool]

    def __init__(
        self,
        name: str,
        service_id: pulumi.Input[int],
        api_key: pulumi.Input[str],
        backup_name: Optional[pulumi.Input[str]] = None,
        restore: Optional[pulumi.Input[bool]] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        provider = SHCBackupProvider()
        props: dict[str, Any] = {
            "service_id": service_id,
            "api_key": pulumi.Output.secret(api_key) if api_key else "",
            "name": backup_name or name,
            "restore": restore if restore is not None else False,
            "backup_id": None,
        }
        super().__init__(provider, name, props, opts)
