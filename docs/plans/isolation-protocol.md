Reference: docs/claude_ops.md

# The isolation protocol — putting the judge inside the shared substrate

**Status: Draft** (rewritten 2026-09-11 against the shared engine's landed substrate; Codex review
applied 2026-09-13) · **Reviewed: No**
**Rewrite reason:** the first draft specified paper-trail-local machinery for work the shared
`agentic-label-opt` engine has already designed, built and landed. Phil, 2026-09-11: *the entire idea
of agentic program opt was to abstract away shared needs across these use cases.* This version starts
from what the engine provides and specifies only what paper-trail adds on top — which is much less.
**Review history — two independent passes, both applied.** Fresh-Claude audit of the first draft
(verdict *Revise*, 5 Critical) at `docs/plans/reviews/isolation-protocol-feedback-claude.md`. Then a
Codex cross-model review of this rewrite (verdict **Blocked**, 6 Critical, 7 failure modes, ~13
verification gaps) at `docs/plans/reviews/isolation-protocol-feedback.md` — **all applied 2026-09-13**.
What it changed, in one line each: the engine already threads the materialised path, so the
consumer-side agent is **ours** not the engine's (Phase 1a, and a new engine dependency that does not
exist yet); the Docker prefix cannot be built once at construction (Phase 1c, per-dispatch factory
plus a canonical container path map); one shared minimal cwd cannot serve a per-version editable
driver (Phase 2a, version-addressed); mounts do not cover credentials, and the token lands in host
argv and a log file (Phase 1b, a real engine diff and a prerequisite); containerizing discards the
judge's trace (Phase 1d); the refusal must cover **21** construction sites, not 7 (Phase 1f); the pin
hashed only host-side properties (Phase 3); Phase 4 named a function instead of an implementation;
and V2a-seal — the plan's centrepiece — could be defeated by a broad mount at an unexpected target.
A separate Codex adjudication chose the mechanism order (**containers first, hooks second**) at
`docs/plans/reviews/isolation-mechanism-options-feedback.md`.
**Findings this is built on:** `docs/session/2026-09-09-optimizer-loop-and-isolation-findings.md` §4.
**Prior work — read this before changing anything here:**
`docs/plans/isolation-prior-work-inventory.md`, a four-repo sweep of every branch, worktree, plan and
VM readback (2026-09-12). It exists because two sessions running concluded something was unbuilt when
it was already built and running. **Its first rule governs this plan too: current code beats every
document, including that one.**

⚠ **Recorded reversal, 2026-09-12.** Containers for the per-claim tier were rejected on startup cost
2026-04-23 (`experiment-sarol-eval-arm-isolation.md:174`) and adopted for the landmark tier only.
Phil reversed that, deliberately, on two grounds: the original assumed *thousands* of per-claim
invocations where the real figure is 561 (≈14 minutes on a multi-hour run), and the rejection was
conditional on finding a concrete case where prose is insufficient — which the 2026-09-09 run
produced. Recorded so this reads as a decision, not an oversight.

⚠ **And a risk acceptance this plan must not silently re-open.** 2026-04-23 named three exact
leakage vectors and accepted them: *"these require deliberate effort; the defenses make casual or
accidental leakage structurally impossible"*, under a stated threat model of honest optimisation
rather than an adversary (`agentic-pipeline-optimization-framework.md:319`). This plan addresses
**accidental** exposure — which is what 2026-09-09 demonstrated. It does not claim to defeat a
deliberate adversary, and should not be read as reversing that acceptance.
**Sibling:** Plan A is **done** (`feat/optimizer-prompt-latitude`, **447/447 at `f02d761`**; 445 at
the older `94a376f`, where sampling is 48/50). This plan rebases onto
it and lands after. ⚠ **Rebase base moved:** Plan A's tip is now **`f02d761`**, five commits past the
`94a376f` this plan's line numbers were taken against — re-spot-check the citations when the branch
is cut.

---

## Goal

Every number the optimizer has seen was produced by a judge session running with `cwd` = the full
repo root under `--dangerously-skip-permissions`. That tree holds the optimizer's own per-claim
failure analysis, its hypothesis log, and `iter/<n>/release_train.json` — **which carries per-claim
gold labels**. Across 561 judge traces nothing was read; but 13 sessions that lost their task fell
back on surveying their working directory, and two listed the optimizer's own findings as candidate
work. The only thing between "listed" and "read" was that no human was there to say yes.

Make the judge's boundary a fact about the filesystem instead of a sentence in a prompt, and prove it
with the test whose absence caused this: plant a sentinel where the gold labels live and show a judge
**cannot** open it.

### What landing this certifies, and what it does not

Written out because the review asked and because the first draft answered it two different ways in
two places.

**Certified on land:** the judge cannot *read* gold, the benchmark tree, the optimizer's findings,
the hypothesis log, or the repo outside its own staging — by absence from its mount set, proved by
probe. And the optimizer cannot *write* the scorer, the manifest, `iter/`, or gold — same mechanism,
one scope up (Phase 1e). Both principals are contained, so this is not "judge read isolation"
wearing a bigger name.

**Not certified, and each one named on purpose:**

| Residual | Why it is open | Where it goes |
|---|---|---|
| A **deliberate** adversary | the 2026-04-23 threat model is honest optimisation; this plan addresses accidental exposure, which is what 2026-09-09 demonstrated | unchanged, not reopened here |
| The session can read **its own token** | fixing host-argv and log disclosure (Phase 1b) does not hide a variable from the process holding it | needs a credential broker; out of scope, stated |
| **Audit rows** from container sessions | container mode discards the engine ledger, so four tripwires go blind | engine work, recorded in Phase 1e |
| **Per-call tool policy** (hooks) | deferred by Phil 2026-07-22; `--allowedTools` is coarser than a hook that fails closed per call | the second landing |
| Egress beyond the **host allowlist** | an allowlisted host can still receive data | the allowlist narrows the surface, it does not close it |

⚠ The pattern to avoid here is the one in the root-cause table: a residual that stops being written
down becomes a residual nobody remembers accepting.

## The architecture, in Phil's terms

Two things are fixed and one is free (Phil, 2026-09-11):

- **Scoring is deterministic code we never touch.** `SarolScorer` (`adapter.py:1130`) makes zero LLM
  calls; `parse_verdict.py` is the single seam allowed to touch gold.
- **How the agent generates a label for an example is 100% the agent's choice** — the dispatch
  prompt, the rubric, the driver, the topology, and whether it writes Python to do it.
- **The only bound on that freedom is no leakage and no cheating**, and that bound is enforced
  **structurally, by the container's mount set** — not by prose rules the agent could edit away.

So there are two boundaries, and the engine owns the design of both:

| Boundary | What it stops | Who builds it |
|---|---|---|
| **Read** — the judge cannot reach gold, the optimizer's workspace, or the benchmark data | leakage | **this plan**, consumer-side, no engine change (NF4) |
| **Write** — the optimizer cannot edit the scorer | cheating | **the engine**, one wiring step short of done (see *What the engine still owes*) |

Everything else in this plan is a layer behind the read boundary, or an integrity fix that has to
land before any number means anything.

---

## What the engine already gives us

All verified present in the SHA this repo pins (`82f547d`), which is an ancestor of engine `main`
and byte-identical to it under `isolation/`. Two engine plans, both **Completed**:
`2026-07-22-isolation-docker-substrate.md` (landed `de07032`, VM smoke 104 passed / 0 skipped) and
`2026-08-10-optional-edit-agent-mounts.md` (landed `dcefe1e`, 212 passed).

| Capability | Where | What it means for us |
|---|---|---|
| Container image | `isolation/Dockerfile` | non-root user, pinned CLI, `git`+`curl` guaranteed present so a probe failure can't be mistaken for a seal |
| Mount rendering | `isolation/docker_prefix.py::build_docker_cmd_prefix` (`:444-464`) | generic `extra_ro_mounts`, `writable_mounts`, `workdir`, `env`, `container_user`, `adc_path` — **the judge's mount set is expressible today with zero engine diff** |
| Plural editable set | `EditAgentMounts.editable_files` (`:96-112`) | went plural **for paper-trail by name**: its review found *"paper-trail's optimizable program is a five-file Markdown globset a singular `editable_file_rel` cannot express"*, and Phil's recorded decision was *"paper-trail is a future consumer and the shape is designed for it"* |
| Network profiles | `isolation/open_profile.py:68-72` | `network_policy="open"` + `adc_path=None` + `CLAUDE_CODE_OAUTH_TOKEN` — paper-trail's documented answer |
| Negative-control harness | `isolation/negative_control.py` (`run_probe` `:44-58`, fixture `:102`), `docker_available()` | a direct `docker run … cat <path>` probe is decisive **for the path it probes** — ⚠ not for the seal, since a broad mount at an unexpected target defeats a path list (see V2a-seal); skips cleanly with no daemon |
| Materialised path threading | `engine/loop.py:192`, `:426-431` + `tests/test_materialized_path_threading.py` | ✅ **already done** — the per-iteration snapshot path reaches `agent.run`. ⚠ The engine README saying otherwise is six weeks stale; the first draft cited it over code |
| A built consumer-side container agent | rad-eval `src/optimizer_loop/docker_agent.py` (198 lines, on `main`, armed run 2026-08-05, $4.13) | the pattern to copy for **both** principals: prefix from the engine, fresh temp writable staging, copy-back, reduced tool set. ⚠ Its provisioning `chown -R`s the clone and leaves Write/Edit enabled, so the boundary is the **mount set**, not the ownership — take the mounts, drop the chown |
| Read-only frozen checkout | `engine/materialize.py:100-107` | `.git`-free, chmod'd read-only **files and directories** — no git-history channel, nothing writable |
| Injection seam | `engine/claude_wrapper.py::run(cmd_prefix=…, extra_env=…)` | Docker slots in as a `cmd_prefix`, exactly parallel to rad-eval's `sudo -u optimizer env …`. No wrapper change |
| Edit-artifact contract | substrate plan, item 3 | frozen tree read-only; *more-specific* writable mounts overlay only the editable files; harness copies out before and back after, then commits |
| Tool-policy decision logic | `engine/policy.py` | tested `evaluate_read`/`evaluate_bash`/`evaluate_tool`, deliberately not wired to a hook |
| Per-run clone precedent | rad-eval `src/optimizer_loop/run_artifacts.py::default_loop_clone(run_id)` | *"two run-ids → two independent `.git` clones → the working tree, `iter/`, the `program-v*` tag namespace, and the in-clone audit ledger all isolate for free"* |

⚠ **The write boundary is the mount set — not a hook and not a checker.** Two ideas from the first
draft were the wrong layer and are withdrawn: re-hashing the scoring files (detects, does not
prevent) and porting rad-eval's `PreToolUse` hook. The substrate plan is explicit that rad-eval does
not hook `Write`/`Edit` either — *"that surface is constrained purely by OS file permissions, exactly
the role this plan's bind-mount permissions + harness copy-back already fill."* **The scorer is
protected by not being mounted writable.**

⚠ **But "the mount set is the boundary" is true of *writes* and false of everything else.** The
narrow claim holds: an unmounted scorer cannot be written, and no hook is needed for that. The
broader reading — that mounts are the whole protocol — is wrong for five threats a mount cannot
touch: **what commands run**, **outbound network**, **the credential** the session holds, **audit
rows**, and **what a Task subagent inherits**. rad-eval layers for exactly this reason: its
`--allowedTools` removes whole tools and its `PreToolUse` hooks fail closed per call, while OS
permissions police only Write/Edit. So deferring hooks (Phil, 2026-07-22) is a **stated residual**,
not a solved problem, and Phase 1's tool surface has to carry weight the mount set cannot.

## What lives where: paper-trail, the shared engine, and crc

Corrected 2026-09-12 against the prior-work sweep and Codex's review, and reframed 2026-09-14 on
Phil's OQ4 ruling. The first draft had the boundary backwards and handed away work that is
paper-trail's. Phil's reframe guards against the opposite error: **do not treat these problems as
paper-trail's alone.** Both paper-trail and crc-extraction-agent are ours, and crc will need much of
what this plan builds — the gold-holding container boundary, the by-name credential transport, the
audit rows from container sessions, the isolation-label check, the per-run clone, the bucket-mode
storage. So for each piece the real question is **modularity, not ownership**: does it belong in the
shared engine because more than one consumer needs it, or is it genuinely paper-trail-specific? The
list sorts the work on that axis. "Consumer work now" means *this plan builds or wires it on the
paper-trail side*; several of those are candidates to lift into the shared engine the moment crc needs
them, flagged where they apply.

### Consumer work this plan does now (paper-trail side)

1. **A consumer-side agent class for each principal.** ⚠ The materialised path **is** already
   threaded (`engine/loop.py:192`, `:426-431`, dedicated test); only cwd/env are not, by design,
   because a session binds those at construction. The engine README saying otherwise is six weeks
   stale, and the first draft cited it over code it had already read. **Model on
   `rad-eval:src/optimizer_loop/docker_agent.py`** — 198 lines, on `main`, run for real: prefix
   delegated to the engine, fresh temp writable staging, copy-back into the live tree, reduced tool
   set.
2. **An engine dependency.** paper-trail has **none** — two prose mentions, no package dependency.
   rad-eval pins it as a git revision under `[tool.uv.sources]`. Nothing in this plan can work until
   that exists.
