#!/bin/bash

# Setup script for Nexus Agent Network (Tailscale)

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Nexus Agent Network Setup (Tailscale) ===${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
fi

# detailed instructions
echo -e "\nTo enable the Nexus Network, you need a **Tailscale Auth Key**."
echo -e "This allows the agent to join your private network automatically."
echo -e "\n${YELLOW}Step 1: Generate a Key${NC}"
echo -e "   Go to: https://login.tailscale.com/admin/settings/keys"
echo -e "   Click 'Generate auth key'"
echo -e "   Settings:"
echo -e "     - [x] Reusable (Recommended)"
echo -e "     - [x] Ephemeral (Optional, good for testing)"
echo -e "     - [x] Tags: 'tag:nexus-agent' (Important for ACLs)"

echo -e "\n${YELLOW}Step 2: Configure .env${NC}"
echo -e "   Paste the key into your .env file:"
echo -e "   TAILSCALE_AUTH_KEY=tskey-auth-..."

echo -e "\n${YELLOW}Step 3: Launch${NC}"
echo -e "   Run: ./scripts/deploy_local.sh"

echo -e "\n${BLUE}Info: Setup complete. Please verify your .env file.${NC}"
