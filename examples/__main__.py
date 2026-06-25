import pulumi
from shc_pulumi import SHCVMResource

config = pulumi.Config()

vm = SHCVMResource("shc-test-vm",
    hostname="pulumi-shc-test",
    package_id=81,
    pricing_id=245,
    api_key=config.require_secret("shc_api_key"),
    ssh_key=open("/Users/macbook/.ssh/id_rsa.pub").read().strip(),
    auto_cancel=True,
)

pulumi.export("ip", vm.ip)
pulumi.export("service_id", vm.service_id)
pulumi.export("hostname", vm.hostname)
pulumi.export("os_user", vm.os_user)
