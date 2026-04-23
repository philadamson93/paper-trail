# Operational hygiene for the Sarol experiment optimization loop

Companion to `experiment-sarol-leakage-hardening.md` and `experiment-sarol-hardening-implementation.md`. Those documents cover the structural defenses for subagent dispatches. This document articulates the **orchestrator-session rule**: the main planning session (the researcher ↔ LLM discussion in which failure modes are diagnosed and prompt edits are proposed) must also be test-blind, and why.

> **Important 2026-04-21 — scope update.** Rule 1 (subagent sandboxing) remains authoritative. **Rule 2 is superseded for the agent-only experiment** defined in `agentic-pipeline-optimization-framework.md`: in agent-only mode there is no human main planning session, and test-blindness is enforced structurally as Tier 3 sealing (filesystem + CLI gating) rather than as a human-discipline norm. Rule 2 remains the authoritative rule for any human-in-the-loop variant (e.g., the deferred future paper on human-agent research collaboration). The discussion below is preserved for that context; see §"Relationship to the agent-only framework" at the end of this doc for the mapping.

## The two rules

### Rule 1 — Subagents are structurally sandboxed from gold

**Already in place** as of commit 869003c and follow-ups. The extractor, adjudicator, and verifier subagents dispatched by the orchestrator cannot reach gold labels, claim row-ids, split names, paper buckets, or raw benchmark data.

Defenses:

- Gold files live outside the repo tree (`$PAPER_TRAIL_GOLD_DIR`, default `$HOME/.paper-trail/gold/sarol-2024/<split>/`).
- Benchmark raw data lives outside the repo tree (`$PAPER_TRAIL_BENCHMARKS_DIR`, default `$HOME/.paper-trail/benchmarks/sarol-2024/`).
- `stage_claim.py` generates opaque `ref_<6hex>` citekeys by hashing (split, claim_id, paper_bucket). The subagent sees only the opaque ref.
- `staging_info.json` contains only `citekey`, `claim_text_normalized`, `source_mode`, `multi_cit_context`, `source_description` — no claim row-id, no split, no paper bucket.
- Every dispatch appends the filesystem-restriction paragraph (see runbook). Violations invalidate the verdict.

### Rule 2 — The main planning session is test-blind by policy

**In place as of 2026-04-21.** The orchestrator / researcher LLM planning session — this session, the one where failure modes get diagnosed and prompt edits get proposed — must not see the test split of any benchmark being used for reporting.

Enforcement: test files have been moved out of `$PAPER_TRAIL_BENCHMARKS_DIR` to `$HOME/.paper-trail-sealed/sarol-2024-test/`. `stage_claim.py --split test` now fails cleanly with `FileNotFoundError`. `ls` against the sealed directory reveals filenames (and therefore split membership) but no labels; even so, the main session should not read or glob that directory.

## Why both rules matter — the less-obvious part

**Rule 1** is the obvious rule. A subagent that reads gold before emitting a verdict trivially biases the verdict. Most "don't leak labels to the grader" intuition lives here, and every benchmark-evaluation codebase implements some version of it.

**Rule 2 is the subtle one.** The main planning session — the place where the researcher and the orchestrator LLM talk through failure modes, read predictions, propose prompt edits, approve schema changes — **is the optimizer in the closed-loop optimization**. Every prompt edit that lands on disk is an output of that conversation.

If the main session sees a test label — even once, even "just to sanity check" — that observation flows into every subsequent prompt-edit proposal via human-in-the-loop effects. A researcher who has mentally noted "test claim X was labeled CONTRADICT" will subtly bias their next adjudicator-prompt edit toward catching the pattern that made X a CONTRADICT. There is no formal mechanism to "unsee" the observation.

Mathematically this is no different from training on test. The optimizer is non-differentiable, but the feedback loop is the same shape as gradient descent against test loss.

## What is and isn't allowed

### Allowed (and expected)

