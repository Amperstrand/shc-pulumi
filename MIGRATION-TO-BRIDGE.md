# Pulumi via Terraform Bridge (Recommended)

As of 2026-07-11, the recommended way to use SHC from Pulumi is via
Pulumi's "Any Terraform Provider" feature, which bridges the
`terraform-provider-shc` binary at runtime — no separate Python
provider codebase needed.

## Quick Start

```bash
# 1. Build the Terraform provider
git clone https://github.com/Amperstrand/terraform-provider-shc
cd terraform-provider-shc
go build -o terraform-provider-shc .

# 2. Create a Pulumi project
mkdir my-pulumi-project && cd my-pulumi-project
pulumi new python

# 3. Add the SHC provider
pulumi package add terraform-provider ./terraform-provider-shc --language python

# 4. Use it in your Pulumi program
cat > __main__.py << 'PY'
import pulumi
import pulumi_shc as shc

vm = shc.Vm("my-vm",
    hostname="pulumi-test",
    size="dev-2c-8gb",
    template="debian12-cloud",
    auto_cancel=True,
    term=58,  # monthly billing (v2.5.0)
)

pulumi.export("ip", vm.ip)
pulumi.export("service_id", vm.service_id)
PY

# 5. Deploy
pulumi up
```

## Why This Replaces shc-pulumi

| Feature | shc-pulumi (old) | TF Bridge (new) |
|---------|------------------|-----------------|
| Codebase | 7 resource files, 95 tests | 0 files (runtime bridge) |
| Maintenance | Manual sync with shc-toolkit | Auto-syncs with TF provider |
| Type safety | Python dynamic resources | Generated typed SDK |
| New attributes | Manual addition per resource | Auto-generated from TF schema |
| v2.5.0 `term` attr | Not available | ✅ Available immediately |
| NoDNS integration | ✅ Built-in | ❌ Not in TF provider (use shc CLI) |

## Migration from shc-pulumi

If you're using the old `shc-pulumi` Python package:

1. Replace `import shc_pulumi` with `import pulumi_shc`
2. Replace `shc_pulumi.SHCVMResource` with `shc.Vm`
3. Replace `shc_pulumi.SHCSnapshotResource` with `shc.Snapshot`
4. Replace `shc_pulumi.SHCBackupResource` with `shc.Backup`
5. Replace `shc_pulumi.SHCFirewallRuleResource` with `shc.FirewallRule`
6. Replace `shc_pulumi.SHCRdnsResource` with `shc.Rdns`
7. Attribute names change from snake_case to PascalCase inputs:
   - `package_id` → `package_id` (unchanged)
   - `pricing_id` → `pricing_id` (unchanged)
   - `nodns=True` → not available (use `shc nodns --ip <ip>` CLI instead)

## NoDNS Workaround

The TF provider doesn't include NoDNS integration (it's a Python-only
feature of shc-toolkit). To provision NoDNS alongside a Pulumi-managed
VM:

```python
import pulumi
import pulumi_shc as shc
import subprocess

vm = shc.Vm("my-vm", hostname="pulumi-test", size="dev-2c-8gb")

# After VM is created, publish NoDNS
def publish_nodns(args):
    ip = args[0]
    subprocess.run(["shc", "nodns", "--ip", ip], check=True)

vm.ip.apply(publish_nodns)
```

## Requirements

- Pulumi CLI v3.248.0+ (for `pulumi package add terraform-provider`)
- terraform-provider-shc binary (build from source)
- The old `shc-pulumi` Python package still works but is deprecated
