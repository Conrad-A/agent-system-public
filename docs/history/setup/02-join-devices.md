# 02 — Join devices to your Headscale

You use the **official Tailscale apps** everywhere; they just point at *your* server instead of Tailscale's.

## Desktop (the agent host — same machine as headscale is fine)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --login-server http://YOUR-SERVER:8080 --authkey <DESKTOP-KEY-FROM-STEP-01>
tailscale ip -4   # note this 100.x.y.z address — it's your desktop's tailnet IP
```

## Phone

Install the Tailscale app (iOS App Store / Google Play), then point it at your server:

- **Android:** open the app → three-dot menu (before logging in) → **Change server** → enter `http://YOUR-SERVER:8080` → log in with the reusable key (or headscale's web/CLI approval flow).
- **iOS:** iOS Settings app → Tailscale → **Alternate Coordination Server URL** → enter your server URL → then open the app and log in.

If a menu has moved (apps update), search "headscale android/ios client setup" — the headscale docs site keeps current instructions.

## Verify

From the phone (Wi-Fi off, mobile data on, VPN on): open `http://<desktop-tailnet-ip>:3080` in the browser once dsh is running (step 03). If the UI binds only to localhost, use the SSH tunnel fallback in step 03's header.

Also on the phone: install **Termius** (or any SSH app), add the desktop by its tailnet IP — this is your admin fallback and works even if the web UI misbehaves.
