#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────
# Minipupper + OpenClaw Setup — Gateway Side
# Part of: Minipupper-Openclaw-Backup-2  (2-script version)
#
# Run on the GATEWAY VM:
#   cd Minipupper-Openclaw-Backup-2 && ./setup-gateway.sh
#
# Pair with: setup-pi.sh (run on the Pi)
# ──────────────────────────────────────────────────────

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}→${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✖ $1${NC}"; }

echo -e "${BOLD}
╔══════════════════════════════════════════╗
║   Minipupper + OpenClaw Setup           ║
║       (Gateway side — 2-script version) ║
╚══════════════════════════════════════════╝${NC}"
echo ""

# ──────────────────────────────────────────────────────
# Usage
# ──────────────────────────────────────────────────────
usage() {
    echo "Usage:"
    echo "  ./setup-gateway.sh approve <REQUEST_ID>    — Approve a pending Pi node"
    echo "  ./setup-gateway.sh perms                   — Grant exec permissions to Pi node"
    echo "  ./setup-gateway.sh list                    — List devices"
    echo "  ./setup-gateway.sh check                   — Check node connection status"
    echo "  ./setup-gateway.sh full <REQUEST_ID>       — Approve + grant perms (all-in-one)"
    echo ""
    echo "Workflow:"
    echo "  1. On the Pi:   ./setup-pi.sh"
    echo "  2. Pi prints a request ID → run:  ./setup-gateway.sh approve <ID>"
    echo "  3. One-time:    ./setup-gateway.sh perms"
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

CMD="$1"

case "$CMD" in
    approve)
        if [ $# -lt 2 ]; then
            error "Missing REQUEST_ID. Usage: ./setup-gateway.sh approve <REQUEST_ID>"
            exit 1
        fi
        REQ_ID="$2"
        info "Approving device: $REQ_ID"
        openclaw devices approve "$REQ_ID"
        info "Done. Check with: openclaw devices list"
        ;;

    perms)
        info "Granting full exec permissions to node minipupperv2..."
        openclaw approvals allowlist add --node minipupperv2 "*"
        info "Done. Node should now have full exec access."
        ;;

    list)
        info "Listing devices..."
        openclaw devices list
        ;;

    check)
        info "Checking node status..."
        openclaw nodes status | grep -E "(minipupperv2|Status|Connected|paired)"
        ;;

    full)
        if [ $# -lt 2 ]; then
            error "Missing REQUEST_ID. Usage: ./setup-gateway.sh full <REQUEST_ID>"
            exit 1
        fi
        REQ_ID="$2"
        info "Step 1/2: Approving device..."
        openclaw devices approve "$REQ_ID"
        echo ""
        info "Step 2/2: Granting exec permissions..."
        openclaw approvals allowlist add --node minipupperv2 "*"
        echo ""
        info "✅ All done! The Pi should now be fully connected."
        ;;

    *)
        error "Unknown command: $CMD"
        usage
        ;;
esac