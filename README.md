# SHC Pulumi Provider

Pulumi dynamic provider for Sovereign Hybrid Compute (SHC) VPS. Manage SHC
virtual machines as Pulumi infrastructure-as-code.

This package wraps the [shc-toolkit](https://github.com/Amperstrand/shc-toolkit)
API client and exposes SHC VPS instances (and their snapshots) as first-class
Pulumi dynamic resources, so you can provision, inspect, and tear down VMs
from your Pulumi stack.

## Features

- **VM lifecycle** -- create, read, delete, and diff SHC virtual machines with
  automatic provisioning-state polling (waits up to 300 s for a VM to reach
  `ready`).
- **Snapshot management** -- create, list, read, and delete VM snapshots as
  standalone Pulumi resources.
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
       package_id=81,
       pricing_id=245,
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
| `package_id`  | `pulumi.Input[int]` | yes      |         | SHC package ID (plan). Changing this forces replacement. |
| `pricing_id`  | `pulumi.Input[int]` | yes      |         | SHC pricing option ID for the chosen package. Changing this forces replacement. |
| `api_key`     | `pulumi.Input[str]` | yes      |         | SHC API key. Pass as a Pulumi secret for safety. |
| `ssh_key`     | `pulumi.Input[str]` | no       | `None`  | Public SSH key to install on the VM. |
| `auto_cancel` | `bool`              | no       | `True`  | When `True`, schedules a non-immediate cancellation right after creation so that destroying the Pulumi resource also cancels the VPS. |

**Outputs**

| Output        | Type    | Description |
|---------------|---------|-------------|
| `ip`          | `str`   | Primary IPv4 address of the VM (empty until assigned). |
| `hostname`    | `str`   | Hostname of the VM. |
| `service_id`  | `int`   | SHC service ID for the VM. |
| `os_user`     | `str`   | Default OS login user (e.g. `debian`). |
| `status`      | `str`   | Last-known provisioning state (e.g. `ready`). |

**Example**

```python
vm = SHCVMResource("web-server",
    hostname="web-01",
    package_id=81,
    pricing_id=245,
    api_key=pulumi.Config().require_secret("shc_api_key"),
    ssh_key=open("~/.ssh/id_rsa.pub").read().strip(),
    auto_cancel=True,
)
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
- **No in-place updates**: Changes to `hostname`, `package_id`, `pricing_id`, or `ssh_key` force VM replacement. Changes to `auto_cancel` or `api_key` update state only.

## License

MIT

---

**Get SHC VPS**: [Sovereign Hybrid Compute](https://blesta.sovereignhybridcompute.com/order/forms/a/lecture-mushroom-lunar) -- bitcoin-native VPS hosting
