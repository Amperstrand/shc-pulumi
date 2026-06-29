import os

import pulumi
from shc_pulumi import SHCVMResource, SHCSnapshotResource

config = pulumi.Config()

# Read SSH public key from env or default location.
ssh_key_path = os.environ.get("SHC_SSH_KEY_PATH", os.path.expanduser("~/.ssh/id_rsa.pub"))
with open(ssh_key_path) as f:
    ssh_pub_key = f.read().strip()

vm = SHCVMResource("shc-test-vm",
    hostname="pulumi-shc-test",
    package_id=23,
    pricing_id=55,
    api_key=config.require_secret("shc_api_key"),
    ssh_key=ssh_pub_key,
    auto_cancel=True,
)

pulumi.export("ip", vm.ip)
pulumi.export("service_id", vm.service_id)
pulumi.export("hostname", vm.hostname)
pulumi.export("os_user", vm.os_user)

# Create a snapshot of the VM for pre-deploy rollback.
snapshot = SHCSnapshotResource("pre-deploy-snapshot",
    service_id=vm.service_id,
    snapshot_name="pre-deploy",
    api_key=config.require_secret("shc_api_key"),
)

pulumi.export("snapshot_id", snapshot.snapshot_id)
