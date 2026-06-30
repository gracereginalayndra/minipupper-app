# Minipupper OpenClaw — One-Click Environment Replication

A self-contained setup repo for deploying the Mini Pupper robot with OpenClaw Gateway, task processing, and the HF Dance demo. Clone once, run one script, follow the prompts.

## Quick Start

```bash
git clone https://github.com/gracereginalayndra/minipupper-app.git

cd minipupper-app

./setup-1script.sh
```

That's it. The script handles everything on the Pi side. You'll need the gateway VM terminal open nearby for ~2 minutes during the approval step.

---

## What You Need Before Starting

| Item | Notes |
|------|-------|
| Mini Pupper v2 (Raspberry Pi, Ubuntu) | Powered on, connected to internet |
| Gateway VM | OpenClaw already installed and running |
| Tailscale account | Sign in: `mangdang@mangdang.net` |
| Google Cloud service account key | Required for TTS — `20250923.json` |
| `OPENCLAW_GATEWAY_TOKEN` | Should already be in `config/config.yaml` |

---

## What the Script Does

| # | Step | Auto? | What Happens |
|---|------|-------|-------------|
| 0 | Pre-flight check | ✅ | Verifies repo structure is complete |
| 1 | Install Node.js 22 | ✅ | `curl` + `apt install`, sets up npm global prefix |
| 2 | Install OpenClaw | ✅ | `npm install -g openclaw@2026.5.7` |
| 3 | Tailscale install & connect | ⏸️ | Prints login URL, waits for auth, polls until connected |
| 4 | Python dependencies | ✅ | `pip install webrtcvad websocket-client` |
| 5 | Copy config files | ✅ | Copies pre-configured `minipupper-app/`, `StanfordQuadruped/`, YAML, prompts |
| 6 | Export environment variables | ✅ | Extracts gateway token from config, adds to `.bashrc` |
| 7 | Connect as OpenClaw node | ⏸️ | Starts `openclaw node run`, you approve on gateway VM |
| 8 | Launch dashboard | ⏸️ | Opens tmux with 3 panes (node + tasks + operator) |

---

## Step-by-Step Walkthrough

### 1. Clone and Run

```bash
git clone https://github.com/gracereginalayndra/Minipupper-Openclaw-Backup-2.git
cd Minipupper-Openclaw-Backup-2
./setup-1script.sh
```

The script runs Steps 1–6 automatically. Sit back while Node.js, OpenClaw, Tailscale, and Python deps install.

### 2. Tailscale Login

When prompted, `sudo tailscale up` runs and prints a browser link. Open it, sign in, and click **Connect**. The script waits and detects when you're online.

### 3. Approve the Node (Gateway VM Required)

At Step 7, the script starts `openclaw node run` and prints a **request ID**. Switch to your **gateway VM terminal** and run:

```bash
openclaw devices approve <REQUEST_ID>
```

Then grant exec permissions (one-time):

```bash
openclaw approvals allowlist add --node minipupperv2 "*"
```

Come back to the Pi and press Enter.

### 4. Add Your API Key

Before the dashboard launches, the script pauses and asks for your `20250923.json`. If you haven't placed it yet, open another terminal:

```bash
mkdir -p ~/apps-md-robots
cat > ~/apps-md-robots/20250923.json
# Paste the JSON contents, then Ctrl+D
```

Then press Enter to continue.

### 5. Launch Dashboard

The script opens **tmux** with three panes:

```
┌─────────────────────┬─────────────────────┐
│                     │                     │
│   Pane 1            │   Pane 2            │
│   Node connection   │   task.json watcher │
│   (openclaw         │   (watch -n 2       │
│    node run)        │    cat tasks.json)  │
│                     │                     │
├─────────────────────┴─────────────────────┤
│                                           │
│   Pane 3                                  │
│   Operator app                            │
│   (minipupper_operator.py -k)             │
│                                           │
└───────────────────────────────────────────┘
```

Everything is running. Talk to the robot, and it'll process tasks through the OpenClaw pipeline.

---

## File Structure (on the Pi)

| Path | Purpose |
|------|---------|
| `~/minipupper-app/` | Operator app, configs, dance demo, scripts |
| `~/StanfordQuadruped/` | Robot control stack |
| `~/apps-md-robots/20250923.json` | Google Cloud service account key (add manually) |
| `~/.npm-global/bin/openclaw` | OpenClaw CLI |
| `~/.bashrc` | Exports `OPENCLAW_GATEWAY_TOKEN` + npm path |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `openclaw: command not found` | npm path not loaded | `source ~/.bashrc` or re-login |
| Node shows "pending" | Not approved on gateway | `openclaw devices approve <id>` on gateway |
| Node shows "denied" | No exec permissions | `openclaw approvals allowlist add --node minipupperv2 "*"` |
| Cron not picking up tasks | cron ID mismatch | Check cron ID in `config.yaml` matches gateway's cron job |
| Operator fails to connect | Device not paired | Run `openclaw devices list` on gateway, approve if pending |
| TTS not working | Missing API key | Place `20250923.json` at `~/apps-md-robots/20250923.json` |

### Checking Node Status

On the gateway VM:

```bash
openclaw nodes status        # Shows all nodes + connection health
openclaw devices list        # Shows pending/paired devices
```

On the Pi:

```bash
cat ~/minipupper-app/tasks.json          # Current task state
tail -f ~/minipupper-app/tasks.json      # Live task updates
```

---

## After Setup

- **Talk to the robot** — it listens for speech and handles tasks through Gemini + OpenClaw
- **Check task processing** — Pane 2 shows live task updates
- **Dance demo** — The agent handles it. Or manually: `hf_dance_to_audio.py dance <youtube-url>`
- **Say "stop"** to cancel any running task (dance, movement, etc.)

---

## Files in This Repo

| File | Purpose |
|------|---------|
| `setup-1script.sh` | Single script — run on Pi, handles everything |
| `config/config.yaml` | OpenClaw + app config (cron ID pre-matched) |
| `config/system_prompt_phase2.txt` | Gemini system prompt for task offloading |
| `apps-md-robots/20250923.json.example` | Template for the API key (fill in your real key) |
| `minipupper-app/` | Pre-configured operator app with dance demo |
| `StanfordQuadruped/` | Robot control stack |