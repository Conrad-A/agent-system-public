# 05 — Remote desktop: 1:1 screen over the tailnet (planned)

Goal: see the actual desktop screen from the phone — true 1:1 capture of
whatever is running (ZCode window, tmux, dsh web) — with full control.
Everything stays inside the Headscale tailnet; nothing is exposed publicly.

## DECIDED (2026-08-27): Sunshine + Moonlight. Conrad reports Wayland.

Setup on the desktop (Wayland notes inline):

1. Install Sunshine: grab the latest release for your distro from
   https://github.com/LizardByte/Sunshine/releases (deb/rpm/flatpak).
2. Wayland capture: Sunshine uses KMS/DRM capture on Wayland. It needs:
   - `sudo setcap cap_sys_admin+p $(readlink -f $(which sunshine))`
   - input permissions: add your user to the `input` group and ensure the
     uinput udev rule Sunshine ships is active, then re-login.
   - If capture fails on your compositor, fall back: run the session on X11
     (login screen gear icon), or use RustDesk instead.
3. Hardware encoder: VAAPI on Intel/AMD GPUs, NVENC on NVIDIA. Sunshine
   auto-picks; verify in its web config (https://localhost:47990) that a
   hardware encoder is active — software x264 will cook a small machine.
4. First-run: open https://localhost:47990, set credentials, add
   "Desktop" as the app if not present.
5. Phone: install Moonlight (iOS/Android). With VPN on, add host by
   TAILNET IP. Enter the PIN pairing (Sunshine web UI → PIN tab).
6. Lock it down: Sunshine ports (TCP 47984-47990, UDP 47998-48010) should be
   reachable from the tailnet interface only — firewall them on LAN/WAN.

Fallback option if Sunshine/Wayland fights you: RustDesk (direct-by-IP over
tailnet, no relay, ~10 min). Classic VNC/xrdp: skip.

## Caveats

- Bandwidth: streaming is the heaviest of the three access layers; fine on
  Wi-Fi/5G, drop resolution/fps in Moonlight settings on weak connections.
- Moonlight assumes a GPU-ish host; on weak iGPUs lower the resolution.
- Encoder choice in step 3 depends on the GPU: check with
  `lspci | grep -i vga` and `vainfo`.
- Stream encryption: Sunshine/Moonlight has its own AES layer, and the whole
  stream rides inside the WireGuard tunnel anyway — encrypted twice.

## The three access layers (narrow → full)

| Layer | Channel | Gives you | Works when |
|---|---|---|---|
| 1 | Signal (watchdog + dsh plugin) | commands, status, recovery | anywhere, even VPN down |
| 2 | dsh web UI over tailnet | structured harness state | VPN up, dsh up |
| 3 | Remote desktop over tailnet | the actual screen, 1:1, full control | VPN up, machine up |
