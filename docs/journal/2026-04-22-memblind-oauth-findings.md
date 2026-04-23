# 2026-04-22 — Memory-blind isolation under OAuth: empirical findings + IN/OUT formalization

**What this journal entry is.** End-of-day working record from the Tier-0 Gate 2+3 investigation into how to achieve reproducibility-grade isolation for the Sarol eval arm without requiring Vertex AI / ANTHROPIC_API_KEY auth. Covers: (1) empirical canary results from a local working session, (2) the IN-system vs OUT-of-system formalization Human proposed, (3) the two-tier eval-arm architecture that follows from those findings, (4) flagged follow-up investigation items.

Complements the existing Gate 2+3 plan material in `docs/plans/experiment-sarol-archive-and-eval-framework.md` §Q9c and the runbook at `docs/plans/canary-runbook-vertex.md` (both now partially superseded by the iteration-tier/landmark-tier split this entry introduces — see §"Architecture implications" below).

## §1 — Empirical canary results (local, OAuth)

All tests run from this session's main agent against the user's normal Claude Code subscription (OAuth via keychain on macOS). Every canary was planted fresh, probed with and without the relevant disable mechanism, and cleaned up before the next test. Five sub-tests landed:

### Test 1 — `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` + `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` suppresses auto-memory

Canary `canary_memblind.md` planted at `~/.claude/projects/-Users-pmayankees-Documents-Misc-Projects-paper-trail/memory/` with distinctive phrase `QUUX-MEMBLIND-2026` and indexed in `MEMORY.md`. Two invocations:

