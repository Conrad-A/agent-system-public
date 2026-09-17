# OPERATIONS — command cheat sheet (2026-09-01)

Everything from the finishing sequence, in one place. Run from any terminal
unless noted. Repo root = `~/Desktop/"Project 2"/agent-system`.

## Post-reboot health check (the whole system in one paste)

```bash
sudo systemctl is-active headscale tailscaled docker
systemctl --user is-active agent-system dsh-tailnet-relay signal-daemon watchdog consolidate.timer
curl -sk -o /dev/null -w "sunshine:  %{http_code}\n" https://localhost:47990/
curl -s  -o /dev/null -w "dsh relay: %{http_code}\n" https://dsh.YOUR-DOMAIN:3080/
curl -s  -o /dev/null -w "langfuse:  %{http_code}\n" http://localhost:3000/
```

Everything `active`, curls 200-ish (sunshine may 307/401 — fine).

## Daily habit: commit + mirror the genome

```bash
cd ~/Desktop/"Project 2"/agent-system
rm -f .git/*.lock                    # sandbox sessions leave locks
git add -A && git commit -m 'message with no ! in double quotes'
git push backup main                 # off-machine mirror (private GitHub)
```

Bash eats `!` inside double quotes — use single quotes for commit messages.

## Consolidation timer (nightly, 19:45 machine time)

```bash
systemctl --user list-timers | grep consolidate   # next + last run
systemctl --user start consolidate.service        # run it right now
journalctl --user -u consolidate.service -n 20    # what the last run did
systemctl --user disable --now consolidate.timer  # pause
systemctl --user enable  --now consolidate.timer  # resume
nano ~/.config/systemd/user/consolidate.timer     # change OnCalendar=*-*-* HH:MM:00
systemctl --user daemon-reload && systemctl --user restart consolidate.timer
```

Machine clock is US Eastern. DeepSeek off-peak pricing = 16:30–00:30 UTC:
19:45 EDT = 23:45 UTC (inside), but WINTER (EST) makes it 00:45 UTC — just
past the window. Nudge OnCalendar to 19:15 when clocks change in November.

## Judge calibration timer (weekly, Sunday 09:00 — Fable module)

Install once (units ship in the repo — genome rule):

```bash
mkdir -p ~/.config/systemd/user
cp ~/Desktop/'Project 2'/agent-system/systemd/calibrate.service ~/.config/systemd/user/
cp ~/Desktop/'Project 2'/agent-system/systemd/calibrate.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now calibrate.timer
```

Daily use:

```bash
systemctl --user list-timers | grep calibrate     # next + last run
systemctl --user start calibrate.service          # run it right now
cat ~/Desktop/'Project 2'/agent-system/memory/calibration/latest.json
```

Needs !verify traffic in the ledger first (3+ judgments); report-only.

## dsh service (chat surface A)

```bash
pkill -f "@deepseek-ai/dsh"; sleep 2; systemctl --user restart agent-system
tmux capture-pane -pt agents | tail -15           # dsh's own output
```

URLs: desktop `http://localhost:3080` · any device on VPN
`https://dsh.YOUR-DOMAIN:3080` (use the NAME, not the IP — cert matches
the name; iOS Safari silently downgrades https on bare IPs).

## Signal: register a number to signal-cli (the captcha dance)

1. Type, do NOT press Enter, cursor between the quotes:
   `signal-cli -a +1NUMBER register --captcha ''`
2. Browser → signalcaptchas.org/registration/generate.html → solve.
3. Popup appears → Cancel → right-click "Open Signal" → Copy Link.
4. Paste between the quotes, Enter — within ~1 minute (tokens are
   single-use and die fast). Silence = success.
5. SMS with 6 digits arrives at the number (can be slow; voice fallback:
   repeat with `register --voice --captcha '...'` — but only ≥1 min AFTER
   an SMS attempt, fresh captcha).
6. `signal-cli -a +1NUMBER verify DIGITS`

One number = one Signal account = one primary device. Registering here
kicks any phone using that number.

## Watchdog (recovery channel — bot = +1BOTNUMBER)