3. **A paper-trail egress profile.** Phil's ruling 2026-08-18: the network profile is **paper-trail's
   own to own** — adding one to the engine's policy registry re-litigates a resolved question. Build
   it on the generic host-allowlist primitive, which already accepts a caller-supplied host list.
4. **The judge/dispatcher container.** Nobody has built one. Everywhere else ships *one* agent
   container with the runner, scorer, gold and commit in the host process. crc's umbrella plan
   designed the gold-holding dispatcher sibling (`2026-07-10-…:60`, `:232-237`) and it was never
   built. **This is the one place this plan adds something new, and it is a deviation from the built
   substrate — stated as such rather than assumed to exist.** ⚠ **Strongest shared-engine candidate
   (OQ4).** crc designed the identical gold-holding sibling, so paper-trail builds it first here, but
   the mechanism — mount set, path map, per-dispatch prefix factory — should be shaped to lift into
   the shared engine for crc to reuse, not rebuilt from scratch there. Only paper-trail's mount
   *contents* (which paths, which gold) are consumer-specific; the boundary machinery is shared.

### Shared-engine work (serves crc too, not just us)

Each item below is a gap in the shared engine, not a paper-trail defect — and crc-extraction-agent
hits every one of them the same way, so fixing them upstream is the modular move, not a favour to us.
That is the whole of OQ4: these belong in the engine because two consumers need them.

- **A credential transport that keeps a secret out of argv.** The renderer always emits
  `-e KEY=VALUE`, there is no by-name form on any ref, and the wrapper records the full command to a
  metadata file. ⚠ **This is paper-trail's documented auth path** (`isolation/open_profile.py:68-72`
  names our tier as authenticating with a token env var and no credential file), so it is a
  prerequisite, not a follow-up. Minimal change: an `inherit_env=("CLAUDE_CODE_OAUTH_TOKEN",)`
  sequence rendered as `--env NAME`. ⚠ It fixes host argv and log disclosure only — the token stays
  visible **inside** the session. Denying that needs a credential broker, which is out of scope here.
- **Audit rows from container sessions.** rad-eval's Docker agent discards the ledger
  (`docker_agent.py:84`), so the engine's four tripwires — including the one that halts when a
  final-evaluation row appears mid-loop, which *is* the dispatcher principle in code — are **blind in
  container mode**. Going container-first inherits that blind spot. Recorded, not solved here.
- **Permission-hook wiring** — decision logic exists (`engine/policy.py`, 16 tests), no hook anywhere.
  Deliberately deferred by Phil 2026-07-22 and by this plan's second landing.
- **Validating the isolation label** — declared at `engine/schemas.py:214`/`:228`, computed by
  nothing. ⚠ Cannot be tightened upstream as-is: the reference adapter passes `"fake"` and two engine
  tests pass `"h"`, so validation breaks the engine's own suite first.

## Why this happened, and the shape it keeps taking

Full detail in findings §4a–§4f. The requirement existed verbatim in three places — the framework
doc's attack table (*"optimizer workspace not in subagent scope"*,
`agentic-pipeline-optimization-framework.md:310`), **Rule 1**
(`experiment-sarol-optimization-loop-hygiene.md:11-20` — *"Violations invalidate the verdict"*), and
**Rule 3**'s canonical invocation stack (`experiment-sarol-eval-arm-isolation.md:88-115`). **None of
Rule 3 shipped**: in `adapter.py`, `add-dir` 0, `CLAUDE_CONFIG_DIR` 0, `env -i` 0,
`exclude-dynamic-system-prompt` 0, `no-session-persistence` 0.

It was traded for functionality — C4 #5 needed `--setting-sources project` to find
`.claude/settings.json`, so "the Runner keeps a real working checkout" (`adapter.py:722-725`), and
**"a real checkout" was silently read as "the whole repo root"** in the first adapter commit
`ad17478`, with no plan line. Then `papertrail-optimizer-requirements.md:144` claimed a guarantee
stronger than peers *"since there is no in-repo directory for the optimizer to be denied access to"* —
true of gold, **false of the TRAIN release the loop writes back into the repo** — `:169` deferred the
actor-ambiguity, `optimizer-instrument-repair.md:126` deleted the only actor-aware detector, and a
review signed off the wide cwd under a runnability lens. Across ten review docs every isolation
finding is optimizer→VAL directional: **reviews audited the direction that had a test and never the
direction that had only prose.**

**The tighter statement (from the Plan A exchange, and the one to act on):** in every instance **a
mechanism that would have covered it already existed and was pointed somewhere else.** That matters
because it says *re-aim what exists*, not *build another one*.

| Instance | Mechanism that existed | Where it pointed |
|---|---|---|
| The driver file | the frozen manifest | omitted it until 2026-09-11 |
| The notes addressed to the driver | Gate A | scoped to the *judge's* read path |
| The optimizer's hypothesis log | `profiles.py:514` asserts a reset lifecycle | nothing implemented one |
| The evidence envelope (**NF9**) | `runtime_pins` | pins the paperclip CLI, which the only runnable profile never invokes |
| The scorer | `verify_contract_files` re-hash | the ten markdown entries; **no `.py` is in the manifest at all** |
| The program's semantics mid-run (**NF10**) | `ContractGuardedAgent`'s post-agent guard | the `contract_file=True` entries — the files that *cannot* change. The misaim is a **moment**, not a file |
| *(caught in design)* the pins both plans key gates on | `runtime_pins` survives a re-freeze | untested implementation detail of a script neither gate owns |

✅ **Every phase below is that shape**, which is why this plan is small: Phase 1 uses the engine's
existing mount params, Phase 2 re-aims `val_isolation_problem` and a constructor parameter production
ignored, Phase 3 re-aims `runtime_pins`, Phase 4 adopts rad-eval's clone. The one genuinely new
mechanism is the sentinel control — new because its mirror image exists and asserts the opposite.

## Findings that changed the design

Verified on disk. Only the ones that still steer a decision.

**NF1 — `.claude/settings.json` does not exist anywhere.** `git ls-files | grep -i settings` empty;
`find . -name 'settings*.json'` empty; `.claude/` holds only `commands/ prompts/ scripts/ skills/
specs/`. So `--setting-sources project` finds no hook config and **there is no PreToolUse hook in the
judge's path at all** — the trade that bought the wide cwd bought nothing. ⚠ It also silently retires
a specified control: `NEXT.md:463` says a tag-scoped settings file *should* be committed. Retiring it
is defensible (the container supersedes it) but must be a recorded decision — **OQ6** — because
reasoning a requirement away in passing is this plan's own root cause.

**NF2 — the held-out path has no iteration signal.** `engine/loop.py:193-194` types
`train_inputs: RunInputs | Callable[[int], RunInputs]` but `val_inputs: RunInputs`, documented at
`:255` as *"fixed for the whole run, as always"*, and `:345` reuses the one object every iteration.
Both batch ids are iteration-free (`dispatcher.py:898`, `:816`). Proven on disk: batches `i1` and
`i5` point claim `1059-13` at the identical staging dir, and one verdict file carries mtime `06:51`
against a directory created `01:42` — overwritten in place. ⇒ staging cannot be keyed on the
iteration without an engine change.

**NF3 — the staging fix is a precondition for the fail-closed fix, not a sibling.** While a stale
verdict sits at `ledger/claims/<claim_id>.json`, "wrote nothing" is indistinguishable from "last
iteration wrote it", and `adapter.py:907` reads that path unconditionally after the session exits —
so a stale file is validated and **scored as this iteration's prediction**.

**NF4 — the judge side needs no engine change.** `runner.run(materialized, inputs)` is duck-typed and
consumer-constructed (`loop.py:344-345`, `:443`; built in `dispatcher.build_components` →
`adapter.SarolRunner`). Only the *Agent* side needs the engine's owed wiring.

**NF5 — Rule 3 cannot be restored verbatim.** Its stack ends in `--add-dir $REPO`, granting exactly
the tree this plan denies; it was written when `:144`'s "nothing in-repo to be denied" was believed.
Adopt its hygiene, invert its scope. All the flags exist on the installed CLI (2.1.267).

**NF6 — the judge inherits the optimizer's whole environment.** `headless_claude_invoke`
(`adapter.py:470-478`) calls `subprocess.Popen(..., cwd=…, start_new_session=True)` with **no
`env=`**. ⚠ Do not over-claim it: `_gold_root()` (`parse_verdict.py:47-51`) falls back to
`~/.paper-trail/gold` with **no env var set at all**, so scrubbing `PAPER_TRAIL_GOLD_DIR` buys
nothing against gold — the path is hard-coded. `env -i` closes every *other* variable; the gold
boundary has to be the mount set.

**NF8 — the driver is optimizer-editable, and stays fully so.** It is the 10th manifest entry at
`contract_file=False`, in `JUDGE_SCOPE` (`profiles.py:58`), editable on `retrieval`. Phil,
2026-09-11: *everything inside the labeling program is editable, including what is passed along to
subagents*, and **including Python if the optimizer wants to write Python**. ⚠ An earlier draft moved
~40% of that file (argument parsing, input checks, slot filling, the abort sidecar) into harness code
and out of the optimizer's reach — withdrawn. The consequence is accepted deliberately: the delivery
path can be rewritten mid-run, so **the no-task failure class is detected rather than prevented**
(Phase 0b), at roughly 2% of sessions.

**NF9 — the evidence envelope is version-uncovered.** The manifest's ten entries are all `.md`;
`evidence_producers.py`, which writes the envelope the judge reads *as its evidence*, is not among
them and is not in `deliberately_excluded` either — never considered. The only record of the
retrieval condition is two scalars (`dispatcher.py:827`) whose selftest (`:1147`) checks they are
**present**, never that they describe what ran; and `retrieval_k` pins the *budget*, not the
selection function. **Plan A owns this**, leaning `runtime_pins` + a gate.

**NF10 — gates run once at preflight while the optimizer edits mid-run. Real, but not isolation.**
⚠ Phil's ruling: the gold/docs/`spec_root` prohibitions are enforced by the mount set once Phase 1
lands, so editing that prose changes nothing — the read fails regardless. Sorting the driver's eight
prohibitions, every one an edit can actually defeat (never ask, never write the verdict yourself,
never repair, never retry, never pre-read the paper) is **measurement integrity**, not leakage. So
the post-edit check belongs to Plan A and Gate F, and this plan does not carry it.

---

## Approach

**Phases are numbered in build order.** The containers are the boundary, so they land before the
layers behind them — not last, as the first draft had it. **Both principals get one** (Phil): the
judge, and the optimizer. The scorer and gold sit outside both.

Four design rules, each taken from something already working here:

- **Re-aim what exists.** The root-cause table above says every defect had a mechanism pointed
  elsewhere. Before adding a mechanism, find the one already there.
- **Fail closed.** A gate refuses the run rather than degrading it. A gate that warns gets read past.
- **No green-by-absence.** A gate reading a value out of a file it does not write must assert the
  value **is there**, not merely compare it — a comparison against a missing or empty value passes
  and reports green while checking nothing. It applies to registers too: a list is load-bearing only
  if something reads it and something fails when it is wrong. **V1d is the prototype** (it asserts
  the engine checks *ran*). This rule caught four holes, two of them in this plan's own centrepiece
  — see the green-by-absence audit.
- **Copy the built thing, not the designed thing.** Where a capability exists in code that has
  actually run, port its shape rather than re-deriving it: rad-eval's container agent for both
  principals, its per-run clone for Phase 4, the engine's mount renderer for the boundary. The one
  place this plan has no built precedent is the judge/dispatcher container, and that is said out loud
  rather than assumed (see `isolation-prior-work-inventory.md`).

### Phase 0 — the integrity floor

Nothing downstream is measurable until this lands, and it is independent of the boundary.

**0a. Archive the previous verdict, then assert it is gone** (§4g item 6). Per NF2 there is no
iteration number on the held-out path, so immediately before dispatching a claim the Runner (1) moves
any existing `ledger/claims/<claim_id>.json` to
`ledger/_superseded/<utc_timestamp>-<claim_id>.json`, (2) asserts the live path is absent. Same for
`ledger/errors/`. No iteration number needed, consumer-only, and it **preserves** the prior verdict
rather than destroying it as today's overwrite does. *Alternative:* make `val_inputs` accept a
`Callable[[int], RunInputs]` mirroring the existing `train_inputs` precedent (`loop.py:249-255`) —
cleaner, but an engine change shared with three consumers for a consumer-side defect. **OQ2.**

**0b. Refuse to score a dispatch that produced no verdict** (§4g item 5). ⚠ **This is the
load-bearing step of Phase 0**, because NF8 leaves the delivery path editable: nothing prevents a
broken dispatch, so this is the only thing between one and a poisoned iteration.

