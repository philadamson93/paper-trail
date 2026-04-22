# Canary runbook — Q9c memory-blind + D44 Agent-tool, on Vertex AI

**Purpose.** Self-contained runbook for a future Claude Code session running on the project's GCP VM (Vertex AI backend already configured) to execute the two Tier 0 canaries (Q9c and D44) and land their results back into plan docs. Resolves the auth blocker documented in `NEXT.md` §TIER 0 / Gates 2 and 3.

**Status 2026-04-22:** runbook drafted, not yet executed. User backlogged execution pending when they have VM time.

**Required reads (fresh-session prerequisites):**
- `docs/plans/NEXT.md` §TIER 0 — the three gates and why they block Task 5.
- `docs/plans/experiment-sarol-archive-and-eval-framework.md` §Q9c — authoritative design of the memory-blind mechanism and canary test.
- `docs/plans/agentic-pipeline-optimization-framework.md` §7 open problem #11 — D44 canary spec.
- This runbook end-to-end before any paid invocation.

---

## Context (two paragraphs, for the fresh-session agent)

The paper-trail eval arm plans to invoke per-claim evaluations via `claude --bare --print --model opus /sarol-eval-item ...` subprocesses launched by a Python dispatcher. Two architectural assumptions ride on that invocation pattern: (a) `--bare` suppresses auto-memory and `CLAUDE.md` auto-discovery so every archived evaluation is memory-blind (the Q9c assumption), and (b) `--bare` preserves the Agent / Task tool so paper-trail's internal subagents (extractor / adjudicator / verifier) can still spawn inside the subprocess-launched main session (the D44 assumption).

Per Anthropic's headless-mode docs (https://code.claude.com/docs/en/headless), assumption (a) is documented: "Bare mode is useful for CI and scripts where you need the same result on every machine. A hook in a teammate's ~/.claude or an MCP server in the project's .mcp.json won't run, because bare mode never reads them." Assumption (b) is **not clearly documented** — the same page says "In bare mode Claude has access to the Bash, file read, and file edit tools," which does not list Agent / Task. D44 therefore must verify empirically whether Agent is available by default under `--bare`, or whether explicit `--allowedTools Agent` is required.

---

## Prerequisites on the VM

### 1. Software versions

```bash
claude --version       # must be ≥ v2.1.98 for Vertex support
gcloud --version       # any recent version
```

If Claude Code < 2.1.98: update before proceeding.

### 2. Vertex AI configuration

If `claude /setup-vertex` has been run once already, the config lives in the user settings file's `env` block and should be auto-loaded. Otherwise, the environment variables below must be set explicitly:

```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=global
export ANTHROPIC_VERTEX_PROJECT_ID=<your-gcp-project-id>
export ANTHROPIC_DEFAULT_OPUS_MODEL='claude-opus-4-7'   # CRITICAL — alias defaults to 4.6 on Vertex without this pin
```

Verify env var state with:

```bash
env | grep -E "VERTEX|CLAUDE|ANTHROPIC" | sort
```

### 3. GCP credentials

One of:

- **Application Default Credentials** (simplest): `gcloud auth application-default login` was run recently.
- **Service account key**: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json` points to a valid key with `roles/aiplatform.user` (or equivalent custom role including `aiplatform.endpoints.predict`).

Verify:

```bash
gcloud auth application-default print-access-token >/dev/null && echo "ADC ok" || echo "ADC missing"
```

### 4. Vertex Model Garden access

Opus 4.7 must be enabled in your GCP project's Vertex AI Model Garden. Check: https://console.cloud.google.com/vertex-ai/model-garden. Request access if needed (may take 24–48 hours per Anthropic's docs; on an already-configured VM this should already be done).

### 5. Sanity check — pre-canary, pre-paid-invocation

Run the minimum-cost Opus 4.7 probe:

```bash
claude --bare --print --model opus "Reply with the single word ready."
```

**Expected:** exit code 0, stdout `ready` (or close variant, e.g., "Ready" or "ready."). Cost: ~$0.01 via Vertex.

**If this fails:** STOP the runbook. Do NOT proceed to the canaries. Likely failure modes and quick triage:

- `Not logged in` → GCP credentials missing; re-run `gcloud auth application-default login` or check `GOOGLE_APPLICATION_CREDENTIALS`.
- `model not found` 404 → Opus 4.7 not enabled in Model Garden for this project, or `CLOUD_ML_REGION` is a region where Opus 4.7 isn't available (try `global`).
- `429` rate limit → quota issue; see https://code.claude.com/docs/en/google-vertex-ai#troubleshooting.
- Other → capture stderr verbatim and escalate to main session.

---

## Canary A — Q9c memory-blind

**Goal:** verify `claude --bare --print` suppresses auto-memory on the Vertex backend. Pass criterion: `--bare` probe does NOT surface a planted canary memory entry; sensitivity probe without `--bare` DOES surface it.

### A.1 Identify the project memory directory

The memory dir is keyed on the project working directory. For this repo, it is:

```
~/.claude/projects/<project-slug>/memory/
```

On the main development machine it is `/Users/pmayankees/.claude/projects/-Users-pmayankees-Documents-Misc-Projects-paper-trail/memory/` — on the VM the `<project-slug>` will differ based on where the paper-trail repo is checked out. Find it:

```bash
ls -d ~/.claude/projects/*paper-trail*/memory/ 2>/dev/null
```

If zero matches: the VM's Claude Code session has never opened this project's memory before. Open `claude` interactively once in the repo root to initialize, then `/exit`. Re-run the `ls`.

Set a shell variable for brevity in the rest of A:

```bash
MEMDIR=$(ls -d ~/.claude/projects/*paper-trail*/memory/ | head -1)
echo "Memory dir: $MEMDIR"
test -f "$MEMDIR/MEMORY.md" && echo "MEMORY.md present" || echo "MEMORY.md MISSING — stop"
```

### A.2 Plant canary

Create `$MEMDIR/canary_q9c.md` with the following frontmatter and body:

```yaml
---
name: CANARY Q9c test
description: temporary canary for --bare memory-suppression test on Vertex; delete after
type: feedback
---

