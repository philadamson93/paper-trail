# Plan — isolated `/paper-trail` run framework

**Status.** Plan-only. No code yet.

**Provenance.** Scoped 2026-05-01 in the same session as `docs/plans/repo-organization.md` and `docs/plans/feature-paperclip-first-architecture.md`. Decision-log entry to be appended to `docs/journal/2026-05-01-paperclip-coverage-revisit.md`.

**Depends on.** `docs/plans/repo-organization.md` lands first. This plan assumes the post-repo-org world where ship-surface artifacts live under `src/` and `.claude/<dir>/` is a symlink to `src/<dir>/`. If repo-org does not land first, the path references in this doc need updating to `.claude/<dir>/<file>`.

---

## Headline rationale and framing

The shipped product is `/paper-trail` — a Claude Code slash command driven by Markdown prompts plus Python helpers. To validate that the shipped product works for someone who is not the developer, we need to run it in an environment that does not depend on the developer's accumulated host state: locally-installed Python packages, MCP servers, environment variables already exported, paperclip credentials, scratch directories from prior runs.

The framework this plan scopes is **isolation, not unit testing**. There is no test suite to pass-or-fail. The output is a **regression-investigation report** that surfaces, per claim, how a controlled-environment run of `/paper-trail` agrees or disagrees with a baseline. The user — or a future review-agent — reads the report and decides, per case, which verdict is right. The framework does not assume the M1 baseline (`examples/paper-trail-adamson-2025/`) is ground truth. It reports drift; it does not adjudicate it.

This framing matters because the post-paperclip-first product will produce different verdicts than the M1 baseline for some references — paperclip-mode reading a different version of the same paper than M1's PDF-mode read may be more or less accurate. The framework needs to surface those cases for review, not silently fail or silently pass.

The principles inherited from the user's broader direction:

- **No train-test split.** Per memory `feedback_agentic_optimization_hygiene.md`, train/test/dev hygiene applies to the agentic-pipeline-optimization track on `sarol`, not to paper-trail-the-tool development on `main`. Isolation here is about reproducibility-under-controlled-deps, not about prompt-tuning hygiene.
- **Default to instructions over code.** The framework is mostly Docker plus a small shell driver. The diff/report tool is Python because it is genuine batch processing of JSON files.
- **Validate via real workflows.** v1 of the framework runs against the canonical Adamson fixture. A second small-and-fast fixture is an open question deferred until the first one shipped surfaces concrete time-cost.

---

## Implementation surface

**New directory layout:**

```
dev/
└── isolation/
    ├── Dockerfile              ← Claude Code CLI + paperclip CLI + Python deps
    ├── docker-compose.yml      ← orchestrates the Claude container + GROBID sidecar
    ├── run-test.sh             ← driver: bring up, run /paper-trail, capture output, generate report
    ├── report.py               ← diff/report tool (Python)
    ├── README.md               ← short explainer + quickstart
    └── runs/                   ← gitignored; per-invocation output dirs
        └── 2026-05-01T14:30Z-adamson/
            ├── paper-trail-adamson-2025-input-paper/
            │   ├── data/claims/*.json
            │   ├── claims_ledger.md
            │   └── ...
            ├── claude-session.jsonl       ← captured Claude Code session log
            ├── stdout.log
            └── report.html                ← the diff/investigation report
```

**Files to create:**