⚠ **What happens today — the first draft got this wrong twice.** A no-task session exits 0 (a slash
command cannot set the host's exit code) and writes nothing, so control reaches the exit validator,
**not** the exit-code branch: `validate_file(<missing>)` → `violations=["UNREADABLE:…"]` →
`record["status"] = "invalid_output"` at **`adapter.py:907-930`**. `:900-903` is the exit-code branch
and is not on this path.

⚠ **And a naive new status would zero the whole batch.** The Scorer demands total coverage
(`complete = scored["n_total"] == requested and unresolved == 0` → `result(0.0, …)`,
`adapter.py:1414-1435`) and `continue`s past any status not in `("ok", "invalid_output")` (`:1382`).
A third status drops the claim, breaks coverage, and returns **0.0 for all 50** — verbatim the
2026-09-07 failure the comments at `:1378-1382` and `:918-930` exist to prevent (*"93 of 100 claims
were fine and every number came back 0.0"*), whose own odds are ~64% at a 2% failure rate.

The earlier draft weighed three ways to **score around** the failure — all now superseded by OQ5's
resolution below, but kept because they show why the naive fixes are wrong:

| Option | Mechanism | Cost |
|---|---|---|
| (a) **Re-dispatch once** | retry the claim; coverage holds by construction | +1 session per no-task (~2.3%) |
| (b) **Shrink the denominator** | decrement `requested_count` (`:1006`, read at `:1371`/`:1414`) | run-manifest contract change; iterations score different denominators |
| (c) **Tag but keep scored** | leave in the denominator, exclude from the mistake corpus | metric absorbs our own infra failure |

⚠ **(c) is closer to today's behaviour than the table implies.** An unreadable verdict already lands
`invalid_output`, is already scored as `INVALID_OUTPUT`, and is already **not** appended to `joined`
— so it is already out of the mistake corpus. Choosing (c) therefore adds a **field**, not a
behaviour: a distinguishable `n_infra` count so an infrastructure failure stops being reported as a
program failure.

**Resolution — OQ5 (Phil, 2026-09-14): allow it to fail; the optimizer determines and fixes it.**
No Runner-side retry, no scoring around it. A dispatch that produces no verdict **fails the claim,
and that failure is surfaced to the optimizer as feedback.** The reasoning is NF8: the delivery path
is optimizer-editable, so a no-task dispatch is a **delivery defect inside the program the optimizer
owns** — exactly the kind of failure the optimize loop exists to catch and fix in the next version. A
silent retry would hide the very defect the optimizer is supposed to see and repair. Concretely:

- **The load-bearing gate still stands.** A no-verdict dispatch must never read the stale verdict left
  on the held-out path (Phase 0a) and must never be silently scored 0.0 across the whole batch (the
  2026-09-07 failure). Refusing to score is what makes the failure *visible*; that half does not change.
- **The failure is distinguishable, not reported as program quality.** Record it under a separate
  delivery-failure / `n_infra` count, keyed **only** on the `UNREADABLE:` prefix, so it never lands in
  the mistake corpus and is never reported as a program-performance number. A malformed-but-present
  verdict stays `invalid_output` and stays scored — that is a result about the program.
- **The iteration returns a failure signal, not a misleading score.** Rather than the total-coverage
  path returning 0.0 for all 50 (`adapter.py:1414-1435`), the iteration surfaces the delivery failure
  to the optimizer as its outcome. The optimizer reads it, diagnoses the broken delivery, and fixes it.
- **No cache trap, no count desync.** With no retry, the probe-cache hazard (a cached empty result
  re-served, `dispatcher.py:306-320`) and the session-count-vs-claim-count desync (batch aggregation,
  `adapter.py:1111-1122`) both vanish — they were artifacts of the retry option, now dropped.
- **Gate F is no longer in tension.** Plan A's `check_orchestrator_consistency.py` forbids
  `retry`/`re-dispatch`/`bounce` in driver-facing prose. With no retry, there is nothing for it to catch.

**0c. Render the dispatch prompt in Python — as a default the driver may override** (§4g item 4).
Both observed delivery bugs (`$dispatch_prompt` unexpanded; `$(cat /tmp/adjudicator_filled_$$.txt)`
with an unexpanded `$$`) appear **nowhere in this repo** — the model authored them at run time,
differently each run, and 13 of 561 sessions started with no task. A new `dispatch_prompt.py` reads
the frozen prompt between the markers, loads slots from `ledger/evidence/<claim_id>.json` +
`staging_info.json`, substitutes, and writes the rendered bytes into staging, refusing on an
unresolved slot (`SLOT_UNRESOLVED:<slot>`).

⚠ **Per NF8 this is a default, not a constraint.** The driver stays fully editable. An optimizer that
leaves the delivery text alone gets deterministic substitution; one that rewrites it owns the result.
What reaches the subagent is 100% optimizer-authored either way — Python only fills placeholders in a
prompt the optimizer wrote. Reuse, so this does not fork existing logic: `evidence_producers.py:210-216`
already reads `staging_info.json` and `claim_text_normalized` (factor **one** shared slot-source
helper), and `validate_sarol.py:266` already emits `CLAIM_ID_MISMATCH:` (reuse that vocabulary).
⚠ Honest scope: under `retrieval` the same Python process writes both sides of the join, so
`CLAIM_TEXT_MISMATCH` compares a value to its own source and **cannot fire**. Keep it for profile
parity; do not present a tautology as a guarantee.

### Phase 1 — the containers: the boundary itself

**Both principals get one.** Phil, 2026-09-11: the optimizer runs in its own container too, and the
scorer stays outside both. So this phase builds two boundaries, not one. Phil: *"we DO want this
running in docker, that's our whole isolation engine and intentional."* Everything in Phase 2 is a
layer behind this, not an alternative to it.

**1a. Depend on the engine at a pinned revision.** paper-trail has **no** dependency on
`agentic-label-opt` today — two prose mentions, no package. Nothing else in this plan can be built
until that exists. Copy rad-eval's shape: a git revision under `[tool.uv.sources]`, pinned to a
commit, not a branch. The adapter's `engine_path()` env-var dance (`adapter.py:117-118`) stays as the
selftest path; the pin is what the runtime imports. ⚠ Pinning to `main` instead of a revision
reintroduces exactly the drift that made the stale README outrank live code in this plan's first
draft.

**1b. The judge's mount set** (§4g item 8). Grant: `{claim staging (rw), materialized spec root (ro),
version-addressed cwd (ro)}`. Everything else — `iter/`, `optimizer/findings/`, `meta-learnings.md`,
`optimizer/context/`, **`~/.paper-trail/gold`**, **`~/.paper-trail/benchmarks`** — is denied by
absence *and* asserted denied.

✅ **Zero engine diff for the mounts themselves.** `build_docker_cmd_prefix` (`:444-464`) already
exposes `extra_ro_mounts`, `writable_mounts`, `workdir`, `env`, `container_user`, `adc_path`, and an
explicit `edit_agent_mounts=None` documented for *"a consumer with no editing agent at all (e.g.
crc)"* — exactly the judge's shape. An earlier draft proposed a `JudgeMounts` dataclass in a repo
three siblings consume; that buys naming, not capability.

⚠ **But the mount set does not cover credentials or network, and the first draft implied it did.**
Two separate holes:

- **Network policy is required and has no default.** `"none"` — what the existing controls use —
  would deny the judge its own API calls, so it would fail rather than be isolated. Use
  **`network_policy="open"`** + **`adc_path=None`** + `CLAUDE_CODE_OAUTH_TOKEN`
  (`isolation/open_profile.py:68-72`). A paper-trail allowlist profile built on the generic
  host-allowlist primitive is **ours to own** (Phil, 2026-08-18), not an addition to the engine's
  registry.
- **The token lands in host argv and in a log file.** The renderer only emits `-e KEY=VALUE`
  (`docker_prefix.py:437-439`), and the wrapper records the whole command to `meta.json`
  (`claude_wrapper.py:342-365`). Since a token env var **is** paper-trail's documented auth path, the
  by-name form (`inherit_env=("CLAUDE_CODE_OAUTH_TOKEN",)` → `--env NAME`) is a **prerequisite of
  this phase**, not a follow-up. ⚠ It fixes host argv and log disclosure only; the token stays
  readable **inside** the session. Denying that needs a credential broker — out of scope, stated so
  nobody reads this as solved.

⚠ **Also adopt deny-by-default inside the container**, replacing `--dangerously-skip-permissions`:
`--permission-prompts none` (`claude --help`: *"nobody: anything that would prompt is denied
automatically"*) with a non-bypass `--permission-mode` and an `--allowedTools` set. Strictly better
than bypass-everything even behind a mount boundary. **Not** an alternative to the container — an
earlier draft framed it that way and Phil withdrew it (**OQ3**, resolved). ⚠ **The allowlist must
carry `Task`** if OQ1 keeps the driver: the judge *is* a Task subagent, so an allowlist that omits it
kills every dispatch while looking like a permissions tightening. V0c covers it.

**The tool surface is a named deliverable, not a flag choice.** Write it down as an exact list with
a reason per entry, because this is the layer covering the four threats the mount set cannot. Minimum
shape: `Task` present (the judge **is** a subagent), `Read`/`Write` scoped to staging, `Bash` either
absent or reduced, `WebFetch`/`WebSearch` **absent**. Model the list on rad-eval's
`src/optimizer_loop/allowed_tools.py`, which removed `WebSearch` and `Agent` until inheritance was
proven. ⚠ **Prove it rather than declaring it** (V2h): inside the container, `env`/`printenv`,
arbitrary `Bash`, `WebFetch`, and an outbound request to a non-allowlisted host must each fail, and
the failures must be attributed to a named layer — otherwise a pass says only "nothing happened".

⚠ **A deny list as a config field would be inert.** Docker mounts are allow-only, so a deny list
means nothing unless it is the input to a runtime probe. Its contract here: *every entry is probed by
V2a-seal and must fail to read.*

⚠ **Writable mounts are directory-oriented, and host preparation is ours.** The engine separates
`prepare_writable_mounts` from the renderer deliberately, so paper-trail owns the host-side
permissions of the staging tree and must test them against **the real container uid**, not root. The
crc gate that preceded this used the ADC uid 1033 with a tmpfs `HOME`; the same care applies here.

**1c. Build the prefix per dispatch, not once at construction** (§4g item 9). ⚠ **The first draft put
this in `dispatcher.build_components` and that cannot work.** Three inputs are only known later:

| Input | Known when | Consequence |
|---|---|---|
| `materialized_path` | per Runner call (the engine passes it into `run`) | one prefix per iteration, not per process |
| `claim.staging_dir` | per claim | one prefix per dispatch |
| the staged argv | `_stage_command` (`adapter.py:700-731`) embeds **host absolute paths** | those paths do not resolve to `/workspace/...` inside the container |

So the seam is a **factory owned by `SarolRunner.process(claim)`**: given `(materialized_path,
claim)` it returns the prefix for that one dispatch. With it comes a **canonical container path map**
— a single place that says host path → container path (`/workspace/program`, `/workspace/staging`,
`/workspace/cwd`) — and **every** host path that crosses into the container is translated through it:
the argv, `--add-dir`, `workdir`, and any path interpolated into prompt text. A path that is correct
in argv and stale in the prompt is a dispatch the judge cannot complete, and it will look like a
model failure.

Two properties to keep: the prefix wraps the **driver** invocation and therefore the Task subagent
inside it, so containerizing the driver containerizes the judge transitively; and a wholesale
`DockerRunner` must preserve the `CachingRunner` + `BudgetGuard` wrapping at `dispatcher.py:553-570`
or it loses the probe cache or the spend ceiling.

**The rendered shape, for one claim** — written out because the review's judgement was that the phase
was not implementable without it, and because every path below is one the first draft would have
left as a host path:

```
docker run --rm
  -v <runs>/<run_id>/iter3-current:/workspace/program:ro      # the version being scored
  -v <staging>/<claim_id>:/workspace/staging:rw               # this claim only
  -v <runs>/<run_id>/traces/<claim_id>:/workspace/trace:rw    # 1d, so the trace survives --rm
  --network <profile>                                         # paper-trail's allowlist
  --env CLAUDE_CODE_OAUTH_TOKEN                               # by NAME, not KEY=VALUE (1b)
  -u <container_uid>
  -w /workspace/program                                       # cwd = the snapshot (2a)
  <image>@<digest>                                            # digest, not tag (Phase 3)
  claude --print
    --permission-prompts none --permission-mode <non-bypass>
    --allowedTools Task,Read,Write                            # Task is required, not optional
    --add-dir /workspace/staging
    /sarol-eval-item '<prompt with /workspace/... paths only>'
```

Three things to read off it. **Every path is a container path** — `--add-dir`, the workdir, and the
paths inside the prompt text all come from the same map, and a `/home/philadamson/...` string
anywhere in this command is a bug V2d catches. **Nothing here is constant across dispatches**: the
program mount changes per iteration, the staging and trace mounts per claim. And **the token appears
as a name**, which is the one real engine diff this phase needs.

*Gate:* **two claims × two program versions in one process** (V2d). One prefix reused across either
axis is the failure mode — it silently points a v1 dispatch at v0's bytes, or claim B at claim A's
staging, and both produce plausible verdicts.

**1d. Keep the judge's trace** (new; the first draft lost it). `find_transcript`
(`adapter.py:427-438`) globs the **host's** `~/.claude/projects`. Inside a container that directory
is the container's, and it is discarded with the container — so containerizing silently ends judge
traceability, which is how the 61% stale-verdict contamination was found in the first place. Cheapest
fix, no new plumbing: the adapter **already holds the streamed session JSON in memory**
(`:469-503`); persist it beside the verdict and record it as `trace_ref`. ⚠ Do this in the same
change as 1c, not after — a containerized run with no trace cannot be audited, and the audit is the
deliverable.

**1e. The optimizer's container.** Model on **rad-eval's `src/optimizer_loop/docker_agent.py`** — 198
lines, on `main`, actually run: prefix delegated to the engine, a fresh temp writable staging tree,
copy-back into the live tree afterwards, a reduced tool set. What it gives paper-trail that a
permission rule cannot: the scorer, gold, `iter/`, and the manifest are **not in the optimizer's
mount set**, so "the optimizer cannot edit the scorer" holds by construction rather than by a rule
the optimizer is asked to respect. ⚠ **A literal port does not give us the write boundary.**
rad-eval's provisioning `chown -R`s the whole clone to the sandbox account and leaves Write/Edit
enabled, so its own boundary is the mount set, not the ownership. Take the mount discipline and drop
the chown.

⚠ **Docker mode writes zero audit rows.** rad-eval's Docker agent discards the engine ledger
(`docker_agent.py:84`), so the engine's four tripwires — including the one that halts when a
final-evaluation row appears mid-loop, which *is* the dispatcher principle expressed in code — are
**blind in container mode**. Going container-first inherits that blind spot knowingly. Recorded here
so it is a decision, not a surprise; fixing it is engine work.

**1f. One refusal locus, covering every construction site.** ⚠ **There are 21 direct `SarolRunner`
constructions, not the 7 the first draft counted** — 19 in `adapter.py`, one in `canary.py`, one in
`scripts/run_baseline.py`. A gate inside `build_components` protects the paths that go through
`build_components` and silently does not apply to the rest, which is worse than failing: the widest
judge in the system (the baseline recut) would run ungated while the suite reports green. So the
refusal lives in **`SarolRunner.__init__`**: absent an explicit prefix factory it raises, and an
**offline test** may opt out by passing an explicit sentinel plus an injected fake prefix. That makes
every one of the 21 sites either containerized or visibly opted out, and makes the count itself
assertable (**V2c**).

⚠ **No opt-out for anything that produces or guards a reportable number.** That rules out both
non-test sites: `scripts/run_baseline.py` **produces** Plan A's baseline recut, and `canary.py`
**guards** it. Both take the shipping factory. An opt-out there would mean the baseline is measured
on the uncontained instrument while every iteration compared against it is measured on the contained
one — which is not a weaker guarantee, it is an invalid comparison. **OQ7** is therefore about the
selftest sentinel's shape, not about whether the baseline gets one.

**1g. The sentinel negative control** (§4g item 8). Plant sentinels and assert a judge **cannot**
read them. This mirrors the one read-oriented control that shipped — `test_train_only_read_scope`
(`tests/test_isolation_negative_control.py:173`), which asserts reads **succeed**. Its own plan
classifies that control's *failure* as *"adapter-wiring bug, halt (not an isolation failure…)"*
(`docs/plans/2026-07-22-isolation-docker-substrate.md:100`). ⚠ The findings doc attributes that quote
to `smoke.md:98`; corrected here. The smoke that passed 104/0 had **six** Docker negative controls
and none about read-scoping. ⚠ **Sentinels include gold and the benchmark tree**, which an earlier
draft omitted entirely — they are the highest-value secrets in the system.

⚠ **Containerizing swaps the instrument.** `isolation/Dockerfile:25` pins
`CLAUDE_CODE_VERSION=2.1.218`; the installed CLI is **2.1.267** — 49 patch releases apart, at the
exact moment this plan owes Plan A a clean baseline. Pinning the image to the host version is an
explicit deliverable, the version is recorded in the run manifest beside `model`/`profile`/
`retrieval_k`, and **V5 asserts parity**.

⚠ **Shared-repo footprint: four files, not one.** The first draft said one and that was wrong even on
its own terms — a new control in `isolation/negative_control.py` needs matching assertions in
`tests/test_isolation_negative_control.py`, and re-pinning the image's CLI version touches
`isolation/Dockerfile` and `isolation/README.md`. Add the credential-by-name change in
`isolation/docker_prefix.py` and it is a real, if small, upstream diff. ✅ Still nothing in `engine/`.
⚠ And the dividing line: **paper-trail's own sentinels and auth stay in paper-trail.** An upstream
change earns its place only if it is genuinely generic and tested upstream — otherwise it is our
specifics living in three other consumers' repo.

### Phase 2 — narrow what the judge sees: layers inside the box

Phase 1 makes things unreachable. Phase 2 reduces what is *exposed* even where the mount set already
denies it — it removes the ambient-survey channel that actually fired in the 2026-09-09 run.

**2a. A version-addressed working directory** (§4g item 2). `working_checkout` is already a
constructor parameter (`adapter.py:628`), already exercised against a scratch dir
(`adapter.py:2110-2130`); production simply passes the `REPO_ROOT` default. Per NF1 the judge's
session needs only one file in cwd: `.claude/commands/sarol-eval-item.md`, the slash-command
definition it runs.

⚠ **It cannot be a single fixed directory, and the first draft made it one.** That file is manifest
entry #10 and is **fully editable by the optimizer** (NF8), so its bytes differ per program version.
One shared minimal checkout serves whichever version wrote it last — so a v0 dispatch and a v1
dispatch in the same process can run the *same* driver while the release payload says they ran
different programs. That is a measurement-integrity failure of exactly the kind this plan exists to
close, and it would be invisible: both dispatches return plausible verdicts.

So **cwd is addressed by program version**, and the cleanest form of that is already on disk: the
per-iteration materialised snapshot contains the driver at the same relative path, is read-only
(`materialize.py:100-107`, verified `dr-xr-xr-x`), and has no `.git` and no `CLAUDE.md`. So the
judge's cwd can simply *be* the snapshot: one fewer directory, one fewer copy to keep in sync, one
fewer mount, and version-addressing for free. The first draft's reason for a separate `/tmp` root was
gold-adjacency (snapshots live under `~/.paper-trail/runs/`, two hops from `~/.paper-trail/gold`) —
**inside the container that reason disappears**, since only the mount is visible.

*The one unknown, folded into V0c:* the snapshot is read-only including directories, so if the CLI
needs to create anything in cwd this fails outright. **Pre-encoded fork:** works → cwd is the
snapshot; CLI needs to write → a per-dispatch copy of the snapshot's command file into a temp dir,
**keyed by program version**, and record *write access* as the reason, not gold-adjacency. Either way
the version-addressing requirement stands.

⚠ **`command_path()` against a fixed checkout stops being a valid implementation.** Command discovery
and `missing_command_error()` currently resolve against one directory; they have to resolve against
**the version being scored**. That is the real code change behind this step — the mount is the easy
part.

*Gate:* **V3d** — two program versions whose drivers emit distinct markers, dispatched in one
process; each verdict must carry its own version's marker. A test that only checks "cwd contains
exactly one file" passes on the broken design.

**2b. A scope check beside the one that already works** (§4g item 1). A pure predicate in a new
`isolation.py` returning a problem if any forbidden path sits inside the judge's readable tree.

⚠ **Two loci, and the first draft conflated them.** The *scope predicate* belongs where
`val_isolation_problem` is already raised — `dispatcher.py:549-551`, inside **`build_components`**
(`def` at `:495`), which is also where `working_checkout` is already threaded. But the *refusal* that
makes it load-bearing cannot live there, because **`build_components` is not on every path**: of the
21 direct `SarolRunner` constructions, only a handful route through it. Per 1f the refusal lives in
`SarolRunner.__init__`; `build_components` raises early with the better error message. Both, not
either.

⚠ **The lockstep change is therefore bigger than seven callers.** The seven `build_components`
callers still change (`:748` plus six selftest sites at `:1253`, `:1399`, `:1404`, `:1416`, `:1421`,
`:1603`), *and* every direct construction site must pass a prefix factory or an explicit opt-out
sentinel — 19 in `adapter.py`, one in `canary.py`, one in `scripts/run_baseline.py`. That last one
produces the baseline recut this plan owes Plan A, so it is the one that matters most and the one a
`build_components` gate would have missed entirely. **OQ7** covers the opt-out policy.

**Reuse, not re-derivation:** the predicate reuses `val_isolation_problem`'s containment idiom
(`resolve()`, then `path == other or other in path.parents`, `dispatcher.py:481-487`), and its
negative control reuses `_raises_valueerror` (`:455`), which the VAL check's own control uses.
⚠ **Forbidden set needs absolute entries** — Rule 1's list includes *raw benchmark data*, and
`~/.paper-trail/gold` / `~/.paper-trail/benchmarks` are absolute paths a repo-relative set cannot
see. Per NF6 the gold path is hard-coded with no env var, so this is the only place it becomes
checkable.

**2c. Rule 3's hygiene, scope piece inverted** (§4g item 3, per NF5):

| Piece | Value | Vector it closes |
|---|---|---|
| `cwd` | the **version-addressed** working dir (2a) — no `.git`, no `CLAUDE.md`, not under the gold tree's parent | ambient survey — the demonstrated vector |
| `--add-dir` | **staging + materialized spec root only** — *not* `$REPO` | out-of-tree reads it legitimately needs, nothing more |
| `env` | `env -i` + pinned allowlist (`PATH`, `LANG`, `TZ`, `HOME`, `CLAUDE_CODE_OAUTH_TOKEN`) | NF6 — every inherited variable |
| `CLAUDE_CONFIG_DIR` | fresh per invocation | cross-session state |
| `--no-session-persistence` | on | same |
| `--exclude-dynamic-system-prompt-sections` | on | dynamic injection, including the git-state section |
| auto-memory / project-`CLAUDE.md` | disabled, or `--bare` | project-context loading |

⚠ **The demonstrated vector was git state, not `CLAUDE.md`.** `195-41` enumerated filenames *"based
on the git status"* — the dynamic git-state section, which is **cwd-dependent** and which Rule 3
kills at the source (*"no `.git/` in cwd means no branch/uncommitted-files section; empirically
verified 2026-04-23"*). Both channels fired; the one producing the filename list was git state. So
2a's root does more work here than any env var, and **V3b asserts both absences**.

**`--bare` is a candidate for the last row, with two caveats.** Verified on CLI 2.1.267: *"skip
hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and
`CLAUDE.md` auto-discovery"* — one flag for the row whose two env-var names are unverified, and
`NEXT.md:461` already names `claude --bare --print /sarol-eval-item …`. But it **refuses
OAuth/keychain auth**, and Rule 3 records that `--bare`-style default toolsets **omit `Task`** —
which OQ1 option (i) requires. V0b tests it; OQ1 decides. **Three canonical pieces are deliberately
omitted** and said so plainly: `--tools default`, `--agents`, `--settings <tag-scoped>`
(`experiment-sarol-eval-arm-isolation.md:107-115`) — all unused today; `--tools default` becomes
required if OQ1 keeps the driver, `--settings` returns only if OQ6 authors the file.

*Seam note.* `Invoker` is `Callable[[Sequence[str], pathlib.Path, float], InvocationResult]`
(`adapter.py:332`) and dozens of gates pass 3-arg spies. Rather than widen the protocol, `env` and
`cmd_prefix` are bound onto `headless_claude_invoke` with `functools.partial`, keeping the call shape
at `:868`. **The same binding carries Phase 1c's Docker prefix — one seam, both uses.**

⚠ **Bind it inside `process(claim)`, not in `__init__`.** The first draft bound once per Runner, which
works for a static env and **cannot** work for the prefix: per 1c the prefix depends on
`materialized_path` (per Runner call) and `claim.staging_dir` (per claim), so a construction-time
binding pins the first dispatch's paths onto every later one. The static env may still be bound at
construction; the prefix is rebound per dispatch. ⚠ Bound values are invisible to a 3-arg spy, so the
Runner must also **expose the resolved env and the prefix it used** or V3c and V2d are both
unwritable.

### Phase 3 — pin the configuration

`optimizer_isolation_hash` is declared (`engine/schemas.py:214`, `:228`) and never validated; this run
wrote the literal `'sarol-2024'` on all ten payloads (`adapter.py:1499-1503`). Per the engine's owed
item 5 this is a **consumer-side** gate.

⚠ **The obvious construction is a tautology.** `SarolReleaseBuilder()` takes its default at all five
construction sites (`dispatcher.py:582`, `:1019`, `:1089`, `:1205`; `adapter.py:2038`), so comparing
"what the builder would stamp" against "the computed value" compares a value to itself and can never
fail — the same inertness, one layer up.

**Use `runtime_pins`, not a new file.** `canary.py:16-36` states the rule: *a guard whose reference
value is not under version control is not a guard.* `isolation.py` computes a hash over the judge's
actual configuration and the gate compares it against the manifest's **`runtime_pins`**. ⚠ An earlier
draft invented a separate `isolation-pin.json` — itself an instance of building beside a mechanism
aimed one dependency away (`runtime_pins` pins the paperclip CLI, which the only runnable profile
never invokes). Four facts verified before switching: `combined_hash` covers `entries` **only**
(`freeze_program_v0.py:93-97`) so this cannot re-version the program; `cmd_write` does
`manifest = dict(old)` and overwrites five keys (`:117-139`) so `runtime_pins` survives a re-freeze
untouched; `deliberately_excluded` already records `SKILL.md` as *"pinned via `runtime_pins`
instead"*; and the manifest is committed, so the canary rule is satisfied for free. ⚠ **Read the pin
from `git show HEAD:<manifest>`, not the worktree** — Plan A's Gate H shipped exactly that defect
(sheet compared against a stub that was also editable in the same tree, so one session rewriting both
passed).

⚠ **What the hash covers, in full.** The first draft listed five components and every one of them
was a *host-side* property, so a container swapped underneath it would not move the hash — the pin
would certify a configuration it never saw. Now that containers are the mechanism the schema has to
name them:

| Group | Components |
|---|---|
| Image | image **digest** (not tag), pinned `CLAUDE_CODE_VERSION`, container user, workdir |
| Boundary | the rendered mount set as `(source, target, mode)` triples **with each mount's role**, the network policy name, the egress allowlist |
| Session | `--add-dir` set, env allowlist **names**, permission mode, `--permission-prompts` value, `--allowedTools` set |
| Program | the judge fileset, the trace-persistence destination |

Two rules on top: **names not values** for the env allowlist, so a rotated token does not read as a
configuration change; and **the mount set as rendered**, so the pin is computed from the same bytes
V2a-seal probes rather than from the intent that produced them. ⚠ A version string is not a digest —
an image rebuilt from the same Dockerfile with a newer base layer keeps the tag and changes the
contents.

### Phase 4 — one clone per run

**The finding (Plan A).** `optimizer/meta-learnings.md` — injected into every optimizer session — has
**never been archived or reset between runs**, while `profiles.py:514` reasons as though a reset were
guaranteed. It is not a manifest entry. So two runs both labelled `program-v0` could open with
different inherited hypotheses and nothing would record it. Plan A archived the 258-line sheet and
reset it to a stub, which unblocks its owed baseline recut.

**The root cause is structural.** paper-trail's run boundary stops half-way — its own log line says
*"Results under `$RUNS`; releases under `$REPO_ROOT/iter/`."* Per-run: results only. Shared: releases,
the lessons sheet, `findings/`, and the `program-v*` tag namespace.

**Adopt rad-eval's `default_loop_clone(run_id)`** — a fresh git clone per run id. Phil's framing: *the
program is per iteration; the optimizer is per run.* It lands here rather than beside this plan
because Phase 2a already builds a per-run working directory for the judge; this is the same move one
level up, for the optimizer. Three consequences: **Gate H becomes unnecessary** (it exists only to
refuse starting when a previous run's `findings/iter-*.md` are present, and a disposable clone has no
residue — it *retires* the gate rather than satisfying it); **most of the ledger-recut hazard
disappears** (the recut is dangerous only because it rewrites shared tags); and it closes NF9's class
for the optimizer's inputs, since a clone boundary covers everything in the tree.

✅ **Where run state lives — OQ8 resolved (Phil, 2026-09-14): local git and local disk.** paper-trail
is non-PHI forever, so Gate H's archive at `~/.paper-trail/runs/_archive/` and the per-run clone both
stay on local VM disk — plain git is a fine home. No split to the shared mount: the "bucket mode"
that lands run state on the mount is a modular capability of the shared engine for a PHI consumer like
crc-extraction-agent, which paper-trail leaves off (see OQ4). This also sidesteps the mount's ~2 MB/s
small-file reads, which would have made a clone working tree there slow anyway.

⚠ **Precondition, verified 2026-09-11:** the archive holds `meta-learnings.md` **only**. The five
`findings/iter-*.md` in the primary checkout are still untracked, unarchived, and **the only copy**.
Archiving them is a precondition, not a consequence.

⚠ **Where this actually gets built — the first draft named a function and stopped.** "Adopt
`default_loop_clone`" is not an implementation surface; the engine helper only makes a clone, and
every decision about what runs inside it is ours. Concretely:

| Piece | Decision |
|---|---|
| Who mints the run id | the VM runner script (`run_hillclimb_vm.sh`), which already owns `$RUNS`; one id per invocation, passed down, never re-derived |
| Where the clone is made | before `build_components`, so every path the dispatcher resolves is already inside it |
| What `REPO_ROOT` means afterwards | the clone, not the checkout — this is the change with reach, because `REPO_ROOT` is the default for `working_checkout` and for the forbidden-path set |
| What comes back out | releases under `iter/`, `findings/`, and the lessons sheet, copied to the run's archive at the end; nothing copied back into the source checkout |
| What the optimizer's container mounts | the clone's writable subtree only — 1e's mount set is defined against the clone, so Phase 4 and Phase 1e have to agree on paths |

⚠ **Phase 4 and Phase 1e are the same boundary at two scopes and must land together or in that
order.** An optimizer container whose mounts point at the shared checkout has no clone to protect,
and a clone with no container around the optimizer is a fresh tree the optimizer can still walk out
of. Neither half is isolation alone.

### Deliberately out of scope

- **The corpus accounting bug** (§3.4) — iter-5's corpus claims `n_correct=37`; truth is 36.
- **The runner prints the lagging metric** (§3.5) —
  `experiments/sarol-2024/scripts/vm/run_hillclimb_vm.sh:184-195` reads `iter/5/release_val.json` and
  reports program-**v4**; the fix is `best_metric_value` from `run_summary.json`. Plan A did not fix
  it. ⚠ Plan A inserts 24 lines near `:54`, moving this to ~`:208-219` after it lands.
- **The evidence envelope** (NF9) — Plan A owns it.
- **Post-edit semantic checks** (NF10) — Plan A's, on the `ContractGuardedAgent.run()` seam. Two
  lessons to carry there: **normalize whitespace before matching prose** (Gate G was defeated by a
  line wrap — `used to\nsay` never matched `used to say`, and the fixed gate found seven more
  instances), reusing Gate A's `_normalize()`; and keep any deferral register **occurrence-level and
  self-asserting** so a stale entry fails.
- **One line owed to the optimizer's prompt** (Phil) — `optimizer/prompt/optimizer-instructions.md`
  says nothing about this today (checked: zero matches for permission / denied / will-fail). Once
  Phase 1 lands, tell the optimizer that gold, the benchmark tree, the repo outside its own staging
  and anything under `spec_root` are **denied at the permission layer**, so instructing the program to
  read them buys a wasted iteration. **Guidance for efficiency, not a gate.** Plan A's surface.
- **Letting the optimizer author Python** — the boundary already permits it (`editable_files` is a
  plural sequence, nothing markdown-specific). The constraint is the **freeze**:
  `freeze_program_v0.py` hardcodes a `FILESET` literal, and Stepback Phase F already crashed here (an
  `extractor_lib/`-only edit silently dropped by a program-v0-vintage `versioning.py`). Glob a program
  directory rather than list files — program-model work, separate from isolation.
- The measurement redesign (§6 D1–D4), the artifact rewrite (§7.4), the judge-model A/B (§7.5).

---

## Files to Modify

**New — `optimizer/isolation.py`.** Scope predicate (`inner_scope_problem`), the judge's and the
optimizer's mount-set builders over the engine's generic params, the canonical container path map
(1c), the env allowlist, the version-addressed cwd builder, the configuration hash. One module for
one concern, matching this directory's one-module-per-concern convention. **Sister files:**
`dispatcher.py:465-490` (`val_isolation_problem`) for the predicate and its containment idiom;
`canary.py:16-36`, `:118-151` for the committed-pin / refusal shape.

**New — `optimizer/dispatch_prompt.py`.** Slot resolution, integrity checks, prompt rendering (0c).
Out of `adapter.py` (already ~2,900 lines) and out of `isolation.py` (different concern). **Reuse
target:** `evidence_producers.py:201-216`.

**`pyproject.toml`** — ⚠ **the dependency that does not exist yet**: `agentic-label-opt` pinned to a
git **revision** under `[tool.uv.sources]`, copying rad-eval's shape (1a). Nothing else in this plan
imports until this lands.

**`optimizer/adapter.py`** — the largest surface, and bigger than the first draft said:
- the **per-dispatch prefix factory** called from `SarolRunner.process(claim)`, and the **refusal in
  `SarolRunner.__init__`** (1c, 1f) — ⚠ **19 direct construction sites in this file** each pass a
  factory or an explicit opt-out sentinel;
- **path translation** through the canonical map everywhere a host path crosses the boundary:
  `_stage_command` (`:700-731`, which embeds host absolute paths today), the `--add-dir` set, the
  workdir, and any path interpolated into prompt text;
- **persist the streamed session JSON as `trace_ref`** (`:469-503`), because `find_transcript`
  (`:427-438`) globs the host's `~/.claude/projects` and goes blind in a container (1d);
- bind `env`/`cmd_prefix` via `functools.partial` (leaving `Invoker`'s 3-arg shape at `:332`/`:868`
  intact) **and expose the resolved env for V3c**;
- archive-and-assert-absent before dispatch (`:907`); the infrastructure-failure classification at
  **`:907-930`** keyed on `UNREADABLE:` (**not** the exit-code branch at `:900-903`), plus the OQ5
  fail-and-feed change: a distinguishable delivery-failure count, surfaced to the optimizer, never
  scored as program quality (no retry — see OQ5). ⚠ **Its lockstep readers are wider than the first
  draft's three** — the Scorer's coverage rule (`:1371`, `:1382`, `:1414`), `write_manifest`'s
  `requested_count` (`:1006`), **batch status aggregation** (`:1111-1122`, which must report the
  delivery-failure count so an infra failure is never summed into the program's mistakes),
  **`_VAL_BREAKDOWN_ALLOWED`**, **`SarolReleaseBuilder`**, **mistake-corpus routing**, and any
  **run-summary** consumer. Change them together or the metric and the manifest disagree about what
  was measured;
- call the renderer; drop the `optimizer_isolation_hash` literal default (`:1499-1503`). New checks
  in `_selftest()` (`:1642`). ⚠ Plan A also edits `_selftest()` at `@@ -1665`, `@@ -1764` — expect a
  rebase there.

**`optimizer/dispatcher.py`** — raise `inner_scope_problem` beside `val_isolation_problem` at
`:549-551`, **inside `build_components`** (`:495`); pass the version-addressed cwd (`:500`, `:556`);
the pin gate; preserve the `CachingRunner` + `BudgetGuard` wrapping at `:553-570`. (No retry path to
build — OQ5 resolved to fail-and-feed, so the probe-cache bypass the retry option needed is dropped.)
**Seven `build_components` callers change in
lockstep:** `:748`, `:1253`, `:1399`, `:1404`, `:1416`, `:1421`, `:1603` — and separately every
direct `SarolRunner` site, which `build_components` does not cover.

**`optimizer/canary.py`** — one direct `SarolRunner` construction; opt-out or factory (1f).

**`scripts/run_baseline.py`** — `:119-121` constructs `SarolRunner` directly. ⚠ This is the widest
judge in the system and the one that produces Plan A's baseline recut, so it is the site the first
draft's `build_components` gate would have missed. Its own version-addressed cwd, or an explicit
reasoned opt-out (**OQ7**).

**`experiments/sarol-2024/scripts/vm/run_hillclimb_vm.sh`** — mints the run id, calls the provisioner
before `build_components` (Phase 4), and records the in-container CLI version and the **image
digest** beside `model`/`profile`/`retrieval_k`.

**New — `optimizer/run_clone.py`** (Phase 4, **only if OQ9 answers "keep"**). The provisioner
rad-eval's `default_loop_clone` does *not* include, which is the part that does the security work:
clone from a named source ref with stated options, set ownership for the container uid, mark the tree
`safe.directory`, define **resume** behaviour for an interrupted run, define the `program-v*` **tag
policy** inside the clone, and re-resolve **every consumer of `REPO_ROOT`** — which is the change
with reach, since `REPO_ROOT` is the default for both the working checkout and the forbidden-path
set. **Sister file:** rad-eval `src/optimizer_loop/run_artifacts.py`. Tests: two run ids isolate
releases, tags and findings. ⚠ If OQ9 answers "split", this file and the runner's clone call move to
that plan and Phase 4 is struck from this one — not left in as prose.

**`experiments/sarol-2024/program-v0/manifest.json`** — one new key under **`runtime_pins`** carrying
the expected configuration hash over Phase 3's expanded schema (image digest, mount triples with
roles, network policy, session flags). Not a new file, and it cannot re-version the program:
`combined_hash` covers `entries` only, and `cmd_write` preserves `runtime_pins` across re-freezes.

**`.claude/commands/sarol-eval-item.md`** — the default delivery text points at the pre-rendered
prompt. ⚠ **Fully editable** (NF8): this is a default the optimizer may rewrite, not a contract.

**Shared engine** (`~/code/agentic-label-opt`, now on `main` @ `c2dd0b3`) — ⚠ **four files, where the
first draft claimed one:**
- **`isolation/docker_prefix.py`** (small, real) — a by-name env form
  (`inherit_env=(...)` → `--env NAME`) so the OAuth token stops appearing in host argv (`:437-439`)
  and in the wrapper's recorded command (`claude_wrapper.py:342-365`). A prerequisite, not a
  follow-up, because a token env var is paper-trail's documented auth path.
- **`isolation/negative_control.py`** (additive) — the generic parts of the seal control: exact
  mount-set comparison, ancestor-source rejection, probe-every-rendered-target, reusing `run_probe` +
  `_build_common_fixture` (`:44-58`, `:102`).
- **`tests/test_isolation_negative_control.py`** — the matching assertions, including the negative
  control that mounts a tree at an unexpected target and must **fail**. A control with no test
  asserting it is exactly the inert-mechanism pattern.
- **`isolation/Dockerfile`** + **`isolation/README.md`** — re-pin `CLAUDE_CODE_VERSION` from 2.1.218
  to the host version and say so. ⚠ The README is also the file whose six-week-stale sentence about
  `iter_n` outranked live code in this plan's first draft; correcting it is part of the change, not
  tidying.

⚠ **Paper-trail's own sentinels and auth stay here, not upstream.** An upstream addition earns its
place only if it is generic and tested there; otherwise it is our specifics living in three other
consumers' repo.

✅ Still **no change to `engine/`** — the materialised path is already threaded (`loop.py:192`,
`:426-431`).

**`docs/claude_ops.md`** — one line: its §Environment says this repo has "no build step, no runtime,
and no test suite" while this plan's verification rests on a 447-check suite. Repo-local copy.

**`docs/plans/README.md`** — one row. **`docs/plans/NEXT.md`** — the isolation entry's state.

---

## Open Questions

Nine numbered, **five open** — OQ3, OQ4, OQ5 and OQ8 are resolved (2026-09-14) and kept for
reference. OQ5 was the implementation gate and is now settled (fail-and-feed-the-optimizer).
**OQ9 still decides this plan's scope and should be answered first;** OQ1, OQ2, OQ6 and OQ7 remain.

**OQ9 — does Phase 4 stay in this plan, or become its own reviewed plan?** The review's judgement was
blunt: Phase 4 as written is *"not implementable by a fresh session"* — it named a helper and left
out the provisioner, the resume behaviour, the tag policy, and every consumer of `REPO_ROOT`. It now
has an implementation surface (see the table there), but it is still the largest remaining unknown in
a plan that already covers two container boundaries. Options: **(i) split it** — land Phases 0-3,
which are the isolation the 2026-09-09 run demanded, and give the per-run clone its own review;
**(ii) keep it and fully specify** — write the provisioner, the clone options, ownership, resume,
tag policy and the `REPO_ROOT` consumer list into *Files to Modify* before implementation starts.
*Recommendation: (i).* ⚠ With one condition, because splitting has a real cost: Phase 1e's optimizer
mounts are defined against the clone, so a split means Phase 1e lands against the shared checkout and
the optimizer's boundary is weaker until the clone follows. Say that in the landing note rather than
discovering it later.

**OQ5 — ✅ RESOLVED 2026-09-14 (Phil): allow it to fail; the optimizer determines and fixes it.**
No Runner-side retry and no scoring around the failure. A dispatch that produces no verdict fails the
claim, and that failure is surfaced to the optimizer as feedback — because the delivery path is
optimizer-editable (NF8), a no-task dispatch is a delivery defect inside the program the optimizer
owns, and the optimize loop exists to catch and fix exactly that. The refuse-to-score gate still
stands (never read the stale verdict, never silently return 0.0 for the whole batch); the failure is
recorded under a distinguishable delivery-failure count, keyed only on `UNREADABLE:`, so it is never
reported as program quality. Dropping the retry also removes the probe-cache trap, the
session/claim-count desync, and any tension with Gate F. ⚠ Plan A's baseline recut runs on this.

**OQ1 — does the driver session survive 0c?** (i) keep it, pre-render its prompt — minimal change to
the measured condition (the judge stays a Task subagent, which is what all five iterations were
measured under); (ii) eliminate it — simpler, removes a model from the delivery path, applies every
flag directly to the judge, saves its ~10% of spend. *Recommendation: (i) here*; (ii) changes what
the judge *is* and belongs with the measurement redesign. ⚠ Interacts with `--bare` (omits `Task`),
and (ii) now costs a manifest re-freeze back to 9 entries, breaking five count/scope selftests.

**OQ2 — staging: consumer archive, or an engine change?** *Recommendation: consumer-side now* — the
defect is ours and the engine change touches three other consumers; the engine version is the better
end state if per-iteration trees are wanted for forensics.

**OQ3 — ✅ RESOLVED 2026-09-11 (Phil): the container is the mechanism.** An earlier draft asked
whether `--permission-prompts none` could replace it and said Phase 1 would then "demote to
defence-in-depth" — that reopened a settled decision and is withdrawn. Deny-by-default is adopted
**inside** the container as a second layer. What survives is a measurement, not a fork: **V0c reports
the containerization cost** across ~561 sessions/run; it does not decide whether to containerize.

**OQ4 — ✅ RESOLVED 2026-09-14 (Phil): it is a modularity question, and much of this belongs in the
shared engine.** Phil's ruling reframes the whole "what lives where" section above: do not assume
these issues are paper-trail's alone — crc-extraction-agent will need much of the same (the container
boundary, the by-name credential transport, the audit rows, the isolation-label check, bucket-mode
storage), and **both repos are ours**. So each piece is sorted by *where it should live*, not *who
owns the defect*. For the narrow instance that opened this question — pin the isolation-label check
consumer-side or upstream? — do the check **consumer-side now** (upstream breaks the engine's own
reference adapter and two of its tests first, engine-owed item 5) but **file it as shared-engine
work**, because crc needs the identical check and rebuilding it there would repeat the work.

**OQ6 — is the tag-scoped settings file retired, or deferred?** NF1 proves it never existed;
`NEXT.md:463` says it should be committed. Retiring it is defensible now the container supersedes it,
but it must be a **recorded** decision — reasoning a requirement away in passing is this plan's own
root cause.

**OQ7 — what shape does the offline-test opt-out take?** ⚠ Narrower than it looks, because the
review closed the part that mattered: `run_baseline.py` and `canary.py` **produce and guard
reportable numbers**, so both take the shipping factory and neither gets an opt-out (1f). What is
left is the 19 selftest sites: an `isolation_mode="test"` keyword, an injected fake prefix, or a
module-level fixture. *Recommendation:* an injected fake prefix — it keeps the argv assertions real,
so the selftests still exercise the path translation rather than skipping it, and there is no
production-reachable branch to disable by accident. ⚠ A boolean flag is the option to avoid: a
keyword that silently disables the boundary is the kind of mechanism this plan's root-cause table is
made of.

**OQ8 — ✅ RESOLVED 2026-09-14 (Phil): paper-trail uses local git and local disk.** paper-trail is
explicitly not PHI and never will be, so plain git and local VM disk are a fine home for the per-run
clone and its archives — no bucket needed. The shared-mount "bucket mode" (run state and archives
landing on the mount so a PHI consumer can hold them off local disk) is for a repo like
crc-extraction-agent, which *is* PHI. So bucket mode is not paper-trail's concern — it is a **modular
capability of the shared engine** that crc turns on and paper-trail leaves off (see OQ4). Practical
consequence: drop the "clone local, archive to mount" split from Phase 4; both stay local.

---

## Verification

⚠ **Line numbers in this plan are against Plan A's branch at `94a376f`, which this plan rebases onto
— not the current primary checkout, and ⚠ not Plan A's current tip `f02d761`, five commits later.
Re-spot-check on cutting the branch.** Spot-checked: `adapter.py:1130` (`class SarolScorer`) and
`dispatcher.py:495` (`def build_components`) resolve in both; `profiles.py:58` (`JUDGE_SCOPE`)
resolves **only** on `94a376f`, because the driver-in-judge-scope change is Plan A's. Cut the branch
from `94a376f` first and the citations hold.

Run wherever this is implemented; `phil-sllm-01` has Docker (verified: `docker info` succeeds, user in
the `docker` group), so Phase 1 runs here. Selftests are an inline `_selftest()` per module behind
`--selftest`.

⚠ **The baseline, measured — and the first measurement was itself inert.** An earlier draft
prescribed `export PYTHONPATH=…` and reported 258/259. `adapter.engine_path()` (`adapter.py:117-118`)
reads **`AGENTIC_LABEL_OPT`**, defaulting to a Mac-only path; run that way the adapter prints
`PASS engine not found … engine-facing checks SKIPPED` and `32/32 passed` — green while **186 checks
never execute**, and the skip prints `PASS`, not `SKIP`.

```
cd experiments/sarol-2024/optimizer
export AGENTIC_LABEL_OPT=/home/philadamson/engine-82f547d   # NOT PYTHONPATH
~/.local/bin/python3.13 <module>.py --selftest              # default python3 is 3.10, too old
```

On Plan A's tip **`f02d761`**: adapter **152/152** · dispatcher 114/114 · validate_sarol 33/33 ·
sampling 50/50 · evidence_producers 26/26 (no flag) · canary 24/24 · profiles 48/48 — **447/447**.
⚠ **At `94a376f` it is 445, not 447** — sampling reports 48/50 there, and the two fixes are among the
five commits between the two. So the bar depends on the base: cut from `f02d761` and require 447/447.
Using `94a376f`'s number as the bar on a branch cut from `f02d761` would let two real failures pass.
✅ `run_hillclimb_vm.sh:47`
now hard-fails when `AGENTIC_LABEL_OPT` is unset, so half of V1d already landed at the runner level;
the selftest path still has no guard.

### Green-by-absence audit

Every gate reads a value out of something it does not write, so every gate carries an existence or
count assertion. **Four were real holes** — the two found while writing the plan, plus two the
cross-model review found in the gates that matter most.

| Gate | Vacuity risk | Assertion |
|---|---|---|
| **V2a-seal** | **empty deny list ⇒ zero probes ⇒ green, seal unproven**; and a **broad mount at an unexpected target** passes every path probe | list non-empty, expected entries by name **and count**, probe count equals list length; the rendered mount set equals an **exact** `(source, target, mode)` allowlist; no source is an **ancestor** of a forbidden path; probes enumerated **from the argv**; plus a positive control and a **negative control that must fail** |
| **V2c** | a refusal that only covers the sites we remembered ⇒ green while an ungated judge ships | assert the **count** of direct `SarolRunner` constructions (21) and classify each as containerized or explicitly opted out |
| **V4** | pin container emptied by a `cmd_write` refactor; pin read from the worktree; **a host-only hash ⇒ a swapped container leaves it unmoved** | round-trip re-freeze test; pin read from `git show HEAD:`; one divergence case per container component, image by **digest** not tag |
| **V3b** | an exact-fileset assertion passes on a **single shared** cwd serving two program versions | V3b keeps the fileset assertion; **V3d** asserts each version's own driver bytes reached its own verdict |
| **V1c** | a manifest with no matching entry leaves nothing to compare | assert the manifest resolves and the entry is present before comparing bytes |
| **V3a** | a truncated forbidden set ⇒ fewer cases ⇒ still green | assert the set's **length**, one case per entry including the two absolute ones |
| **V3c** | an empty `--add-dir` set trivially satisfies "no entry is an ancestor of `$REPO`" | assert the set equals **exactly** the two expected paths |
| **V2e** | a `trace_ref` field that exists but points nowhere | non-empty file **and** the claim id present in its content; at run scale, trace count equals dispatch count |
| **V2f** | grepping for a token that was never set ⇒ nothing found ⇒ green | assert the variable **name** is present in the argv before asserting the **value** is absent |
| **V2h / V2i** | every attempt failing ⇒ green, but a broken container looks identical to a sealed one | each result attributed to a **named layer**, plus a positive control that must **succeed** (staging read; subagent staging read) |
| **V1d** | — | **the prototype**: asserts the checks *ran*, not that they passed |
| **V2b** | a skipped suite reports no failures; and the historical "104" is a number from another machine | asserts **0 skipped**, and records **this run's** engine SHA, image digest, Docker version and pytest counts rather than reusing the old total |
| **V0b** | a matrix row silently disappears and the rest still pass; a flag works in a scratch probe and is dropped by `_stage_command` | assert the **candidate count**, and assert each surviving flag appears in the **shipping argv**, not just in a probe |
| **V0c** | a hand-built `docker run` or a direct judge prompt proves the fixture, not the system | run the **real driver→Task topology** through the **same per-dispatch prefix factory** production uses |
| **V1a** | two archived attempts overwrite each other and the gate still sees "an archive exists" | collision-proof archive names; assert the live verdict **and** error paths absent before each attempt; assert archives are **not** inside the judge's readable mount |
| **V1b** | a fail-closed change that looks clean at the Runner breaks the seam it shares | trace the resolved OQ5 behaviour (fail-and-feed) end to end — Runner record → batch status → Scorer → release → corpus → optimizer-facing outcome |
| **V2a-live** | a valid verdict proves the judge works, not that it was contained | plus non-null readable `trace_ref`, `Task` available, exact in-container CLI version and image digest, token non-disclosure, and one adversarial read/write/egress attempt |
| **V5** | "zero no-task sessions" is stochastic — a small batch can be clean by luck | the load-bearing assertion is that an **induced** no-task is detected and handled per OQ5; the observed zero is telemetry, not the gate |

⚠ **The pattern across all four holes is the same one the root-cause table names.** Each gate had a
mechanism that worked, aimed at the cases its author had in mind: the probe list, the constructor set,
the host-side config, the file count. None of them was wrong; all of them were pointed slightly
elsewhere. That is worth stating here because it is the reason this plan was reviewed twice.

### Step 0 — two probes, about $1

**V0b — do the named flags and env vars exist, and do they do anything?** Matrix: `--add-dir`,
`--exclude-dynamic-system-prompt-sections`, `--no-session-persistence`, `--setting-sources`,
`CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `--bare`,
`--permission-prompts`, `--permission-mode`, `--allowedTools`.
*Expected, with a real observable:* run a session in a scratch dir containing **both** a `CLAUDE.md`
**and** a `.git` with dirty state, with and without each candidate, and assert on the
presence/absence of the project-context and git-status sections in the trace. ⚠ **Normalize the trace
before matching** — a wrapped header will not match a pattern containing a literal space, and the
gate then certifies the exact thing it was built to detect (Plan A's Gate G defect).
*Already verified present on CLI 2.1.267:* all four original flags plus `--bare`,
`--permission-mode`, `--permission-prompts`. Unverified: the two `CLAUDE_CODE_DISABLE_*` names.
⚠ **Assert the candidate count, and assert the shipping argv.** Two ways this gate goes vacuous: a
matrix row gets dropped in a refactor and the remaining rows still pass, so the count is asserted;
and a flag that demonstrably works in a scratch CLI probe can still be **dropped by
`_stage_command`** on the way to production, so each surviving flag is asserted present in the argv
the Runner actually builds — not only in the probe that discovered it.
*Stop:* any name with no observable effect is **removed from the plan** — shipping an inert flag here
would be self-refuting. Also stop if a flag passes the probe and is absent from the shipping argv:
that is the inert-mechanism pattern, caught one layer earlier than usual.

**V0c — does a judge run in-container, under the shipping configuration, at what cost?** ⚠ **Through
the real topology**: the driver spawning a Task subagent, launched by the **same per-dispatch prefix
factory** production uses (1c). A hand-built `docker run` or a direct judge prompt measures a fixture
and tells us nothing about Phase 1c — and Phase 1c is where the review found the design could not
work. One claim,
`network_policy="open"` + `adc_path=None` + `CLAUDE_CODE_OAUTH_TOKEN`, **and**
`--permission-prompts none` + a non-bypass `--permission-mode` + `--allowedTools` in place of
`--dangerously-skip-permissions`. **Also test cwd = the read-only program snapshot** instead of a
separate working dir (2a's open item).
*Expected:* a valid verdict; an out-of-tree read **denied**, measured per layer so a pass says which
one held; per-claim wall-clock and cost against the $0.183 median — **this is OQ3's cost number**; the
in-container CLI version recorded.
*Pre-encoded forks:* the allowlist denies a tool the judge needs → widen once and re-run, **not** fall
back to bypass (the mount boundary is unaffected). The snapshot works as cwd → drop the separate
working dir. The CLI needs to write to cwd → keep it, and record write access as the reason.
*Stop:* container auth unresolved → halt the agentic control and report; do not improvise a credential
path. ⚠ It does **not** block the non-agentic seal proof — but it **does** block the judge actually
running inside the container, which is the seal. Phase 0 may land alone; **landing Phase 2 without
Phase 1 means landing without isolation**, and must be described that way.

### Step 1 — Phase 0 gates

**V1a (staging).** Dispatch the same claim twice. ⚠ Against `SarolRunner` directly, or
`CachingRunner(..., enable_cache=False)` — the cache is on by default and keys on
`(program_digest, input_ref, split)` (`dispatcher.py:306-320`), so a second dispatch returns the
cached artifacts **without dispatching** and the archive code never runs.
*Expected:* the second dispatch sees no pre-existing verdict; the first is intact under
`_superseded/`; a companion check confirms the archive fires on a genuine cache **miss**.
⚠ **Three more assertions the first draft left out:** archive names are **collision-proof** (two
attempts in the same second must not overwrite — a timestamp alone is not enough, so include the
attempt index); the **error sidecar** path is asserted absent too, not just the verdict path; and the
archive directory is **not inside the judge's readable mount**, or archiving a verdict hands the next
judge the very thing this plan removes.

**V1b (fail closed, and the failure reaches the optimizer — OQ5 resolved to fail-and-feed).** Spy
invoker returns exit 0, writes no verdict. *Expected, all four:* (1) the stale verdict on the
held-out path is **never read** (Phase 0a); (2) the batch does **not** silently score 0.0 across all
50 (the 2026-09-07 regression); (3) the failure is recorded under a **distinguishable
delivery-failure count** (keyed only on `UNREADABLE:`) and kept out of the mistake corpus; (4) the
iteration's outcome **surfaces that delivery failure to the optimizer** rather than a misleading
number. Also assert the discriminator is narrow: a malformed-but-present verdict stays
`invalid_output` and stays scored.
⚠ **Trace the seam end to end** — Runner record → batch status (`:1111-1122`) → Scorer coverage →
release breakdown → mistake corpus → optimizer-facing outcome — because a change that looks clean at
the Runner can break two layers down. It is cheap (spy invoker, no LLM calls).
*Stop:* the batch scores 0.0 (the 2026-09-07 regression reproduced), a stale verdict is read, a
present-but-malformed verdict gets reclassified as infrastructure, or the delivery failure never
reaches the optimizer.

**V1c (rendering).** Render for the full fixture set. *Expected:* zero unresolved template tokens.
⚠ **Not "zero shell metacharacters"** — the first draft's phrasing was not a coherent contract:
ordinary claim and evidence text legitimately contains `$`, `|`, backticks and quotes, and rejecting
them would refuse valid clinical text. The real property is that **no shell evaluation can occur**,
which holds because the prompt is passed as a single argv element — so assert *that* (one argv
element, no shell interpolation, no unresolved token), not the presence of characters; a missing slot raises `SLOT_UNRESOLVED:<slot>`; mismatches use
`validate_sarol`'s existing vocabulary; bytes byte-identical to the frozen prompt with slots
substituted, checked against **whichever manifest is live** — ⚠ **never pin a literal hash** (it moved
four times in one week; live value after Plan A is 10 entries at `7431a5bc98a9`), and the manifest
freezes from **git refs**, so a prompt edit must be committed before the freeze sees it.
⚠ **Scope limit (NF8):** this proves the **renderer** is correct. It cannot prove the shipped system
uses it, since the driver may rewrite the delivery text — **V1b** proves a broken delivery is caught.
A green V1c must not read as "delivery is guaranteed."

**V1d (the gate that detects a skipped gate).** Assert the engine block **ran**: adapter total ≥150
and `_import_engine()` succeeded. *Stop:* the adapter reports 32/32 — the silent-skip signature, not
a pass. Also make the skip print `SKIP`.

### Step 2 — Phase 1 gates: the containers

**V2a-seal — non-agentic, runs today, gates everything downstream.** ⚠ **The first draft's version
was not a complete proof, and this is the plan's centrepiece.** Probing a list of host paths only
shows those paths are absent; it says nothing about a **broad mount at a different container
target** — mount `$REPO` at `/extra` and every one of the probes still fails while the whole repo is
readable one directory over. The probe was aimed at the paths we thought of, which is the same defect
as every other finding in this plan.

So the gate asserts the **rendered mount set** before it probes anything:

1. **The set equals an exact allowlist**, compared as `(source, target, mode)` triples — not a subset
   check, not "contains", and the allowlist lives in the test, not in the code under test.
2. **No source is an ancestor of a forbidden path.** A mount of `$HOME` is not caught by comparing
   against `$HOME/.paper-trail/gold`; resolve every source and reject any that contains a forbidden
   entry in its subtree.
3. **Probe every rendered target**, not every host path we remembered — enumerate from the argv, so
   a mount nobody planned still gets probed.
4. **Then** probe the sentinel paths: a distinct sentinel planted in `iter/<n>/release_train.json`,
   `optimizer/findings/iter-1.md`, `optimizer/meta-learnings.md`, **`~/.paper-trail/gold/sarol-2024/…`**,
   and **`~/.paper-trail/benchmarks/…`**, each via a direct `docker run … cat`, reusing `run_probe` +
   `_build_common_fixture`.
5. **Two controls.** A **positive** one: the judge's own staging and spec root *are* readable in the
   same run, so a container that denies everything cannot pass as a seal. And a **negative** one:
   deliberately mount the repo at an unexpected target and assert the gate **FAILS** — without it,
   step 1 is untested and can be silently weakened to a subset check by anyone refactoring.

Also assert, as before: the deny list **exists, is non-empty, and holds the expected entries by name
and by count**; probe count equals list length; every sentinel probe fails `ENOENT`/`EACCES`.
⚠ **And assert the prefix came from production.** A standalone engine fixture proves the fixture. The
mount set under test must be the one the **production per-dispatch factory** rendered for a real
claim and a real materialised version — otherwise the gate certifies a code path the shipping system
does not take, which is the same defect as `optimizer_isolation_hash` being a literal string.
*Stop:* **any** sentinel readable, or the negative control passing → halt. Do not weaken the
assertion; report which mount granted it. This is the gate whose absence caused this plan.

**V2a-live — agentic, gated on V0c.** One real `claude -p` judge session in-container on one staged
claim. *Expected:* a valid verdict, proving the seal did not simply break the judge — **and a
non-null, readable `trace_ref`** (per 1d), because a containerized judge with no trace is a less
diagnosable instrument than the defective one it replaces.

**V2b — the permissive controls still pass.** `test_train_only_read_scope`
(`tests/test_isolation_negative_control.py:173`) and the six existing Docker negative controls stay
green. *Expected:* the whole smoke suite green with **0 skipped**, plus the new controls.
⚠ **Do not carry the historical "104" forward as the bar.** It was measured on another machine at
another SHA, and the review environment could not re-run it (`/var/run/docker.sock` denied there).
Record **this run's** numbers as the baseline: engine SHA, image digest, Docker version, full pytest
counts, zero skips — on the VM. (For reference, 104 was the *whole* suite; that file holds ~15
tests.) *Stop:* a regression in the edit-agent principal — this plan is additive to it.

**V2c — the refusal gate, at every construction site.** Construct the Runner with no prefix factory
and no opt-out sentinel. *Expected:* refuses at `__init__`, before any spend. **And assert the
inventory:** the count of direct `SarolRunner` constructions equals **21**, and each one is
classified as containerized or explicitly opted out — a source-level census in the selftest, so a new
ungated site added later fails the suite instead of running ungated. ⚠ Without the count assertion
this gate is green-by-absence: a refusal that applies to the sites we remembered is exactly what the
first draft shipped.
⚠ **One negative control per production entry point**, not one for the class: `build_components`,
the canary's pinning path, the baseline recut, and the CLI runner each get a case asserting they
refuse without a factory. A test-only fake invoker must stay possible **without** creating a
production-reachable bypass — if the same keyword can disable the boundary in production, the gate
is decoration. Also confirm the `CachingRunner` + `BudgetGuard` wrapping survives the containerized
path.

**V2d — one prefix per dispatch.** Two claims × two program versions in a single process.
*Expected:* four distinct prefixes; each dispatch's `--add-dir`, workdir, and any path in prompt text
resolve to **that** claim's staging and **that** version's snapshot; no host absolute path survives
anywhere in the rendered argv or prompt. *Stop:* any prefix reused across either axis, or any host
path reaching the container — a `/home/philadamson/...` string inside the container is a dispatch
that cannot complete and will read as a model failure.

**V2e — the trace survives containerization.** Run one containerized dispatch. *Expected:* a
`trace_ref` exists, points at a non-empty file, and its content is the session stream for **that**
claim (assert the claim id appears in it). *Stop:* `trace_ref` absent or empty — a containerized run
with no trace cannot be audited, which was how the stale-verdict contamination was found at all.

**V2f — the token is not in host argv or in the log.** Render a prefix with the credential set.
*Expected:* the token **value** appears nowhere in the rendered argv and nowhere in the wrapper's
recorded `meta.json`; the variable **name** does appear. *Stop:* the value appears anywhere on disk
or in a process listing. ⚠ Scope stated plainly: this does not test whether the session can read its
own token — it can.

**V2g — the optimizer's boundary.** Plant sentinels in the scorer module, `iter/`, the manifest, and
gold; run the optimizer's container over the per-run clone. *Expected:* every sentinel unreadable;
the optimizer's own editable subtree writable; edits appear in the clone after copy-back and **not**
in the source checkout. *Stop:* the scorer or the manifest is writable — that is the one boundary
Phil named as non-negotiable.

**V2h — the tool surface and egress, proved per layer.** ⚠ The gate the first draft did not have at
all, and the one covering the four threats a mount cannot reach. Inside the container, attempt each
of: read the staging tree (**must succeed** — the positive control), read a gold sentinel, run
`printenv`, run an arbitrary shell command, `WebFetch` a non-allowlisted host, and issue an outbound
request to one. *Expected:* each result attributed to **a named layer** — mount absence, tool
allowlist, network policy, or permission mode. *Stop:* any forbidden attempt succeeding; **or** every
attempt failing with no layer identified, which is a green that proves nothing — a broken container
and a sealed one look identical from outside.

**V2i — what the Task subagent inherits.** The judge **is** a Task subagent, so the driver's policy
has to reach it and nothing in the plan proved that. rad-eval removed `Agent` from its allowlist
precisely until inheritance was demonstrated. A purpose-built control: the driver spawns one subagent
that attempts (1) an allowed staging read, (2) a forbidden gold-sentinel read, (3) a forbidden write
to the scorer path, (4) one outbound request. *Expected:* (1) succeeds, (2)-(4) fail, each with its
layer named. *Stop:* any of (2)-(4) succeeding — the boundary holds for the driver and leaks one
level down, which is the shape of the leak that started this. ⚠ Also *stop* if (1) fails: a subagent
that cannot read staging cannot judge, and a run of all-failures would otherwise read as a pass.

**Recipe (this box).** Build the image first with the host CLI version
(`docker build --build-arg CLAUDE_CODE_VERSION=2.1.267`, per Phase 1g), record its **digest** for the
Phase 3 pin, then
`AGENTIC_LABEL_OPT=/home/philadamson/engine-82f547d ~/.local/bin/python3.13 -m pytest tests/test_isolation_negative_control.py`.

### Step 3 — Phase 2 gates: the layers inside

**V3a (the scope check), mirroring `val_isolation_problem`'s ~8 selftests.** *Expected:*
`working_checkout=REPO_ROOT` → refuses, naming the path; the version-addressed dir → passes; a dir containing
any one forbidden path → refuses, **one case per forbidden entry including the two absolute ones**,
asserted by length; a **negative control** where it must *not* fire, reusing `_raises_valueerror`.
*Stop:* it passes on `REPO_ROOT`, passes on a dir under `~/.paper-trail/`, or `build_components`
proceeds past a returned problem. **Also assert all seven `build_components` callers still work** —
and note the wider inventory is **V2c's** job, not this gate's: a scope predicate raised inside
`build_components` cannot see the 14 sites that never call it, and a green suite with
`run_baseline.py` silently bypassing is a false pass (OQ7).

**V3b (the working directory's contents).** *Expected:* the command file is present; **no `.git`**;
**no `CLAUDE.md` in it or any ancestor**; not under `~/.paper-trail/`; `missing_command_error()`
returns `None`; `command_path()` resolves inside it; a run with the command file removed still fails
up front with `NESTED_COMMAND_MISSING` (`adapter.py:2110-2130` — note that gate only runs when the
engine block is not skipped, so V1d gates it).
*Stop:* a `.git` or `CLAUDE.md` is reachable — the two channels that produced the observed leak.
⚠ **Add a byte assertion, per call:** the driver's bytes in cwd equal the **matching entry in that
version's materialised manifest**. An exact fileset with no `.git` and no `CLAUDE.md` is satisfied by
a single shared directory holding one correct-*looking* command file, so the structural assertions
alone cannot see the defect. **V3d** proves the behavioural half; this byte check proves the static
half. Do not let a green V3b stand in for either.

**V3d (the driver's bytes match the version being scored).** Two program versions whose
`sarol-eval-item.md` emits a distinct marker, dispatched in one process. *Expected:* each verdict
carries **its own** version's marker, and the cwd the judge saw resolves under that version's
snapshot. *Stop:* both verdicts carry the same marker — the release payload then attributes one
program's behaviour to another, silently, which is the failure this plan's measurement rests on not
having.

**V3c (invocation shape).** Assert on the built argv and the bound env. ⚠ **"`$REPO` absent" cannot
hold** — staging can resolve *under* `REPO_ROOT` (`adapter.py:559`; `.gitignore` carries
`/experiments/*/staging/`), so the repo path may be a prefix. Restate as: **no `--add-dir` entry
equals or is an ancestor of `$REPO`**, **and** the entry set is **exactly**
`{<staging>/<claim_id>, <materialized spec_root>}`.
*Expected, env side:* only the allowlist; `PAPER_TRAIL_GOLD_DIR` absent from the child even when set
in the parent; `CLAUDE_CONFIG_DIR` differs between two invocations. ⚠ **State how the gate observes a
bound env** — with `functools.partial` the 3-arg spies see only `(cmd, cwd, timeout)`, so expose the
resolved env as a Runner attribute, or V3c is unwritable.
⚠ **Compare key sets and redacted values only, and keep the host env separate from the container
env.** They are different objects with different rules: the host `Popen` environment is sanitized;
the container environment is the allowlist. And a failing assertion that prints `.keywords` would
dump the OAuth token into test output — a gate that leaks the secret it guards. Assert on key sets
and on redacted values; never print a value.

### Step 4 — Phase 3 gate

**V4 (the pin).** Run with the computed configuration diverging from the pin committed in
`runtime_pins`. *Expected:* refuses **before spending**; the literal `'sarol-2024'` no longer
satisfies it; changing any component changes the hash; the documented re-pin path lands cleanly; the
pin is read from **committed bytes**, not the worktree; **and a re-freeze leaves it intact** —
verified **behaviourally**, not by reading source: copy the manifest to a tmp path, point
`freeze_program_v0.py:33`'s `MANIFEST` global at the copy, run `cmd_write` against the real refs,
assert `runtime_pins` byte-identical before and after. ⚠ Asserting "`cmd_write` copies `old`" by
inspecting source breaks on a rename and is itself green-by-absence-prone.
⚠ **Cover the container components explicitly**, one case each: a different image **digest** at the
same tag, a changed mount triple, a changed mount **role**, a different network policy, a different
container user or workdir, a changed `--allowedTools` set, a changed trace destination. The first
draft hashed only host-side properties, so a container swapped underneath it left the hash unmoved —
the pin would then certify a configuration it never saw. Also assert the env allowlist contributes
**names only**: rotating the token must **not** move the hash, or every credential refresh reads as a
configuration change and the gate gets disabled.
*Stop:* the run proceeds; the hash is stable across any one of those changes; or the gate compares
against what the release builder would stamp — the tautology this phase exists to avoid.

### Step 5 — end to end, gated on Step 2

**V5.** One real iteration on a small TRAIN batch under the full stack. ⚠ **"Zero no-task sessions"
is telemetry, not a gate** — at a ~2% rate a small batch is clean by luck roughly a third of the
time, so a green would prove nothing about the handling path. The load-bearing criterion is that an
**induced** no-task is detected and handled per OQ5; record the observed count beside it.
*Expected:* an induced no-task detected and handled; zero stale-verdict reads; infrastructure failures and `n_invalid` counted **separately**; a
non-zero metric despite any infra failure; per-claim cost within the V0c envelope; **in-container CLI
version == host version**, recorded in the run manifest.
⚠ **Record the metric, and do not read a drop as a regression.** Removing 61% eval contamination
should push the held-out number **down** — a judge that can no longer read the previous iteration's
verdict for the same claim loses its self-consistency crutch. A lower number is the **expected
signature of the fix working**. Stated because the first person to see it fall is otherwise likely to
revert.
Also expected: **every dispatch has a `trace_ref`** (V2e at run scale — the count of traces equals
the count of dispatches, retries included); **retries are counted and reported** separately from
claims, so the session count and the claim count reconcile; the recorded **image digest** matches the
image that ran.
*Stop:* any no-task session silently scored or read from a stale verdict (OQ5 fail-and-feed means it
must surface to the optimizer instead), any dispatch with no trace, cost >25% over the V0c envelope,
or a version/digest mismatch.

### Anticipated forks

- **V0c's deny-by-default layer blocks a tool the judge needs** → widen the allowlist once and re-run;
  do not fall back to bypass, the container boundary is unaffected.
- **V0c's cost comes back high** → report the number and the per-run total. Information for Phil, not
  a decision to skip the container (OQ3).
- **V0c blocked on container auth** → run V2a-seal anyway (non-agentic, still proves the mount set)
  and file V2a-live with auth as its single named blocker. Phase 0 lands regardless. ⚠ Do not land
  Phase 2 and call the isolation done.
- **V0b finds an inert env var** → drop it and rely on 2a's root, which §2c's re-ranking says was the
  stronger channel anyway; note the residual explicitly.
- **V0b shows `--bare` covers the row but omits `Task`** → `--bare` and OQ1 option (i) are mutually
  exclusive; OQ1 decides and the loser is dropped explicitly.
- **A delivery failure fires mid-run (OQ5 fail-and-feed)** → the iteration returns the failure to the
  optimizer rather than a score; record the delivery-failure count in the release breakdown so it is
  never read as a program-quality drop.
- **V5's number drops** → expected, not a regression. Record the new baseline as the honest one.
- **V2a-seal leaks** → halt at Step 2 under any schedule pressure.
- **V2a-seal's mount-set allowlist keeps needing entries** → each addition is a boundary widening and
  gets a written reason next to it; three or more means the mount set was designed wrong, so re-derive
  it from what the judge reads rather than appending.
- **V2c's census finds more than 21 construction sites** → the count moved under us; update the
  assertion *and* say which sites appeared, because a new ungated judge is the defect this plan is
  about.
- **V2f shows the by-name env form is not available on the pinned engine revision** → the engine
  change is a prerequisite (1b), so land it upstream first; do **not** ship the `-e KEY=VALUE` form
  with a note to fix later, which is how `optimizer_isolation_hash` became a literal string.
- **V2g finds the optimizer needs write access to something in the deny set** → name the file and ask,
  rather than widening. The scorer and the manifest are not negotiable (Phil); anything else is a
  design question about what the program *is*.
- **V2i shows the Task subagent does not inherit the driver's policy** → this is a halt, not a
  widening: follow rad-eval and drop the subagent path until inheritance is demonstrated, which makes
  OQ1 option (ii) — eliminate the driver and apply every flag to the judge directly — the live
  option rather than the deferred one.
- **V2h cannot attribute a failure to a layer** → treat as red. Re-run with one layer relaxed at a
  time until each result has an owner; an unattributed all-fail is indistinguishable from a container
  that never started.
- **V3d shows the CLI cannot run with cwd on a read-only snapshot** → per-dispatch copy keyed by
  program version; the version-addressing requirement is unchanged either way.

---

## Landing & cleanup

**Branch.** `feat/optimizer-isolation-protocol`, cut from Plan A's tip — **`f02d761`** as of
2026-09-13, five commits past the `94a376f` this plan's citations were taken against (not
`sarol-optimizer-concurrent`'s older `591eb02`), in its own worktree `~/paper-trail-isolation`. The
primary checkout holds `meta-learnings.md` modified plus five untracked `findings/iter-*.md` with no
blob to restore, and a sibling session has been live in `~/paper-trail-planA` — so implementation does
not happen in place. Lands into `sarol-optimizer-concurrent`, **not** `main` (that branch is 163 ahead
/ 40 behind main; reconciling is out of scope).

⚠ **Merge hazard.** `meta-learnings.md` is modified here (225 lines, the 2026-09-09 sheet) and reset
to a 57-line stub on Plan A's branch. That conflicts on rebase. Do **not** `git checkout`,
`reset --hard`, or `stash` that file: this copy holds content that exists nowhere else, and the five
untracked findings beside it have **no blob to restore**.

**Landing gate.** `/read-plan` sign-off with **OQ1–OQ9 resolved** (OQ9 first — it sets the scope); the five findings archived (a
Phase 4 precondition and the only copy); Step 0's probes run and recorded; **V2a-seal green,
including its negative control** — a land with either red is not a land; **V2c's 21-site census
green**, so no ungated judge ships; **V2d and V3d green**, because a reused prefix or a shared cwd
mis-attributes one program's behaviour to another and nothing downstream would show it; **V2h and
V2i green with every result attributed to a layer**, since they cover the four threats the mount set
cannot; **V2e green**, so a containerized run is still auditable; the credential-by-name engine
change **landed upstream first** (Phase 1b is a prerequisite, not a follow-up); then `/review-implementation` → `/commit-review` → `/phi-vet`. No PHI is
expected anywhere here (claim ids and sentinel strings only), but the repo is gated. ✅ Codex credits
are restored, and this is a **rewrite** of a plan whose only review covered a different structure — a
cross-model pass is worth running.

**Merge sequence.** Plan A finished first, so: this plan rebases onto its tip, implements against a
10-entry manifest (`combined_hash 7431a5bc98a9`) and Plan A's three new preflight gates, then lands
after it. Plan B stays parked behind both, and must not start while Gate F's `KNOWN_DEFERRED` holds
six live contradictions in the stages it would enable. ⚠ Adding or removing a manifest entry breaks
five count/scope selftests (`adapter.py:1668`, `:1773` and its retrieval-scope assertion;
`profiles.py:262` and its retrieval-scope assertion) — update them individually.

**Contract owed to Plan A's baseline recut.** It must run on the **post-isolation** instrument: 61% of
iter-5 judges read a stale verdict, so a baseline measured today measures the contamination. The
landing order satisfies this. ⚠ It also depends on whatever OQ7 decides (OQ5 is settled:
fail-and-feed, so the recut runs on the fail-and-feed instrument).

**Three new gates this plan must not break** (Plan A's, all in the preflight, all green at
Plan A's tip): the **consistency gate** (`check_orchestrator_consistency.py`, 16 checks — trivially
green now OQ5 resolved to fail-and-feed, since there is no retry to keep out of driver-facing prose;
its `KNOWN_DEFERRED` holds six contradictions that go live if
`profiles.IMPLEMENTED_STAGES` grows, which this plan must not touch); the **prompt-hygiene gate**
(`check_prompt_hygiene.py`, 12 files — ⚠ this plan's inline `⚠` convention is fine in `docs/`, which
is not swept, but must never be carried into a prompt file; and *describe* a removed instruction,
never reproduce it, since a restated imperative stays actionable to a model that skims); and the
**fresh-run gate** (`check_run_scope.py` — ⚠ it will refuse in this checkout, which holds five
`findings/iter-*.md`; run `--archive <run-id>` first. **Phase 4 retires it.** ⚠ It resolves paths from
its own location, so running Plan A's copy from its worktree passes and says nothing about this tree).

**Cleanup on land.** `/land` prunes the branch (local + remote) and the worktree, marks this plan
`Status: Completed`, updates its `docs/plans/README.md` row, prunes the `NEXT.md` entry, and retires
the scratch sentinel fixtures and any per-run working dirs.

**Owed to the engine, and owed by us** — see *What is ours, and what the engine still owes*. ⚠ The
first draft had this backwards: it named "thread a materialized path into `agent.run`" as the engine's
load-bearing debt, but that is **already done** (`loop.py:192`, `:426-431`, with its own test), and
the consumer-side agent class is **ours**. What is genuinely owed upstream is smaller and named in
that section: the by-name credential form (a **prerequisite** of Phase 1b, not a follow-up), audit
rows from container sessions, permission-hook wiring, and validating the isolation label. The half of
isolation this plan adds that nobody has built anywhere is the **judge/dispatcher container** — crc's
umbrella plan designed it, no repo shipped it. Everything else here is re-aiming a built mechanism,
which is the whole reason the shared package exists.
Findings §4/§8 get promoted to `docs/journal/` on land, per `NEXT.md`.
