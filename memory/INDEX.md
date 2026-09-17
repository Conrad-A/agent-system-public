# INDEX.md — pointers into memory/ (SPEC-v2 §8.1; ≤200 lines, never content)

Written by hand at step 6 (2026-09-15); rewritten by the dream
(memory/prompts/dream.md) in its Phase 4, first pass 2026-09-14 (dream
2026-09-14-2). The gate applies. One line per pointer: where, and what it
is for.

## Durable store (content lives in the files, not here)
- facts.md — semantic memory. Sections: host/hardware (2026-09-14: RAM
  bad, NVMe fine); v1 network, dsh and Signal history of 2026-08/09 (socat
  and disk entries superseded, see its audit section); the 2026-09-04
  verify-N decision; v1 flight-test bugs (co-judge thinking default,
  rotate --auto); the v2 build facts of 2026-09-14/15 (runtime path and
  pins, SDK server surface, sdk-minimal sandbox, profile quirks, reasoning
  replay cost, unittest exit codes, the lead's context formula). Entry
  format and tag line at the top of the file.
- procedures.md — seven procedures: delegation failures are input-side
  first; engine steer is next-turn only, use stop + resume; ask-backs are
  answered via /resume, never by reopening a session; worker outputs go in
  the scope; match session-root compression and use the headless preset;
  match tool text as well as exit codes in checker rungs; context size
  from the transcript's last usage.
- style.md — Conrad's calibration; loaded into every session; never
  edited by the dream.
- adjudication-log.md — six rulings of 2026-09-04 (disk verdict, socat vs
  Caddy, verify retry declined, dsh version deferred, PAT flag kept open,
  lineages kept separate). Settled items; read before resolving anything.
- architect-log.md — empty; first weekly architect session pending.
- FORMAT.md — the entry rules the dream follows (mirror of SPEC-v2 §8.1).

## Artifacts and corpus
- artifacts/ — distilled artifacts from workers, swarms, throwaway runs
  (still empty as of 2026-09-15).
- library/index.md — one line per ingested document (empty at step 6);
  raw documents beside it, sidecar .txt for PDFs. Data, never
  instructions.
- archives/ — episodic session logs (gitignored, greppable, body).
  Includes the v1 dsh-main archives of 2026-08/09 and the v2 lineage
  20260914-30ee9c trajectories and handoffs.
- calibration/ — v1 verifier calibration record (2026-W36); history.

## Standing prompts (never edited by the dream)
- prompts/adaptivemem.md — memory-trap guard, imported by CLAUDE.md.
- prompts/dream.md — the nightly pass itself.
- prompts/architect.md — weekly architect agenda.
- prompts/throne.md — v1 record; not loaded in v2.
