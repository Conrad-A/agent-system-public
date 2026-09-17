#!/bin/sh
# SessionStart hook (SPEC §3, §14): print the lineage's state.md and the newest handoff. Copies and prints only.
cd "$(dirname "$0")/../.." || exit 0
RT="${AGENT_RUNTIME:-$(grep '^AGENT_RUNTIME=' .env | cut -d= -f2-)}"
LID=$(python3 -c "import json,os;print(json.load(open('$RT/lineages/index.json')).get(os.getcwd(),''))" 2>/dev/null)
[ -n "$LID" ] && [ -f "$RT/lineages/$LID/state.md" ] && { echo "=== lineage $LID state.md ==="; cat "$RT/lineages/$LID/state.md"; }
H=$(ls -t "$RT"/handoffs/*.md 2>/dev/null | head -1)
[ -n "$H" ] && { echo; echo "=== newest handoff: $H ==="; cat "$H"; }
exit 0
