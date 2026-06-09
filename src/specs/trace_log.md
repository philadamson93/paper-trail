# Trace log — per-subagent observability records

Every subagent dispatch and final message in a `/paper-trail` run is logged to `<output-dir>/trace/<subagent_id>.jsonl` — one file per subagent, newline-delimited JSON records. This is the local observability substrate: grep-able, diff-able, no vendor dependency. No Phoenix / Langfuse dependency in v1; if a vendor observability tool is needed later (M2+), it reads this same JSONL as its source.

## Record schema

Each line is one event:

```json
{
  "ts": "2026-04-18T15:22:03.412Z",
  "run_id": "run_20260418T1522Z",
  "subagent_id": "extractor-C042",
  "stage": "grounding",
  "role": "extractor",
  "claim_id": "C042",
  "event": "dispatch",
  "prompt_hash": "sha256:abcdef...",
  "payload": {"claim_text": "...", "handle": "pdfs/hammernik2021/"}
}
```

## Events

- `dispatch` — orchestrator sends a prompt to a subagent. `payload` = the dispatch slot values.
- `final_message` — subagent returns. `payload` = the subagent's last message + exit path.
- `validation_pass` / `validation_fail` — orchestrator's schema check result. On fail, `payload.errors` is populated.
- `bounce` — verifier rejected; re-dispatching. `payload.reason` is the verifier's note.
- `escalation` — the orchestrator gave up on a claim (second bounce, second schema fail).

## Usage

- `cat trace/*.jsonl | jq 'select(.event == "validation_fail")'` — find every schema violation across the run.
- `grep '"claim_id":"C042"' trace/*.jsonl` — reconstruct the full history of one claim.
- `jq -r 'select(.event == "final_message") | [.role, .claim_id, .payload.exit_path] | @tsv' trace/*.jsonl` — quick tabular view of all subagent outcomes.
