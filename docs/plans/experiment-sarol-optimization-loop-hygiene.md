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

### Canonical operator interface — `scripts/run-eval.sh` (wrapper script)

**2026-04-23 update:** operator-facing invocation is the committed wrapper script; the full env-var + flag chain documented below is what the script runs internally. Rationale: 4 env vars + 8 flags + clean-cwd + `--add-dir` is operator-error-prone; baking the invocation into a committed script both prevents forgotten pieces AND commits the invocation shape as a reviewable artifact. Addresses the "why didn't he just use a script?" criticism pre-emptively.

```bash
# Operator-facing (iteration tier):
./scripts/run-eval.sh --tier iteration --version v<N> --claim <id>

# Operator-facing (landmark tier, via committed Dockerfile):
docker run --rm \
  -e ANTHROPIC_VERTEX_PROJECT_ID=<proj> \
  -v <gcp-key>:/creds/key.json:ro \
  -v <repo>:/repo:ro \
  paper-trail-eval:v<N> \
  /repo/scripts/run-eval.sh --tier landmark --version v<N> --claim <id>
```

The Docker image `paper-trail-eval:v<N>` is built from a committed `experiments/sarol-2024/eval-harness/Dockerfile` at the tag; pins Claude Code binary via `npm install -g @anthropic-ai/claude-code@<specific-version>`. This closes the binary-drift gap the critic identified 2026-04-22 for landmark-tier numbers.

### Mechanisms (two-tier; verified 2026-04-22, amended 2026-04-23 post-benchmark-integrity-lit-review — see `docs/journal/2026-04-23-benchmark-integrity-lit-review.md` and `docs/journal/2026-04-22-memblind-oauth-findings.md`)

**Honest scope of the isolation claim** (updated 2026-04-23 post-lit-review): the iteration-tier stack is functionally equivalent to `--bare` **for the six documented auto-discovery sources** that `--bare` skips (hooks, skills, plugins, MCP servers, auto-memory, CLAUDE.md). Additional flags and conventions cover dynamic-system-prompt sections, session persistence, shell env determinism, git-state leakage, and binary version — each tied to a specific vector identified either empirically in a canary or documented in prior-art benchmark-integrity work (Zhu et al. 2025 arxiv 2507.02825 Agentic Benchmark Checklist; Wang et al. 2026 Berkeley Agent-Eval Checklist). Subagent-level persistent memory is assumed suppressed-by-inheritance but not yet empirically canary-tested at the subagent-specific memory path.

**Iteration tier — internal bash that the wrapper script runs** (local, subscription token, used during optimizer revision loops):

```bash
# Fresh uuid per invocation for both CLAUDE_CONFIG_DIR and the working directory
EVAL_UUID=$(uuidgen)
mkdir -p "/tmp/pt-eval-cfg-$EVAL_UUID" "/tmp/pt-eval-wd-$EVAL_UUID"

env -i \
  HOME="$HOME" \
  PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin \
  LANG=en_US.UTF-8 \
  TZ=UTC \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
  CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 \
  CLAUDE_CONFIG_DIR="/tmp/pt-eval-cfg-$EVAL_UUID" \
  /bin/sh -c "cd /tmp/pt-eval-wd-$EVAL_UUID && \
    claude \
      --add-dir $REPO \
      --print --model opus \
      --no-session-persistence \
      --exclude-dynamic-system-prompt-sections \
      --tools default \
      --agents \"\$(cat \$REPO/experiments/sarol-2024/eval-harness/subagent-registry-v${VERSION}.json)\" \
      --settings \$REPO/experiments/sarol-2024/eval-harness/eval.settings.json \
      --mcp-config \$REPO/experiments/sarol-2024/eval-harness/mcp.json \
      --strict-mcp-config \
      /sarol-eval-item --version v$VERSION --claim $CLAIM"

# Cleanup
rm -rf "/tmp/pt-eval-cfg-$EVAL_UUID" "/tmp/pt-eval-wd-$EVAL_UUID"
```

Each piece of this stack is there because of a specific leakage source:

