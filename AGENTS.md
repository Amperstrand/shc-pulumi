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
