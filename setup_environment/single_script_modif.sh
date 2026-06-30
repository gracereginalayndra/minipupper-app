#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────
# Minipupper + OpenClaw Setup Script  (modified)
#
# Run on a fresh Pi:
#   git clone https://github.com/gracereginalayndra/minipupper-app.git
#   cd minipupper-app
#   ./single_script_modif.sh
#
# Installs: Node.js, OpenClaw, Tailscale, Python deps,
# copies configs, connects as node, launches operator.
# ──────────────────────────────────────────────────────

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
SEP="────────────────────────────────────────────────────"

info()  { echo -e "${GREEN}→${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
step()  { echo -e "\n${CYAN}${SEP}${NC}\n${BOLD}Step $1${NC}: $2\n${CYAN}${SEP}${NC}"; }
pause() { echo -e "${DIM}Press Enter to continue (or Ctrl+C to abort)...${NC}" && read -r; }

echo -e "${BOLD}
╔══════════════════════════════════════════╗
║   Minipupper + OpenClaw Setup Script    ║
╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Run this entirely on the Pi."
echo "Keep the gateway VM terminal open nearby for 2 quick approvals."
echo ""

# ──────────────────────────────────────────────────────
# 0 — Pre-flight
# ──────────────────────────────────────────────────────
step 0 "Pre-flight checks"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "setup_environment" ]; then
    REPO_DIR="$(dirname "$SCRIPT_DIR")"
else
    REPO_DIR="$SCRIPT_DIR"
fi

info "Repo directory: $REPO_DIR"

if [ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]; then
    warn "OPENCLAW_GATEWAY_TOKEN not set — will try config.yaml later."
fi
pause

# ──────────────────────────────────────────────────────
# 1 — System deps (Node.js)
# ──────────────────────────────────────────────────────
step 1 "Install system dependencies (Node.js)"

info "Installing Node.js 22..."
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

mkdir -p ~/.npm-global
npm config set prefix "$HOME/.npm-global"
if ! grep -q '\.npm-global/bin' ~/.bashrc 2>/dev/null; then
    echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
fi
export PATH="$HOME/.npm-global/bin:$PATH"

info "Node.js $(node --version) · npm $(npm --version)"
pause

# ──────────────────────────────────────────────────────
# 2 — OpenClaw
# ──────────────────────────────────────────────────────
step 2 "Install OpenClaw"

info "Installing openclaw@2026.5.7..."
npm install -g openclaw@2026.5.7
info "Verified: $(openclaw --version)"
pause

# ──────────────────────────────────────────────────────
# 3 — Tailscale
# ──────────────────────────────────────────────────────
step 3 "Install & connect Tailscale"

if command -v tailscale &>/dev/null; then
    info "Tailscale already installed ($(tailscale --version | head -1))"
else
    info "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

if tailscale status 2>/dev/null | grep -q '^100\.'; then
    info "Tailscale already connected"
else
    echo ""
    warn "Run sudo tailscale up, log in via the browser link, then come back."
    echo ""
    sudo tailscale up
    for i in {1..15}; do
        if tailscale status 2>/dev/null | grep -q '^100\.'; then
            info "✅ Tailscale connected"
            tailscale status | head -3
            break
        fi
        echo "  Waiting... ($i/15)"
        sleep 2
    done
    if ! tailscale status 2>/dev/null | grep -q '^100\.'; then
        warn "Tailscale didn't connect. Run 'sudo tailscale up' manually."
        exit 1
    fi
fi
pause

# ──────────────────────────────────────────────────────
# 4 — Python deps
# ──────────────────────────────────────────────────────
step 4 "Install Python dependencies"

pip install webrtcvad websocket-client
info "Python packages installed."
pause

# ──────────────────────────────────────────────────────
# 5 — Copy configs
# ──────────────────────────────────────────────────────
step 5 "Copy config files from repo"

# YAML config
if [ -f "$REPO_DIR/config/config.yaml" ]; then
    mkdir -p ~/minipupper-app/config
    cp "$REPO_DIR/config/config.yaml" ~/minipupper-app/config/config.yaml
    info "✅ config/config.yaml"
fi

# System prompt
if [ -f "$REPO_DIR/config/system_prompt_phase2.txt" ]; then
    mkdir -p ~/minipupper-app/config
    cp "$REPO_DIR/config/system_prompt_phase2.txt" ~/minipupper-app/config/system_prompt_phase2.txt
    info "✅ config/system_prompt_phase2.txt"
