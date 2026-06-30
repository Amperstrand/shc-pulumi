"""Pulumi dynamic resource for SHC VM firewall rules."""

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
    UpdateResult,
)
from shc_toolkit import SHCClient
from shc_toolkit.client import SHCError

logger = logging.getLogger(__name__)

# Changes to these props force a full replacement (delete + recreate).
_REPLACE_PROPS = frozenset({"service_id", "action", "protocol", "port", "source"})


class SHCFirewallRuleProvider(ResourceProvider):
    """Dynamic provider for a single SHC VM firewall rule."""

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
        action = props.get("action", "accept")
        protocol = props.get("protocol", "tcp")
        port = props.get("port")
        source = props.get("source", "0.0.0.0/0")
        direction = props.get("direction", "in")
        name = props.get("name")

        result = client.create_firewall_rule(
            service_id,
            action=action,
            protocol=protocol,
            dest_port=port,
            source=source,
            direction=direction,
            name=name,
        )

        position = result.get("position")
        if position is None:
            rules = client.get_firewall(service_id).get("rules", [])
            position = rules[-1].get("position") if rules else 0

        outs = {
            "service_id": service_id,
            "action": action,
            "protocol": protocol,
            "port": port,
            "source": source,
            "direction": direction,
            "name": name or "",
            "position": position,
        }
        return CreateResult(id_=f"{service_id}:{position}", outs=outs)

    def read(self, id_: str, props: dict[str, Any]) -> ReadResult:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        try:
            fw = client.get_firewall(service_id)
        except SHCError:
            return ReadResult(id_="", outs=None)

        target_position = props.get("position")
        for rule in fw.get("rules", []):
            if rule.get("position") == target_position:
                outs = {
                    "service_id": service_id,
                    "action": rule.get("action", props.get("action", "accept")),
                    "protocol": rule.get(
                        "protocol", props.get("protocol", "tcp")
                    ),
                    "port": rule.get("dest_port", rule.get("port", props.get("port"))),
                    "source": rule.get("source", props.get("source", "0.0.0.0/0")),
                    "direction": rule.get(
                        "direction", props.get("direction", "in")
                    ),
                    "name": rule.get("name", props.get("name", "")),
                    "position": rule.get("position"),
                }
                return ReadResult(id_=id_, outs=outs)
        return ReadResult(id_="", outs=None)

    def delete(self, id_: str, props: dict[str, Any]) -> None:
        client = self._get_client(props)
        service_id = int(props["service_id"])
        position = props.get("position")
        if position is None:
            return
        try:
            client.delete_firewall_rule(service_id, int(position))
        except SHCError as e:
            if "not_found" in e.code:
                return
            raise

    def update(
        self,
        id_: str,
        props: dict[str, Any],
        olds: dict[str, Any],
    ) -> UpdateResult:
        # direction and name can be updated in place by recreating the rule.
        client = self._get_client(props)
        service_id = int(props["service_id"])
        old_position = olds.get("position")
        if old_position is not None:
            try:
                client.delete_firewall_rule(service_id, int(old_position))
            except SHCError as e:
                if "not_found" not in e.code:
                    raise

        action = props.get("action", "accept")
        protocol = props.get("protocol", "tcp")
        port = props.get("port")
        source = props.get("source", "0.0.0.0/0")
        direction = props.get("direction", "in")
        name = props.get("name")

        result = client.create_firewall_rule(
            service_id,
            action=action,
            protocol=protocol,
            dest_port=port,
            source=source,
            direction=direction,
            name=name,
        )
        position = result.get("position", old_position)

        outs = {
            "service_id": service_id,
            "action": action,
            "protocol": protocol,
            "port": port,
            "source": source,
            "direction": direction,
            "name": name or "",
            "position": position,
        }
        return UpdateResult(outs=outs)

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

        has_updates = any(
            olds.get(prop) != news.get(prop)
            for prop in ("direction", "name", "api_key")
        )
        if has_updates:
            return DiffResult(changes=True)
        return DiffResult(changes=False)


class SHCFirewallRuleResource(pulumi.dynamic.Resource):
    """Pulumi resource representing a single SHC VM firewall rule.

    Example::

        rule = SHCFirewallRuleResource("allow-ssh",
            service_id=vm.service_id,
            api_key=pulumi.Config().require_secret("shc_api_key"),
            action="accept",
            protocol="tcp",
            port="22",
            source="0.0.0.0/0",
            direction="in",
            name="allow-ssh",
        )
    """

    position: pulumi.Output[int]
    service_id: pulumi.Output[int]
    action: pulumi.Output[str]
    protocol: pulumi.Output[str]
    port: pulumi.Output[str]
    source: pulumi.Output[str]
    direction: pulumi.Output[str]
    name: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        service_id: pulumi.Input[int],
        api_key: pulumi.Input[str],
        action: pulumi.Input[str] = "accept",
        protocol: pulumi.Input[str] = "tcp",
        port: Optional[pulumi.Input[str]] = None,
        source: pulumi.Input[str] = "0.0.0.0/0",
        direction: pulumi.Input[str] = "in",
        rule_name: Optional[pulumi.Input[str]] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        provider = SHCFirewallRuleProvider()
        props: dict[str, Any] = {
            "service_id": service_id,
            "api_key": pulumi.Output.secret(api_key) if api_key else "",
            "action": action,
            "protocol": protocol,
            "port": port,
            "source": source,
            "direction": direction,
            "name": rule_name or name,
            "position": None,
        }
        super().__init__(provider, name, props, opts)
