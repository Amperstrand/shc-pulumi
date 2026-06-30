# Web Server Example

This example provisions a complete web server on SHC using Pulumi with:

- A VM with SSH key injection
- Firewall rules to allow HTTP, HTTPS, and SSH
- A snapshot for rollback capability
- Optional Caddy reverse proxy configuration

## Prerequisites

Install the SHC Pulumi provider:

```bash
pip install shc-pulumi
```

Install Pulumi CLI:

```bash
curl -fsSL https://get.pulumi.com | sh
```

Set your SHC API key:

```bash
export SHC_API_KEY="shc_live_..."

# Or set as a Pulumi secret
pulumi config set shc_api_key --secret
```

## Quick Start

```bash
# Create a new Pulumi stack
pulumi stack init dev

# Install dependencies
pip install -r requirements.txt

# Set API key
pulumi config set shc_api_key --secret

# Preview changes
pulumi preview

# Deploy
pulumi up
```

## Usage

The VM will be created with:

- 2 vCPUs, 8 GB RAM, 16 GB disk (NVMe Standard, pkg 26)
- Your SSH public key injected
- Firewall rules for ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- A snapshot named "initial-deploy"

After provisioning, you can SSH into the VM:

```bash
ssh debian@$(pulumi stack output vm_ip)
```

Or use the exported SSH command:

```bash
$(pulumi stack output ssh_command)
```

Install and configure Caddy for HTTPS:

```bash
sudo apt update
sudo apt install -y caddy

# Create a simple reverse proxy config
sudo tee /etc/caddy/Caddyfile << EOF
example.com {
    reverse_proxy localhost:3000
}

example.com:443 {
    reverse_proxy localhost:3000
}
EOF

sudo systemctl restart caddy
```

## Configuration

Set configuration values with `pulumi config set`:

```bash
# Required
pulumi config set shc_api_key --secret

# Optional (defaults shown)
pulumi config set hostname web-server
pulumi config set package_id 26
pulumi config set pricing_id 55
pulumi config set snapshot_name initial-deploy

# SSH source ranges (comma-separated CIDRs)
pulumi config set ssh_source_ranges 0.0.0.0/0

# Or specify a custom SSH key path
export SHC_SSH_KEY_PATH=~/.ssh/custom.pub
```

## Package Options

Available packages for web servers:

| Package | Pricing | vCPUs | RAM | Disk | Price |
|---------|---------|-------|-----|------|-------|
| 23 | 55 | 1 | 4 GB | 8 GB | $7.78/mo |
| 23 | 56 | 1 | 8 GB | 8 GB | $11.78/mo |
| 26 | 55 | 2 | 8 GB | 16 GB | $14.83/mo |
| 26 | 56 | 2 | 16 GB | 16 GB | $20.83/mo |
| 30 | 55 | 4 | 16 GB | 32 GB | $29.83/mo |
| 33 | 55 | 6 | 32 GB | 64 GB | $59.83/mo |

Use `shc catalog` to see all available packages.

## Outputs

- `vm_ip` - Public IP address of the VM
- `service_id` - SHC service ID for the VM
- `hostname` - Hostname of the VM
- `os_user` - Default OS login user (e.g., debian)
- `snapshot_id` - ID of the created snapshot
- `ssh_command` - SSH command to connect to the web server

## Cleanup

```bash
pulumi destroy
```

This cancels the VM and deletes the snapshot.

## Next Steps

- Configure your web application on the VM
- Set up DNS to point your domain to the VM IP
- Configure Caddy or another reverse proxy for HTTPS
- Set up monitoring using `shc metrics <service_id>`