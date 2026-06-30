"""Web server example for SHC Pulumi provider.

This example provisions a complete web server on SHC with:
- A VM with SSH key injection
- Firewall rules to allow HTTP, HTTPS, and SSH
- A snapshot for rollback capability
- Optional Caddy reverse proxy configuration
"""

import os
from pathlib import Path

import pulumi
from shc_pulumi import (
    SHCVMResource,
    SHCSnapshotResource,
    SHCFirewallRuleResource,
)

config = pulumi.Config()

# Read SSH public key from env or default location
ssh_key_path = os.environ.get(
    "SHC_SSH_KEY_PATH",
    os.path.expanduser("~/.ssh/id_rsa.pub")
)
with open(ssh_key_path) as f:
    ssh_pub_key = f.read().strip()

# Configuration variables
hostname = config.get("hostname", "web-server")
package_id = config.get_int("package_id", 26)
pricing_id = config.get_int("pricing_id", 55)
ssh_source_ranges = config.get_list(
    "ssh_source_ranges",
    ["0.0.0.0/0"]
)
snapshot_name = config.get("snapshot_name", "initial-deploy")

# Create the VM
vm = SHCVMResource(
    "web-server",
    hostname=hostname,
    package_id=package_id,
    pricing_id=pricing_id,
    api_key=config.require_secret("shc_api_key"),
    ssh_key=ssh_pub_key,
    auto_cancel=True,
    power_state="running",
)

# Create firewall rules
allow_ssh = SHCFirewallRuleResource(
    "allow-ssh",
    service_id=vm.service_id,
    api_key=config.require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="22",
    source=",".join(ssh_source_ranges),
    direction="in",
    rule_name="allow-ssh",
)

allow_http = SHCFirewallRuleResource(
    "allow-http",
    service_id=vm.service_id,
    api_key=config.require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="80",
    source="0.0.0.0/0",
    direction="in",
    rule_name="allow-http",
)

allow_https = SHCFirewallRuleResource(
    "allow-https",
    service_id=vm.service_id,
    api_key=config.require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="443",
    source="0.0.0.0/0",
    direction="in",
    rule_name="allow-https",
)

# Create a snapshot for rollback
snapshot = SHCSnapshotResource(
    "initial-deploy",
    service_id=vm.service_id,
    snapshot_name=snapshot_name,
    api_key=config.require_secret("shc_api_key"),
)

# Export outputs
pulumi.export("vm_ip", vm.ip)
pulumi.export("service_id", vm.service_id)
pulumi.export("hostname", vm.hostname)
pulumi.export("os_user", vm.os_user)
pulumi.export("snapshot_id", snapshot.snapshot_id)
pulumi.export("ssh_command", pulumi.Output.concat(
    "ssh ",
    vm.os_user,
    "@",
    vm.ip
))