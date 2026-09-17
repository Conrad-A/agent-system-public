# 04 — Signal bridge (DIY, planned)

Goal: command both harnesses from Signal on the phone, E2EE end to end.

## Design (rev 2: dsh plugin, not external script)

dsh has a documented channel-plugin pattern (platform → upstream driver →
channel adapter → ChannelService → harness bridge) and existing community
channel plugins (Telegram remote, 25+-channel notify/control). No Signal
channel exists — Signal has no bot API — so we build one:

```
Signal app (phone) ⇄ Signal servers (E2EE — content unreadable in transit)
                       ⇅
   signal-cli daemon (desktop, registered to a SECOND number — see below)
                       ⇅
   dsh-signal-channel plugin: signal-cli as upstream driver, adapter modeled
   on dsh-telegram-channel → inherits session binding, !status/!stop-style
   commands, notifications. ZCode is commanded THROUGH dsh (control logic
   lives in dsh only).
```

- Register signal-cli with a separate number (free eSIM/VoIP number), NOT your
  personal one — you message the bridge like a contact.
- signal-cli runs in daemon/JSON-RPC mode; the plugin long-polls it.
- Faster interim option: wire signal-cli to the multi-channel plugin's generic
  webhook lane — less integrated, quicker to stand up.
- Reference implementations: github.com/hi-wenw/dsh-telegram-channel,
  github.com/wsz987/dsh-channels, github.com/AsamK/signal-cli

## Security rules (non-negotiable)

1. Allowlist: bridge acts ONLY on messages from your Signal number; everything
   else is logged and ignored.
2. Low privilege: coarse command set (status, start goal X, pause, approve/deny).
   No raw shell passthrough. The bridge is an INPUT to the harness, and message
   content is untrusted (prompt-injection surface) — never interpolated into
   shell commands.
3. Confirmations: any destructive/irreversible action requires an explicit
   second "yes" message.
4. No secrets in channel — not keys, not file contents from sensitive dirs.
5. Bridge process runs as your user, no sudo, and is stopped by
   `systemctl --user stop signal-bridge` if anything looks weird.

## Connecting Signal + tailnet (decided 2026-08-27)

1. SIGNAL WATCHDOG (separate from the dsh plugin): a standalone systemd service
   running its own signal-cli listener, independent of dsh, with a hardcoded
   command set only: `restart dsh` / `restart zcode` / `reboot` / `status` /
   `vpn up`. Same allowlist rules. ~50 lines. This is the recovery path when
   dsh (and therefore the channel plugin) is down — no VPN required.
2. DEEP LINKS: bridge notifications include tailnet URLs
   (http://<desktop-tailnet-ip>:3080/...) so a tap + VPN toggle jumps from a
   Signal alert into the full web UI. Signal = notify/trigger layer,
   tailnet = full-control layer.
   Limit: Signal is a messaging API, not a transport — full UI/SSH cannot
   tunnel through it; rich access stays on Headscale.

## Status

Planned — build after Phase 1 (access + harnesses) is running. Build order:
watchdog first (it's tiny and covers recovery), then the dsh channel plugin.
signal-cli: https://github.com/AsamK/signal-cli
