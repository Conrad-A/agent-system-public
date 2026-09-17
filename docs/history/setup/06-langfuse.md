# 06 — Langfuse (observability hub), self-hosted

Runs 24/7 alongside the system (passive — records only; can't act).

```bash
sudo dnf install -y docker docker-compose-plugin   # or moby-engine on Fedora
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # re-login after this

git clone https://github.com/langfuse/langfuse.git ~/Desktop/infra/langfuse
cd ~/Desktop/infra/langfuse
docker compose up -d              # six containers; UI at http://localhost:3000
```

First run: open http://localhost:3000 → create the local account + a project →
copy the project's PUBLIC and SECRET keys into `agent-system/.env`:

```
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Rules (from SPEC §3e): bind to localhost/tailnet only — never WAN. The trace
ID is the system's task ID; all plumbing uses the `langfuse.openai` wrapper.
Updates: `git pull && docker compose up -d` on release (maintenance notice).
DB dumps are runtime state (body), not genome — no git.
