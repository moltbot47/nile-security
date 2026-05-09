#!/usr/bin/env bash
set -euo pipefail

export PATH="$PATH:/root/.foundry/bin"
source /root/nile-security/.env

RPC_URL="${BASE_SEPOLIA_RPC_URL:-https://sepolia.base.org}"
PRIVATE_KEY="${DEPLOYER_PRIVATE_KEY}"
DEPLOYER="${DEPLOYER_ADDRESS}"

echo "=== NILE Smart Contracts Deployment ==="
echo "Network: Base Sepolia (Chain ID: 84532)"
echo "Deployer: $DEPLOYER"

BALANCE=$(cast balance $DEPLOYER --rpc-url $RPC_URL --ether)
echo "Balance: $BALANCE ETH"

BALANCE_WEI=$(cast balance $DEPLOYER --rpc-url $RPC_URL)
if [ "$BALANCE_WEI" = "0" ]; then
    echo "ERROR: No ETH. Fund $DEPLOYER from a faucet first."
    exit 1
fi

export PROTOCOL_WALLET="${PROTOCOL_WALLET:-$DEPLOYER}"

BROADCAST_FLAG=""
for arg in "$@"; do
    case $arg in
        --broadcast) BROADCAST_FLAG="--broadcast" ;;
    esac
done

cd /root/nile-security/contracts
forge script script/Deploy.s.sol --rpc-url $RPC_URL --private-key $PRIVATE_KEY $BROADCAST_FLAG -vvvv
