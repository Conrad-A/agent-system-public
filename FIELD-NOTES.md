# FIELD NOTES — what the build actually taught us

Companion to `SPEC-v3.1.md`. The SPEC says WHAT to build; this file is everything
we learned building it for real (Fedora 44 KDE Plasma, Aug 2026). Paste BOTH
files into an AI session when replicating. Where something is OS-specific
it's marked; a portability table sits at the end. The v2 build (Sept
2026) added the dsh SDK runtime section; KICKOFF.md is the v2
replication prompt.

## §0 — Kickoff prompt (paste this, then attach SPEC-v3.1.md + FIELD-NOTES.md)

```
You are helping me replicate a personal always-on AI agent system 1:1.
Two documents follow: SPEC-v3.1.md is the canonical design (if anything
conflicts, SPEC wins on WHAT to build); FIELD-NOTES.md is the deployment
experience from the original build (it wins on HOW things actually behave
— treat its gotchas as ground truth, not suggestions).

Work like this:
1. First, read both documents fully and tell me: my OS and what adapts
   (use the porting table), the build order you propose (network layer →
   harness A → plumbing/commands → verifier → harness B → memory/timers →
   observability → remote access → recovery channel), and what you need
   from me before starting (accounts, API keys, a domain, phone numbers,
   hardware facts). Ask your questions, then wait.
2. Then build ONE layer at a time. After each layer, give me its flight
   test from FIELD-NOTES and wait for my confirmation before continuing.
3. Commands you give me must be paste-safe: no line-continuation
   backslashes, single quotes around anything containing "!", and
   placeholders clearly marked — remind me a placeholder is ONLY the
   marked part (prefixes like ghp_ / signalcaptcha:// are already in the
   value I paste).
4. I mint my own domain, keys, tokens, and numbers. Never reuse example
   values from the documents; anything I accidentally paste into chat,
   tell me to rotate. Keys live in .env (gitignored), minimum scopes.
5. Keep a git repo from the start; after every working layer: commit,
   and push to a private off-machine remote.
6. When something fails, debug from evidence (logs, journals, curl status
   codes) before changing anything — FIELD-NOTES lists the known failure
   signatures per layer. Do not improvise around a safety refusal in a
   tool (e.g. a harness refusing 0.0.0.0): the notes give the sanctioned
   workaround.
Start with step 1 now.
```

## How to use these notes

- Build one layer at a time, verify each with a real end-to-end test before
  moving on. Every layer below carries a "flight test" — do it.
- When the assistant gives commands with PLACEHOLDERS (tokens, numbers,
  captcha links): the placeholder is ONLY the marked part. Two failure modes
  we hit repeatedly: pasting a value that already contains its prefix after
  a typed prefix (`ghp_ghp_...`, `signalcaptcha://signalcaptcha://...`), and
  running commands with the placeholder still in them.
- Paste command blocks WITHOUT line-continuation backslashes into terminals —
  wrapped lines with trailing `\ ` silently break mid-block.
