#!/usr/bin/env bash
# 03 — Agent host: Node, tmux, DeepSeek Harness (dsh), systemd user service.
#
# dsh is a DEVELOPER PREVIEW. This script pins nothing yet because the package
# is moving fast; once you have a working version, pin it (see note at bottom).
#
# Web UI on the phone: dsh serves http://127.0.0.1:3080 by default. Check
#   npx @deepseek-ai/dsh web --help
# for a host/port flag to bind the tailnet address. If there isn't one yet,
# use the SSH tunnel from your phone's SSH app instead:
#   Local forward 3080 → 127.0.0.1:3080, then browse http://localhost:3080
set -euo pipefail

# --- deps (Fedora host) ------------------------------------------------------
sudo dnf install -y tmux git curl nodejs
node --version   # Fedora's nodejs is current enough for dsh; if not:
                 # sudo dnf module install nodejs:22

# --- env ---------------------------------------------------------------------
cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; echo ">> EDIT .env with your DeepSeek API key, then re-run"; exit 1; }

# --- keep the machine awake (desktop 24/7 duty) ------------------------------
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target || true

# --- systemd user service: dsh web UI inside tmux ---------------------------
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/agent-system.service <<'EOF'
[Unit]
Description=agent-system: DeepSeek Harness web UI (in tmux session "agents")
After=network-online.target

[Service]
Type=forking
WorkingDirectory=%h/Desktop/Project 2/agent-system
EnvironmentFile=%h/Desktop/Project 2/agent-system/.env
ExecStart=/usr/bin/tmux new-session -d -s agents 'npx @deepseek-ai/dsh@0.1.1-rc.2 web --no-open'
ExecStop=/usr/bin/tmux kill-session -t agents
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now agent-system
sudo loginctl enable-linger "$USER"   # service runs even when not logged in

echo
echo "dsh is starting in tmux session 'agents' (attach: tmux attach -t agents)"
echo "Web UI: http://127.0.0.1:3080 locally; from phone see script header."
echo
echo "PIN LATER: once stable, replace 'npx @deepseek-ai/dsh' with a pinned"
echo "version 'npx @deepseek-ai/dsh@X.Y.Z' here and record it in configs/."
