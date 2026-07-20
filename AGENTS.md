# shc-pulumi — Agent Knowledge Base

Pulumi dynamic provider for Sovereign Hybrid Compute (SHC) VPS.

## Testing Protocol (MANDATORY)

When shc-pulumi or shc-toolkit is modified:

### 1. Unit Tests
```bash
python3 -m pytest tests/ -v --timeout=30
```
95 mocked tests. All must pass.

### 2. Integration Test (creates real VM, costs ~$0.26)
Via GitHub Actions:
```bash
gh workflow run integration.yml -R Amperstrand/shc-pulumi
```
Or locally (takes 5-15min for SHC provisioning).

### 3. Reap Orphaned VMs After Testing
```bash
shc reap --max-age-hours 0
```

### SHC Provisioning Latency
SHC VMs take 5-15 minutes to provision. The integration test has
a 20-minute CI timeout and the provider uses a 900s (15min) wait.
If provisioning exceeds this, check SHC service status.

## Downstream Projects
- physical-router-test-automation: uses shc-pulumi via cloud_lab
- tollgate-lab: uses shc-toolkit (which shc-pulumi depends on)
## Critical Lessons

### provisioning_state never becomes "ready"
SHC VMs report `provisioning_state: "provisioning"` forever. The `_wait_for_ready` method must check `service_status == "active"` AND `ips` non-empty — NOT `provisioning_state == "ready"`.

**Evidence**: europa-vpn-vps (production, 17 days running) still reports provisioning_state="provisioning".

### CI timeout + reap_orphans safety net
Integration test creates real VMs. Always pair with:
1. `if: always()` cleanup step
2. `reap_orphans()` from shc-toolkit
3. Hourly reaper GitHub Actions workflow on shc-toolkit

### SHC VM hostname prefixes for test detection
The reaper matches these prefixes: `tf-acc-`, `tollgate-`, `test-`, `ci-`, `tg-`, `zone-test-`.
Never name a production VM with these prefixes.