- bash history expansion eats `!` inside double quotes (`!status` → "event
  not found"). Single-quote anything containing `!`.
- Any credential pasted into a chat is burned: rotate it. Mint tokens with
  minimum scopes only.

## dsh / Cordis plugin system (harness A)

- Pin the dsh version (`npx @deepseek-ai/dsh@<ver>`) and re-review community
  presets on every upgrade.
- `cordis.patch.yml`: a bare `- id:` row REPLACES an existing entry; NEW
  entries need the `- insert:` list form. Appending YAML to the shipped file
  creates two YAML docs → YAMLException: rewrite the whole file.
- Any `ctx.<prop>` access needs an inject declaration; the object form
  `{optional:[...]}` is unsupported on 0.1.1-rc.2 — plain arrays only.
  Safest plugin uses only `ctx.on`.
- Plugins can't print to chat directly; `reject`+`inject` parks output in an
  invisible inbox. Delivery = relay-rewrite: return `{kind:'enter'}` with
  the user message rewritten to "relay the following verbatim".
- `web --host` accepts ONLY 127.0.0.1 or 0.0.0.0 in config — and then the
  web command REFUSES 0.0.0.0 at runtime ("would expose remote code
  execution"). Keep dsh on loopback; do remote access with a relay (below).
- `--trusted-host` covers RPC only. The configuration plane
  (host.pickDirectory etc.) is loopback-same-origin by design, and the
  workspace picker is a NATIVE dialog on the host's screen — remote devices
  resume existing sessions instead of creating workspaces.
- Foreground `dsh | head` left running holds the port → EADDRINUSE loops.
  `pkill -f "@deepseek-ai/dsh"` before restarts; `timeout 45` for tests.

## dsh SDK runtime — v2 build notes (2026-09-14/16)

The v2 workers run on `deepseek-harness-sdk` 0.1.5rc1 (the `sdk` server
over the pkg-packaged dsh runtime), not on the dsh CLI above; the facts
below were read from the runtime binary and proven in flight (HANDOFF.md,
step 8). KICKOFF.md, the v2 replication prompt, points here.

- THE PKG NATIVE CACHE LIVES UNDER HOME. The runtime is a pkg-packaged
  node executable; its dlopen hook copies every native module's package
  under `$PKG_NATIVE_CACHE_PATH`, else `$HOME/.cache/pkg/<hash>`, on
  EVERY launch, with plain overwrites (no temp-and-rename). A worker
  whose shell HOME is its lane dir therefore drops ~38 MB of `.cache/pkg`
  in the lane — under memory/artifacts/, where the dream's copy choked on
  a native `.node` file (UnicodeDecodeError, 2026-09-15). Fix: engine.py
  sets `PKG_NATIVE_CACHE_PATH=$DSH_HOME/cache/<worker id>` PER WORKER
  (never one shared dir — simultaneous lanes would race on the
  non-atomic re-copy) and rmtree's it at close; the lane fence trips on
  that path; consolidate.py copies UTF-8 text only and skips the rest.
  The harness forwards its env to the worker's shell — only
  credential-shaped and `DSH_*` names are scrubbed.
- THE HOOKS BRIDGE IS THE ONLY CHANNEL INTO A RUNNING TURN. A steer
  queued as a follow-up is spliced `next-turn`; the running turn never
  sees it. What does reach it: `@deepseek-ai/dsh-hooks-claude-code`
  (installed in the profile's node_modules, mounted by neither shipped
  profile) runs Claude-Code-style hooks from one config per process
  (`configPath`, read at startup; hook cwd = the session workspace); a
  PostToolUse command hook's stdout JSON `additionalContext` lands as a
  user message after the tool result. The context meter rides on it:
  `cat <meter file>`, the file rewritten atomically before every model
  call. Fail-open: an unreadable config or a failing hook is logged and
  the agent continues.
- MOUNTING IT: the v1 note above holds — a bare `- id:` row MODIFIES an
  entry the patch finds (and warns `patch: entry "…" not found`
  otherwise); new rows need the `- insert:` list form. The bridge injects
  `["shell", "sessionProjections"]`, and the minimal profile never
  provides `ctx.shell` (its persistent bash runs over the PTY seam), so
  on minimal the row sits `pending (waiting for service: shell)` until
  the patch also inserts the sdk profile's `bash-sandbox` row
  (`@deepseek-ai/dsh-bash-sandbox`, registers as ctx.shell; the tool
  layer is unchanged). Prove a mount offline: start + close the harness
  on both profiles and read `h.client._stderr_lines` (a deque of 400) —
  zero lines, or `N entry did not activate`. `dsh --profile <p>
  --dump-default-config` prints the shipped tree offline.
- Binary recipes: `LC_ALL=C grep -a -o -E '<pat>' <runtime binary> |
  sort | uniq -c` for counts; python `b.find(b'<literal>')` and a
  ±300-byte window for context; a plugin's docs sit at `@module
  @deepseek-ai/<pkg>` with `const name / inject / provide`.

## DeepSeek API quirks

- Thinking mode silently ignores temperature/top_p.
- With `tools` present, `reasoning_content` must be replayed on every
  subsequent request or the API 400s.
- max_tokens INCLUDES thinking tokens. 4096 with effort=max returns EMPTY
  answers (all budget spent reasoning). Use ≥16384 for generator calls.
- The visible tool catalog conditions the chain-of-thought (Minimal →
  "We/Let's" deep chain; wide Standard catalog → "Let me" stepwise). This is
  a real, reproducible effect — tool scope IS a cognition knob.

## Z.ai / GLM quirks (judge + harness B)

- The endpoint returns NO logprobs, ever. Score-token logprob expectation
  (the paper's method) is impossible — approximate with N samples at
  temp ~0.6, parse the digit from text.
- GLM-5.3-flash CANNOT disable thinking (only low/high/max) — a judge with
  max_tokens=4 returns empty content. Use effort low + max_tokens ~2048.
- Judge bills the Z.ai account: empty balance → 429 → silent fallback to
  self-scoring with meaningless flat scores. CROSS mode + score spread is
  the health signal.
- ZCode "Use API Key" with prepaid balance needs the OpenAI protocol and
  base URL `https://api.z.ai/api/paas/v4` (the default Anthropic route
  fails auth for balance accounts; coding-plan accounts use /api/coding/).

## ZCode plugins (harness B surface)

- Claude-Code-compatible layout; `.zcode-plugin/plugin.json` manifest;
  hooks in `hooks/hooks.json` auto-discovered.
- UserPromptSubmit hooks CANNOT rewrite the prompt. Blocking works, but the
  UI shows only "Blocked" — the reason text is swallowed. Deliver command
  output by injecting `additionalContext` with a relay-verbatim instruction.
- Installed plugins are COPIES in a cache — path-relative tricks back to
  your repo break. Anchor absolute paths (env override + fallback).
  Updates need a marketplace refresh + version bump in BOTH plugin.json and
  marketplace.json (or uninstall/reinstall). Hooks snapshot at session
  start: test in a NEW session.

## Remote access saga (the hardest 20%)

- iOS Tailscale REFUSES plain-http coordination servers (ATS). Headscale
  must serve real HTTPS: forward TCP 80+443, Let's Encrypt HTTP-01,
  listen on the LAN IP if tailscaled already holds 443 on tailnet IPs.
- Home NAT usually can't hairpin: map your public domain to the LAN IP in
  /etc/hosts on the server machine. Side effect: with no static hostname
  set, the machine ADOPTS the domain's first label as its transient
  hostname — `hostnamectl set-hostname <name>` pins it.
- LE rate limit: 5 failed authorizations/hour per name. Fix the setup
  BEFORE retrying, or wait out the window.
- Newer headscale: `nodes register` is deprecated → `auth register
  --auth-id hskey-authreq-... --user <name>`; `preauthkeys create` wants
  the NUMERIC user id. iOS join: app's custom-server flow shows the
  auth-id; run the register command server-side.
- Enable the embedded DERP (needs the HTTPS) — without a relay, a phone
  with a suspended tunnel has no fallback path and everything "randomly"
  times out.
- Web apps over the tunnel NEED a secure context: plain http origins lack
  crypto.randomUUID → the app breaks mysteriously. And iOS Safari:
  (a) silently downgrades https→http for bare IP:port URLs and for hosts
  it previously saw over http (cache survives private tabs; Chrome or
  Clear History escapes it); (b) hard-rejects self-signed certs >825 days
  or missing serverAuth EKU — and even compliant self-signed certs get a
  silent http fallback, not a warning. VERDICT: skip self-signed entirely;
  issue a real LE cert for a DEDICATED name (DNS-01 via your dyndns
  provider's API), serve it tailnet-side, and resolve that name to the
  tailnet IP via headscale `dns.extra_records` (watch for an existing
  `extra_records: []` line that overrides an inserted block).
- Relay = Caddy: terminate TLS on the tailnet IP, `reverse_proxy` to
  loopback with `header_up Host localhost:<port>` + `header_up -Origin`
  (grants tailnet devices localhost-grade access — fine for owner-only
  tailnets, remember it before enrolling anything less trusted).
- iCloud Private Relay proxies Safari traffic around your VPN for
  public-looking domains — a confounder while debugging; its "IP will be
  revealed" prompt on private IPs is harmless.

## Signal watchdog

- signal-cli ships a native Linux binary (no Java) — check releases.
- One number = one Signal account = one primary device. Registering a
  number that a phone's Signal uses KICKS the phone. The bot needs a
  number that is nobody's.
- Registration captcha: tokens are single-use, ~1-minute life. On the
  captcha page: Cancel the open-app popup, RIGHT-CLICK "Open Signal" →
  copy link. `register --captcha 'link'` (the link already starts with
  signalcaptcha://). Voice fallback exists but only ≥1 min after an SMS
  attempt, with a fresh captcha.
- Signal hides sender numbers (number privacy): envelopes carry
  `sourceUuid`, often NO sourceNumber. Match the UUID (find it in the
  daemon journal) and reply to the UUID.
- Daemon socket: `$XDG_RUNTIME_DIR/signal-cli/socket` — a wrong default
  path = silent reconnect loop that looks exactly like "bot ignores me".
- Flight test: message `status` from the allowed account; check
  the daemon journal (received envelope?) then the watchdog log
  (IGNORED/COMMAND lines) to localize failures.

## systemd (user services run everything)

- Paths with spaces MUST be quoted in `EnvironmentFile=` and `ExecStart=`
  ("Project 2" broke both, twice).
- `%h` expands to $HOME inside user units.
- A service wrapping `tmux new-session -d '<cmd>'` reports SUCCESS even
  when `<cmd>` dies instantly — debug by running the inner command in
  the foreground with `timeout`.
- Vendors name units creatively (`app-dev.lizardbyte.app.Sunshine.service`)
  — `rpm -ql <pkg> | grep service` before guessing.
- Timers: `Persistent=true` catches missed runs; verify with
  `systemctl --user list-timers`.

## Infra grab-bag

- Corrupted docker layer pulls happen; a plain retry may reuse the bad
  cache — `docker image prune -af` forces a truly clean re-pull. ClickHouse
  validates its own binary checksum and says "faulty hardware" — believe
  it enough to run smartctl. Repeated corruption events (docker, .pyc,
  rpmdb) in one day = check the DISK (`smartctl -a`, Media Errors counter)
  and schedule a memtest. `rpm --rebuilddb` fixes a malformed rpmdb.
- Port collisions cascade: headscale metrics vs MinIO (9090/9091) — move
  metrics somewhere boring (9095).
- firewalld pattern that served us well: tailscale0 interface in the
  trusted zone; per-port rich rules rejecting 192.168.0.0/16 for anything
  that must be tailnet-only; a blunt reject also kills loopback-path
  traffic — scope rejects by source subnet.
- GitHub asset names change (`latest/download/<guessed-name>` 404s
  silently → 9-byte "Not Found" files that fail tar). Query the releases
  API for real asset URLs.
- Genome vs body: git repo (+ private off-machine remote) holds everything
  behavior-defining; runtime state/DBs stay local. Push after every
  meaningful commit.

## Porting off Fedora (broad strokes)

| Fedora piece | macOS | Windows |
|---|---|---|
| dnf / rpm | Homebrew | winget/choco |
| systemd user units + timers | launchd (LaunchAgents) | Task Scheduler / NSSM services |
| firewalld rich rules | pf / app firewall | Windows Defender Firewall rules |
| tmux service wrapper | same (brew tmux) | run in a service wrapper instead |
| KMS/Wayland capture (Sunshine) | native capture | native capture (easiest platform) |
| /etc/hosts hairpin fix | /etc/hosts | C:\Windows\System32\drivers\etc\hosts |
| signal-cli native binary | native build exists | use the JVM build |
| SELinux/setcap steps | not applicable | not applicable |

Everything above the OS layer — dsh, ZCode, the plugins, plumbing (Python),
verifier, Langfuse (Docker), headscale clients — is cross-platform as-is.
Headscale SERVER is easiest on Linux; a $3 VPS is the clean alternative
(kept-as-idea in SPEC-v3.1 §4).

## Before sharing your copy publicly

Sanitize: your domain, phone numbers, tailnet IPs beyond defaults, GitHub
username, any UUIDs, and `memory/` contents are all personal. `.env` is
gitignored — keep it that way; check `git log` for leaked values before
publishing history. Fresh replicators should mint their OWN: domain,
numbers, tokens, keys.
