# Ship surface

Everything paper-trail ships lives under `src/` — mostly Markdown prompts, because the shipped product is an agent workflow, not a codebase.

## What's in `src/`

| Directory | Contents |
|---|---|
| `src/commands/` | Slash-command prompts — `/paper-trail` (the orchestrator) and its five sister commands. The orchestrator IS the agent: these prompts are the program. |
| `src/prompts/` | Dispatch prompts the orchestrator fills with `{{slot}}` values and sends to subagents (extractor / adjudicator / verifier). |
| `src/specs/` | Interface specs: `verdict_schema.md` (per-claim verdict contract), `ingest.md` (PDF-handle layout), `control_flow.md` (the orchestrator → dispatch → validation map — start here to trace the system), `trace_log.md` (observability records). |
| `src/skills/` | Project-owned skills (tracked via explicit `.gitignore` carveouts; local experiments stay untracked). |
| `src/scripts/` | Python only where Markdown is the wrong tool: `validate_claims.py`, `render_html_demo.py`, `ingest_pdf.py`. |
| `src/templates/` | `claims_ledger.md` — the canonical ledger schema both modes reuse. |

## How `.claude/` relates

Claude Code's discovery rules require commands and skills at `.claude/<dir>/` paths, so each content-bearing `.claude/<dir>/` is a subdirectory symlink into `src/<dir>/`. `src/` is canonical; `.claude/` is a publication target. Never edit through `.claude/`; if a symlink breaks, regenerate it from `src/` (`ln -s ../src/<dir> .claude/<dir>`). `.claude/settings.local.json` is machine-local Claude Code state and is not part of the ship surface.

## What's *not* ship surface

- `docs/` — human-facing documentation, plans, decision journal (you are here).
- `examples/` — canonical fixture runs used for smoke tests and demos.
- `experiments/` — gitignored scratch.
- `dev/` — engineering tooling for validating the ship surface (paper-trail itself is the tool, so this isn't called `tools/`).

## Where to start reading

1. `src/specs/control_flow.md` — the dispatch graph in three tables.
2. `src/commands/paper-trail.md` — the orchestrator, phases 0–5.
3. `src/specs/verdict_schema.md` — the contract every subagent's output is validated against.
