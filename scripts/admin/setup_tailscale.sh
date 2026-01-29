#!/bin/bash
# Nexus Agent - Tailscale Setup Utility

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${YELLOW}Nexus Agent - Tailscale Configuration Wizard${RESET}"
echo "============================================"
echo "This script helps you configure secure remote access via Tailscale."
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${RESET}"
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        echo "Error: .env.example not found. Please run this script from the project root."
        exit 1
    fi
fi

# Explanation
echo "To enable remote access, you need a TS_AUTHKEY from Tailscale."
echo "1. Go to: https://login.tailscale.com/admin/settings/keys"
echo "2. Generate a new 'One-off key' (recommended) or 'Reusable key'."
echo "3. (Optional) Tag it with 'tag:nexus-agent' for auto-ACLs."
echo ""
echo -n "Paste your TS_AUTHKEY here (starts with tskey-...): "
read TS_KEY

if [ -z "$TS_KEY" ]; then
    echo "Skipping Tailscale configuration."
else
    # Update .env
    # Check if TAILSCALE_AUTH_KEY exists
    if grep -q "TAILSCALE_AUTH_KEY=" .env; then
        # Replace existing
        # escaping / is tricky in sed, using | as delimiter
        sed -i.bak "s|TAILSCALE_AUTH_KEY=.*|TAILSCALE_AUTH_KEY=$TS_KEY|" .env
        rm .env.bak
    else
        # Append
        echo "" >> .env
        echo "TAILSCALE_AUTH_KEY=$TS_KEY" >> .env
    fi
    echo -e "${GREEN}✓ .env updated with Tailscale Auth Key!${RESET}"
fi

echo ""
echo "Configuration complete. Run 'docker-compose up -d' to apply changes."