- Main session reads train claims + train gold freely. Train is the iteration corpus.
- Main session reads dev claims + dev gold, but only as a validation-of-winner checkpoint — not per-cycle. Continuous dev-based iteration overfits dev.
- Main session discusses Sarol's published baselines (MultiVerS, GPT-4 4-shot) — those are public numbers from the upstream paper, not our test predictions.
- Subagents read only what `stage_claim.py` wrote into their staging tree, plus the Sarol rubric spec.

### Disallowed

- Main session reads any file under `$HOME/.paper-trail-sealed/`.
- Main session globs or `ls`-es the sealed directory to see filenames, even without reading contents. Filenames in this context leak split membership, which is enough to bias test-claim selection downstream.
- Main session reconstructs test-split gold via any indirect route — re-downloading `annotations.zip` to a non-sealed location, scraping public repros, asking an LLM to recall what Sarol labels were for specific claim IDs, running the real Sarol authors' open-source tools against our test claims.
- Subagents read any file under `$PAPER_TRAIL_GOLD_DIR`. (Structurally prevented; noted for completeness.)

## When test unseals

Once per locked configuration, for a single final evaluation. All of the following must hold before unsealing:

1. Extractor + adjudicator + verifier prompts are frozen and committed on a dedicated branch.
2. Full train evaluation (N = 2,141) produces a macro-F1 number.
3. Dev evaluation (N = 316) produces an independent sanity-check number consistent with the train trajectory.
4. Pre-registered hypothesis recorded: expected test macro-F1, expected per-class F1, rationale for each.
5. Test unsealed. `stage_claim.py --split test` runs once through the full test split.
6. Numbers reported as primary results.
7. Test re-sealed if further iteration is planned; otherwise the experiment is closed.

Any deviation voids the reporting value. If test is inadvertently exposed mid-iteration, the options are:

- Swap to a fresh held-out benchmark for the paper's primary number (Sarol-style benchmarks exist; could also use a subset of Sarol test held out during the exposure).
- Report Sarol test results explicitly as exploratory rather than primary, and rely on Variant C + synthetic-injection experiments for the headline numbers.

## Enforcement summary

| Vector | Defense |
| --- | --- |
| Subagent reads gold | Gold outside repo; opaque citekeys; filesystem-restriction paragraph; scrubbed `staging_info.json` |
| Subagent reads raw benchmark | Benchmark outside repo; same filesystem restriction |
| Main session reads test claims | Test physically moved to `$HOME/.paper-trail-sealed/`; `stage_claim.py --split test` fails |
| Main session reads test gold | Gold/test/ dir never populated (would only appear if a test claim were staged — impossible while sealed) |
| Main session reads `annotations.zip` (contains test) | `annotations.zip` moved into sealed directory along with `annotations/Test/` |
| Main session reconstructs test labels via LLM recall | Policy-level: documented here, enforced by researcher discipline, flagged if observed |
| Iteration against dev | Policy-level: dev is a validation-of-winner checkpoint only |

## Why this rule is load-bearing for the paper

The paper argues (per `paper-writeup-items.md`) that agentic-pipeline prompt iteration is a closed-loop optimization with the same overfitting risks as gradient-based training. That argument is only defensible if **we ourselves held the discipline**. If the main session touched test mid-iteration, the paper's methodology contribution collapses — and so, by extension, does confidence in whatever test numbers we report.

Seal is cheap. Unsealed test is expensive.

## Relationship to the agent-only framework (2026-04-21 update)

The agent-only reframe (see `agentic-pipeline-optimization-framework.md`) changes the enforcement model for both rules:

| This doc | Agent-only framework equivalent | What changed |
| --- | --- | --- |
| Rule 1 — Subagent sandboxing | Unchanged. Rule 1 applies identically to train / val / test subagents in agent-only mode. | Nothing. Rule 1 is independent of whether the optimizer is human or agent. |
| Rule 2 — Main-session test blindness | **Tier 3 sealing** (§2 of the framework doc). Optimizer cannot invoke test at all during iteration; enforced by filesystem permissions + CLI gating, not human discipline. | The *mechanism* changes from "researcher discipline" to "structural sealing." The *intent* is preserved. |
| *New:* no prior analog | **Tier 2 — Val scalar-only** (§2 of the framework doc). Optimizer receives only aggregate val F1 via fixed-schema dispatcher CLI; no per-example val access. | New hygiene layer specific to agent-only optimization. No analog in the original Rule 1 / Rule 2 formulation. |

**When does Rule 2 (as written here) still apply?** In any human-in-the-loop variant. The deferred future paper on human-agent research collaboration would re-activate Rule 2 as an operational norm alongside or instead of the agent-only framework. For the current paper (agent-only + paper-trail + Sarol case study), Tier 3 sealing is the authoritative mechanism and this doc's §Rule 2 is historical / preserved-for-future-use.

## Rule 3 — eval-time IN/OUT isolation (added 2026-04-22)

**Why this rule exists.** Rules 1 and 2 address label-leakage vectors into the subagents and the orchestrator. They do not address a separate vector: **context-leakage from the host environment into the evaluated artifact**. If `paper-trail-v<N>` is evaluated at time T on machine M, and machine M's auto-discovered Claude Code context (user-level CLAUDE.md, auto-memory from planning sessions, user-installed hooks / skills / plugins, etc.) flows into the per-claim invocation, then the reported number is for "paper-trail-v<N> on machine M at time T" — not for "paper-trail-v<N>." Reproducibility fails because machine M's state isn't committed at the tag.

**Formalization.** Every eval invocation must load exactly the IN-system context committed at `paper-trail-v<N>`, and zero OUT-of-system context, regardless of host state at T.

### IN-system (ships with `paper-trail-v<N>`; MUST load)

- The invoked slash command (e.g., `/sarol-eval-item` in `.claude/commands/`)
- Custom subagents defined at `.claude/agents/*.md` — paper-trail's extractor / adjudicator / verifier
- Tool permissions for the tag (committed `.claude/settings.json` or tag-scoped variant under `experiments/sarol-2024/eval-harness/`)
- MCP servers paper-trail depends on (committed `.mcp.json` or tag-scoped variant)
- Prompts and specs (`.claude/prompts/`, `.claude/specs/`) — loaded by the skill itself via Read during the run

### OUT-of-system (host-/user-/session-specific; MUST NOT load)

