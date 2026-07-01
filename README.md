# SHC Pulumi Provider

Pulumi dynamic provider for Sovereign Hybrid Compute (SHC) VPS. Manage SHC
virtual machines as Pulumi infrastructure-as-code.

This package wraps the [shc-toolkit](https://github.com/Amperstrand/shc-toolkit)
API client and exposes SHC VPS instances (and their snapshots) as first-class
Pulumi dynamic resources, so you can provision, inspect, and tear down VMs
from your Pulumi stack.

## Quick Start

```python
from shc_pulumi import SHCVMResource
import pulumi

vm = SHCVMResource("web",
    hostname="web",
    size="standard",
    api_key=pulumi.Config().require_secret("shc_api_key"),
)
pulumi.export("ip", vm.ip)
```

```bash
pulumi config set shc_api_key --secret
pulumi up
```

## Features

- **Size abstraction** -- use `size="standard"` instead of raw package/pricing
  IDs. The provider resolves the correct SHC package automatically. Changing
  `size` triggers an in-place upgrade (not a destroy/recreate).
- **VM lifecycle** -- create, read, delete, and diff SHC virtual machines with
  automatic provisioning-state polling (waits up to 600 s for a VM to reach
  `ready`).
- **In-place upgrade** -- changing `size` (or `package_id`/`pricing_id`)
  triggers an in-place upgrade via the SHC upgrade API (no destroy/recreate).
- **Power management** -- set `power_state` to `running` or `stopped`; changing
  it triggers an in-place start/stop without replacing the VM.
- **NoDNS hostnames** -- `nodns=True` auto-publishes a `.nodns.shop` or
  `.dns4sats.xyz` domain pointing to the VM via Nostr (kind 11111 events).
- **Firewall rules** -- `SHCFirewallRuleResource` manages individual VM
  firewall rules as standalone Pulumi resources.
- **Reverse DNS (rDNS)** -- `SHCrDNSResource` manages PTR records for VM IP
  addresses.
- **Backups** -- `SHCBackupResource` manages VM backups as standalone Pulumi
  resources.
- **Snapshots** -- `SHCSnapshotResource` manages VM snapshots.
- **Credit safety** -- before ordering, `create()` checks available credit
  against the estimated daily cost and raises early if funds are insufficient.
  The check fails open (continues) if the billing endpoint is unreachable.
- **Discovery helpers** -- `get_plan()`, `get_templates()`, and
  `get_machine_types()` query the live SHC catalog.
- **SSH key injection** -- optionally inject a public SSH key onto the VM at
  creation time (retried up to 3 times).
- **Auto-cancel on destroy** -- every VM resource defaults to
  `auto_cancel=True`, so destroying a Pulumi stack cancels the underlying VPS
  without manual intervention.
- **Secret-safe API key** -- the API key is accepted as a plain string or a
  Pulumi secret `Output`, and is never logged.

## Install

```bash
pip install shc-pulumi
```

`shc-pulumi` depends on [`shc-toolkit`](https://github.com/Amperstrand/shc-toolkit),
which is installed automatically.

You also need the Pulumi CLI and a Python 3.11+ runtime for your stack.

## Quick Start

1. Create a new Pulumi project (Python runtime).

2. Install the provider into the project virtualenv:

   ```bash
   pip install shc-pulumi
   ```

3. Set your SHC API key as a Pulumi secret (recommended):

   ```bash
   pulumi config set shc_api_key --secret
   ```

   Alternatively, export the `SHC_API_KEY` environment variable.

4. Define a VM in `__main__.py`:

   ```python
   import pulumi
   from shc_pulumi import SHCVMResource

   vm = SHCVMResource("my-vm",
       hostname="pulumi-test",
       size="standard",
       api_key=pulumi.Config().require_secret("shc_api_key"),
   )

   pulumi.export("ip", vm.ip)
   pulumi.export("service_id", vm.service_id)
   ```

5. Deploy:

   ```bash
   pulumi up
   ```

6. Tear down (cancels the VM automatically):

   ```bash
   pulumi destroy
   ```

## Resources

### `SHCVMResource`

A Pulumi dynamic resource representing a single SHC VPS instance.

**Inputs**

| Argument      | Type                | Required | Default | Description |
|---------------|---------------------|----------|---------|-------------|
| `hostname`    | `pulumi.Input[str]` | yes      |         | Hostname assigned to the VM. Changing this forces replacement. |
| `size`        | `pulumi.Input[str]` | no       | `None`  | Human-readable plan name (e.g. `standard`). Takes precedence over `package_id`/`pricing_id`. Changing this triggers an in-place upgrade. |
| `package_id`  | `pulumi.Input[int]` | no       | `None`  | SHC package ID (plan). Required if `size` is not set. Changing this triggers an in-place upgrade. |
| `pricing_id`  | `pulumi.Input[int]` | no       | `None`  | SHC pricing option ID for the chosen package. Required if `size` is not set. Changing this triggers an in-place upgrade. |
| `api_key`     | `pulumi.Input[str]` | yes      |         | SHC API key. Pass as a Pulumi secret for safety. |
| `ssh_key`     | `pulumi.Input[str]` | no       | `None`  | Public SSH key to install on the VM. |
| `auto_cancel` | `bool`              | no       | `True`  | When `True`, schedules a non-immediate cancellation right after creation so that destroying the Pulumi resource also cancels the VPS. |
| `power_state` | `pulumi.Input[str]` | no       | `running` | Desired VM power state: `running` or `stopped`. Changing this triggers an in-place start/stop without replacing the VM. When `stopped`, the VM is stopped immediately after provisioning reaches `ready`. |
| `nodns`       | `pulumi.Input[bool]`| no       | `None`  | If `True`, auto-publishes a NoDNS record pointing to the VM's IP after provisioning. Requires `shc-toolkit[nostr]` (`nostr-sdk`). |
| `nodns_zone`  | `pulumi.Input[str]` | no       | `nodns.shop` | NoDNS zone: `nodns.shop` or `dns4sats.xyz`. Only used when `nodns=True`. |

**Outputs**

| Output        | Type    | Description |
|---------------|---------|-------------|
| `ip`          | `str`   | Primary IPv4 address of the VM (empty until assigned). |
| `hostname`    | `str`   | Hostname of the VM. |
| `service_id`  | `int`   | SHC service ID for the VM. |
| `os_user`     | `str`   | Default OS login user (e.g. `debian`). |
| `status`      | `str`   | Last-known provisioning state (e.g. `ready`). |
| `fqdn`        | `str`   | NoDNS FQDN (e.g. `npub1abc.nodns.shop`). Empty unless `nodns=True`. |
| `nodns_nsec`  | `str`   | Nostr secret key for the NoDNS record. Empty unless `nodns=True`. Store securely. |

**Example**

```python
vm = SHCVMResource("web-server",
    hostname="web-01",
    size="standard",
    api_key=pulumi.Config().require_secret("shc_api_key"),
    ssh_key=open("~/.ssh/id_rsa.pub").read().strip(),
    auto_cancel=True,
)
```

### Upgrading a VM

Changing `size` (or `package_id` and `pricing_id`) triggers an in-place upgrade
via the SHC upgrade API. The upgrade is queued -- it creates a prorated invoice
and the VM is resized after payment. Only upgrades (more CPU/RAM/disk) are
supported.

```python
# Upgrade from Standard to Professional -- triggers update(), not replacement
vm = SHCVMResource("web",
    hostname="web-server",
    size="professional",  # was "standard"
    api_key=config.require_secret("shc_api_key"),
)
```

### Size abstraction

Instead of `package_id` and `pricing_id`, use `size`:

```python
vm = SHCVMResource("web",
    hostname="web",
    size="standard",
    api_key=config.require_secret("shc_api_key"),
)
```

Sizes: starter, standard, professional, business, enterprise (NVMe);
dev-starter, dev-standard, dev-professional, dev-business, dev-enterprise (Dev VPS).

### NoDNS hostname

Set `nodns=True` to automatically get a `.nodns.shop` (or `.dns4sats.xyz`)
domain pointing to the VM's IP. The provider calls `provision_dns_for_vm` from
`shc-toolkit`, which publishes a kind 11111 Nostr event. The FQDN and nsec
secret key are exposed as outputs.

Requires the optional `nostr-sdk` dependency:

```bash
pip install shc-toolkit[nostr]
```

```python
vm = SHCVMResource("web",
    hostname="web-server",
    size="standard",
    api_key=config.require_secret("shc_api_key"),
    nodns=True,
    nodns_zone="dns4sats.xyz",
)

pulumi.export("fqdn", vm.fqdn)
```

### `SHCSnapshotResource`

A Pulumi dynamic resource representing a VM snapshot.

**Inputs**

| Argument        | Type                | Required | Default | Description |
|-----------------|---------------------|----------|---------|-------------|
| `service_id`    | `pulumi.Input[int]` | yes      |         | SHC service ID of the VM to snapshot. Changing this forces replacement. |
| `api_key`       | `pulumi.Input[str]` | yes      |         | SHC API key. |
| `snapshot_name` | `pulumi.Input[str]` | no       | resource name | Name label for the snapshot. Changing this forces replacement. |

**Outputs**

| Output        | Type  | Description |
|---------------|-------|-------------|
| `snapshot_id` | `str` | ID of the created snapshot. |
| `service_id`  | `int` | Service ID the snapshot belongs to. |
| `name`        | `str` | Snapshot name label. |

**Example**

```python
from shc_pulumi import SHCSnapshotResource

snapshot = SHCSnapshotResource("pre-deploy",
    service_id=vm.service_id,
    api_key=pulumi.Config().require_secret("shc_api_key"),
    snapshot_name="pre-deploy",
)
```

### `SHCBackupResource`

A Pulumi dynamic resource representing a VM backup.

**Inputs**

| Argument      | Type                | Required | Default       | Description |
|---------------|---------------------|----------|---------------|-------------|
| `service_id`  | `pulumi.Input[int]` | yes      |               | SHC service ID of the VM to back up. Changing this forces replacement. |
| `api_key`     | `pulumi.Input[str]` | yes      |               | SHC API key. |
| `backup_name` | `pulumi.Input[str]` | no       | resource name | Name label for the backup. Changing this forces replacement. |
| `restore`     | `pulumi.Input[bool]`| no       | `False`       | When `True`, restores from the named backup instead of creating a new one. |

**Outputs**

| Output       | Type  | Description |
|--------------|-------|-------------|
| `backup_id`  | `str` | ID of the created backup. |
| `service_id` | `int` | Service ID the backup belongs to. |
| `name`       | `str` | Backup name label. |

**Example**

```python
from shc_pulumi import SHCBackupResource

backup = SHCBackupResource("weekly",
    service_id=vm.service_id,
    api_key=pulumi.Config().require_secret("shc_api_key"),
    backup_name="weekly",
)
```

### `SHCFirewallRuleResource`

A Pulumi dynamic resource representing a single firewall rule on an SHC VM.

**Inputs**

| Argument     | Type                | Required | Default       | Description |
|--------------|---------------------|----------|---------------|-------------|
| `service_id` | `pulumi.Input[int]` | yes      |               | SHC service ID of the VM. Changing this forces replacement. |
| `api_key`    | `pulumi.Input[str]` | yes      |               | SHC API key. |
| `action`     | `pulumi.Input[str]` | no       | `accept`      | Firewall action (`accept` or `drop`). Changing this forces replacement. |
| `protocol`   | `pulumi.Input[str]` | no       | `tcp`         | Protocol (`tcp`, `udp`, etc.). Changing this forces replacement. |
| `port`       | `pulumi.Input[str]` | no       | `None`        | Destination port or port range. Changing this forces replacement. |
| `source`     | `pulumi.Input[str]` | no       | `0.0.0.0/0`   | Source CIDR. Changing this forces replacement. |
| `direction`  | `pulumi.Input[str]` | no       | `in`          | Direction (`in` or `out`). |
| `rule_name`  | `pulumi.Input[str]` | no       | resource name | Human-readable label for the rule. |

**Outputs**

| Output       | Type  | Description |
|--------------|-------|-------------|
| `position`   | `int` | Position (priority) of the rule in the VM's firewall chain. |
| `service_id` | `int` | Service ID the rule belongs to. |
| `action`     | `str` | Echoed action value. |
| `protocol`   | `str` | Echoed protocol value. |
| `port`       | `str` | Echoed port value. |
| `source`     | `str` | Echoed source CIDR. |
| `direction`  | `str` | Echoed direction. |
| `name`       | `str` | Echoed rule label. |

**Example**

```python
from shc_pulumi import SHCFirewallRuleResource

allow_ssh = SHCFirewallRuleResource("allow-ssh",
    service_id=vm.service_id,
    api_key=pulumi.Config().require_secret("shc_api_key"),
    action="accept",
    protocol="tcp",
    port="22",
    source="0.0.0.0/0",
    direction="in",
    rule_name="allow-ssh",
)
```

### `SHCrDNSResource`

A Pulumi dynamic resource representing a reverse DNS (PTR) record for a single
VM IP address.

**Inputs**

| Argument     | Type                | Required | Default | Description |
|--------------|---------------------|----------|---------|-------------|
| `service_id` | `pulumi.Input[int]` | yes      |         | SHC service ID of the VM. Changing this forces replacement. |
| `api_key`    | `pulumi.Input[str]` | yes      |         | SHC API key. |
| `ip`         | `pulumi.Input[str]` | yes      |         | IP address to set the PTR record on. Changing this forces replacement. |
| `hostname`   | `pulumi.Input[str]` | yes      |         | The PTR value (reverse DNS hostname). Changing this forces replacement. |

**Outputs**

| Output       | Type  | Description |
|--------------|-------|-------------|
| `job_id`     | `str` | Job ID returned by the rDNS set operation (may be empty). |
| `service_id` | `int` | Service ID the record belongs to. |
| `ip`         | `str` | Echoed IP address. |
| `hostname`   | `str` | Echoed PTR hostname. |

**Example**

```python
from shc_pulumi import SHCrDNSResource

rdns = SHCrDNSResource("vm-rdns",
    service_id=vm.service_id,
    api_key=pulumi.Config().require_secret("shc_api_key"),
    ip=vm.ip,
    hostname="mail.example.com",
)
```

## Discovery Helpers

The package exports three helpers that query the live SHC catalog. These are
useful for exploring available plans and templates before defining resources.

### `get_plan(name, period="day")`

Searches the catalog for a plan name (case-insensitive substring match) and
returns `(package_id, pricing_id)` for the given billing period.

```python
from shc_pulumi import get_plan

pkg_id, price_id = get_plan("NVMe VPS - Standard", period="day")
```

### `get_templates()`

Lists all available OS templates (Debian, Ubuntu, Fedora, etc.).

```python
from shc_pulumi import get_templates

for t in get_templates():
    print(t["name"], t["family"], t["arch"])
```

### `get_machine_types()`

Lists all VPS plans with CPU, RAM, disk, and daily pricing.

```python
from shc_pulumi import get_machine_types

for m in get_machine_types():
    print(f"{m['name']}: {m['cpu']} CPU, {m['memory_mb']} MB, ${m['price_daily']}/day")
```

## Credit Safety

Before placing an order, `create()` performs a credit pre-check:

1. Calls `client.estimate_daily_cost(package_id)` to get the daily price.
2. Calls `client.get_available_credit()` to get the available USD balance.
3. If `available < daily_cost`, raises `RuntimeError` with a link to add
   credit -- **before** any order is submitted.

```python
RuntimeError: Insufficient credit: need $0.46, have $0.05.
    Add credit at https://blesta.sovereignhybridcompute.com/client/
```

This check **fails open**: if the billing endpoint is unreachable (network
error, auth failure, etc.), the pre-check is skipped and the order proceeds
normally. This ensures transient API issues never block provisioning.

The `check()` method also emits a warning (as a `CheckFailure` with property
`"credit"`) when the balance falls below $0.10, so `pulumi preview` surfaces
low credit before you even run `pulumi up`.

## Configuration

The provider needs an SHC API key to authenticate. Provide it in either of two
ways:

- **Pulumi config (recommended)** -- store the key as a secret and read it with
  `pulumi.Config().require_secret("shc_api_key")`, then pass the resulting
  `Output` to the resource `api_key` argument. The provider resolves the secret
  at execution time and marks it as secret throughout.

  ```bash
  pulumi config set shc_api_key --secret
  ```

- **Environment variable** -- export `SHC_API_KEY` in the shell that runs
  Pulumi. The provider falls back to this when no `api_key` argument is
  supplied.

  ```bash
  export SHC_API_KEY="your-api-key"
  ```

You can generate an API key from the
[SHC user API panel](https://blesta.sovereignhybridcompute.com/user-api/docs/).

## Known Limitations

- **Snapshots & backups not available on Dev VPS plans**: Dev VPS plans (pkg 80-84) lack the storage infrastructure for snapshots and backups. `SHCSnapshotResource` will fail with `upstream_failure` on these plans. Use NVMe/SSD/HDD VPS plans (pkg 23+) for snapshot support. All other API features (firewall, rDNS, ISO, console, metrics) work on both plan types.
- **Limited in-place updates**: Changes to `hostname` or `ssh_key` force VM replacement (destroy + recreate). Changes to `package_id` and `pricing_id` trigger an in-place upgrade via the SHC upgrade API (queued, prorated). Changes to `auto_cancel`, `api_key`, or `power_state` update state only (`power_state` triggers an actual start/stop of the VM).
- **rDNS FCrDNS constraint**: The hostname set via `SHCrDNSResource` must have a matching forward DNS record (A/AAAA) pointing back to the same IP. SHC enforces forward-confirmed reverse DNS (FCrDNS); the rDNS set operation will fail if the forward lookup does not resolve to the target IP.

## License

MIT

---

**Get SHC VPS**: [Sovereign Hybrid Compute](https://blesta.sovereignhybridcompute.com/order/forms/a/lecture-mushroom-lunar) -- bitcoin-native VPS hosting