- `env -i` + pinned `HOME` / `PATH` / `LANG` / `TZ` — strips parent shell env (aliases, TZ, LC_ALL, virtualenv state, inherited CLAUDE_CODE_* env vars); sets only what we need. (Added 2026-04-23 per creative-defenses brainstorm.)
- `CLAUDE_CODE_OAUTH_TOKEN` — subscription-scoped env-var auth; replaces keychain OAuth (which `--bare` refuses, and which is host-specific).
- `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` — suppresses auto-memory at main-session scope; verified propagates to Agent-tool-spawned subagents.
- `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` — suppresses user CLAUDE.md, project CLAUDE.md, `.claude/rules/*.md`, CLAUDE.local.md.
- `CLAUDE_CONFIG_DIR=/tmp/pt-eval-cfg-$EVAL_UUID/` — structurally blinds user hooks/skills/plugins (they live under the config dir); fresh per invocation so no session-history accumulation.
- Clean cwd (`cd /tmp/pt-eval-wd-$EVAL_UUID/`) — kills dynamic-system-prompt git-state leakage at the source (no `.git/` in cwd means no branch/uncommitted-files section in the prompt); empirically verified 2026-04-23.
- `--add-dir $REPO` — grants file access to the committed paper-trail repo without making it a config root.
- `--no-session-persistence` — prevents `sessions/` accumulation even under the fresh config dir (belt + suspenders with per-uuid cleanup).
- `--exclude-dynamic-system-prompt-sections` — suppresses the remaining dynamic-prompt sections (cwd-path, env info, memory paths) that clean-cwd alone doesn't cover.
- `--tools default` — enables Task (the subagent-spawn tool) which `--bare`-style default toolsets omit.
- `--agents '<tag-scoped-json>'` — loads paper-trail's custom subagents (extractor/adjudicator/verifier) under suppressed auto-discovery.
- `--settings`, `--mcp-config`, `--strict-mcp-config` — tag-scoped tool-permission + MCP-server config; replaces host-level merge.

**Landmark tier — internal bash that the wrapper script runs inside the Docker container** (used for paper-reportable numbers at `paper-trail-v<N>` landmark tags):

```bash
# Dockerfile: FROM node:22; RUN npm install -g @anthropic-ai/claude-code@<specific-version>; COPY eval-arm files.
# Host-side env: CLAUDE_CODE_USE_VERTEX=1, CLOUD_ML_REGION=global, ANTHROPIC_VERTEX_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS,
#                ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-7

claude \
  --bare \
  --print --model opus \
  --no-session-persistence \
  --exclude-dynamic-system-prompt-sections \
  --tools default \
  --agents "$(cat /repo/experiments/sarol-2024/eval-harness/subagent-registry-v$VERSION.json)" \
  --settings /repo/experiments/sarol-2024/eval-harness/eval.settings.json \
  --mcp-config /repo/experiments/sarol-2024/eval-harness/mcp.json \
  --strict-mcp-config \
  --add-dir /repo \
  /sarol-eval-item --version v$VERSION --claim $CLAIM
```

Docker-in-Vertex provides: (a) pinned Claude Code binary (closes the 2026-04-22 critic-flagged binary-drift gap), (b) clean-by-construction container filesystem (no user ~/.claude), (c) read-only repo mount (Berkeley Agent-Eval Checklist: "read-only filesystems for binaries, test files, or infrastructure the evaluation depends on"), (d) Vertex GCP-mediated auth (no keychain / OAuth-token considerations).

**Binary version invariant (added 2026-04-22 post-critic).** Every archived `paper-trail-v<N>` eval run must record the Claude Code binary version (`claude --version` captured at run time) in its `summary.json` / archive metadata. Landmark-tier runs SHOULD pin the binary version via `npm install -g @anthropic-ai/claude-code@<pinned>` on the eval host; iteration-tier runs record version without pinning and accept version-drift-within-iteration as an acknowledged residual. A binary-version change across a landmark-tier curve requires re-baselining.

### Relationship to Rules 1 and 2

