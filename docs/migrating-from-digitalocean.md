# Migrating from DigitalOcean to SHC with Pulumi

This guide shows how to migrate DigitalOcean Pulumi configurations to SHC using the `shc-pulumi` provider.

## Resource Mapping

| DigitalOcean Pulumi | SHC Pulumi | Notes |
|---------------------|------------|-------|
| `digitalocean.Droplet` | `SHCVMResource` | VM instance |
| `digitalocean.DropletSnapshot` | `SHCSnapshotResource` | VM snapshot |
| `digitalocean.Firewall` | `SHCFirewallRuleResource` | Firewall rules (one rule per resource) |
| `digitalocean.SshKey` | N/A | Pass SSH key directly to `SHCVMResource` |
| `digitalocean.FloatingIp` | N/A | Each VM gets a public IP automatically |
| `digitalocean.LoadBalancer` | N/A | Use reverse proxy on VM (Caddy, Nginx) |
| `digitalocean.Volume` | N/A | No persistent disks, use snapshots |
| `digitalocean.SpacesBucket` | N/A | SHC is compute-only, use external S3-compatible storage |

## Size Mapping

| DigitalOcean Size | SHC Package | SHC Pricing | Price |
|-------------------|-------------|-------------|-------|
| s-1vcpu-1gb | 23 | 55 | $7.78/mo |
| s-1vcpu-2gb | 23 | 56 | $11.78/mo |
| s-2vcpu-2gb | 26 | 55 | $14.83/mo |
| s-2vcpu-4gb | 26 | 56 | $20.83/mo |
| c-2vcpu-4gb | 81 | 245 | ~$20/mo |
| c-4vcpu-8gb | 82 | 249 | ~$35/mo |

## Before: DigitalOcean Droplet

```python
import pulumi
import pulumi_digitalocean as do

ssh_key = do.SshKey("default",
    name="default",
    public_key=(Path("~/.ssh/id_rsa.pub").read_text().strip())
)

droplet = do.Droplet("web",
    name="web-01",
    size="s-2vcpu-2gb",
    image="ubuntu-22-04-x64",
    region="nyc3",
    ssh_keys=[ssh_key.fingerprint],
    monitoring=True,
    tags=["web", "production"],
)

firewall = do.Firewall("web",
    name="web-firewall",
    droplet_ids=[droplet.id],
    inbound_rules=[
        do.FirewallInboundRuleArgs(
            protocol="tcp",
            port_range="22",
            source_addresses=["0.0.0.0/0"],
        ),
        do.FirewallInboundRuleArgs(
            protocol="tcp",
            port_range="80",
            source_addresses=["0.0.0.0/0"],
        ),
        do.FirewallInboundRuleArgs(
            protocol="tcp",
            port_range="443",
            source_addresses=["0.0.0.0/0"],
        ),
    ],
)

pulumi.export("droplet_ip", droplet.ipv4_address)
```

## After: SHC VM

```python
import pulumi
from shc_pulumi import SHCVMResource, SHCFirewallRuleResource

config = pulumi.Config()

ssh_key = Path("~/.ssh/id_rsa.pub").read_text().strip()

vm = SHCVMResource("web",
    hostname="web-01",
    package_id=26,
    pricing_id=55,
    api_key=config.require_secret("shc_api_key"),
    ssh_key=ssh_key,
    auto_cancel=True,
)

allow_ssh = SHCFirewallRuleResource("allow-ssh",
    service_id=vm.service_id,
    api_key=config.require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="22",
    source="0.0.0.0/0",
    direction="in",
    rule_name="allow-ssh",
)

allow_http = SHCFirewallRuleResource("allow-http",
    service_id=vm.service_id,
    api_key=config.require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="80",
    source="0.0.0.0/0",
    direction="in",
    rule_name="allow-http",
)

allow_https = SHCFirewallRuleResource("allow-https",
    service_id=vm.service_id,
    api_key=config.require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="443",
    source="0.0.0.0/0",
    direction="in",
    rule_name="allow-https",
)

pulumi.export("vm_ip", vm.ip)
```

## Finding Package IDs

Use the SHC catalog to find package and pricing IDs:

```bash
shc catalog
```

Or use the `get_plan()` helper in Python:

```python
from shc_toolkit import SHCClient

client = SHCClient()
catalog = client.get_catalog()

# Find NVMe Standard package
for pkg in catalog:
    if "NVMe Standard" in pkg.get("name", ""):
        print(f"Package ID: {pkg['package_id']}")
        for pricing in pkg.get("pricing", []):
            print(f"  Pricing ID {pricing['pricing_id']}: {pricing['price']}")
```

For NVMe VPS packages:

- Package 23: NVMe Starter
- Package 26: NVMe Standard
- Package 30: NVMe Performance
- Package 33: NVMe Ultra

For Dev VPS packages:

- Package 81: Dev VPS Standard
- Package 82: Dev VPS Professional
- Package 83: Dev VPS Business

## Snapshot Migration

**Before (DigitalOcean):**

```python
import pulumi_digitalocean as do

snapshot = do.DropletSnapshot("pre-deploy",
    name="pre-deploy",
    droplet_id=droplet.id,
)
```

**After (SHC):**