fi

# API key template
if [ -f "$REPO_DIR/config/20250923.json.example" ]; then
    mkdir -p ~/apps-md-robots
    cp "$REPO_DIR/config/20250923.json.example" ~/apps-md-robots/
    info "✅ config/20250923.json.example (place real key later)"
fi

# Custom / dance scripts
if [ -d "$REPO_DIR/custom" ]; then
    mkdir -p ~/minipupper-app/custom
    cp -r "$REPO_DIR/custom/"* ~/minipupper-app/custom/ 2>/dev/null || true
    info "✅ custom/"
fi

if [ -d "$REPO_DIR/scripts" ]; then
    mkdir -p ~/minipupper-app/scripts
    cp -r "$REPO_DIR/scripts/"* ~/minipupper-app/scripts/ 2>/dev/null || true
    info "✅ scripts/"
fi

info "All configs copied."
pause

# ──────────────────────────────────────────────────────
# 6 — Environment variables
# ──────────────────────────────────────────────────────
step 6 "Set up environment variables"

TOKEN=""
if [ -f ~/minipupper-app/config/config.yaml ]; then
    TOKEN=$(grep 'openclaw_gateway_token' ~/minipupper-app/config/config.yaml 2>/dev/null \
            | awk '{print $2}' | tr -d '"')
fi

if [ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ] && [ -n "$TOKEN" ]; then
    export OPENCLAW_GATEWAY_TOKEN="$TOKEN"
    if ! grep -q 'OPENCLAW_GATEWAY_TOKEN' ~/.bashrc 2>/dev/null; then
        echo "export OPENCLAW_GATEWAY_TOKEN=\"$TOKEN\"" >> ~/.bashrc
    fi
    info "Gateway token exported."
elif [ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]; then
    warn "No gateway token found. Add it to config.yaml or export it manually."
fi
pause

# ──────────────────────────────────────────────────────
# 7 — Connect node
# ──────────────────────────────────────────────────────
step 7 "Connect Pi as an OpenClaw node"

GATEWAY_HOST="instance-20260506-083731.tail2df607.ts.net"
GATEWAY_PORT="443"

if [ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]; then
    warn "Gateway token not set! Re-run after exporting it."
    exit 1
fi

echo ""
echo "Starting node connection..."
echo ""
echo -e "${BOLD}❶${NC} Watch for the request ID below."
echo -e "${BOLD}❷${NC} On your gateway VM, run:"
echo -e "     ${CYAN}openclaw devices approve <REQUEST_ID>${NC}"
echo -e "${BOLD}❸${NC} Also on the gateway (one time):"
echo -e "     ${CYAN}openclaw approvals allowlist add --node minipupperv2 \"*\"${NC}"
echo ""

openclaw node run --host "$GATEWAY_HOST" --port "$GATEWAY_PORT" --tls &
NODE_PID=$!
sleep 5

echo ""
echo -e "${YELLOW}⏸  Approve on gateway, then come back.${NC}"
read -p "  Press Enter after approval... "
echo "Node PID: $NODE_PID"
pause

# ──────────────────────────────────────────────────────
# 8 — tmux dashboard
# ──────────────────────────────────────────────────────
step 8 "Launch monitoring dashboard (tmux)"

echo "Before starting — do you have your 20250923.json key ready?"
echo "  If not, paste it in another terminal:"
echo "    mkdir -p ~/apps-md-robots"
echo "    cat > ~/apps-md-robots/20250923.json"
echo "    (paste JSON, then Ctrl+D)"
echo ""
pause

tmux kill-session -t minipupper 2>/dev/null || true
tmux new-session -d -s minipupper -n setup

tmux send-keys -t minipupper:0 \
    "openclaw node run --host \"$GATEWAY_HOST\" --port $GATEWAY_PORT --tls" Enter

tmux split-window -h
tmux send-keys -t minipupper:0.1 \
    "watch -n 2 'cat ~/minipupper-app/tasks.json | tail -n \$((LINES-2))'" Enter

tmux split-window -v
tmux send-keys -t minipupper:0.2 \
    "cd ~/minipupper-app && python minipupper_operator.py -k" Enter

tmux select-pane -t minipupper:0.0
tmux attach -t minipupper