- `dev/isolation/Dockerfile` — base image with Claude Code CLI plus paperclip CLI plus Python plus the project's scripts. Pinned versions per the "reproducibility" decision below.
- `dev/isolation/docker-compose.yml` — two services: the Claude container and a GROBID sidecar. Network shared so the Claude container can reach GROBID at `http://grobid:8070`.
- `dev/isolation/run-test.sh` — driver script. Args: fixture path (e.g., `examples/paper-trail-adamson-2025/`). Brings up the compose stack, runs `/paper-trail` against the fixture inside the Claude container, captures all output to `dev/isolation/runs/<timestamp>-<fixture-stem>/`, runs `report.py`, brings down the stack.
- `dev/isolation/report.py` — diff/investigation report generator. Reads new-run claims plus M1-baseline claims; emits `report.html` with per-claim side-by-side: claim text, baseline verdict + reasoning excerpt, new verdict + reasoning excerpt, agreement classification (`agree-same-reasoning` | `agree-different-reasoning` | `disagree`).
- `dev/isolation/README.md` — short explainer: what this framework does, how to run it, what to expect in `report.html`. Not the project README; just the tool README. Per memory `feedback_short_headline_copy.md`, headline copy 1-2 sentences max.

**Files to update:**

- `.gitignore` — add `/dev/isolation/runs/` (per-run output dirs are scratch, not artifacts).
- `CLAUDE.md` — add `dev/` to the "Where things live" section as a tracked-but-not-shipped directory: tooling for validating the ship surface, not part of `/paper-trail` itself. Per memory `project_paperclip_collab.md` keep the framing factual; do not over-engineer the description.
- `docs/plans/repo-organization.md` — fold `dev/` into the recognized non-shipped top-level directories list so the repo-org plan and this plan agree on the layout.

**Naming and shape pins:**