- **Rule 1** applies inside each `claude --print` invocation: the subagents dispatched by paper-trail's internal Agent-tool calls are sandboxed from gold labels. Unchanged.
- **Rule 2** applies to the optimizer's read access to val / test splits. Structurally enforced via Tier 3 sealing in the agent-only framework. Unchanged.
- **Rule 3** applies to every `claude` subprocess the optimizer spawns — it controls what auto-discovered context enters each invocation regardless of Rule 1 / Rule 2.

All three rules must hold simultaneously. Rule 3 is the newest and covers a vector the first two don't address.

### Structural defenses beyond native Claude Code flags (alternatives evaluated 2026-04-23)

Evaluated during the 2026-04-23 creative-defenses brainstorm; each listed with what it solves, what it doesn't, and our adoption decision. Serves as the pre-emptive answer to "why didn't you just use X?" reviewer criticism, and as a menu of escalation options if specific empirical canaries fail. Full brainstorm captured in `docs/journal/2026-04-23-benchmark-integrity-lit-review.md` §2.

| Mechanism | Solves | Doesn't solve | Our adoption |
|---|---|---|---|
| `env -i` + pinned `LANG`/`TZ`/`PATH` | Shell env leakage | File-based | **Adopted** in canonical iteration-tier shape |
| Clean cwd + `--add-dir` (empirically verified 2026-04-23) | Dynamic-prompt git-state at source + project CLAUDE.md walk | User-level | **Adopted** in canonical shape |
| Git worktree at tag (`git worktree add /tmp/eval-v<N> v<N>`) | Clean-tree + exact-tag-content guarantee | Host state | Task 5 option; implement if operator-forgetfulness of git-state becomes an issue |
| Wrapper script (`scripts/run-eval.sh`) | Operator forgetfulness; commits invocation as reviewable artifact | No new isolation | **Adopted as canonical operator interface** |
| APFS/ZFS pre-run snapshot of relevant paths | Silent-drift detection post-run | Not isolation | Defer |
| macOS `sandbox-exec` | OS-level read-denial | Binary version | Defer (bespoke, one-platform) |
| Separate OS user | User-scope isolation | Binary drift, dynamic prompt | Defer (CLAUDE_CONFIG_DIR gets same cheaper) |
| `chmod` / `mv` on discovery targets | File-based source suppression (read-only FS per Berkeley checklist) | Runtime-constructed context, racy with parallel sessions | Belt-and-suspenders option if `CLAUDE_CONFIG_DIR` empirically fails |
| Docker with pinned Claude Code | Binary drift, clean-by-construction, read-only infra (Berkeley-recommended) | Container latency × iteration throughput | **Adopted for landmark tier** — committed `Dockerfile` |
| Ephemeral VM per run | Maximum isolation | Latency + cost for iteration | Already via Vertex for landmark tier |
| Transactional FS (Fan et al. 2512.12806) | Rollback on state tampering | Requires fault-tolerant-filesystem layer | Future-work / post-submission |
| Pre-run state assertion (path hash) | Silent-drift detection | Not isolation | Partial: `paper-trail-v<N>.json` records binary version + MCP + subagent registry hashes |

**Why not Docker for iteration tier too?** Docker startup latency (~1-2 s per invocation) × thousands of per-claim invocations per optimizer revision × many revisions = non-trivial wall-clock + cost overhead. Iteration tier's env-var-based approach achieves same-host-same-time reproducibility without the per-call container spin-up. The tier split is deliberate; paper methods should name this tradeoff explicitly.

**Why not a separate OS user?** CLAUDE_CONFIG_DIR override gets the same user-scope isolation without per-user keychain provisioning (which on macOS is non-trivial) and without the operational overhead of managing a dedicated eval user. Doesn't solve binary drift or dynamic-prompt leakage either way; those need orthogonal mechanisms.

### Residual investigation items (flagged, with priority from 2026-04-22 critic audit + 2026-04-23 benchmark-integrity lit-review)

**Blocking-for-landmark-tagging** (must resolve before the first `paper-trail-v<N>` landmark run producing paper-reportable numbers):