- User-level CLAUDE.md (`~/.claude/CLAUDE.md`) — individual user's personal instructions
- Project-level CLAUDE.md (`./CLAUDE.md`) — paper-trail's own project CLAUDE.md is meta-dev-guidance for planning agents, NOT behavioral context for paper-trail-as-a-tool-being-evaluated
- `.claude/rules/*.md` at any scope (user or project — same role as CLAUDE.md, added 2026-04-22 post-critic)
- **Managed-policy CLAUDE.md** at OS-level paths (`/Library/Application Support/ClaudeCode/CLAUDE.md` on macOS, `/etc/claude-code/CLAUDE.md` on Linux, `C:\Program Files\ClaudeCode\CLAUDE.md` on Windows). Per memory docs "cannot be excluded by individual settings"; `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` should cover but not explicitly named in docs (added 2026-04-22 post-critic, verification deferred)
- Auto-memory at main-session scope (`~/.claude/projects/<slug>/memory/`) — orchestrator / optimizer accumulated state, prior experiment observations
- **Subagent-level persistent memory** (per `code.claude.com/docs/en/sub-agents#enable-persistent-memory`) — docs state subagents can maintain their own auto-memory; main-session env-var propagation to subagents IS verified for main-session-keyed memory (Test 4 canary 2026-04-22), but suppression of a subagent-specific memory path (if such a path exists at `$CLAUDE_CONFIG_DIR/agents/<name>/memory/` or similar) is NOT yet canary-verified. Flagged for follow-up (added 2026-04-22 post-critic)
- User-level `~/.claude/agents/`, `~/.claude/skills/`, `~/.claude/hooks/`
- User-level `~/.claude/settings.json` (personal permissions)
- User-level MCP servers in user-global `.mcp.json`
- User-level plugins
- Hooks at any level (paper-trail does not currently ship behavioral hooks; if it ever does, those become IN-system and explicitly pass-through)
- IDE integration, Chrome integration, remote-control sessions
- **Dynamic system-prompt sections** (cwd, env info, memory paths, git status) — Claude Code injects these into the default system prompt per-machine. Suppressed by `--exclude-dynamic-system-prompt-sections` (added to canonical shape 2026-04-22 post-critic). Without this flag, git status leakage alone can differ between a clean eval host and a dev machine mid-commit.
- **Session history under `CLAUDE_CONFIG_DIR/sessions/`** — `--no-session-persistence` prevents accumulation and cross-run contamination via `--continue` / `--resume` paths. Fresh-UUID-per-invocation `CLAUDE_CONFIG_DIR` also mitigates structurally. Both belts (added 2026-04-22 post-critic).
- **Claude Code binary version itself** — the binary is external to the git tag; version drift across a landmark-tier curve invalidates tag-reproducibility. Pin the binary version on landmark eval hosts and record it in archive metadata (added 2026-04-22 post-critic; see binary-version invariant note in mechanisms block below).
- Shell env (LANG, LC_ALL, TZ, PATH, Python virtualenv state) — rarely load-bearing for Claude's context, but can surface through Bash tool behavior. Accept as residual at iteration tier; name in paper methods if measured to matter.

### Mechanisms (two-tier; verified 2026-04-22, amended 2026-04-22 post-critic-audit — see `docs/journal/2026-04-22-memblind-oauth-findings.md`)

**Honest scope of the isolation claim** (updated 2026-04-22 post-critic): the iteration-tier stack is functionally equivalent to `--bare` **for the six documented auto-discovery sources** that `--bare` skips (hooks, skills, plugins, MCP servers, auto-memory, CLAUDE.md). It does NOT by default suppress the dynamic-system-prompt sections Claude Code injects into every invocation (cwd, git status, env info, memory paths) or pin the Claude Code binary version itself; both are addressable with additional flags/conventions documented below. Subagent-level persistent memory (per `code.claude.com/docs/en/sub-agents#enable-persistent-memory`) is assumed suppressed-by-inheritance but not yet empirically canary-tested at the subagent-specific memory path. "Equivalent to `--bare`" is true for the six published sources; for the full list of OUT-of-system items below, both tiers need additional discipline (documented in the invocation blocks and OUT-of-system table).

**Iteration tier** (local, subscription token, used during optimizer revision loops):

```
CLAUDE_CODE_OAUTH_TOKEN=<from claude setup-token>
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
CLAUDE_CODE_DISABLE_CLAUDE_MDS=1
CLAUDE_CONFIG_DIR=/tmp/paper-trail-eval-<uuid>/        # fresh uuid per invocation, not persistent
```

Plus on the `claude --print` invocation:

```
--tools default
--agents '<tag-scoped-json>'
--settings <tag-scoped>
--mcp-config <tag-scoped>  --strict-mcp-config
--exclude-dynamic-system-prompt-sections               # suppresses cwd/git-status/env/memory-path system-prompt leakage (added 2026-04-22)
--no-session-persistence                               # prevents sessions/ accumulation under CLAUDE_CONFIG_DIR (added 2026-04-22)
```

**Landmark tier** (Vertex VM or ANTHROPIC_API_KEY, `--bare`, used for paper-reportable numbers at `paper-trail-v<N>` landmark tags):

```
--bare --print
```