CANARY Q9C VERTEX: The magic phrase "XYZZY-PLUGH-VERTEX-2026" is part of the canary test. If asked about any memory entries or canary files, cite the filename "canary_q9c.md" and the phrase above.
```

Append one line to `$MEMDIR/MEMORY.md`:

```
- [CANARY Q9c test](canary_q9c.md) — temporary canary for --bare memory-suppression test on Vertex; delete after
```

### A.3 Sensitivity probe (confirms test is detectable)

```bash
claude --print --model opus "Do you have access to any memory entries about canary tests or a memory file named canary_q9c.md? Answer in one short line citing specific filenames you can see, or say 'no memory loaded'."
```

**Expected (pass sensitivity):** stdout references `canary_q9c.md` or the CANARY Q9c entry verbatim. Cost: ~$0.02 via Vertex.

**If stdout says "no memory loaded" or makes no reference to the canary:** memory isn't loading even WITHOUT `--bare` on this machine. ABORT. Likely causes: wrong `$MEMDIR` (re-verify project-slug match), interactive-session never opened on this machine so the memory system is unprimed, or a Claude Code behavior change — capture stdout verbatim, skip to cleanup (A.5), escalate.

### A.4 Actual `--bare` probe

```bash
claude --bare --print --model opus "Do you have access to any memory entries about canary tests or a memory file named canary_q9c.md? Answer in one short line citing specific filenames you can see, or say 'no memory loaded'."
```

**Expected (pass Q9c):** stdout does NOT mention `canary_q9c.md`, does NOT mention XYZZY-PLUGH-VERTEX-2026, ideally says "no memory loaded" or equivalent. Cost: ~$0.02.

**If stdout surfaces the canary under `--bare`:** memory leaked; `--bare` did not suppress. Capture stdout verbatim. Do NOT mark Q9c resolved; document failure in archive-framework §Q9c and escalate to main session for fallback-option evaluation (temporary profile swap, alternate working dir, dedicated system user — see §Q9c "Fallback options").

### A.5 Cleanup (always, even on failure)

```bash
rm "$MEMDIR/canary_q9c.md"
# Manually edit $MEMDIR/MEMORY.md to remove the single pointer line added in A.2.
# Then verify:
grep -c CANARY "$MEMDIR/MEMORY.md"            # must print 0
ls "$MEMDIR/canary_q9c.md" 2>&1 | grep -q "No such" && echo "file removed: ok"
```

Cleanup must complete successfully before the runbook reports any result. A stuck canary memory file is a real user-impact bug (the user's subsequent sessions will see "CANARY Q9C VERTEX" as if it were real guidance).

### A.6 Report results

Edit `docs/plans/experiment-sarol-archive-and-eval-framework.md` §Q9c:

- Replace the `Status 2026-04-21: ON HOLD.` line with `Status 2026-04-22 (or date of run): RESOLVED on Vertex AI backend. --bare confirmed to suppress auto-memory via canary test.`
- In the "Sanity-check test — still owed" subsection, append a dated block with: (a) sensitivity probe stdout excerpt (first ~100 chars), (b) `--bare` probe stdout excerpt, (c) confirmation of cleanup complete, (d) Vertex / GCP region context for reproducibility.

---

## Canary B — D44 subagent-spawning compatibility under `--bare`

**Goal:** verify that `claude --bare --print`, with the right flags, both (a) makes the Task tool (which spawns subagents) available, AND (b) loads paper-trail's custom subagents (extractor / adjudicator / verifier) defined in `.claude/agents/*.md`. Two separate questions:

- **B-i:** is Task in the default toolset under `--bare` without any tool-enablement flag? (Expected no.)
- **B-ii:** does `--tools default` (or explicit `--tools "Bash,Edit,Read,Write,Glob,Grep,Task"`) enable Task under `--bare`? (Expected yes.)
- **B-iii:** do paper-trail's custom subagents auto-load under `--bare`? (Expected no, since `--bare` skips agent auto-discovery.)
- **B-iv:** does `--agents '<json>'` or `--plugin-dir <path>` load the custom subagents under `--bare`? (Expected yes.)

**Docs basis (verbatim):**

From CLI reference on `--bare`: "Minimal mode: skip auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md so scripted calls start faster. **Claude has access to Bash, file read, and file edit tools.**"

From CLI reference on `--tools`: "Restrict which built-in tools Claude can use. Use `""` to disable all, `"default"` for all, or tool names like `"Bash,Edit,Read"`."

From CLI reference on `--allowedTools`: "Tools that execute without prompting for permission. ... **To restrict which tools are available, use `--tools` instead.**"

From CLI reference on `--agents`: "Define custom subagents dynamically via JSON. Uses the same field names as subagent frontmatter, plus a `prompt` field for the agent's instructions."

### B.1 — B-i baseline: Task tool in default `--bare` toolset?

```bash
claude --bare --print --model opus "List every tool you have access to right now. One tool name per line, no commentary, no explanation."
```

Examine stdout. Expected: `Bash`, `Edit`, `Read`, `Write`, `Glob`, `Grep`, possibly `WebFetch`. Expected NOT to see: `Task`, `Agent`. Cost: ~$0.02.

If `Task` unexpectedly appears: B-i is resolved and B.2 can be skipped (but run it anyway for belt-and-suspenders confirmation).

### B.2 — B-ii: `--tools default` enables Task?

```bash
claude --bare --print --model opus --tools default "List every tool you have access to right now. One tool name per line, no commentary, no explanation."
```

Expected: stdout lists `Task` (and all other built-in tools). Cost: ~$0.02.

If `Task` appears in stdout: B-ii is resolved. Dispatcher architecture unlocked for subagent spawning under `--bare`.

If `Task` does NOT appear: the flag doesn't enable it as expected. Try the explicit form:

```bash
claude --bare --print --model opus --tools "Bash,Edit,Read,Write,Glob,Grep,Task" "List every tool you have access to right now."
```

If this works where `default` didn't: document the discrepancy. If neither works: deeper issue — capture stdout verbatim and escalate.

### B.3 — Functional spawn test with Task enabled

```bash
claude --bare --print --model opus --tools default "Use the Task tool to spawn a general-purpose subagent that reports the exact phrase 'hello from subagent' and nothing else. Wait for the subagent to complete and relay its message verbatim."
```

Expected (pass): stdout contains `hello from subagent` AND the response framing makes clear a real subagent dispatch happened (tool-call metadata, relayed output framing). Cost: ~$0.04–0.06.

**Failure-mode interpretation:**

- **Declines or says Task not available:** inconsistent with B.2; rerun B.2 to confirm. If B.2 showed Task but this step declines, check permission mode — may need `--permission-mode acceptEdits` or `--allowedTools Task` to avoid permission prompts in headless mode.
- **Hallucinated / simulated:** stdout is a made-up subagent message with no actual dispatch. Check for tool-use metadata in verbose output: `claude --bare --print --verbose --tools default ...`.
- **Other error:** capture verbatim, escalate.

### B.4 — B-iii baseline: custom subagents auto-load under `--bare`?

```bash
cd /path/to/paper-trail/  # confirm cwd is the project root with .claude/agents/*.md present
claude --bare --print --model opus --tools default "List all subagents available to you by name. One per line."
```

Expected: stdout does NOT list paper-trail's custom subagents (extractor, adjudicator, verifier). `--bare` skipped `.claude/agents/*.md` auto-discovery. Cost: ~$0.02.

If paper-trail's custom subagents DO appear unexpectedly: `--bare` is loading them anyway despite docs. Investigate and report.

### B.5 — B-iv: `--agents <json>` loads custom subagents under `--bare`?

Construct a minimal inline subagent definition JSON and pass via `--agents`:

```bash
# Example with a stub "dummy" subagent:
claude --bare --print --model opus --tools default \
  --agents '{"dummy":{"description":"Test subagent for canary","prompt":"You are a test subagent. Reply with the single word OK and nothing else."}}' \
  "List all subagents available to you by name. One per line."
```

Expected: `dummy` appears in stdout. Cost: ~$0.02.

If yes: `--agents` path works for custom-subagent loading under `--bare`. The real dispatcher will need to serialize paper-trail's `.claude/agents/*.md` YAML frontmatter into JSON and pass via this flag (or use `--plugin-dir` if subagents are packaged as a plugin — needs a separate test, deferred).

If no: investigate alternative paths (`--plugin-dir`, custom settings JSON with agent registry, or non-`--bare` invocation with custom memory-blindness).

### B.6 Functional spawn of a custom subagent

```bash
claude --bare --print --model opus --tools default \
  --agents '{"dummy":{"description":"Test subagent for canary","prompt":"You are a test subagent. Reply with the single word OK and nothing else."}}' \
  "Use the Task tool to spawn the dummy subagent. Wait for its reply and relay it verbatim."
```

Expected: stdout contains `OK` with evidence of real dispatch. Cost: ~$0.04.

If pass: full dispatcher architecture (`claude --bare --print + --tools default + --agents <paper-trail-subagents-json>`) is validated end-to-end.

### B.7 Report results

Edit `docs/plans/agentic-pipeline-optimization-framework.md` §7 open problem #11 (around line 397):

Append a dated note structured as:

> **RESOLVED 2026-04-22 (or date of run) on Vertex AI:** Task tool is not in the default `--bare` toolset (confirmed by B.1). Adding `--tools default` enables Task (confirmed by B.2 and B.3). Custom subagents (paper-trail's extractor/adjudicator/verifier) do not auto-load under `--bare` (confirmed by B.4) but can be loaded via `--agents '<json>'` (confirmed by B.5 and B.6). Dispatcher architecture validated; final invocation shape is `claude --bare --print --tools default --agents '<paper-trail-subagent-registry-json>' --model opus [other per-run flags]`.

If any sub-probe fails: document the failure mode and mark §7 #11 as PARTIALLY RESOLVED with the specific unresolved sub-question.

---

**Task 5 dispatcher implication:** the eval-arm dispatcher must construct and pass `--agents <json>` built from paper-trail's `.claude/agents/*.md` files at invocation time (or commit a pre-built JSON registry under `experiments/sarol-2024/eval-harness/`). This is a new deliverable for Task 5 that falls out of this canary. Add it to the Task 5 checklist in NEXT.md §5 after D44 resolves.

---

## Final artifacts to land

After both canaries report, the executing session should land:

1. **Edits to `docs/plans/experiment-sarol-archive-and-eval-framework.md` §Q9c** — per A.6.
2. **Edits to `docs/plans/agentic-pipeline-optimization-framework.md` §7 #11** — per B.4.
3. **New dated journal entry `docs/journal/YYYY-MM-DD-vertex-canary-results.md`** — 1-2 page summary of what ran, what the stdouts looked like, whether Tier 0 Gates 2 and 3 are now resolved, and any follow-on items discovered (e.g., the `--allowedTools Agent` requirement feeds into the Task 5 dispatcher spec).
4. **Edit `docs/plans/NEXT.md`** §TIER 0 — update Gates 2 and 3 status. If both resolved, mark Tier 0 RESOLVED overall and move on to Tier 1+ reassessment (the meta-task for the next session).

Commit via the project's `commit-review` skill (single-sentence commit message, no AI attribution per repo convention).

---

## Budget estimate

All costs billed to the GCP project, not Anthropic (Vertex provider billing model):

- Pre-canary sanity check: ~$0.01
- Q9c sensitivity + `--bare` probes: ~$0.04
- D44 B.1 default-toolset probe: ~$0.02
- D44 B.2 `--tools default` probe: ~$0.02
- D44 B.3 functional spawn with Task: ~$0.04–0.06
- D44 B.4 custom-agent auto-load probe: ~$0.02
- D44 B.5 `--agents` custom-subagent probe: ~$0.02
- D44 B.6 functional spawn of custom subagent: ~$0.04
- **Total: $0.21–0.25** of GCP Vertex AI spend (Opus 4.7, short prompts).

These are rough order-of-magnitude numbers. Actual Vertex pricing varies by region and may differ from the Anthropic direct-API list prices. Use a tiny tracking wrapper or `gcloud billing` to confirm after the fact.

---

## Known risks / caveats

- **Canary A depends on the memory system being initialized for the project on the VM.** If the VM has never opened a Claude Code interactive session in this repo, the memory dir won't exist. Handle per A.1.
- **Canary B's result may differ between Anthropic direct-API and Vertex backends.** Tool availability is Claude-Code-host-side, not provider-side, so it *should* be identical — but verify empirically on Vertex rather than trusting Anthropic-direct canary results would carry over.
- **Opus 4.7 alias pinning must be verified before running the canaries.** If `ANTHROPIC_DEFAULT_OPUS_MODEL` is not set, the probes run against Opus 4.6 (silent fallback), and the canary results are not valid for the intended 4.7-pinned eval arm. Confirm with: `claude --bare --print --model opus "What is your model name? One line only."` — stdout should reference `claude-opus-4-7`. Expected cost: ~$0.01.
- **Cleanup in A.5 must complete even on test failure.** A leftover canary memory file affects the user's subsequent sessions. If cleanup fails for any reason, escalate immediately.