From your phone's Signal, message the bot. Commands (plain, no `!`):
`status` · `restart dsh` · `restart zcode` · `reboot` · `vpn up`

Caveats: `restart zcode` targets a `zcode` user unit that doesn't exist yet
(ZCode runs as a desktop app) — it will report FAILED until one is defined;
`reboot` needs a polkit rule (or sudoers) to work unprivileged; `vpn up`
needs a `NOPASSWD: /usr/bin/tailscale` sudoers entry. `status` and
`restart dsh` work out of the box.

```bash
systemctl --user is-active signal-daemon watchdog
journalctl --user -u signal-daemon -n 12 --no-pager  # shows received envelopes
cat ~/Desktop/agent-system-runtime/watchdog.log | tail -5
systemctl --user restart signal-daemon watchdog
```

Allowed sender lives in `~/.config/systemd/user/watchdog.service`:
`WATCHDOG_ALLOWED_NUMBER` (your number) AND `WATCHDOG_ALLOWED_UUID` — Signal
hides sender numbers, so the UUID is what usually matches. Find a sender's
UUID in the signal-daemon journal ("Envelope from: ... <uuid>"). After any
edit: `systemctl --user daemon-reload && systemctl --user restart watchdog`.

## Manage the bot's Signal account (without touching your phone)

GUI: link Signal Desktop to the bot account —

```bash
flatpak install -y flathub org.signal.Signal
sudo dnf install -y zbar
flatpak run org.signal.Signal &        # shows a link QR
# screenshot the QR to /tmp/qr.png, then:
zbarimg --raw /tmp/qr.png              # prints the sgnl:// link
systemctl --user stop signal-daemon
signal-cli -a +1BOTNUMBER addDevice --uri 'sgnl://PASTE'
systemctl --user start signal-daemon
```

CLI one-liners (stop the daemon first — one process owns the account):

```bash
systemctl --user stop signal-daemon
signal-cli -a +1BOTNUMBER updateProfile --given-name "Watchdog"
signal-cli -a +1BOTNUMBER send -m "hello" +1SOMEONE
systemctl --user start signal-daemon
```

## Headscale / tailnet

```bash
sudo headscale nodes list
sudo headscale preauthkeys create --user 1 --expiration 24h --reusable   # numeric user id!
sudo headscale auth register --user conrad --auth-id hskey-authreq-...   # iOS join flow
sudo headscale nodes rename -i <ID> <newname>
tailscale ping <node>            # direct vs DERP path
```

iOS app: custom coordination server = `https://YOUR-DOMAIN` (HTTPS
mandatory — iOS refuses plain http). Router forwards: TCP 80 (ACME renewals
— keep it), TCP 443, UDP 3478. Nothing else.

## Certificates (all auto-renew — spot-check ~Oct 27)

- headscale: Let's Encrypt built-in (needs router TCP 80).
- dsh relay: acme.sh cron renews dsh.YOUR-DOMAIN and restarts the
  relay itself. Manual poke: `~/.acme.sh/acme.sh --renew -d dsh.YOUR-DOMAIN --ecc`
  (the cert was issued as ECC — without `--ecc` acme.sh looks in the wrong dir).

## Langfuse (traces at http://localhost:3000)

```bash
cd ~/Desktop/infra/langfuse
sudo docker compose ps                 # all six healthy
sudo docker compose restart            # gentle kick
sudo docker compose down && sudo docker compose up -d   # full cycle
git pull && sudo docker compose up -d  # update on release
```

## Tests (run before promoting any change)

```bash
cd ~/Desktop/"Project 2"/agent-system && python3 plumbing/tests/run_tests.py
```

## Hardware note (corrected 2026-09-14)

The drive is fine — the 2026-08-31 / 09-04 "replace the drive" verdict was
wrong and is withdrawn. The RAM needs replacing (owner chore).

## Credential hygiene (learned the hard way)

- Any token/key pasted into a chat is burned — rotate it.
- Tokens get minimum scopes (`repo` only, etc.).
- Keys live in `.env` (gitignored) and systemd EnvironmentFile lines —
  quote paths containing spaces: `EnvironmentFile="%h/Desktop/Project 2/..."`.