```python
from shc_pulumi import SHCSnapshotResource

snapshot = SHCSnapshotResource("pre-deploy",
    service_id=vm.service_id,
    snapshot_name="pre-deploy",
    api_key=config.require_secret("shc_api_key"),
)

pulumi.export("snapshot_id", snapshot.snapshot_id)
```

## Key Differences

### Regions

DigitalOcean has multiple regions (nyc3, sfo2, ams3, etc.). SHC operates in a single location (Katy, Texas). No region argument is needed.

### Images

DigitalOcean uses slugs like `ubuntu-22-04-x64`. SHC uses option IDs for templates:

```python
# DigitalOcean
droplet = do.Droplet("web",
    image="ubuntu-22-04-x64",
)

# SHC - the template is selected during ordering
# Use option 126 for Dev VPS, option 174 for NVMe/SSD/HDD
# Values include: debian13-cloud, debian12-cloud, ubuntu2404-cloud, etc.
```

The template is specified when ordering via the SHC API, but the Pulumi provider does not expose this option. Templates are selected through the SHC web console or API.

### SSH Keys

DigitalOcean requires creating SSH key resources first. SHC accepts the public key directly as a string:

```python
# DigitalOcean
ssh_key = do.SshKey("default",
    public_key=Path("~/.ssh/id_rsa.pub").read_text().strip()
)
droplet = do.Droplet("web", ssh_keys=[ssh_key.fingerprint])

# SHC
vm = SHCVMResource("web",
    ssh_key=Path("~/.ssh/id_rsa.pub").read_text().strip()
)
```

### Firewall Rules

DigitalOcean uses a single firewall resource with multiple rules. SHC uses one resource per rule:

```python
# DigitalOcean - one resource, multiple rules
firewall = do.Firewall("web",
    inbound_rules=[
        do.FirewallInboundRuleArgs(port_range="22"),
        do.FirewallInboundRuleArgs(port_range="80"),
    ],
)

# SHC - one resource per rule
allow_ssh = SHCFirewallRuleResource("allow-ssh", port="22")
allow_http = SHCFirewallRuleResource("allow-http", port="80")
```

### Load Balancers

DigitalOcean has managed load balancers. SHC does not. Use a reverse proxy on a VM:

```python
# Install Caddy on the VM via cloud-init or SSH
# Then configure it as a reverse proxy
```

### Monitoring

DigitalOcean droplets have a `monitoring` flag. SHC provides metrics via the API:

```bash
shc metrics <service_id>
shc bandwidth <service_id>
```

### Billing

DigitalOcean charges hourly. SHC bills daily with a minimum charge of one day, even if you use the VM for minutes.

### No Persistent Disks

DigitalOcean supports volumes for persistent storage. SHC does not. Use snapshots for backups:

```python
from shc_pulumi import SHCSnapshotResource

backup = SHCSnapshotResource("backup",
    service_id=vm.service_id,
    snapshot_name="daily-backup",
)
```

### Tags

DigitalOcean uses `tags` attributes on droplets. SHC stores metadata locally when using `shc-compute`, but this is not exposed in Pulumi.

## Migration Checklist

Before migrating from DigitalOcean to SHC:

1. Identify all droplet sizes and map them to SHC packages
2. Export data from DigitalOcean volumes if using persistent storage
3. Replace load balancers with reverse proxy configurations
4. Update firewall rules to use `SHCFirewallRuleResource`
5. Set up snapshots as replacements for volume backups
6. Remove SSH key resources and pass keys directly to VMs
7. Update CI/CD pipelines to account for hourly proration billing
8. Test SSH access and firewall rules after migration
9. Update monitoring to use SHC metrics API

## Example: Complete Migration

**Original DigitalOcean config:**

```python
import pulumi
import pulumi_digitalocean as do

droplet = do.Droplet("app",
    name="app-01",
    size="s-2vcpu-4gb",
    image="debian-11-x64",
    region="nyc3",
    monitoring=True,
)

volume = do.Volume("data",
    name="app-data",
    region="nyc3",
    size=100,
    droplet_id=droplet.id,
)

load_balancer = do.LoadBalancer("app",
    name="app-lb",
    region="nyc3",
    forwarding_rules=[
        do.LoadBalancerForwardingRuleArgs(
            entry_port=443,
            entry_protocol="https",
            target_port=80,
            target_protocol="http",
        ),
    ],
    droplet_ids=[droplet.id],
)
```

**Migrated SHC config:**

```python
import pulumi
from shc_pulumi import SHCVMResource, SHCSnapshotResource

config = pulumi.Config()

vm = SHCVMResource("app",
    hostname="app-01",
    package_id=26,
    pricing_id=56,
    api_key=config.require_secret("shc_api_key"),
    ssh_key=Path("~/.ssh/id_rsa.pub").read_text().strip(),
    auto_cancel=True,
)

backup = SHCSnapshotResource("data-backup",
    service_id=vm.service_id,
    snapshot_name="data-backup",
    api_key=config.require_secret("shc_api_key"),
)

# Configure Caddy as reverse proxy on the VM
# This replaces the load balancer
```

## Next Steps

- See [examples/web-server/__main__.py](../examples/web-server/__main__.py) for a complete working example
- Read the [main README](../README.md) for complete provider documentation
- Explore the [SHC API docs](https://blesta.sovereignhybridcompute.com/user-api/docs/)