1. **Dynamic system prompt canary** — verify `--exclude-dynamic-system-prompt-sections` actually moves cwd/git/env/memory-path sections out of the system prompt. One probe invocation asking a subagent to report verbatim what its system prompt contains re: those sections.
2. **Claude Code binary version pinning** — on the landmark-tier host (Vertex VM; inside Docker image at the tag), `npm install -g @anthropic-ai/claude-code@<version>` before the first landmark run; add version capture to archive metadata schema in `paper-trail-v<N>.json`. Docker image `paper-trail-eval:v<N>` supersedes ad-hoc pinning.
3. **Subagent-side persistent memory canary** — plant a canary at the subagent-scoped memory path (first identify canonical path from sub-agents docs) and verify main-session env vars suppress it. Mirror Test 4 design but at subagent-specific plant location.
4. **Adversarial-agent smoketest suite** (new 2026-04-23, from Berkeley Agent-Eval Checklist + Zhu et al. ABC). Four small agents in `experiments/sarol-2024/eval-harness/adversarial/`:
   - `null_agent.py` — returns empty verdict. Expected: ~0 macro-F1 on Sarol. Floor test.
   - `random_agent.py` — samples from 9-class verdict uniformly. Expected: ~11% random baseline.
   - `injection_agent.py` — attempts prompt injection in the adjudicator's input. Expected: verifier catches.
   - `tamper_agent.py` — attempts filesystem writes to gold / eval-harness dirs. Expected: Rule-1 structural defenses block at OS-error.
   Results land in `paper-trail-v1.json` alongside the real run.
5. **Scorer adversarial audit** (new 2026-04-23). Before v1 tag, run `parse_verdict.py` + macro-F1 against malformed inputs: empty string, whitespace, wrong-schema JSON, extra-keys JSON, all-9-verdicts JSON, non-UTF-8 bytes. All must fail with typed errors, not silently score.
6. **LLM-judge sanitization audit** (new 2026-04-23). Review adjudicator + verifier prompts for: delimiter discipline around agent content, escape of system-prompt-looking text, structured-output enforcement (no substring matching against gold labels).
7. **E3 dispatcher crashed-task semantics** (new 2026-04-23). Explicit spec: fetch-failure → claim scored as FAILED_FETCH → counts as missed in macro-F1 denominator; not dropped. Matches Berkeley / Zhu et al. crashed-task discipline (TAU-bench "empty = success" bug).

**Blocking-for-iteration-tier-Task-5-scaffolding**:

8. Project-level `.claude/commands/` resolution under fresh `CLAUDE_CONFIG_DIR` — not yet tested; deferred to Task 5 scaffolding. Write a trivial `/sarol-canary-cmd` and confirm it loads from project cwd despite config-dir override.
9. Settings-merge fail-closed canary — verify user `~/.claude/settings.json` IS suppressed by fresh `CLAUDE_CONFIG_DIR`, NOT just by `--settings`. Negative-test (prove suppression is load-bearing). Protocol involves temporarily moving user settings.json; handle carefully.

**Nice-to-have** (document, don't necessarily fix):

10. Hook granular disable under non-`--bare` — no `CLAUDE_CODE_DISABLE_HOOKS` env var documented; acceptable for iteration tier where paper-trail ships no hooks; `--bare` covers it at landmark.
11. `@imports` in skill files (`.claude/commands/*.md` can use `@~/...` imports per CLAUDE.md mechanism docs) — if paper-trail's skill definitions ever use `@` imports, verify they resolve as expected.
12. Two-tier cross-comparability — whether iteration-tier and landmark-tier numbers differ systematically on the same input. Pin to empirical side-by-side at `paper-trail-v1` smoketest.
13. `--bare` skill resolution with user-vs-project skill-name collision — if both `~/.claude/skills/foo` and `.claude/skills/foo` exist, which wins under `--bare --print /foo`? Docs silent.
14. `@imports` expansion in `--append-system-prompt-file` — unverified whether `@` syntax is honored outside CLAUDE.md.
15. Transactional-filesystem sandboxing (Fan et al. 2512.12806) for paper-trail's PDF-fetch cache — future-paper investigation.