- **`dev/isolation/`** — the path. `dev/` because "paper-trail" is the shipped tool (and "tools" would read as the product's name); `isolation/` because that is the specific concern. Future siblings could be `dev/release/`, `dev/lint/`, etc., as needed.
- **`runs/<timestamp>-<fixture-stem>/`** — per-invocation output directory naming. ISO 8601 timestamp (`2026-05-01T14:30Z`) plus a slug derived from the fixture path. Stable enough to sort lexically, unique enough to avoid collisions, human-parseable.
- **`report.html`** — the investigation report. Static HTML, viewable in any browser. Self-contained (inlines styles, no external assets) for portability.
- **`/paper-trail --paperclip=prefer`** — the default mode the isolation framework runs `/paper-trail` in (post-paperclip-first). Lets paperclip-mode handle in-corpus references and PDF-mode handle out-of-corpus. To exercise paperclip-mode in isolation specifically, pass `--paperclip=only` to the driver and accept that `unresolved` references will be flagged.

**Pinned design decisions:**

- **Authentication via host credential mount.** The Claude container reads `~/.paperclip/credentials.json` from the host as a read-only mount. The container has zero baked-in secrets; the credential file lives on host disk and the container references it at run time. Tradeoff: not a pure isolation — one host file is visible to the container — but the cost is zero developer friction. CI integration (a future plan) will switch to the `PAPERCLIP_API_KEY` env-var path.
- **GROBID runs as a sidecar in docker-compose.** Keeps the Claude container free of GROBID-installed-system state. The Claude container references it at the docker-compose service-name `grobid`. GROBID's image version is pinned in `docker-compose.yml`.
- **Pinned versions across the image stack.** The Dockerfile pins the Claude Code CLI version, paperclip CLI version, Python version, and Python package versions. GROBID's image is pinned in `docker-compose.yml`. Pinning is what makes "isolation" a real claim — without it, an upstream version bump silently changes the test environment. v1 pins to whatever versions are current at land-time; bumps happen as deliberate `dev/isolation/Dockerfile` PRs.
- **No silent baseline-vs-new pass-or-fail.** `report.py` reports drift. Drift is not a failure. The user (or a review-agent invoked manually) reads the report and decides per claim. The shell-script exit code is success (0) regardless of drift count, success (0) if `/paper-trail` itself completed, failure if `/paper-trail` errored or the container did not start.
- **Captured Claude session log.** The Claude Code session log (subagent dispatches, prompts sent, responses received, tool calls) is captured to `claude-session.jsonl` in the run directory. Useful when investigating disagreements: "what did paperclip-mode actually grep, and what did it find?" answers may live in the session log rather than in the verdict JSON.
- **No CI hookup in v1.** The framework is invokable on demand from a developer machine. Adding a GitHub Actions workflow (or similar) that runs the framework on every push is a separate plan once the framework's wall-clock cost is known.

**Smoke test fixture:** `examples/paper-trail-adamson-2025/`. The 56-reference, 88-claim canonical M1 reference run. Mounted read-only into the Claude container. Output goes to a fresh `dev/isolation/runs/<timestamp>-adamson/` directory each invocation.

---

## Codebase pointers for fresh agents

When picking up this plan and starting implementation:

- **`src/commands/paper-trail.md`** (post-repo-org; today `.claude/commands/paper-trail.md`) — the orchestrator. The Claude container needs to be able to invoke this slash command via Claude Code CLI (the CLI must have access to the project's `.claude/` dir, which means mounting the repo into the container).
- **`src/commands/paper-trail-init.md`** — the orchestrator's setup probe. Useful as a sanity check at container start: "are all dependencies actually available?" — if not, `/paper-trail` will fail with a confusing error. The driver script could optionally run `/paper-trail-init` before the actual run to surface dep issues fast.
- **`src/scripts/validate_claims.py`** — the JSON validator. The isolation framework runs it against the run's output as part of report generation. Failures here are real bugs (the run produced invalid claim JSONs), distinct from verdict-drift.
- **`src/scripts/render_html_demo.py`** — the per-claim HTML renderer. Different from `dev/isolation/report.py`, which is the diff-report tool. Both produce HTML; only `render_html_demo.py` is part of the ship surface. Confusing-but-real distinction.
- **`examples/paper-trail-adamson-2025/data/claims/`** — the M1 baseline `report.py` diffs against. 87 claim JSONs. The path is the legacy `data/claims/` layout (per CLAUDE.md note about `render_html_demo.py` auto-detecting both `data/claims/` and `ledger/claims/`).
- **`~/.paperclip/credentials.json`** — the host credential file the container mounts. If absent on host, `paperclip login` from host first. If absent and the developer is offline-only (no plan to use paperclip), the framework runs in `--paperclip=off` mode with the obvious caveat that paperclip-mode is not exercised.
- **paperclip CLI version** — currently 0.3.0 on the developer's host. The Dockerfile pins to whatever is current at land-time. To track upstream, watch for `paperclip update` notices in dev sessions.

---

## Smoke test plan

The framework succeeds in v1 if:

1. From a fresh checkout of the repo (no host-side `node_modules/`, no host `pdfs/` from prior runs, no host `.env` file beyond the project's standard configuration), running `./dev/isolation/run-test.sh examples/paper-trail-adamson-2025/` produces a `dev/isolation/runs/<timestamp>-adamson/report.html` containing 87 per-claim rows.
2. The Claude container had no host filesystem dependencies beyond:
   - The repo (mounted read-only)
   - `~/.paperclip/credentials.json` (mounted read-only)
   - The output dir under `dev/isolation/runs/` (mounted read-write)
3. `report.html` shows three classification buckets per claim:
   - **agree-same-reasoning** — new and baseline verdicts match, reasoning excerpts are substantively the same
   - **agree-different-reasoning** — new and baseline verdicts match, reasoning differs (often "paperclip-mode found a different supporting passage than PDF-mode found")
   - **disagree** — new and baseline verdicts differ
4. The shell driver exits 0 if the run completed; exits non-zero only on infrastructure failures (container did not start, GROBID unreachable, repo not mounted).
5. Re-running with the same fixture and the same Docker image version produces a `report.html` with the same agreement classification per claim — modulo LLM noise on AMBIGUOUS verdicts and modulo any reasoning-text drift on agree-different-reasoning claims. (The point isn't perfect reproducibility; it's that infrastructure-level differences shouldn't be the source of drift.)

What v1 does NOT need to do:

- Compare runs across paperclip-mode and PDF-mode for the same reference (that is interesting but a separate report).
- Track wall-clock cost or token cost (interesting but separate).
- Run multiple fixtures in parallel (interesting but separate).
- Hook into CI (separate plan once wall-clock is known).

---

## Open questions

1. **GROBID pinning depth.** GROBID's official Docker image is `lfoppiano/grobid:<version>`; the project's existing Phase 2.5 ingest pins `<version>` somewhere. Should `dev/isolation/docker-compose.yml` reuse the project's pinned version (one source of truth) or pin independently (clearer change log)? Default to reuse via a `.grobid-version` file at repo root; both Phase 2.5 and isolation read it.
2. **Claude Code CLI version pinning.** Claude Code releases on its own cadence. Pinning a specific Claude Code CLI version in the Dockerfile means isolation runs use that version regardless of what the developer has locally. Default: yes, pin. Update via deliberate `dev/isolation/Dockerfile` PRs.
3. **A second, fast-running fixture.** Adamson is 88 claims and probably 30+ minutes wall-clock. Useful for confidence; painful for iteration. Should `dev/` host a smaller fixture (e.g., 5-10 claims, 2-3 references) for quick smoke tests during framework development? Default: defer until v1 of the framework lands and we know the iteration loop's friction.
4. **Network-isolation level.** The Claude container needs network for paperclip, CrossRef, Semantic Scholar. Should it be allowed unrestricted egress, or should the docker-compose network be locked to specific outbound hosts? Default: unrestricted in v1; revisit if it becomes a security concern.
5. **Capturing the model version.** The Claude session log records which model the container's Claude Code CLI talked to (Opus 4.7 in this user's case at land-time). `report.py` should surface this as a per-run metadata field — a verdict produced by Opus 4.7 vs Sonnet 4.6 should be flagged when comparing across runs.
6. **Reporting output scope.** `report.html` per-claim rows are the primary surface. Should the report also produce a Markdown summary suitable for pasting into a PR description ("23 agree-same-reasoning, 12 agree-different-reasoning, 3 disagree, 0 errored")? Default: yes, as a top-of-`report.html` summary block plus a `report-summary.md` companion file.
7. **Symlink-aware bind-mounts in docker-compose.** Post-repo-org, `.claude/<dir>/` is a symlink to `src/<dir>/`. Docker bind-mounts dereference symlinks by default (mounts the target, not the link). Verify in implementation that mounting the repo root preserves both the canonical source and the symlinked-to-by-Claude-Code paths. If there is a problem, fall back to mounting `src/` and `.claude/` separately.

---

## Out of scope

- **Continuous Integration hook-up.** Once v1 runs, a separate plan can scope GitHub Actions invocation, secrets management for the CI auth path (`PAPERCLIP_API_KEY`), per-PR runs, etc.
- **Multi-fixture parallel runs.** v1 runs one fixture at a time.
- **Cost / wall-clock tracking dashboards.** v1 logs the run; aggregation is a future tool.
- **Comparing model versions.** Out of scope per the focused-validation framing. A separate "verdict drift across models" plan can come later if the question becomes load-bearing.
- **Anything related to `sarol`-track agentic-pipeline-optimization train/test/dev hygiene.** This plan is for paper-trail-the-tool engineering hygiene; the agentic-pipeline-optimization research line has different machinery and is not affected.
- **Replaying a run deterministically from captured prompts.** Cool but separate. Would require capturing every dispatch payload plus every subagent response, then a replay harness that feeds them back through.
- **Validating the `/issue` flow end-to-end.** `/issue` (per `docs/plans/feature-issue-command.md`) submits a bug report or verdict-dispute issue to the project's GitHub. Running it inside isolation needs a separate-from-real-GitHub mock; that is a follow-on plan once `/issue` ships.
- **Author-mode isolation runs.** v1 covers reader mode (Adamson PDF input) only. Author-mode isolation (using `examples/DFD_authormode/` as the fixture) is a follow-on plan.
