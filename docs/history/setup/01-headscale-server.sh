#!/usr/bin/env bash
# 01 — Headscale control server on this desktop (Debian/Ubuntu).
#
# BEFORE RUNNING, two things only you can do:
#   1. Router port-forward: TCP 8080 (and UDP 3478 for the embedded DERP/STUN
#      relay) → this machine. Give this machine a static LAN IP first.
#   2. You need a real public IP. If your ISP uses CGNAT (public IP on
#      whatismyip.com ≠ WAN IP in your router), port-forwarding won't work —
#      in that case run ONLY headscale on a ~€3/mo VPS instead (this same
#      script works there) and keep the agent system on this desktop.
#   Optional but recommended: free dynamic-DNS name (e.g. DuckDNS) so your
#   phone config survives IP changes. Use it as SERVER_URL below.
set -euo pipefail

SERVER_URL="${SERVER_URL:-http://YOUR-DOMAIN:8080}"   # your domain

# --- firewall hardening (Fedora/firewalld) — ONLY these two ports open ------
sudo firewall-cmd --permanent --add-port=8080/tcp --add-port=3478/udp
sudo firewall-cmd --reload
# Everything else (dsh :3080, Langfuse :3000, Sunshine) stays firewalled even
# if a service misbinds to 0.0.0.0. Port-drift note: the router forwards
# WAN:8080 to THIS box's :8080 — headscale's unit has Restart=always so
# nothing else should ever claim the port; if you retire headscale, close
# the router forward the same day.
# Optional scanner-noise cut: forward a random high WAN port (e.g. 47831)
# -> internal 8080 on the router, and use that port in SERVER_URL instead.

# --- install latest headscale release (Fedora: raw binary + systemd) ---------
TAG=$(curl -fsSL https://api.github.com/repos/juanfont/headscale/releases/latest | grep -oP '"tag_name": "\K[^"]+')
VER="${TAG#v}"
curl -fsSL -o /tmp/headscale \
  "https://github.com/juanfont/headscale/releases/download/${TAG}/headscale_${VER}_linux_amd64"
sudo install -m 755 /tmp/headscale /usr/local/bin/headscale
sudo useradd -r -s /usr/sbin/nologin headscale 2>/dev/null || true
sudo mkdir -p /etc/headscale /var/lib/headscale
sudo headscale configtest 2>/dev/null || \
  curl -fsSL -o /tmp/hs-config.yaml \
    "https://raw.githubusercontent.com/juanfont/headscale/${TAG}/config-example.yaml" && \
  sudo cp -n /tmp/hs-config.yaml /etc/headscale/config.yaml
sudo tee /etc/systemd/system/headscale.service >/dev/null <<'UNIT'
[Unit]
Description=headscale coordination server
After=network-online.target
[Service]
User=headscale
ExecStart=/usr/local/bin/headscale serve
Restart=always
RestartSec=5
StateDirectory=headscale
RuntimeDirectory=headscale
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload

# --- minimal config ----------------------------------------------------------
sudo sed -i "s|^server_url:.*|server_url: ${SERVER_URL}|" /etc/headscale/config.yaml
sudo sed -i "s|^listen_addr:.*|listen_addr: 0.0.0.0:8080|" /etc/headscale/config.yaml

sudo systemctl enable --now headscale
sleep 2

# --- one user, two preauth keys (desktop + phone) ----------------------------
sudo headscale users create conrad || true
UID_=$(sudo headscale users list | awk '/conrad/{print $1; exit}')
echo "== Desktop preauth key =="
sudo headscale preauthkeys create --user "${UID_:-1}" --expiration 1h
echo "== Phone preauth key (reusable 24h) =="
sudo headscale preauthkeys create --user "${UID_:-1}" --expiration 24h --reusable

echo
echo "Done. headscale is at ${SERVER_URL}"
echo "Next: setup/02-join-devices.md"