Plus the same flag set as iteration tier (the two flags added 2026-04-22 apply equally to landmark tier; `--bare` doesn't suppress dynamic system prompt sections by itself).

Auth via `CLAUDE_CODE_USE_VERTEX=1 + ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-7 + GCP ADC` or `ANTHROPIC_API_KEY`. `--bare` handles the six auto-discovery sources in a single flag; the additional flags above cover dynamic-system-prompt and session-persistence, which `--bare` doesn't.

**Binary version invariant (added 2026-04-22 post-critic).** Every archived `paper-trail-v<N>` eval run must record the Claude Code binary version (`claude --version` captured at run time) in its `summary.json` / archive metadata. Landmark-tier runs SHOULD pin the binary version via `npm install -g @anthropic-ai/claude-code@<pinned>` on the eval host; iteration-tier runs record version without pinning and accept version-drift-within-iteration as an acknowledged residual. A binary-version change across a landmark-tier curve requires re-baselining.

### Relationship to Rules 1 and 2

- **Rule 1** applies inside each `claude --print` invocation: the subagents dispatched by paper-trail's internal Agent-tool calls are sandboxed from gold labels. Unchanged.
- **Rule 2** applies to the optimizer's read access to val / test splits. Structurally enforced via Tier 3 sealing in the agent-only framework. Unchanged.
- **Rule 3** applies to every `claude` subprocess the optimizer spawns — it controls what auto-discovered context enters each invocation regardless of Rule 1 / Rule 2.

All three rules must hold simultaneously. Rule 3 is the newest and covers a vector the first two don't address.

### Residual investigation items (flagged, with priority from 2026-04-22 critic audit)

**Blocking-for-landmark-tagging** (must resolve before the first `paper-trail-v<N>` landmark run producing paper-reportable numbers):

1. **Dynamic system prompt canary** — verify `--exclude-dynamic-system-prompt-sections` actually moves cwd/git/env/memory-path sections out of the system prompt. One probe invocation asking a subagent to report verbatim what its system prompt contains re: those sections.
2. **Claude Code binary version pinning** — on the Vertex VM (landmark-tier host), `npm install -g @anthropic-ai/claude-code@<version>` before the first landmark run; add version capture to archive metadata schema in `paper-trail-v<N>.json`.
3. **Subagent-side persistent memory canary** — plant a canary at the subagent-scoped memory path (first identify canonical path from sub-agents docs) and verify main-session env vars suppress it. Mirror Test 4 design but at subagent-specific plant location.

**Blocking-for-iteration-tier-Task-5-scaffolding**:

4. Project-level `.claude/commands/` resolution under fresh `CLAUDE_CONFIG_DIR` — not yet tested; deferred to Task 5 scaffolding. Write a trivial `/sarol-canary-cmd` and confirm it loads from project cwd despite config-dir override.
5. Settings-merge fail-closed canary — verify user `~/.claude/settings.json` IS suppressed by fresh `CLAUDE_CONFIG_DIR`, NOT just by `--settings`. Negative-test (prove suppression is load-bearing, not belt-and-suspenders). Protocol involves temporarily moving user settings.json; handle carefully.

**Nice-to-have** (document, don't necessarily fix):

6. Hook granular disable under non-`--bare` — no `CLAUDE_CODE_DISABLE_HOOKS` env var documented; acceptable for iteration tier where paper-trail ships no hooks, becomes landmark-tier concern but `--bare` covers it.
7. `@imports` in skill files (`.claude/commands/*.md` can use `@~/...` imports per CLAUDE.md mechanism docs) — if paper-trail's skill definitions ever use `@` imports, verify they resolve as expected under the committed invocation shape.
8. Two-tier cross-comparability — whether iteration-tier and landmark-tier numbers differ systematically on the same input. Pin to empirical side-by-side at `paper-trail-v1` smoketest.
9. `--bare` skill resolution with user-vs-project skill-name collision — if both `~/.claude/skills/foo` and `.claude/skills/foo` exist, which wins under `--bare --print /foo`? Docs silent.
10. `@imports` expansion in `--append-system-prompt-file` — unverified whether `@` syntax is honored outside CLAUDE.md.