- Sensitivity (no env vars): `claude --print --model opus "Do you have access to any memory entries named canary_memblind.md or containing QUUX-MEMBLIND-2026?"` → stdout: *"Yes — `canary_memblind.md` is listed in `MEMORY.md`..."*. Memory loaded as expected in baseline OAuth mode.
- Memblind test: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 claude --print --model opus "..."` → stdout: *"no memory loaded"*. **Memory suppressed.**

Canary cleaned up; `grep -c CANARY MEMORY.md` returned 0.

**Conclusion:** the two-env-var combo structurally blinds auto-memory under OAuth. `CLAUDE_CODE_DISABLE_AUTO_MEMORY` and `CLAUDE_CODE_DISABLE_CLAUDE_MDS` are both documented at https://code.claude.com/docs/en/env-vars even though neither appears in `claude --help`.

### Test 2 — `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` suppresses all CLAUDE.md files

Canary planted at `./CLAUDE.local.md` in the paper-trail repo root with phrase `BAZ-CLAUDE-MDS-2026`. Two invocations:

- Sensitivity: `claude --print --model opus "Do you have access to any CLAUDE.md or CLAUDE.local.md files?"` → stdout cited `/Users/pmayankees/.claude/CLAUDE.md`, `./CLAUDE.md`, AND `./CLAUDE.local.md` with the canary phrase visible. All three scopes loaded in baseline.
- CLAUDE_MDS disabled: `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 claude --print --model opus "..."` → stdout: *"No CLAUDE.md loaded — I can see `CLAUDE.local.md` listed as untracked in git status, but its contents are not loaded into my context."*. **All three scopes (user, project, local) suppressed.**

Canary cleaned up.

**Conclusion:** one env var blinds CLAUDE.md auto-discovery across all three scopes (`~/.claude/CLAUDE.md`, project `./CLAUDE.md`, and `./CLAUDE.local.md`). Model can still *see that files exist* via Read or via git status, but their contents are not injected into the context window.

### Test 3 — Agent-tool subagent inheritance: env vars propagate transitively

Canary `canary_subagent.md` planted with phrase `GRAULT-SUBAGENT-2026`. A custom `memory-probe` subagent defined inline via `--agents '<json>'` whose system prompt instructs it to self-probe its own memory access. Two invocations:

- Sensitivity (main session WITHOUT env vars): main spawns subagent via Agent tool; subagent relays: `canary_subagent.md: GRAULT-SUBAGENT-2026`. Subagent HAS memory access, as expected in baseline.
- Inheritance test (main session WITH `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`): main spawns subagent identically; subagent relays: `SUBAGENT: no memory loaded.`. **Env vars propagated transitively to the Agent-tool-spawned subagent.**

Canary cleaned up.

**Conclusion:** setting the disable env vars ONCE on the main dispatcher invocation suffices to blind the entire subagent pipeline. Paper-trail's extractor/adjudicator/verifier subagents will inherit memblind status without additional plumbing in the subagent JSON registry. This was Human's explicit concern 2026-04-22 — resolved.

### Test 4 — `--tools default` + `--agents '<json>'` mechanics work under OAuth non-bare

Validated (A1) Agent tool is present in the default non-bare OAuth toolset via `claude --print --model opus "List every tool you have access to right now"` — stdout included `Agent` as the first tool. (A2) Inline `--agents '{"canary-echo": {...}}'` loaded the custom subagent alongside built-ins (`Explore`, `general-purpose`, `Plan`, `statusline-setup`). (A3) Functional spawn test relayed `HELLO-FROM-CANARY-ECHO` verbatim, confirming the full dispatch-and-return loop. (A4) Combined invocation `--tools default --agents '<json>'` behaves identically — no interference.

**Conclusion:** the dispatcher invocation shape we derived from the CLI-reference docs sweep (`--tools default` + `--agents '<json-registry>'`) works empirically. No `--bare` needed for tool-mechanics validation; the same flags work in both modes.

### Test 5 — `CLAUDE_CODE_SIMPLE=1` (env-var form of `--bare`) also refuses OAuth

Tested: `CLAUDE_CODE_SIMPLE=1 claude --print --model opus "..."` → stdout: *"Not logged in · Please run /login"*. The env-var form of `--bare` is functionally equivalent to the flag: same auto-discovery suppression AND same OAuth/keychain refusal.

**Conclusion:** we cannot get `--bare`'s full isolation cheaply via the `CLAUDE_CODE_SIMPLE` env var — it imposes the same non-OAuth auth requirement.

### Test 6 — `CLAUDE_CONFIG_DIR=/tmp/fresh/` also breaks OAuth on macOS

Tested: `mkdir -p /tmp/paper-trail-eval-isolation-test; CLAUDE_CONFIG_DIR=/tmp/paper-trail-eval-isolation-test claude --print --model opus "..."` → stdout: *"Not logged in · Please run /login"*. On macOS, the keychain credentials appear to be keyed to the default `~/.claude` config dir or a default-dir-scoped keychain entry, not solely to the OS user. Pointing `CLAUDE_CONFIG_DIR` at a fresh path breaks the OAuth lookup even though keychain entries for the OS user technically still exist.

**Conclusion:** Human's "run under a different account" intuition is the right architectural direction — `CLAUDE_CONFIG_DIR` is documented as "useful for running multiple accounts side by side" — but on macOS it requires a non-keychain auth path to avoid losing OAuth. The documented non-keychain subscription-auth path is `CLAUDE_CODE_OAUTH_TOKEN` generated by `claude setup-token` (a 1-year subscription-scoped token that works as env-var auth under non-bare). This combination is the ideal "different-account-with-subscription-auth" shape but was NOT empirically verified in this session — flagged as the highest-priority follow-up investigation item in §5 below.

## §2 — IN-system vs OUT-of-system formalization (Human, 2026-04-22)

Earlier leakage-source framing treated all 6 auto-discovery mechanisms (`--bare`'s skip list: hooks, skills, plugins, MCP servers, auto memory, CLAUDE.md) as uniformly "leakage." Human pushed back with a cleaner framing: what matters is what **ships with `paper-trail-v<N>`** (must load during eval because it *is* paper-trail) versus what's **host-/session-specific** (must NOT load because it would make reports host-dependent).

### IN-system — ships with `paper-trail-v<N>`, MUST load during eval

- The specific skill being invoked (e.g., `/sarol-eval-item` living in the repo's `.claude/commands/`)
- Custom subagents (`.claude/agents/*.md`) — paper-trail's extractor / adjudicator / verifier
- Tool permissions for this tag (`.claude/settings.json` or a tag-scoped variant)
- MCP servers paper-trail depends on (any `.mcp.json` in the repo)
- Prompts and specs (`.claude/prompts/`, `.claude/specs/`) — loaded on demand by the skill itself via `Read`

These are the model's "body" at tag v\<N\>. An eval that omits them is not an eval of v\<N\>.

### OUT-of-system — host-/user-/session-specific, MUST NOT load during eval

- User-level CLAUDE.md (`~/.claude/CLAUDE.md`) — the individual user's personal instructions
- **Project-level CLAUDE.md** (`./CLAUDE.md`) — **important:** paper-trail's own `CLAUDE.md` is meta-dev guidance for agents doing planning on the repo, not behavioral context for paper-trail-as-a-tool-being-evaluated. Goes OUT.
- Auto-memory (`~/.claude/projects/<slug>/memory/`) — orchestrator / optimizer accumulated state from planning sessions, prior experiment observations, anything the optimizer has seen before this eval run
- User-level `~/.claude/agents/`, `~/.claude/skills/`, `~/.claude/hooks/`
- User-level `~/.claude/settings.json` (personal permissions)
- User-level MCP servers (user-global `.mcp.json`)
- Plugins installed at the user level
- Hooks at any level (unless paper-trail explicitly ships hooks as part of its behavior, which it currently doesn't)
- IDE integrations, Chrome integration, remote-control sessions

### Reproducibility invariant (post-formalization)

Every `paper-trail-v<N>` eval invocation at time T loads exactly the IN-system bits committed at tag v\<N\>, and loads zero OUT-of-system bits, regardless of host state at time T. The invocation is reproducible in the sense that the same tag evaluated on any compliant host at any time yields the same inputs to the model.

### Why this sharpens the architecture

The prior framing was "achieve memory-blindness." The sharpened framing is "achieve IN-system-only context." Memory-blindness is necessary but not sufficient — the invariant must ALSO cover CLAUDE.md (at all scopes, even paper-trail's own), user hooks/skills/plugins, and user-level MCP servers. It MUST still load the IN-system bits explicitly.

The prior-work-by-`--bare` reason this framing matters: `--bare` blinds everything in one sweep but then requires you to explicitly re-pass the IN-system bits via flags (`--agents`, `--settings`, `--mcp-config`, `--plugin-dir`, `--append-system-prompt-file`). That pattern — blind-everything-then-explicit-pass — IS the IN/OUT formalization; `--bare` just happens to couple it with non-OAuth auth.

## §3 — Two-tier eval-arm architecture (follows from §1 + §2)

No single mechanism perfectly achieves the invariant under OAuth. The two-env-var combo blinds memory + CLAUDE.md (the high-risk sources) but leaves user hooks/skills/plugins intact. Full `--bare` blinds everything but requires non-OAuth auth. This motivates a two-tier split aligned with what each eval actually needs to prove.

### Iteration tier (local, OAuth subscription)

**Purpose.** Fast iteration during optimizer revision loops. Every call compares same-host same-time state, so absolute reproducibility is less load-bearing than quick turnaround.

**Invocation shape:**

```bash
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 \
claude --print --model opus \
  --tools default \
  --agents "$(cat experiments/sarol-2024/eval-harness/subagent-registry-v<N>.json)" \
  --settings experiments/sarol-2024/eval-harness/eval.settings.json \
  --mcp-config experiments/sarol-2024/eval-harness/mcp.json \
  --strict-mcp-config \
  /sarol-eval-item --claim-id N [other per-run flags]
```

**Isolation coverage (iteration tier):**

| Source | Suppressed? | Mechanism |
|---|---|---|
| Auto-memory | ✅ | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` |
| CLAUDE.md (all scopes) | ✅ | `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` |
| Subagent inheritance of both above | ✅ | Env vars propagate to Agent-tool spawns |
| MCP servers (user-level) | ✅ | `--strict-mcp-config` |
| MCP servers (project-level, tag-scoped) | IN-system (loaded) | `--mcp-config <tag-scoped>` |
| Custom subagents (paper-trail's) | IN-system (loaded) | `--agents '<tag-scoped-JSON>'` |
| Tool permissions (tag-scoped) | IN-system (loaded) | `--settings <tag-scoped>` |
| Task tool available | ✅ | `--tools default` |
| Hooks (any level) | ⚠️ NOT suppressed | Accept residual leakage |
| Skills at user level | ⚠️ NOT suppressed | Accept residual leakage |
| Plugins at user level | ⚠️ NOT suppressed | Accept residual leakage |

**Rationale for accepting residual leakage.** Iteration-tier runs happen within a single optimizer-loop session on a single host. Cross-iteration comparability is all that matters, and the residual leakage is constant across iterations (same host, same user, same installed hooks/skills/plugins). This is analogous to "we don't re-baseline every time we change an unrelated kernel parameter" — if the residual state is held constant, differences observed across iterations are attributable to the tag change.

### Landmark tier (Vertex or ANTHROPIC_API_KEY, `--bare`)

**Purpose.** Paper-reportable numbers. Full reproducibility for any `paper-trail-v<N>` at any time on any host.

**Invocation shape** (unchanged from existing archive-framework §Q9c plan):

```bash
claude \
  --bare --print \
  --no-session-persistence \
  --model opus \
  --tools default \
  --agents "$(cat experiments/sarol-2024/eval-harness/subagent-registry-v<N>.json)" \
  --settings experiments/sarol-2024/eval-harness/eval.settings.json \
  --mcp-config experiments/sarol-2024/eval-harness/mcp.json \
  --strict-mcp-config \
  /sarol-eval-item --version v<N> --claim-id N
```

**Isolation coverage (landmark tier):** full — `--bare` suppresses all 6 auto-discovery sources.

**Auth path.** `CLAUDE_CODE_USE_VERTEX=1 + CLOUD_ML_REGION + ANTHROPIC_VERTEX_PROJECT_ID + ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-7` on the project's GCP VM. OR `ANTHROPIC_API_KEY` from the Claude Console if Vertex is unavailable for a given run.

**When this tier runs.** At each `paper-trail-v<N>` tag that produces a landmark number reported in the paper. Frequency: order of ~5-10 tag cuts across the optimization curve, plus final `paper-trail-v_final` + test-split unseal.

### Implications

1. **Iteration tier unblocks Task 5 scaffolding immediately** — we can build the eval arm infrastructure and run cheap smoketests against `paper-trail-v1` today without provisioning Vertex or API key.
2. **Landmark tier stays gated on the Vertex VM canary** — the runbook at `docs/plans/canary-runbook-vertex.md` is the path; execution-time still backlogged pending VM session.
3. **Both tiers share the same dispatcher code** — only the env prefix + presence/absence of `--bare` differs. Target this in the `run_train_eval.py` / `run_val_eval.py` / `run_test_eval.py` design.
4. **Task 5 acceptance criteria extend:** iteration-tier smoketest on `paper-trail-v1` with N=10 validates the iteration-tier invocation shape; landmark-tier smoketest on `paper-trail-v1` with N=10 on Vertex validates the landmark-tier shape and the runbook.

## §4 — Mechanism coverage matrix (canonical reference)

All documented mechanisms for suppressing each auto-discovery source, with their OAuth compatibility verified this session where marked ✅:

| Source | Full disable under OAuth | Full disable non-OAuth | Source doc |
|---|---|---|---|
| Auto-memory | ✅ `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (verified) | same or `--bare` / `CLAUDE_CODE_SIMPLE=1` | env-vars page |
| CLAUDE.md all scopes | ✅ `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` (verified) | same or `--bare` / `CLAUDE_CODE_SIMPLE=1` | env-vars page |
| Hooks | ❌ no granular disable env var | `--bare` or `CLAUDE_CODE_SIMPLE=1` only | env-vars page gap |
| Skills (all, including `/sarol-eval-item` we need) | `--disable-slash-commands` (too aggressive) | same | CLI ref |
| Plugins | Partial: `--plugin-dir <path>` explicit override | Full under `--bare` | CLI ref |
| MCP servers | `--strict-mcp-config --mcp-config <file>` | same | CLI ref |

**Open gap:** no granular OAuth-compatible disable for hooks or a scoped-disable for skills. These are the sources that motivate the landmark-tier's `--bare` + Vertex architecture — without `--bare`, we cannot fully reproduce a clean eval environment.

## §5 — Flagged follow-up investigation items

Items that would further sharpen the iteration tier or unlock additional architectures. Ordered by priority.

### §5.1 — `claude setup-token` + `CLAUDE_CONFIG_DIR` combination — VERIFIED 2026-04-22

**Update 2026-04-22 (same session).** Human generated a `CLAUDE_CODE_OAUTH_TOKEN` via `claude setup-token` and shared it back into the session for empirical verification. Four tests ran:

- **Test 1 — auth under subscription token + fresh config dir:** `CLAUDE_CODE_OAUTH_TOKEN='<token>' CLAUDE_CONFIG_DIR=/tmp/pt-eval-test claude --print --model opus "Reply with just one word: ready"` → stdout `ready`. **Subscription-token auth works with fresh `CLAUDE_CONFIG_DIR` override.** (Contrasts with the earlier Test 6 result where `CLAUDE_CONFIG_DIR` alone, without the token env var, broke OAuth by refusing keychain reads.)
- **Test 2a — isolation under token + fresh config dir only (no disable env vars), from repo cwd:** stdout reported *user-level CLAUDE.md LOADED, project-level CLAUDE.md LOADED, memory NOT loaded.* Implementation split discovered: `CLAUDE_CONFIG_DIR` scopes memory-dir lookup (and hooks/skills/plugins, which live under the config dir) but does NOT override user CLAUDE.md (whose path is `$HOME/.claude/CLAUDE.md`, hardcoded against `$HOME` not `$CLAUDE_CONFIG_DIR`). Project CLAUDE.md loads from cwd walk as expected.
- **Test 2b — full-stack iteration-tier shape:** `CLAUDE_CODE_OAUTH_TOKEN='<token>' CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CONFIG_DIR=/tmp/pt-eval-test claude --print --model opus "..."` → stdout: user CLAUDE.md NOT loaded, project CLAUDE.md NOT loaded, memory NOT loaded. **Full isolation verified.**
- **Test 3 — custom subagent loading + functional spawn under full stack:** `--agents '{"canary-echo":{...}}'` loaded inline; `Use the Agent tool to spawn canary-echo` returned the expected `THUD-FROM-ITERATION-TIER` verbatim. **Agent tool + inline subagents work under the full stack.**
- **Test 4 — subagent inheritance under full stack:** canary memory planted; main-session invocation with all env vars spawned a probe subagent via Agent tool; subagent replied `SUBAGENT no memory.`. **Env vars propagate transitively even under the token + CLAUDE_CONFIG_DIR stack.** Canary cleaned up, MEMORY.md restored.

**Canonical iteration-tier invocation shape (verified):**

```bash
CLAUDE_CODE_OAUTH_TOKEN='<subscription-token-from-claude-setup-token>' \
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 \
CLAUDE_CONFIG_DIR=/tmp/paper-trail-eval-<uuid>/   # or persistent ~/.claude-eval/, as long as it's NOT ~/.claude/ \
claude --print --model opus \
  --tools default \
  --agents "$(cat experiments/sarol-2024/eval-harness/subagent-registry-v<N>.json)" \
  --settings experiments/sarol-2024/eval-harness/eval.settings.json \
  --mcp-config experiments/sarol-2024/eval-harness/mcp.json \
  --strict-mcp-config \
  /sarol-eval-item --version v<N> --claim-id N [other per-run flags]
```

**Isolation coverage — FULLY EQUIVALENT TO `--bare` for this project's IN/OUT boundary.** All four OUT-of-system source categories that `--bare` skips are now structurally blinded under this shape:
1. Auto-memory: blinded by env var + structural (fresh config dir has no projects/<slug>/memory/).
2. CLAUDE.md (all scopes): blinded by env var.
3. User-level hooks/skills/plugins: blinded structurally by fresh CLAUDE_CONFIG_DIR.
4. User-level settings: blinded structurally by fresh CLAUDE_CONFIG_DIR.

Auth is subscription-scoped via `CLAUDE_CODE_OAUTH_TOKEN`. No pay-per-token API billing. No Vertex required. Reproducibility: commit the env var NAMES (not values) and the invocation shape; reproducers supply their own token via `claude setup-token`.

**Landmark-tier relationship revised.** With iteration-tier now providing functional isolation equivalence to `--bare` on local OAuth subscription, the landmark-tier (Vertex + `--bare`) is no longer motivated by *auth/isolation* — it's only motivated by:
- Clean-VM reproducibility (no user-machine state at all)
- Compute scaling / rate-limit headroom
- Ultimate conservatism for paper-reportable numbers

We still run landmark-tier on Vertex for those reasons, but the iteration tier can handle the full optimization loop locally without substrate-level compromises.

### §5.1.5 — Project-level `.claude/commands/` resolution under the full iteration-tier stack (OPEN — needs test)

The verified stack above uses `CLAUDE_CONFIG_DIR=/tmp/fresh` which has no `.claude/commands/`. Paper-trail's slash commands (`/sarol-eval-item`, `/paper-trail`, `/ground-claim`, `/fetch-paper`, `/verify-bib`) live in the project's `.claude/commands/` and `.claude/skills/` directories. CWD-walk auto-discovery of `.claude/commands/` from the project cwd may or may not bypass the `CLAUDE_CONFIG_DIR` override.

**Not yet tested.** The dispatcher invocation will need to work with a committed `/sarol-eval-item` slash command; need to verify either (a) CWD-walk still loads `.claude/commands/` under `CLAUDE_CONFIG_DIR` override, or (b) we pass the skill explicitly via `--plugin-dir` or similar, or (c) we inline the entire skill as `--append-system-prompt-file` content and skip slash-command resolution entirely.

Defer to Task 5 scaffolding — first attempt is (a) and empirical verify at that point.

### §5.2 — Hook granular disable (OPEN DOCS QUESTION)

**Gap.** Docs sweep 2026-04-22 did not surface a `CLAUDE_CODE_DISABLE_HOOKS` env var or equivalent non-`--bare` mechanism. `CLAUDE_CODE_SIMPLE=1` disables hooks but also breaks OAuth.

**What's needed.** Either (a) empirical test with a canary hook to see if one of the undocumented-in-help env vars handles hooks, (b) product-team question to Anthropic, (c) accept hook leakage at iteration tier and note the limitation in paper methods.

### §5.3 — Skill scoping under `--disable-slash-commands`

**Gap.** `--disable-slash-commands` is all-or-nothing. If used, `/sarol-eval-item` itself would also be disabled. Not documented whether there's a way to allow a specific slash command while disabling others.

**What's needed.** Docs sweep on `.claude/commands/` loading semantics. Possibly a `--commands <path>` equivalent to `--agents <json>` for loading only specific commands.

### §5.4 — Session / cwd keying for memory

**Gap.** The memory docs say memory is keyed "by git repository, with worktrees sharing a memory dir; outside a git repo, the project root is used." We verified behavior inside the repo with env vars set. Not verified: does invoking `claude --print` from a cwd OUTSIDE any git repo produce a fresh empty memory dir even without the env vars?

**What's needed.** Empirical test: `cd /tmp && claude --print --model opus "List any memory loaded."` without any disable env vars. If output is "no memory loaded," then cwd-based structural isolation works as a fallback mechanism without needing env vars.

### §5.5 — Documented-but-unverified env vars

The earlier research agent cited GitHub issue #39069 as evidence that the `--bare` OAuth refusal is a known friction point with no timeline for change. Unverified; treat as informational.

## §6 — Task 5 eval-arm architecture impact

Net changes to the existing Task 5 deliverables list (NEXT.md Tier 1) implied by the two-tier split:

- The single-invocation-shape spec expands to a two-invocation-shape spec (iteration + landmark).
- The three dispatcher scripts (`run_train_eval.py` / `run_val_eval.py` / `run_test_eval.py`) each need a `--tier {iteration|landmark}` argument that controls env-prefix + `--bare` flag presence.
- The `validate_run.py` Tier-1-invariants check must record which tier produced each run's output so downstream comparisons are tier-aware.
- The `paper-trail-v<N>.json` archive artifact must include which tier produced each archived number (iteration tier for optimizer-loop observations, landmark tier for reported numbers).
- The `canary-runbook-vertex.md` stays as-is for landmark tier; a sibling `canary-runbook-iteration.md` (or a consolidated `canary-runbook.md`) captures the iteration-tier smoketest.

## §7 — Cleanup verification

All four canary files planted during this session were removed before reporting:

- `canary_q9c.md` (Test ~memory-blind-first-attempt): removed, MEMORY.md pointer removed, grep count 0.
- `canary_memblind.md` (Test 1): removed, MEMORY.md pointer removed, grep count 0.
- `CLAUDE.local.md` (Test 2): removed.
- `canary_subagent.md` (Test 3): removed, MEMORY.md pointer removed, grep count 0.
- `canary_simple.md` (Test 5): removed, MEMORY.md pointer removed, grep count 0.
- `/tmp/paper-trail-eval-isolation-test/` (Test 6): removed.

MEMORY.md restored to its pre-session 24-line state (verified with `wc -l`).

## §8 — Critic audit addendum (added 2026-04-22 same-session)

**Human request 2026-04-22 after the main findings landed:** spawn a skeptical "critic" subagent to audit the "functionally equivalent to `--bare` for our IN/OUT boundary" claim. Goal: find the holes before committing. Critic ran with explicit instructions to pressure-test, grade each claim, enumerate missed context sources, identify concrete leakage scenarios, and return a net verdict. Full critic output archived in-session (not committed separately); key findings integrated here and into `experiment-sarol-optimization-loop-hygiene.md` §Rule 3.

### Critic's net verdict

**"The isolation claim is defensible, but not in the strong form 'fully equivalent to `--bare`.'"** Soft-block on the strong form; the 6 documented auto-discovery sources are genuinely equivalent-to-`--bare` under the committed stack, but Claude Code injects additional host-specific context via mechanisms that `--bare` ALSO doesn't suppress. Critic graded the gap as "important — fix before landmark tagging; iteration-tier Task-5 scaffolding can proceed today." No paper-publication blocker.

### Gaps identified by critic (integrated into docs)

**Blocking for landmark-tier paper numbers** (all three now have mitigations added to the canonical shapes in `experiment-sarol-archive-and-eval-framework.md` §Q9c + `optimization-loop-hygiene.md` §Rule 3):

- **Dynamic system-prompt sections** (cwd, env info, memory paths, git status) — injected into the default system prompt per-machine per-invocation. `--bare` doesn't touch these. **Fix applied:** added `--exclude-dynamic-system-prompt-sections` to both iteration-tier and landmark-tier canonical invocation shapes. Empirical verification still owed.
- **Claude Code binary version drift** — the binary itself is external to the git tag; silent auto-updates across a landmark-tier eval calendar cause behavior drift. **Fix applied:** new "Binary version invariant" codified in `optimization-loop-hygiene.md` §Rule 3 (mechanisms block). Landmark-tier pins via `npm install -g @anthropic-ai/claude-code@<version>`; all archived runs record `claude --version` in `paper-trail-v<N>.json`.
- **Subagent-side persistent memory** — per `code.claude.com/docs/en/sub-agents#enable-persistent-memory`, subagents can maintain their own auto-memory. Main-session env-var propagation is verified for main-session-keyed memory (Test 4), but suppression of a subagent-specific memory path was NOT empirically canary-tested. **Mitigation:** added to OUT-of-system table + flagged as blocking-for-landmark investigation item in §Rule 3.

**Blocking for iteration-tier Task-5 scaffolding** (two items):

- Project-level `.claude/commands/` resolution under fresh `CLAUDE_CONFIG_DIR` — already known from §5.1.5 above. Severity raised from "defer to Task 5" to "must be validated early in Task 5."
- Settings-merge fail-closed canary — critic noted that `--settings` concat-merges with user `~/.claude/settings.json` rather than replacing it; the fresh-`CLAUDE_CONFIG_DIR` is what structurally masks this. If an eval operator forgets `CLAUDE_CONFIG_DIR`, user settings leak silently. Fail-closed canary added to residual investigation items.

**Nice-to-have findings** (documented but not urgent): `.claude/rules/*.md` suppression, managed-policy CLAUDE.md handling, `@imports` in skill definitions, skill-name collision precedence under `--bare`, `@imports` in `--append-system-prompt-file`. All listed in the expanded OUT-of-system table and residual-items list in `optimization-loop-hygiene.md` §Rule 3.

### Doc amendments landed 2026-04-22 post-critic

- `experiment-sarol-optimization-loop-hygiene.md` §Rule 3:
  - "Honest scope of the isolation claim" paragraph softened from "fully equivalent to `--bare`" to "equivalent for the six documented auto-discovery sources; additional flags/conventions address dynamic system prompt and binary version."
  - OUT-of-system table expanded with 7 new entries (`.claude/rules/*.md`, managed-policy CLAUDE.md, subagent memory, dynamic system prompt, session history, binary version, shell env).
  - Canonical iteration-tier and landmark-tier invocation blocks add `--exclude-dynamic-system-prompt-sections` and `--no-session-persistence`.
  - New "Binary version invariant" subsection.
  - Residual investigation items re-prioritized and split into blocking-for-landmark / blocking-for-Task-5 / nice-to-have buckets.
- `experiment-sarol-archive-and-eval-framework.md` §Q9c: iteration-tier and landmark-tier invocation patterns both add the two new flags.
- `NEXT.md` Tier 0: revised canonical iteration-tier shape; new Task 5 deliverables for version-capture in archive schema and the flagged canaries.

### Critic framing as a paper contribution

The critic audit itself exemplifies something the paper's methodology contribution argues for: rigorous agentic-system reproducibility requires adversarial audit of isolation claims, not just execution of documented suppression mechanisms. "We ran the documented disable flags and called it done" would have left dynamic system prompts + binary drift + subagent memory as silent variance drivers. The audit cycle — claim → canary → critic → doc revision — is itself part of the methodological substrate the paper advocates. Adds to the paper-writeup thread on "Claude Code substrate-level primitives are not enough for rigorous agentic experimentation without additional audit discipline" (see `paper-writeup-items.md`).

---

**Attribution.** All empirical tests run by Agent (Claude Opus 4.7, 1M context) in this session's main thread. IN/OUT formalization proposed by Human 2026-04-22 after Agent's initial 6-source leakage framing was judged insufficiently tied to paper-trail's actual system boundary. Two-tier architecture is Agent's synthesis from Human's formalization + empirical mechanism-availability table. Critic audit (§8) performed by a separately-briefed general-purpose subagent on Human's request; findings integrated into docs by main-session Agent. Follow-up investigation items in §5 and §8 are jointly flagged.
