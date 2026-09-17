#!/bin/sh
# PreCompact backstop (SPEC §3, §14): copy state.md + the raw transcript tail to a handoff, log a compaction EVENT. Copies only.
cd "$(dirname "$0")/../.." || exit 0
RT="${AGENT_RUNTIME:-$(grep '^AGENT_RUNTIME=' .env | cut -d= -f2-)}"; TS=$(date -u +%Y%m%dT%H%M%SZ); ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
T=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null)
LID=$(python3 -c "import json,os;print(json.load(open('$RT/lineages/index.json')).get(os.getcwd(),''))" 2>/dev/null)
mkdir -p "$RT/handoffs" && { echo "# handoff $TS — PreCompact backstop, lineage $LID"; echo; cat "$RT/lineages/$LID/state.md" 2>/dev/null; echo; echo "## raw transcript tail"; tail -c 24000 "$T" 2>/dev/null; } > "$RT/handoffs/$TS.md"
echo "{\"ts\": \"$ISO\", \"lineage\": \"$LID\", \"worker\": \"lead\", \"event\": \"compaction\", \"detail\": \"a compaction fired — a rotation was missed; handoff $TS.md\"}" >> "$RT/events.jsonl"
exit 0
