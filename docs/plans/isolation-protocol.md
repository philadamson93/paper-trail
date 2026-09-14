Reference: docs/claude_ops.md

# The isolation protocol — putting the judge inside the shared substrate

**Status: Draft** (rewritten 2026-09-11 against the shared engine's landed substrate; Codex review
applied 2026-09-13; Phil's explain-plan feedback applied 2026-09-14) · **Reviewed: No**
⚠ **Code-audit round, 2026-09-14 (four parallel agents against current code, both repos pulled).**
It found ~20 corrections, several load-bearing, and every one is applied below. The architecture
survived; **the inventory of work did not** — it is smaller than this plan said. The four that change
what gets built: the refusal census is **22 sites, of which only 3 ship** (not "21, mostly in
`adapter.py`"); `--dangerously-skip-permissions` is set by the **shared wrapper**, not by us, so
replacing it is an upstream prerequisite; the engine has **just landed** the feed-the-optimizer
channel OQ5 needs; and the armed run this plan cites as proof reports a safety number that is
**zero by construction**. Engine citations are now stamped with the SHA they were read at
(`c2dd0b3`), because they have gone stale twice.
**All nine open questions are now resolved** (2026-09-14). Three of them cut scope rather than adding
it: the driver session is eliminated (OQ1), the per-run git clone is replaced by a run-start reset
(OQ9), and the tag-scoped settings file is retired (OQ6). One adds a small engine change that the
plan previously ruled out — per-iteration held-out staging (OQ2). *What we are building*, below, is
the concrete list Phil asked for and is the section to read if you read only one.
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
judge's trace (Phase 1d); the refusal must cover **21** construction sites, not 7 (Phase 1f — ⚠ the
2026-09-14 audit re-counted this as **22**, see NF11); the pin
hashed only host-side properties (Phase 3); Phase 4 named a function instead of an implementation;
and V2a-seal — the plan's centrepiece — could be defeated by a broad mount at an unexpected target.
A separate Codex adjudication chose the mechanism order (**containers first, hooks second**) at
`docs/plans/reviews/isolation-mechanism-options-feedback.md`.
**Findings this is built on — and the evidence is now inlined, not cited.**
`docs/session/2026-09-09-optimizer-loop-and-isolation-findings.md` §4 (474 lines, sha256 `a7f17c32…`).

⚠ **Provenance incident, 2026-09-14 — read this, because it explains a real defect in this plan.**
That findings doc lives under `docs/session/`, which is **git-ignored by policy** (`.gitignore:56`,
*"so per-session resume notes cannot be swept into a commit"*; `claude_ops.md` mandates it). So it
never travelled by git, and for most of this plan's life it **did not exist on the authoring machine
at all** — while the plan cited it **23 times** and keyed **seven phase steps** to its `§4g` item
numbers. Every one of those citations was unverifiable. It was recovered off the VM on 2026-09-14 and
now also sits at `/mnt/su-vista-uscentral1/session-docs/paper-trail/2026-09-14/`.

✅ **The fix is not a better citation — it is to stop depending on the file.** §4g's nine-item fix
list is the thing this plan's steps are derived from, so it is reproduced **verbatim** below and the
steps point here. A plan whose evidence base is git-ignored has no evidence base.

> **§4g. The fix (mirror what already works)** — verbatim from the findings doc
> 1. `inner_scope_problem(working_checkout, {iter/, optimizer/findings/, meta-learnings.md})` wired into `run_optimization`'s preflight at exactly the line where `val_isolation_problem` already sits (`dispatcher.py:549-551`). Fail closed.
> 2. Pass a **minimal `working_checkout`** — already a constructor parameter, already exercised with `empty_checkout` at `adapter.py:2118`; production just passes the default.
> 3. Restore Rule 3's stack on judge invocations (`--add-dir` scope, `CLAUDE_CONFIG_DIR`, `env -i`, `--exclude-dynamic-system-prompt-sections`, `--no-session-persistence`).
> 4. **Render the dispatch prompt in Python**, not via shell interpolation into an LLM — kills both §3.2 bugs and the §3.3 fabrications at the root.
> 5. Fail closed on no-task: no verdict written ⇒ `infra_error`, never a scored data point; and never a session that surveys its working directory.
> 6. **Per-iteration staging** (or wipe between iterations) — kills the 61% contamination.
> 7. Make `optimizer_isolation_hash` load-bearing; refuse to run on an unverified value.
> 8. Engine: model **N principals**, not one; add a per-principal mount manifest with an explicit **deny** list; add the negative control that plants a sentinel in `release_train.json` and asserts a judge **cannot** read it — the mirror image of the permissive read test that shipped.
> 9. Wire the Docker substrate for real (consumer-side `DockerAgent`/`DockerRunner`), per Phil: *"we DO want this running in docker, that's our whole isolation engine and intentional."*

⚠ **Two places this plan had drifted from its own source, both found only once the file came back:**

- **Item 8 said "model N principals, not one" and "a *per-principal* mount manifest."** This plan
  collapsed that into a fixed two — *the judge* and *the optimizer* — and then derived **one** mount
  set. That is exactly the error Phil corrected on 2026-09-14 (*"we have the agentic program and the
  optimizer; judge is one PART of the program"*), and the per-stage mount-set gap in *Who is who* is
  literally what "per-principal mount manifest" was asking for. ⚠ Note also that item 8 scopes this as
  **engine** work; this plan made it consumer work (see OQ4).
- **Item 6 said "per-iteration staging."** This plan recommended a consumer-side archive instead and
  called the engine change too costly. Phil's OQ2 ruling restored the source finding — without being
  able to read the source.

✅ Everything else checks out: all 23 citations resolve, and §4g items 1-7 and 9 map cleanly onto
Phases 2b, 2a, 2c, 0c, 0b, 0a, 3 and 1c respectively. ⚠ One evolution, not a drift: item 2 says a
**minimal** working checkout; Phase 2a makes it **version-addressed**, which is a later and correct
refinement once the driver became optimizer-editable. Marked so nobody reads it as a misquote.
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
| **Per-call tool policy** (hooks) | deferred by Phil 2026-07-22; `--allowedTools` is coarser than a hook that fails closed per call. ⚠ On the **optimizer's** path this is a live gap, not a theoretical one — the engine's own egress plan records that rad-eval keeps `WebFetch` only because a `PreToolUse` hook denies every URL, and *"Docker mode has no hook wiring at all"* (`2026-07-30-docker-vertex-only-egress-allowlist.md:123`). On the **judge's** path it is redundant once `Bash`/`WebFetch`/`WebSearch` are off the allowlist — there is no per-call decision left to make (**OQ6**) | the second landing |
| Egress beyond the **host allowlist** | an allowlisted host can still receive data | the allowlist narrows the surface, it does not close it |

⚠ The pattern to avoid here is the one in the root-cause table: a residual that stops being written
down becomes a residual nobody remembers accepting.

## Who is who — the two principals

⚠ **Rewritten 2026-09-14 on Phil's correction. This is a scoping fix, not a naming preference.**
An earlier version called the two principals *the optimizer* and *the judge*. Phil: *"we have the
agentic program (which goes in a container here) and the optimizer. Judge is confusing because it's
one PART of the program."* **Correct — and the mis-naming had already bitten the design**, see the
three consequences below.

| | **The agentic program** | **The optimizer** |
|---|---|---|
| What it is | the labelling pipeline itself — **one session per stage, per claim** | the agent that **edits** the program between iterations |
| How often | `for stage in self.profile.stages` (`adapter.py:866`) × every claim. Today **1 × 561**; under the `agentic` profile **3 × 561** | **one session per iteration**, ~5 in a run (`adapter.py:360`: *"~113 an iteration, against the optimizer's one"*) |
| Must never **read** | **gold labels**, the benchmark tree, the optimizer's findings and hypothesis log | — |
| Must never **write** | — | the scorer, gold, `iter/`, the manifest — it would be marking its own homework |
| Containerized today | ❌ **no. This plan adds it.** Nobody has built one, anywhere | ✅ built and armed-run — **in rad-eval**; ❌ not here |

**The stages, and why "judge" is the wrong name for the boundary.**
`ALL_STAGES = ("extractor", "adjudicator", "verifier")` (`profiles.py:57`). The `retrieval` profile —
Phase 1, the only runnable one today — sets `stages=("adjudicator",)`, so **the program currently
happens to be exactly one stage**, which is why "the judge" and "the program" have looked like the
same thing. They are not. The landed `agentic` profile sets `stages=ALL_STAGES` — *"three sessions per
claim"* — of which the adjudicator is one. ⇒ **Naming the boundary after the judge bakes in a Phase-1
accident.** The convention from here:

- **the program** — the principal that gets the container, whatever stages the profile runs.
- **a program stage** / **the adjudicator stage** — when one specific stage is meant.
- **judge** — acceptable as the *role* of the adjudicator stage; the code uses it that way
  (`JUDGE_SCOPE`, and the selftest `("retrieval runs the judge alone", RETRIEVAL.stages ==
  ("adjudicator",))`, `profiles.py:266`). ⚠ **Never for the container or the mount set.**

⚠ **Three consequences the "judge container" framing hid. These are design changes, not wording:**

1. **The boundary is per `(stage, claim, version)`, not per `(claim, version)`.** The dispatch loop is
   `for stage in self.profile.stages:` (`adapter.py:866`), and `_stage_command(stage, claim,
   materialized_path)` (`:700`) already takes the stage. **Phase 1c's prefix factory must key on it
   too** — as written it keys on the claim and the materialised path only.
2. **Mount sets differ per stage, and this plan only ever derived the adjudicator's.** The extractor
   produces evidence from the source (`evidence_producer="extractor"`, `source_mode="pdf"`), so it
   needs the paper mounted; the adjudicator reads the finished evidence envelope and **must not** see
   the paper. Under `retrieval` the evidence is produced by ordinary Python beforehand
   (`evidence_producer="bm25"`), which is the only reason one mount set has sufficed so far.
3. **Containerization cost triples when Phase 2 runs.** V0c's per-session figure is measured against 1
   stage/claim today and becomes 3 under `agentic`. Report it per **stage-dispatch**, not per claim.

⚠ **Neither principal is the *scorer*.** `SarolScorer` is deterministic Python making zero model
calls; it compares verdicts to gold and sits **outside both containers**. Never an agent, never
containerized. Where this plan protects "the scorer" it means that code and the gold it reads.

⚠ **Known debt from this rename:** the body below still says *judge* ~120 times, usually meaning *the
adjudicator stage* and occasionally *the program*. The definitions here govern; a consistency pass is
owed and is listed in *Landing & cleanup*.


## What we are building

Added 2026-09-14 because Phil asked the question this plan was not answering: *"we're discussing these
things, but what are we building concretely?"* Twelve items. Everything below this section is the
reasoning behind one of them; if the reasoning and this list ever disagree, this list is what a fresh
session should build, and the disagreement is a defect to fix here.

| # | What | Where | Phase |
|---|---|---|---|
| 1 | **Pin the engine dependency that already exists** — ⚠ the dependency is live (our dispatcher drives its loop, our adapter implements its four protocols); what is missing is the **pin**. paper-trail has **no packaging file of any kind**, and resolves the engine by injecting a hardcoded home path onto `sys.path` (`adapter.py:102`, `:117-118`) — duplicated in `scripts/materialize_smoke.py:39`. So a run binds to whatever that tree holds at that moment. Copy rad-eval's shape: a git **revision** under `[tool.uv.sources]` (it pins `rev = "3bbe6c4"`), which means **creating** our first `pyproject.toml` | `pyproject.toml` | 1a |
| 2 | **The program's container**, built **per stage-dispatch** by a factory owned by `SarolRunner.process(claim)` — keyed on `(stage, claim, version)`, ⚠ **not** on the claim alone. Adjudicator-stage mount set: claim staging (rw), materialised spec root (ro), the program snapshot as cwd (ro), a trace dir (rw). Nothing else — `iter/`, `optimizer/findings/`, `meta-learnings.md`, `~/.paper-trail/gold`, `~/.paper-trail/benchmarks` denied by absence. ⚠ The extractor and verifier stages need **their own** mount sets when Phase 2 runs; only the adjudicator's is derived here | `optimizer/adapter.py`, `optimizer/isolation.py` | 1b, 1c |
| 3 | **The optimizer's container**, modelled on rad-eval's `docker_agent.py`: temp writable staging, copy-back into the live tree, and the scorer / gold / `iter/` / manifest **absent from the mount set** — so "the optimizer cannot edit the scorer" holds by construction | `optimizer/isolation.py` | 1e |
| 4 | **A deterministic dispatcher in Python** — reads the frozen prompt from the driver file, fills slots from `ledger/evidence/<claim_id>.json` + `staging_info.json`, refuses on an unresolved slot, and invokes the judge **directly**. No driver *session*, no `Task` subagent | new `optimizer/dispatch_prompt.py` | 0c, **OQ1** |
| 5 | **One refusal locus** — `SarolRunner.__init__` raises absent an explicit prefix factory. ⚠ **22 sites, not 21**, and it must cover three reach-paths (`build_components`, direct construction, and a pre-built `components=` dict that skips the gate). ✅ Only **3 ship**; the other 19 are selftests, and `canary.py` already accepts an injected runner. Offline tests opt out with an **injected fake prefix**, never a boolean | `optimizer/adapter.py`, `dispatcher.py`, `canary.py`, `scripts/run_baseline.py` | 1f, **NF11**, **OQ7** |
| 6 | **The isolation module** — scope predicate, both mount-set builders, the canonical host→container path map, the env allowlist, the version-addressed cwd builder, the configuration hash. ⚠ Shaped so the boundary machinery lifts into the shared engine for crc; only the mount *contents* are ours | new `optimizer/isolation.py` | 2a, 2b, 3, **OQ4** |
| 7 | **Trace persistence** — the streamed session JSON written beside the verdict as `trace_ref`, because `find_transcript` globs the *host's* `~/.claude/projects` and goes blind in a container | `optimizer/adapter.py` | 1d |
| 8 | **Per-iteration held-out staging** — `val_inputs` accepts `Callable[[int], RunInputs]`, mirroring `train_inputs` in the same signature; the Runner asserts the live verdict path is absent before dispatch | `engine/loop.py` (upstream), `optimizer/adapter.py` | 0a, **OQ2** |
| 9 | **Fail-and-feed on a no-verdict dispatch** — a distinguishable delivery-failure count keyed **only** on `UNREADABLE:`, handed to the engine's **newly-landed** stop-reason + partial-run channel (`82f547d`) rather than a new one, never scored as program quality and never summed into the mistake corpus | `optimizer/adapter.py` | 0b, **OQ5** |
| 10 | **A configuration pin under `runtime_pins`** covering image **digest**, the rendered mount triples with roles, network policy, egress allowlist and session flags — read from `git show HEAD:<manifest>`, not the worktree | `manifest.json`, `optimizer/isolation.py` | 3 |
| 11 | **A run-start reset** — archive `meta-learnings.md`, the five `findings/iter-*.md` and `iter/` to the run archive, then assert absent; the VM runner mints the run id. ⚠ **Not** a per-run git clone (**OQ9**) | `run_hillclimb_vm.sh`, `optimizer/isolation.py` | 4 |
| 12 | **The sentinel negative control** — sentinels planted in gold, the benchmark tree, `iter/` and the optimizer's findings; a judge must **fail** to read each, and the control has a negative control of its own | `isolation/negative_control.py` + tests (upstream) | 1g |

**Upstream, in one line:** four small files (by-name credential env, the generic seal control, its test, the CLI re-pin), **plus** one backward-compatible type widening in `engine/loop.py` for item 8, **plus** making `--dangerously-skip-permissions` a caller choice in `engine/claude_wrapper.py:130` — currently unconditional, so item 2's deny-by-default layer does not exist until it lands. That last one corrects this plan's earlier claim of *"no change to `engine/`"* — see **OQ8**'s answer for why it is still small.

**What we are deliberately not building** is its own section (*Deliberately out of scope*), and three things left it on 2026-09-14: the driver **session** (item 4 replaces it), the per-run **git clone** and `optimizer/run_clone.py` (item 11 replaces it), and the tag-scoped **settings file** (**OQ6** retires it).

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

⚠ **Re-verified 2026-09-14 against engine `main` @ `c2dd0b3`** — three commits past the `82f547d`
this repo pins, and the line numbers below moved again. Cite the SHA with the line, always.
Two engine plans, both **Completed**:
`2026-07-22-isolation-docker-substrate.md` (landed `de07032`, **VM smoke 104 passed / 0 skipped** —
a real VM run, and the 0-skip is the pass signal) and `2026-08-10-optional-edit-agent-mounts.md`
(landed `dcefe1e`). ⚠ **The second citation was misleading and is corrected here.** Earlier drafts
quoted it as "212 passed". The real figure is **212 passed / 15 skipped, on the Mac — and the 15
skips are the Docker tests.** That plan had **no VM smoke at all** ("every phase was Mac-local"), and
its own text concedes the writable-mount ownership check is *"on MODE BITS only … a proxy for the
property, not the property"*, with cross-uid proof deferred to crc. So the mount plumbing this plan
builds on is proven by construction and by unit test, **not** by a container run. ⚠ Relatedly: the
engine's negative-control suite has **not been re-verified since a 2026-08-21 refactor** — the last
real-Docker verification is 2026-08-05, before it. Quoting a pass count from a suite whose last real
run predates its own refactor is the green-by-absence rule applied to our evidence, so **V2a-seal
re-runs it rather than citing it.**

⚠ **Two capabilities landed upstream on 2026-09-14, after this plan was written, and both retire work
it specified.** See Phase 0b (OQ5) and Phase 0a (OQ2):

| Landed | What it gives us |
|---|---|
| `82f547d` **LoopStop hardening** | a stop now carries a machine-readable `reason` (`loop.py:63`, categories incl. `agent_session_failed`, `probe_validation_failed`) **and the partial run comes out with it** — the iteration loop is wrapped so a mid-run stop is enriched for reporting, never swallowed (`:544-558`), and the just-committed version is excluded from the reported frontier as untrustworthy. Probe scoring moved inside the validation block precisely so *"a judge that emits a malformed verdict must become a controlled stop, not an uncaught crash."* ⇒ **this is OQ5's feed-the-optimizer channel; do not build a second one.** |
| `ee26d80` **version-addressed manifest loader** | `manifest_for_version: Callable[[str], ProgramManifest] \| None` (`loop.py:217`), resolved per SHA and **failing closed** — never falls back to a stale entry set. ⇒ a second precedent for OQ2's per-iteration callable, in the same file. |

| Capability | Where | What it means for us |
|---|---|---|
| Container image | `isolation/Dockerfile` | non-root user, pinned CLI, `git`+`curl` guaranteed present so a probe failure can't be mistaken for a seal |
| Mount rendering | `isolation/docker_prefix.py::build_docker_cmd_prefix` (`:444-464`) | generic `extra_ro_mounts`, `writable_mounts`, `workdir`, `env`, `container_user`, `adc_path` — **the judge's mount set is expressible today with zero engine diff** |
| Plural editable set | `EditAgentMounts.editable_files` (`:96-112`) | went plural **for paper-trail by name**: its review found *"paper-trail's optimizable program is a five-file Markdown globset a singular `editable_file_rel` cannot express"*, and Phil's recorded decision was *"paper-trail is a future consumer and the shape is designed for it"* |
| Network profiles | `isolation/open_profile.py:68-72` | `network_policy="open"` + `adc_path=None` + `CLAUDE_CODE_OAUTH_TOKEN` — paper-trail's documented answer |
| Negative-control harness | `isolation/negative_control.py` (`run_probe` `:266`, fixture `:102`), `docker_available()` `:44`; 15 tests in `tests/test_isolation_negative_control.py`, all VM-only via `skipif` | a direct `docker run … <probe>` is decisive **for the path it probes** — ⚠ not for the seal, since a broad mount at an unexpected target defeats a path list (see V2a-seal). ⚠ **And it does not cover read denial at all, which strengthens 1g rather than weakening it.** Verified 2026-09-14: `test_sealed_file_is_unreachable` (`:85`) asserts `test ! -e` — the file **is not in the container namespace**, which proves non-mounting, not that a reachable path cannot be read. And `test_train_only_read_scope` (`:173`), the one test whose *name* promises read scoping, is a **positive** control asserting `returncode == 0` on both probes. So across 15 negative controls **nothing asserts that a reachable-but-forbidden path fails to open.** That is exactly the sentinel this plan adds, and it is now evidenced rather than claimed. |
| Materialised path threading | `engine/loop.py:192`, `:426-431` + `tests/test_materialized_path_threading.py` | ✅ **already done** — the per-iteration snapshot path reaches `agent.run`. ⚠ The engine README saying otherwise is six weeks stale; the first draft cited it over code |
| A built consumer-side container agent | rad-eval `src/optimizer_loop/docker_agent.py` (198 lines, on `main`, armed run 2026-08-05, $4.13) | the pattern to copy for **both** principals: prefix delegated wholly to the engine's `build_docker_cmd_prefix` (it builds no docker flags itself), fresh temp writable staging, copy-back into the live tree, reduced tool set (`Read, Write, Edit, Bash` — `WebFetch` dropped for container mode specifically). ⚠ **Correction, 2026-09-14: the "drop the chown" advice was about code that is not there.** `docker_agent.py` contains **no chown** — two `chmod 0o666` calls under a `0700` temp root, nothing else. The `chown -R` belongs to the **non-Docker sudo path** (`scripts/provision_loop_clone.py:123-128`), which Docker mode explicitly retires: *"the container's own non-root user makes the optimizer OS account/sudo unnecessary."* The 2026-08-05 run used a clone owned by the ordinary user. ✅ The conclusion still holds — the boundary **is** the mount set — but for the reason that only two files are mounted `:rw`, not because ownership was worked around. ⚠ **Two real defects not to copy:** it never cleans up `staging_root` (no `rmtree`, no `finally`), so every iteration leaks a temp dir holding the edited program; and see the `denied=0` row in the root-cause table. |
| Read-only frozen checkout | `engine/materialize.py:100-107` | `.git`-free, chmod'd read-only **files and directories** — no git-history channel, nothing writable |
| Injection seam | `engine/claude_wrapper.py::run(cmd_prefix=…, extra_env=…)` | Docker slots in as a `cmd_prefix`, exactly parallel to rad-eval's `sudo -u optimizer env …`. No wrapper change |
| Edit-artifact contract | substrate plan, item 3 | frozen tree read-only; *more-specific* writable mounts overlay only the editable files; harness copies out before and back after, then commits |
| Tool-policy decision logic | `engine/policy.py` | tested `evaluate_read`/`evaluate_bash`/`evaluate_tool`, deliberately not wired to a hook |
| ~~Per-run clone precedent~~ ⚠ **not adopted** | rad-eval `src/optimizer_loop/run_artifacts.py::default_loop_clone(run_id)` | *"two run-ids → two independent `.git` clones → the working tree, `iter/`, the `program-v*` tag namespace, and the in-clone audit ledger all isolate for free"* — ⚠ **"two run-ids" is the operative phrase, and paper-trail never has two at once (OQ9).** Kept in the table because the *tag namespace* line names the one thing the reset does not cover; see Phase 4 |

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
audit rows from container sessions, the isolation-label check, the bucket-mode
storage. (⚠ The per-run clone was on this list until **OQ9** removed it from the plan entirely; crc
may still want one, which is a question for crc.) So for each piece the real question is **modularity, not ownership**: does it belong in the
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
2. **A *pinned* engine dependency.** ⚠ **Corrected 2026-09-14 — the earlier claim here ("paper-trail
   has none — two prose mentions") was wrong twice over.** `agentic-label-opt` is a mature repo (57
   commits, 19 modules under `engine/` + `isolation/`, 17 test files, 4 Completed plans), and
   paper-trail **already depends on it at runtime**: `dispatcher.py` drives its `run_loop`,
   `adapter.py` implements its four `TaskAdapter` protocols, and 8 non-doc files reference it. What is
   missing is **version pinning**, not the dependency and not the repo. paper-trail has **no packaging
   file of any kind** (no `pyproject.toml`, no `requirements.txt`, no lockfile) and resolves the engine
   by `sys.path` injection from an absolute home-directory path —
   `DEFAULT_ENGINE = ~/Documents/Misc/Projects/agentic-label-opt`, overridable by `$AGENTIC_LABEL_OPT`
   (`adapter.py:102`, `engine_path()` at `:117-118`). ⚠ **That is the risk, and it is this plan's own
   root cause in miniature:** a path import binds to whatever is in that working tree *at that moment*
   — current branch, uncommitted edits included — so the bytes under test are unrecorded and
   unreproducible. The clone is on `main`, three commits behind `origin/main`, as of 2026-09-14.
   rad-eval pins it as a git revision under `[tool.uv.sources]`. ⚠ Adopting that shape here means
   **creating** paper-trail's first packaging file, which is more work than adding a line to one.
3. **A paper-trail egress profile.** Phil's ruling 2026-08-18: the network profile is **paper-trail's
   own to own** — adding one to the engine's policy registry re-litigates a resolved question. Build
   it on the generic host-allowlist primitive, which already accepts a caller-supplied host list.
4. **The judge/dispatcher container.** ⚠ **Scope of this claim tightened 2026-09-14, because Phil
read it as saying the optimizer's container is a solved problem for us. It is not.** Precisely:

| | built **anywhere**? | built **in paper-trail**? |
|---|---|---|
| **Optimizer** container | ✅ yes — rad-eval's, armed VM run 2026-08-05, `$4.13` | ❌ **no** |
| **Judge** container | ❌ **no — nowhere, by any consumer** | ❌ no |

So **paper-trail builds both** (Phase 1e and Phase 1b–1d). The difference is only that for the
optimizer we get to *copy* a working implementation, and for the judge there is nothing to copy.

⚠ **"But isn't the judge part of the agentic program?" (Phil) — yes, and that is the reason it needs
the container, not a reason it doesn't.** Verified: the judge's prompt, its rubric and its driver are
literally the editable fileset — `JUDGE_SCOPE = (ADJUDICATOR, RUBRIC_GUIDANCE, DRIVER)`
(`profiles.py:52`/`:58`), editable under **every** profile, because *"optimizing the adjudicator is
the one thing common to the whole ladder."* So the program **is** the judge's instructions, and the
judge is the **execution** of the program: a real Claude Code session, with tools, running
optimizer-authored text. That is exactly why a boundary drawn in prose cannot hold — the optimizer
writes the prose. Nobody has built one. Everywhere else ships *one* agent
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
| ⚠ **the armed run's own safety number** (found 2026-09-14, and the sharpest instance yet) | the `denied=` counter, which on the **hooked** path counts real per-call refusals | **container mode has no hooks at all**, so `denied` is 0 *by construction*. The 2026-08-05 readback reads `denied=0` as *"the agent hit zero sandbox denials (stayed inside the allowed tool/import list)"* — a claim the mechanism cannot support. Structurally confirmed: the container's cwd is the frozen checkout, which carries only manifest entries — no `.claude/`, no hooks — so no hook can fire. ⚠ **This is inside the evidence this plan cites as its proof.** |

✅ **Every phase below is that shape**, which is why this plan is small: Phase 1 uses the engine's
existing mount params, Phase 2 re-aims `val_isolation_problem` and a constructor parameter production
ignored, Phase 3 re-aims `runtime_pins`, Phase 4 adopts rad-eval's clone. The one genuinely new
mechanism is the sentinel control — new because its mirror image exists and asserts the opposite.

## Findings that changed the design

Verified on disk. Only the ones that still steer a decision.

**NF1 — `.claude/settings.json` does not exist anywhere.** `git ls-files | grep -i settings` empty;
`find . -name 'settings*.json'` empty; `.claude/` holds only `commands/ prompts/ scripts/ skills/
specs/`. So `--setting-sources project` finds no hook config and **there is no PreToolUse hook in the
judge's path at all** — the trade that bought the wide cwd bought nothing.

⚠ **And the comment that justifies the wide cwd is itself wrong — corrected 2026-09-14.**
`_stage_command` (`adapter.py:722-723`) explains the real checkout as: *"'project', not '' — ''
silently disables the whole hook stack. Note this reads `.claude/settings.json` from the *cwd*, which
is why cwd is a real checkout."* There is no `.claude/settings.json`, so that is not why. The **real**
dependency is `.claude/commands/sarol-eval-item.md` — the slash-command definition, which is *not* a
manifest entry and therefore **not in the materialised tree** (see NF11 and `adapter.py:642-645`:
*"A real checkout, not the materialized tree… the orchestrator is deliberately not in the fileset"*).
⚠ **This matters concretely for Phase 1:** a container image built to satisfy the comment would ship a
settings file and still fail to resolve the slash command. ✅ It also cross-checks NF1 from the other
side — rad-eval proves the same point structurally: its container cwd is the frozen checkout, which
carries only manifest entries, so *no hook can fire in a container* regardless of the flag. That is
the structural basis for OQ6 retiring the settings file on the judge's path. ⚠ It also silently retires
a specified control: `NEXT.md:463` says a tag-scoped settings file *should* be committed. Retiring it
is defensible (the container supersedes it) but must be a recorded decision — ✅ **OQ6 records it**
(retired 2026-09-14, with the hook *capability* explicitly not retired with the file) — because
reasoning a requirement away in passing is this plan's own root cause.

**NF2 — the held-out path has no iteration signal.** ⚠ **Line numbers have now drifted twice; these
are read at engine `main` @ `c2dd0b3` and must be re-checked against the pinned SHA at implementation
time.** `run_loop` is at `engine/loop.py:183`. It types `train_inputs: RunInputs | Callable[[int],
RunInputs]` (`:193`) but `val_inputs: RunInputs` (`:194`), documented at `:257` as *"fixed for the
whole run, as always"* — the docstring says `val_inputs` *"is unaffected"* by the per-iteration TRAIN
work — and `:377` reuses the one object every iteration, as does the probe at `:475`. (For the record
of how much this moves: the same four facts were at `:193-194`/`:255`/`:345`, then
`:189-190`/`:251`/`:335`/`:410`, now `:193`/`:194`/`:257`/`:377`/`:475`.) Both batch ids are iteration-free (`dispatcher.py:898`,
`:816`). Proven on disk: batches `i1` and `i5` point claim `1059-13` at the identical staging dir, and
one verdict file carries mtime `06:51` against a directory created `01:42` — overwritten in place.
⇒ staging cannot be keyed on the iteration without an engine change. ✅ **OQ2 takes that engine
change** (Phil, 2026-09-14); the two-line widening mirrors `train_inputs` in the same signature and is
backward compatible.

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
`env=`** — confirmed 2026-09-14, zero `env=` hits in the whole file. ⚠ Do not over-claim it, and ⚠
**the earlier wording here was wrong.** `_gold_root()` (`parse_verdict.py:48-52`) *does* read an
override, `PAPER_TRAIL_GOLD_DIR` (`:49`), before falling back to `~/.paper-trail/gold`. The earlier
text said there was "no env var at all", which is false. What is true is the operative half:
**nothing in the repo ever sets it** — every occurrence across the tree is a read or prose — so
scrubbing it from a child environment buys nothing against gold, because the fallback is hard-coded
and deterministic. Same conclusion, accurate premise. `env -i` closes every *other* variable; the gold
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

**NF11 — the refusal census was wrong, and its shape was inverted** (new 2026-09-14, from a direct
code audit). This is the correction with the most reach in this round, because Phase 1f, OQ7 and gate
V2c were all sized against it.

- **The count is 22, not 21.** 19 in `adapter.py`, 1 in `canary.py:257`, 1 in
  `scripts/run_baseline.py:119`, **and 1 the earlier census missed: `dispatcher.py:554`**, a direct
  construction inside `build_components` itself. ⚠ A gate asserting the count equals **21** therefore
  goes red on day one — which is worse than a wrong number, because the first response to a red
  census is to assume the tree grew a new judge.
- **There is a 23rd site reaching the same refusal, invisible to a text search.**
  `adapter.py:2770` constructs `_RealInvokerRunner` (declared `:2739`), a `SarolRunner` **subclass**
  that overrides only `_stage_command`, **not `__init__`** — so a refusal in `__init__` fires there
  too. Any census implemented by grepping `SarolRunner(` will not see it. Count subclasses, or count
  at the constructor.
- ⚠ **And 19 of the 22 are selftest-only.** Every `adapter.py` site is inside `_selftest()`
  (begins `:1642`; first construction `:1742`). **Exactly three sites can run outside a test:**
  `dispatcher.py:554`, `canary.py:257`, `scripts/run_baseline.py:119`. So the earlier framing —
  `adapter.py` as *"the largest surface"*, carrying 19 opt-outs — is 19 units of ceremony over **zero**
  production risk, while the three sites that actually ship got a sentence each. The risk is inverted.
- ✅ **One of the three needs no new mechanism.** `canary.py:257` is already
  `run = runner or adapter.SarolRunner(...)` — an injection seam exists today.
- ⚠ **`build_components` is bypassable through its own entry point**, which the earlier two-way
  partition (goes-through-`build_components` vs direct-construction) does not model.
  `run_optimization` takes `components: dict | None = None` (`dispatcher.py:604`) and does
  `parts = components or build_components(...)` (`:748`). A caller supplying `components=` skips the
  gate entirely — and the suite already does exactly that (`:1222`). So there are **three** paths, not
  two, and the refusal has to sit at the constructor to cover all of them.
- **`val_isolation_problem` is module-level** (`dispatcher.py:467`), *called* from inside
  `build_components` at `:549` with the raise at `:550-551` — not defined there, and independently
  callable (the selftests call it directly at `:1571-1589`).

**NF12 — two cost/topology facts the plan states wrongly** (new 2026-09-14).

- **A claim costs one nested session today, not three.** `profiles.py:67` sets
  `IMPLEMENTED_STAGES = ("adjudicator",)`, and the driver aborts `STAGE_NOT_IMPLEMENTED` for the other
  stages. `adapter.py`'s "three nested Claude Code sessions one claim costs" describes the `agentic` /
  `paperclip` profiles, which **cannot run today**. Any arithmetic keyed to three stages is describing
  an unrunnable configuration.
- **The driver→subagent hop is prose, not structure.** `.claude/commands/sarol-eval-item.md:134` says
  *"Dispatch the filled text as the entire prompt of exactly one general-purpose subagent"* — and that
  is the entire enforcement. The file has **no YAML frontmatter and no `allowed-tools`**, and there is
  **no `.claude/agents/` directory**; "general-purpose subagent" is the built-in Task agent. A driver
  that inlined the work would emit a verdict that looks identical. ✅ This **strengthens OQ1**: cutting
  the driver removes an unenforced convention, not a structural guarantee, so it is a smaller change
  than the plan treated it as.

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
  principals and the engine's mount renderer for the boundary. (⚠ Its per-run clone was the
  precedent for Phase 4 until **OQ9** descoped that phase to a reset — the rule still held; the
  problem turned out not to need the mechanism.) The one
  place this plan has no built precedent is the judge/dispatcher container, and that is said out loud
  rather than assumed (see `isolation-prior-work-inventory.md`).

### Phase 0 — the integrity floor

Nothing downstream is measurable until this lands, and it is independent of the boundary.

**0a. Give the held-out path an iteration, then assert the verdict slot is empty** (§4g item 6).
**Resolved by OQ2 (Phil, 2026-09-14): per-iteration folders, via the engine change** — this plan
previously recommended the consumer-side archive and was overruled, so what follows is the adopted
form, not the alternative.

Widen `val_inputs` to `RunInputs | Callable[[int], RunInputs]` in `engine/loop.py` (`:190`), mirroring
`train_inputs` (`:193`) one line above it, and resolve it at `:377` and the probe at `:475` the way
`:375` already resolves TRAIN — line numbers at engine `c2dd0b3`, and ⚠ re-read them against the
pinned SHA, since they have moved twice (NF2). Backward compatible: a plain `RunInputs` still works, so the engine's
other two consumers need no change. Held-out staging is then keyed on the iteration and **starts
fresh** — which is the property Phil asked about and the one NF2 proves is missing today (batches `i1`
and `i5` point claim `1059-13` at the identical directory; one verdict file carries mtime `06:51` in a
directory created `01:42`).

What stays consumer-side is the **assertion**, and it is the half that matters: immediately before
dispatching a claim the Runner asserts `ledger/claims/<claim_id>.json` and `ledger/errors/` are
**absent**. Per NF3 that is the precondition that makes 0b's refuse-to-score meaningful — while a
stale verdict can sit on the read path, "wrote nothing" is indistinguishable from "last iteration
wrote it". ✅ The archive-and-move step is **dropped**: an iteration-scoped root preserves the prior
verdict for free, in its own folder, which is what the move was recovering. ⚠ The assertion is not
redundant with the scoping — it is the green-by-absence rule applied to this plan's own fix. A
directory that silently was not iteration-scoped (a consumer passing the plain form, a probe path
passing the wrong index) must **fail**, not pass quietly.

⚠ **One seam decision owed at implementation, not here.** `:475` probes a *newly materialised*
program; which iteration index it passes needs stating rather than inferring. ✅ The engine's own
`manifest_for_version` (`:217`) is the pattern to copy for the failure posture: resolve per version
and **fail closed**, never fall back to a stale value.

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
  path returning 0.0 for all 50 (`adapter.py:1414`, `:1428-1433`), the iteration surfaces the delivery
  failure to the optimizer as its outcome. The optimizer reads it, diagnoses the broken delivery, and
  fixes it. ✅ **Use the channel the engine landed on 2026-09-14 rather than building one**
  (`82f547d`): `LoopStop` now carries a machine-readable `reason` (`engine/loop.py:63`) with named
  categories including `agent_session_failed` and `probe_validation_failed`, the iteration loop is
  wrapped so a mid-run stop **brings the partial run out with it** (`:544-558`) instead of losing it,
  and probe scoring moved inside the validation block specifically so *"a judge that emits a malformed
  verdict must become a controlled stop, not an uncaught crash"* — which is this failure class
  exactly. It also excludes the just-committed version from the reported frontier as untrustworthy,
  which is the right default for a delivery failure. ⚠ So Phase 0b's job shrinks to **classifying**
  the failure and handing it to that channel; inventing a parallel reporting path would be a second
  mechanism beside a working one, which is this plan's own root cause.
- **No cache trap, no count desync.** With no retry, the probe-cache hazard (a cached empty result
  re-served, `dispatcher.py:306-320`) and the session-count-vs-claim-count desync (batch aggregation,
  `adapter.py:1111-1122`) both vanish — they were artifacts of the retry option, now dropped.
- **Gate F is no longer in tension.** Plan A's `check_orchestrator_consistency.py` forbids
  `retry`/`re-dispatch`/`bounce` in driver-facing prose. With no retry, there is nothing for it to catch.

**0c. Render the dispatch prompt in Python — and, per OQ1, *be* the dispatcher** (§4g item 4).
Both observed delivery bugs (`$dispatch_prompt` unexpanded; `$(cat /tmp/adjudicator_filled_$$.txt)`
with an unexpanded `$$`) appear **nowhere in this repo** — the model authored them at run time,
differently each run, and 13 of 561 sessions started with no task. A new `dispatch_prompt.py` reads
the frozen prompt between the markers, loads slots from `ledger/evidence/<claim_id>.json` +
`staging_info.json`, substitutes, and writes the rendered bytes into staging, refusing on an
unresolved slot (`SLOT_UNRESOLVED:<slot>`).

✅ **OQ1 (Phil, 2026-09-14) extends this step from "render" to "dispatch".** The driver *session* is
eliminated: the same Python invokes the judge directly with the rendered prompt, rather than handing
the text to a Claude session that spawns a Task subagent. Reading the driver file settles why — its
224 lines do three things, (1) fill slots, (2) dispatch exactly one general-purpose subagent with the
filled text as its whole prompt (`:134`), (3) one `Bash` call to check the output file exists (`:142`)
— and this step already owns (1), a `claude --print` invocation is (2), and the Runner already does
(3) at `adapter.py:907`. Nothing in it requires judgement. ✅ This removes the **no-task failure class**
structurally rather than detecting it: Python cannot improvise a broken heredoc.

⚠ **Per NF8 this remains the optimizer's, not the harness's.** What is removed is the **model**, not
the **editability**. The driver file stays manifest entry #10 at the same path, holding
optimizer-authored prompt text that the dispatcher reads; Phil's ruling that the optimizer may write
Python covers the dispatcher itself. What reaches the judge is 100% optimizer-authored either way —
Python only fills placeholders in a prompt the optimizer wrote. ⚠ An earlier draft moved ~40% of the
driver into harness code and Phil withdrew it; this is not that, and the test of the difference is
whether the optimizer can still change what the judge receives. It can.

⚠ **The driver file's contents change even though its path and manifest slot do not.** Its
driver-facing prose — the dispatch instructions and the prohibitions addressed to a session that no
longer exists ("never repair the subagent's output", "never write the verdict yourself") — becomes
dead text in a frozen entry the optimizer would otherwise spend iterations optimising. Those
prohibitions are not lost: they are **enforced by construction**, since the code that would have
repaired an output is code nobody writes. Trimming to the judge-facing prompt re-freezes
`combined_hash` — a normal program-version event. Entry **count** and scope are untouched, so the five
count/scope selftests do not move.

Reuse, so this does not fork existing logic: `evidence_producers.py:210-216`
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

**1a. Pin the engine dependency that already exists.** ⚠ **Restated 2026-09-14** — the earlier
wording ("paper-trail has no dependency on `agentic-label-opt` today") read as though the engine did
not exist. It does, and paper-trail already uses it: `dispatcher.py` drives its `run_loop`,
`adapter.py` implements its four `TaskAdapter` protocols. What does not exist is a **pinned, versioned**
dependency — paper-trail has no packaging file at all, and the engine is resolved by `sys.path`
injection from a hardcoded home-directory path (`adapter.py:102`), overridable by
`$AGENTIC_LABEL_OPT` (`engine_path()`, `:117-118`). So an import binds to whatever that working tree
holds at that moment, branch and uncommitted edits included. Copy rad-eval's shape: a git revision
under `[tool.uv.sources]`, pinned to a commit, not a branch — which here means **creating
`pyproject.toml`**, paper-trail's first. The `engine_path()` env-var dance stays as the selftest
path; the pin is what the runtime imports. ⚠ Pinning to `main` instead of a revision
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
  (`isolation/open_profile.py:68-72`). ⚠ **Two traps verified 2026-09-14.** `adc_path` defaults to a
  **real credential path**, not `None` (`gcp_credentials.py:35`), so *omitting* it gives the
  credential-bearing shape — `None` must be passed explicitly. And `adc_path=None` is honoured **only
  on the `"open"` policy**; under `"vertex-only"` it is silently coerced back to the default
  (`:557-560`). Our tier is `"open"`, and the open profile was in fact built for *"paper-trail's
  `CLAUDE_CODE_OAUTH_TOKEN`-only tier"* — so this works, but state it as policy-specific, not general. A paper-trail allowlist profile built on the generic
  host-allowlist primitive is **ours to own** (Phil, 2026-08-18), not an addition to the engine's
  registry.
- **The token lands in host argv and in a log file.** The renderer only emits `-e KEY=VALUE`
  (`docker_prefix.py:437-439`), and the wrapper records the whole command to `meta.json`
  (`claude_wrapper.py:342-365`). Since a token env var **is** paper-trail's documented auth path, the
  by-name form (`inherit_env=("CLAUDE_CODE_OAUTH_TOKEN",)` → `--env NAME`) is a **prerequisite of
  this phase**, not a follow-up. ⚠ It fixes host argv and log disclosure only; the token stays
  readable **inside** the session. Denying that needs a credential broker — out of scope, stated so
  nobody reads this as solved.

⚠ **The flag we want to replace is not ours to pass — found 2026-09-14, and it makes this a
prerequisite.** `--dangerously-skip-permissions` is set unconditionally by the **shared wrapper**
(`claude_wrapper.py:130`), not by the consumer, so "we will use different flags" is an upstream change
(a **sixth** engine file), not a local choice. Until it lands, a container session has no hook layer
*and* no permission gate: Write/Edit/Bash are ungated within the mount set. The mount set still holds
— but the second layer this phase claims does not exist yet.

⚠ **Also adopt deny-by-default inside the container**, replacing `--dangerously-skip-permissions`:
`--permission-prompts none` (`claude --help`: *"nobody: anything that would prompt is denied
automatically"*) with a non-bypass `--permission-mode` and an `--allowedTools` set. Strictly better
than bypass-everything even behind a mount boundary. **Not** an alternative to the container — an
earlier draft framed it that way and Phil withdrew it (**OQ3**, resolved). ✅ **`Task` is no longer
required.** OQ1 eliminated the driver session, so the judge is a top-level `claude --print` session
rather than a Task subagent, and the earlier warning — that an allowlist omitting `Task` *"kills every
dispatch while looking like a permissions tightening"* — no longer applies. `Task` comes **off** the
allowlist, which is a real narrowing, and V0c's check becomes the opposite assertion: no subagent is
spawned.

**The tool surface is a named deliverable, not a flag choice.** Write it down as an exact list with
a reason per entry, because this is the layer covering the four threats the mount set cannot. Minimum
shape: `Read`/`Write` scoped to staging, `Bash` either absent or reduced, `Task` **absent** (OQ1),
`WebFetch`/`WebSearch` **absent**. ⚠ With `Bash`, `WebFetch` and `WebSearch` off the list there is no
per-call decision left for a hook to make on the judge's path — which is the finding that let **OQ6**
retire the tag-scoped settings file without retiring the hook requirement on the *optimizer's* path,
where `Bash` is needed and `engine/policy.py`'s per-command granularity still has work to do. Model
the list on rad-eval's
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
stage, claim)` it returns the prefix for that one dispatch. ⚠ **`stage` added 2026-09-14 (Phil's
program-vs-judge correction).** The dispatch loop is `for stage in self.profile.stages:`
(`adapter.py:866`) and `_stage_command` already takes the stage (`:700`), so a factory keyed only on
the claim returns **one prefix for all three stages** the moment the `agentic` profile runs — and
since the stages need *different* mounts (the extractor needs the paper; the adjudicator must not see
it), that is a silent boundary widening, not merely a stale path. Today `retrieval` runs one stage, so
the defect is latent rather than live. With it comes a **canonical container path map**
— a single place that says host path → container path (`/workspace/program`, `/workspace/staging`,
`/workspace/cwd`) — and **every** host path that crosses into the container is translated through it:
the argv, `--add-dir`, `workdir`, and any path interpolated into prompt text. A path that is correct
in argv and stale in the prompt is a dispatch the judge cannot complete, and it will look like a
model failure.

Two properties to keep. ✅ **Since OQ1, the prefix wraps the judge directly** — the earlier form wrapped
the *driver* invocation and relied on the Task subagent inheriting the boundary transitively, which is
a weaker claim (it was V2i's job to demonstrate, and a named halt condition if it failed). With no
driver session there is nothing to inherit through: one container, one session, one boundary, and V2i
becomes moot rather than pending. And a wholesale
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
    --allowedTools Read,Write                                 # no Task: OQ1 removed the subagent
    --add-dir /workspace/staging
    '<rendered judge prompt, /workspace/... paths only>'       # rendered by Python (0c), not a slash command
```

Four things to read off it. **Every path is a container path** — `--add-dir`, the workdir, and the
paths inside the prompt text all come from the same map, and a `/home/philadamson/...` string
anywhere in this command is a bug V2d catches. **Nothing here is constant across dispatches**: the
program mount changes per iteration, the staging and trace mounts per claim. **The token appears
as a name**, which is the one real engine diff this phase needs. And ✅ **the invocation is the judge's
own, not a slash command a driver runs** — the prompt arrives fully rendered on argv (0c), so there is
no second session, no `Task`, and the container boundary and the session boundary are the same
boundary.

⚠ **A writable mount cannot be nested inside a read-only one on current Docker** — verified by
rad-eval's Deviation 1 (2026-07-28, Docker 29.x/runc refuses a mountpoint that does not pre-exist
inside a `:ro` mount). The engine's edit-artifact contract is often summarised as *"more-specific
writable mounts overlay the editable files"*, and that is **not** how the working implementation does
it: rad-eval puts its writable change-note at a **sibling** path (`/workspace/writable/…`), outside
the `:ro` tree. Our staging mount must do the same. ⚠ Related: bind-mounting a host path that does not
exist creates a **directory** at the mount point, silently breaking the overlay — so the host side
must `touch` real files first.

*Gate:* **two claims × two program versions in one process** (V2d). One prefix reused across either
axis is the failure mode — it silently points a v1 dispatch at v0's bytes, or claim B at claim A's
staging, and both produce plausible verdicts.

**1d. Keep the judge's trace** (new; the first draft lost it). `find_transcript`
(`adapter.py:438-439`) globs the **host's** `~/.claude/projects`. Inside a container that directory
is the container's, and it is discarded with the container — so containerizing silently ends judge
traceability, which is how the 61% stale-verdict contamination was found in the first place.
⚠ **And "silently" is literal — verified 2026-09-14.** The lookup is guarded: `trace_ref` starts
`None`, the copy is behind `if src is not None`, and an `OSError` resets it to `None`
(`adapter.py:874-884`). So inside a container every `trace_ref` becomes `null` **while the run still
reports `status: ok`**. A gate that checks run status would not notice. The gate therefore has to
assert `trace_ref` is **non-null**, not that the run succeeded. Cheapest
fix, no new plumbing: the adapter **already holds the streamed session JSON in memory**
(`:469-503`); persist it beside the verdict and record it as `trace_ref`. ⚠ Do this in the same
change as 1c, not after — a containerized run with no trace cannot be audited, and the audit is the
deliverable.

⚠ **Before 1e: do not inherit rad-eval's read scope.** Recovered from the authoring readback
2026-09-09 and verified against code 2026-09-14. The finding, verbatim: *"Engine side, same shape: one
principal (the edit agent), two boundaries. The judge as a second, **less**-privileged principal was
never modeled — and the canonical READ scope **affirmatively grants** `release_train.json`,
`context/*.md` and `meta-learnings.md`."* Confirmed: rad-eval's `READ_WHITELIST`
(`hooks/policy.py:178`) lists `release_train.json` (`:183`) and `meta-learnings.md` (`:194`).

✅ **That is correct for rad-eval and catastrophic for us**, and the difference is the whole of §4g
item 8. Those grants exist because that whitelist belongs to the **optimizer**, which legitimately
reads its own lessons sheet and the TRAIN release. Paper-trail's program principal must never see
either — `release_train.json` **carries per-claim gold labels**. ⚠ So the read scope is
**per-principal**, exactly as item 8 said: copying rad-eval's posture wholesale would hand the judge
the gold file by name, through an allowlist, while every mount-set gate in this plan still reported
green. A boundary defeated by inheritance, not by absence.

**1e. The optimizer's container.** Model on **rad-eval's `src/optimizer_loop/docker_agent.py`** — 198
lines, on `main`, actually run: prefix delegated to the engine, a fresh temp writable staging tree,
copy-back into the live tree afterwards, a reduced tool set. What it gives paper-trail that a
permission rule cannot: the scorer, gold, `iter/`, and the manifest are **not in the optimizer's
mount set**, so "the optimizer cannot edit the scorer" holds by construction rather than by a rule
the optimizer is asked to respect. ⚠ **Correction 2026-09-14 — the earlier version of this warning described code that is not there.**
It said rad-eval's provisioning `chown -R`s the clone to a sandbox account. `docker_agent.py` has
**no chown**: two `chmod 0o666` calls under a `0700` temp root, nothing more. The `chown -R` is in the
**non-Docker sudo path** (`scripts/provision_loop_clone.py:123-128`), which Docker mode retires
outright — *"the container's own non-root user makes the optimizer OS account/sudo unnecessary"* — and
the 2026-08-05 run used an ordinary-user clone. ✅ So the conclusion stands and gets simpler: **there
is no chown to drop.** The boundary is the mount set because exactly two files are mounted `:rw`.
⚠ **What to actually avoid copying:** `staging_root` is never cleaned up — no `rmtree`, no
`TemporaryDirectory`, no `finally` — so every iteration leaks a temp dir holding the edited program and
copies of its reference docs. Ours must clean up.

⚠ **Docker mode writes zero audit rows — but corrected 2026-09-14: this is not a loss for
paper-trail, because paper-trail never had them.** The earlier wording imported rad-eval's caveat and
stated it as our regression. Two separate things were also being conflated, and Phil's question
("*I thought the optimizer reads reasoning traces and everything is saved to the mount*") is exactly
the conflation:

| Artifact | What it is | Status in a container |
|---|---|---|
| **The audit ledger** | one Merkle-chained row **per tool call**, written by the `PreToolUse` hooks, feeding the engine's four tripwires | ❌ empty — and **not because it is discarded**: container mode has no hooks, so there is nothing to write. rad-eval's `del audit_ledger` (`docker_agent.py:84`) is honest about that, not wasteful |
| **The reasoning trace** | the judge's **session transcript** — what Phil is thinking of, and what the optimizer's blame analysis opens (`adapter.py:1920`, the S13 fix) | ⚠ lost **silently** in a container (`find_transcript` globs the *host's* `~/.claude/projects`) → ✅ **Phase 1d preserves it**, which is why 1d is not optional |

✅ **And for paper-trail the ledger half changes nothing, because it was never wired.** `adapter.py:10-17`
states it outright: *"The audit ledger is the engine's, and this consumer does not use it"* —
`dispatcher.py` passes none, and `audit_ledger` / `policy_config` appear **zero** times there. It is
recorded there precisely because four optimizer-facing docs once promised the agent that reaching for
gold was *"logged to the audit ledger, and a denied-call threshold pauses the run"* — **a guarantee
nothing implemented**, since corrected to say what is true: *"VAL/TEST isolation here is by
construction, the records living outside the repository tree entirely, which needs no watcher to
hold."* ⇒ So containerizing costs paper-trail **no** tripwire it currently has. The residual is real
but it belongs to the engine and to rad-eval, and this plan should stop describing it as a blind spot
it is inheriting. ⚠ It is also why the `denied=0` row in the root-cause table matters: the same
absent mechanism is what makes that number meaningless.

**1f. One refusal locus, covering every construction site.** ⚠ **Re-counted 2026-09-14 — see NF11.
The number is 22, and 19 of them are selftests.** 19 in `adapter.py` (all inside `_selftest()`), one
in `canary.py:257`, one in `scripts/run_baseline.py:119`, and one the earlier census missed:
`dispatcher.py:554`, inside `build_components` itself. Plus a 23rd that reaches the same refusal
without matching a text search — `_RealInvokerRunner` (`adapter.py:2770`), a subclass that does not
override `__init__`.

**The refusal still lives in `SarolRunner.__init__`, and the reason is now stronger, not weaker.**
There are **three** ways to reach a Runner, not two: through `build_components`, by direct
construction, and by handing `run_optimization` a pre-built `components=` dict that skips
`build_components` altogether (`dispatcher.py:604`, `:748`; already exercised at `:1222`). Only the
constructor sits under all three. A gate in `build_components` would miss the baseline recut *and*
the `components=` path while the suite reported green.

⚠ **But the effort is not where the plan put it.** The three sites that can run outside a test are
`dispatcher.py:554`, `canary.py:257` and `scripts/run_baseline.py:119` — and `canary.py` **already
accepts an injected runner** (`run = runner or adapter.SarolRunner(...)`), so it needs no new
mechanism at all. That leaves **two** production sites to wire. The 19 `adapter.py` sites are
selftest ceremony: real work to type, but zero production risk, and they should be described that way
rather than as *"the largest surface"*.

✅ Every site is then either containerized or visibly opted out, and the count is assertable
(**V2c**) — ⚠ **against 22, and counting subclasses, not against 21 by grep.**

⚠ **No opt-out for anything that produces or guards a reportable number.** That rules out both
non-test sites: `scripts/run_baseline.py` **produces** Plan A's baseline recut, and `canary.py`
**guards** it. Both take the shipping factory. An opt-out there would mean the baseline is measured
on the uncontained instrument while every iteration compared against it is measured on the contained
one — which is not a weaker guarantee, it is an invalid comparison. **OQ7** was therefore about the
selftest sentinel's shape, not about whether the baseline gets one — ✅ and it resolved to an
**injected fake prefix**, so the selftests keep asserting real argv and no production-reachable branch
can disable the boundary.

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
`build_components` gate would have missed entirely. ✅ **OQ7** settles the opt-out policy: an injected
fake prefix for the 19 selftest sites, and no opt-out here.

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

**`--bare` is now the preferred form for the last row, with one caveat left.** Verified on CLI 2.1.267:
*"skip hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and
`CLAUDE.md` auto-discovery"* — one flag for the row whose two env-var names are unverified, and
`NEXT.md:461` already names `claude --bare --print …`. ✅ **Its blocker is gone.** Rule 3 records that
`--bare`-style default toolsets **omit `Task`**, which was disqualifying while OQ1's option (i) kept
the driver; OQ1 resolved to (ii), so the judge needs no `Task` and `--bare`'s omission is now a
narrowing rather than a breakage. ⚠ **The remaining caveat is auth**: `--bare` refuses OAuth/keychain
auth, and paper-trail authenticates with `CLAUDE_CODE_OAUTH_TOKEN` — an env var rather than a keychain
read, but unverified. **V0b tests it. Pre-encoded fork:** the token survives `--bare` → use `--bare`;
it does not → drop it and set this row's flags individually, which is what the table above lists
anyway, and record the two unverified env-var names as a residual.

**Three canonical pieces are deliberately omitted** and said so plainly: `--tools default`, `--agents`,
`--settings <tag-scoped>` (`experiment-sarol-eval-arm-isolation.md:107-115`) — all unused today. ✅ All
three are now **permanent** rather than pending: `--tools default` was conditional on OQ1 keeping the
driver (it did not), and `--settings` was conditional on OQ6 authoring the file (**OQ6 retires it** —
the flags on this command line carry those controls directly, where Phase 3's hash can pin them, and a
settings file would sit on disk inside the tree the optimizer edits).

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

### Phase 4 — reset the run-scoped state at run start

⚠ **Retitled and descoped 2026-09-14 by OQ9 (Phil).** This phase was *"one clone per run"*. It is now
a reset. The finding below is unchanged and still real; the mechanism is much smaller. Read OQ9 for
the reasoning — in one line: the defect is **sequential** residue between runs, a git clone buys
*concurrent-namespace* isolation that paper-trail will never need, and a reset is the part that does
the work. `optimizer/run_clone.py`, the provisioner, the clone options, the ownership question, the
resume design and the `REPO_ROOT` re-resolution are all **struck**.

**The finding (Plan A).** `optimizer/meta-learnings.md` — injected into every optimizer session — has
**never been archived or reset between runs**, while `profiles.py:514` reasons as though a reset were
guaranteed. It is not a manifest entry. So two runs both labelled `program-v0` could open with
different inherited hypotheses and nothing would record it. Plan A archived the 258-line sheet and
reset it to a stub, which unblocks its owed baseline recut.

**The root cause is structural.** paper-trail's run boundary stops half-way — its own log line says
*"Results under `$RUNS`; releases under `$REPO_ROOT/iter/`."* Per-run: results only. Shared: releases,
the lessons sheet, `findings/`, and the `program-v*` tag namespace.

**Archive-and-assert at run start.** Phil's framing still holds — *the program is per iteration; the
optimizer is per run* — and the implementation of "per run" is a reset, not a clone. Concretely: the
VM runner mints one run id per invocation and, before `build_components`, moves `meta-learnings.md`,
the five `findings/iter-*.md` and `iter/` into the run archive, then **asserts each is absent**. Phase
2a already builds a per-run working directory for the judge; this is the same move one level up, for
the optimizer's inputs.

Three consequences. ✅ **Gate H is satisfied rather than retired** — `check_run_scope.py` exists to
refuse starting when a previous run's `findings/iter-*.md` are present, and the reset clears them
*before* it looks, so the gate keeps asserting instead of being designed away. (A clone would have
removed it; keeping a live gate is the better outcome and was an accidental loss in the clone
version.) ✅ **The ledger-recut hazard is reduced but not eliminated** — the recut is dangerous because
it rewrites *shared tags*, and tags are repo-global whether or not there is a clone. That is the one
thing the clone gave for free, and OQ9 names the two ways out (namespace tags per run id, or drop tags
in favour of the manifest's `combined_hash`, which already identifies a program version and is
committed — recommended). ⚠ **It does not close NF9's class for the optimizer's inputs.** A clone
boundary covered everything in the tree; a reset covers the three things it is told to reset. So the
reset list is load-bearing and must be **derived from what the optimizer reads**, not appended to when
something is noticed — the same discipline the mount-set allowlist gets in the forks section.

✅ **Where run state lives — OQ8 resolved (Phil, 2026-09-14): local git and local disk.** paper-trail
is non-PHI forever, so Gate H's archive at `~/.paper-trail/runs/_archive/` and the run's own state both
stay on local VM disk — plain git is a fine home. No split to the shared mount: the "bucket mode"
that lands run state on the mount is a modular capability of the shared engine for a PHI consumer like
crc-extraction-agent, which paper-trail leaves off (see OQ4). This also sidesteps the mount's ~2 MB/s
small-file reads, which would have made any working tree there slow anyway.

⚠ **Precondition, verified 2026-09-11:** the archive holds `meta-learnings.md` **only**. The five
`findings/iter-*.md` in the primary checkout are still untracked, unarchived, and **the only copy**.
Archiving them is a precondition, not a consequence.

**Where this actually gets built.** The earlier version of this table specified a clone provisioner
and was the reason the review called Phase 4 *"not implementable by a fresh session"*. The reset is
small enough to state in full:

| Piece | Decision |
|---|---|
| Who mints the run id | the VM runner script (`run_hillclimb_vm.sh`), which already owns `$RUNS`; one id per invocation, passed down, never re-derived |
| When the reset runs | before `build_components`, so no component has yet resolved a path into stale state |
| What gets reset | `meta-learnings.md`, `findings/iter-*.md`, `iter/` — moved to `~/.paper-trail/runs/<run_id>/_archive/`, then **asserted absent**. ⚠ The list is derived from what the optimizer reads; adding to it later means the derivation was wrong, not that the list grew |
| What `REPO_ROOT` means afterwards | unchanged — the checkout. ✅ This is the reach the clone had and the reset does not: no consumer of `REPO_ROOT` is re-resolved, so `working_checkout` and the forbidden-path set keep their current meaning |
| The `program-v*` tag namespace | the one thing the clone gave free. Recommended: stop using tags as version identity and key on the manifest's `combined_hash` (committed, already what Phase 3 pins). Alternative: `run-<id>/program-v<n>`. Decide before implementing (OQ9) |
| What the optimizer's container mounts | the program subtree of the checkout, via rad-eval's temp writable staging + copy-back (1e) — **not** a clone, and never the scorer, gold, `iter/` or the manifest |
| Resume after an interrupted run | ⚠ no longer a design question. A reset is idempotent against an already-clean tree, so a resumed run either finds the archive it made or makes one; there is no half-provisioned clone to reconcile |

✅ **Phase 4 and Phase 1e are no longer coupled.** The clone version made them the same boundary at two
scopes, so they had to land together. They do not: 1e's write boundary is the **mount set plus
copy-back**, which this plan already states outright (*"a clone with no container around the optimizer
is a fresh tree the optimizer can still walk out of"* — the clone was never the boundary). 1e protects
the scorer by not mounting it; Phase 4 stops run N's hypotheses reaching run N+1. Different jobs, no
ordering constraint, and OQ9's worry that splitting would leave *"the optimizer's boundary weaker"*
does not survive contact with what each half actually does.

### Deliberately out of scope

**Three things left scope on 2026-09-14**, on Phil's feedback, and are recorded here rather than
silently dropped — reasoning a requirement away in passing is this plan's own root cause:

- **The driver session** (**OQ1**). Eliminated, not deferred: the dispatcher is deterministic, so
  `dispatch_prompt.py` invokes the judge directly. What is *out of scope* is the consequence — the
  judge stops being a Task subagent, so iterations 1-5 are not comparable across the change. Plan A's
  baseline recut already had to run on the post-isolation instrument (61% of iter-5 judges read a
  stale verdict), so the recut absorbs the topology change; it is bundled, not free.
- **The per-run git clone and `optimizer/run_clone.py`** (**OQ9**). Replaced by a run-start reset.
  Phil: there will never be parallel runs, and a clone's distinctive value is concurrent-namespace
  isolation. ⚠ The residual is the `program-v*` tag namespace, named in Phase 4 with a recommendation.
- **The tag-scoped `--settings` file** (**OQ6**). Retired, with the reason recorded: the container's
  explicit flags carry the same controls where Phase 3's hash can pin them, and a settings file would
  live on disk inside the tree the optimizer edits. ⚠ **Hooks are not retired with it** — per-call tool
  policy stays a live gap on the *optimizer's* path and stays in the residuals table.

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

**New — `optimizer/dispatch_prompt.py`.** Slot resolution, integrity checks, prompt rendering **and
the dispatch itself** (0c + **OQ1**) — it reads the frozen prompt from the driver file, fills the
slots, refuses on an unresolved one, and invokes the judge directly. ⚠ **This module replaces the
driver session**, so it is the one place the delivery path lives; per NF8 the optimizer may rewrite it
(Phil: the optimizer may write Python), which is what keeps eliminating the driver *model* from being
a removal of the optimizer's reach. Out of `adapter.py` (already ~2,900 lines) and out of
`isolation.py` (different concern). **Reuse target:** `evidence_producers.py:201-216`.

**`pyproject.toml`** — ⚠ **a new file: paper-trail has no packaging file of any kind today.** The
dependency on `agentic-label-opt` is real and live (see 1a); what this adds is the **pin** that
replaces a hardcoded home-directory path. `agentic-label-opt` pinned to a
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
draft's `build_components` gate would have missed. It takes its own version-addressed cwd and the
**shipping** factory. ✅ **No opt-out** — OQ7 confirms the injected fake prefix is for the 19 selftest
sites only; a baseline measured on an uncontained instrument would not be a weaker guarantee, it would
be an invalid comparison against every iteration measured on the contained one.

**`experiments/sarol-2024/scripts/vm/run_hillclimb_vm.sh`** — mints the run id and runs the
**run-start reset** before `build_components` (Phase 4 as descoped by **OQ9**: archive
`meta-learnings.md`, `findings/iter-*.md` and `iter/`, then assert absent — ⚠ *not* a clone
provisioner), and records the in-container CLI version and the **image digest** beside
`model`/`profile`/`retrieval_k`.

⚠ **~~New — `optimizer/run_clone.py`~~ — STRUCK by OQ9 (Phil, 2026-09-14).** There is no per-run
clone, so there is no provisioner, no clone options, no ownership or `safe.directory` step, no resume
design, and **no re-resolution of `REPO_ROOT`** — which was the change with reach in this plan and is
now simply not made. Phase 4's reset is ~30 lines split between the VM runner (mint the run id, move
the three items to the archive) and `optimizer/isolation.py` (assert absent). Tests: two consecutive
run ids see a clean `meta-learnings.md` and no `findings/iter-*.md`; and the assertion **fails** when
the archive step is skipped — a reset with no negative control is the inert-mechanism pattern.

**`experiments/sarol-2024/program-v0/manifest.json`** — one new key under **`runtime_pins`** carrying
the expected configuration hash over Phase 3's expanded schema (image digest, mount triples with
roles, network policy, session flags). Not a new file, and it cannot re-version the program:
`combined_hash` covers `entries` only, and `cmd_write` preserves `runtime_pins` across re-freezes.

**`.claude/commands/sarol-eval-item.md`** — ⚠ **its role changes, its path and manifest slot do not**
(**OQ1**). It stops being a slash command a driver session executes and becomes the file the
dispatcher reads the judge's prompt out of. Trim the now-dead driver-facing prose — the dispatch
instructions (`:123-138`) and the prohibitions addressed to a session that no longer exists
(`:43-50`), which are enforced by construction once no model sits in the delivery path — and keep the
judge-facing prompt between the markers. This re-freezes `combined_hash`; it does **not** change the
manifest's entry count or scope, so the five count/scope selftests are untouched. ⚠ **Fully editable**
(NF8): this is a default the optimizer may rewrite, not a contract.

**Shared engine** — the `agentic-label-opt` clone (⚠ **not** at the `~/code/…` path this plan gave;
it sits beside the other personal-projects checkouts. ⚠ **Pulled current 2026-09-14: local `main`
is now `c2dd0b3`** (was `6d621ac`, three behind). The pinned `82f547d` is an ancestor, so the
citations resolve — but the line numbers moved, and are re-stamped throughout against `c2dd0b3`)
⚠ **six files now** — the first draft claimed one, the second four; `engine/loop.py` was added by
OQ2 and `engine/claude_wrapper.py` by the 2026-09-14 code audit:
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
- **`engine/claude_wrapper.py`** (⚠ **new 2026-09-14, and a prerequisite**) — `:130` passes
  `--dangerously-skip-permissions` unconditionally for every consumer. Phase 1b's deny-by-default
  layer cannot exist until this is a caller choice. Until then a container session has no hook layer
  and no permission gate; the mount set is the only boundary.
- **`isolation/Dockerfile`** + **`isolation/README.md`** — re-pin `CLAUDE_CODE_VERSION` from 2.1.218
  to the host version and say so. ⚠ The README is also the file whose six-week-stale sentence about
  `iter_n` outranked live code in this plan's first draft; correcting it is part of the change, not
  tidying.

- **`engine/loop.py`** (⚠ **new as of OQ2, 2026-09-14**) — widen `val_inputs` from `RunInputs` to
  `RunInputs | Callable[[int], RunInputs]` (`:194` at engine `c2dd0b3`), mirroring `train_inputs`
  (`:193`) in the same signature, and resolve it at `:377` and the probe at `:475` the way `:375`
  already resolves TRAIN. ⚠ **Re-read these against the pinned SHA before editing — they have moved
  twice already** (NF2). ✅ There is now a second precedent in the same file: `manifest_for_version`
  (`:217`), a per-version callable that **fails closed** rather than falling back to a stale value —
  copy that failure posture. Update the docstring at `:257`, which currently states the opposite (*"`val_inputs` is unaffected
  (fixed for the whole run, as always)"*). Backward compatible — a plain `RunInputs` still works, so
  the other two consumers need no change. Tests: an iteration-keyed VAL batch reaches
  `runner.run`, and the plain form still does.

⚠ **Paper-trail's own sentinels and auth stay here, not upstream.** An upstream addition earns its
place only if it is generic and tested there; otherwise it is our specifics living in three other
consumers' repo.

⚠ **This plan now touches `engine/`, where it previously claimed not to.** The earlier line read
*"✅ Still no change to `engine/`"* and was true until OQ2. The materialised path is indeed already
threaded (`loop.py:192`, `:426-431`) — that part stands — but the held-out inputs are not, and OQ4's
"sort by where it should live" is what moved the fix upstream. It remains a two-line type widening
plus a docstring correction, so the claim that changes is *"no engine change"*, not *"a small engine
change"*.

**`docs/claude_ops.md`** — one line: its §Environment says this repo has "no build step, no runtime,
and no test suite" while this plan's verification rests on a 447-check suite. Repo-local copy.

**`docs/plans/README.md`** — one row. **`docs/plans/NEXT.md`** — the isolation entry's state.

---

## Open Questions

Nine numbered, **all nine resolved** as of 2026-09-14. Kept in full rather than deleted, because
several were resolved *against* this plan's own recommendation and the reasoning is what a fresh
session needs. Resolution order on the day: OQ4, OQ5, OQ8 first, then OQ9 (which set the scope),
then OQ1, OQ2, OQ6, OQ7.

**OQ9 — ✅ RESOLVED 2026-09-14 (Phil): no per-run clone. A run-start reset instead.** Phil: *"I don't
think we're ever going to have multiple runs in parallel… a run is always going to be operating from
the latest checkout… I guess I don't see what the concern is."*

⚠ **The concern was never parallelism, and this plan failed to say so.** Phase 4's finding is
*sequential*: `meta-learnings.md` — injected into every optimizer session — had **never been archived
or reset between runs**, so run N+1 opened carrying run N's inherited hypotheses while
`profiles.py:514` reasoned as though a reset were guaranteed. Two runs both labelled `program-v0`
could therefore start from different states with nothing recording it. That happens with runs strictly
one after another; concurrency has nothing to do with it. Phil's own framing — *"if we update
something for a new run, that would land in the next run"* — assumes each run starts from a defined
state, which is exactly the property that was missing.

**But his ruling does dissolve the clone.** A git clone per run id buys two things: a reset, and an
*independent namespace* (working tree, `iter/`, `program-v*` tags, audit ledger) for runs that
overlap in time. rad-eval needed the second. paper-trail never will. So the clone is a heavyweight
mechanism for a job an archive-and-reset does — and adopting it would be this plan's own anti-pattern
(*re-aim what exists*) in reverse. **Phase 4 is therefore descoped** to: archive `meta-learnings.md`,
the five `findings/iter-*.md` and `iter/` into the run archive at run start, assert them absent, and
mint the run id in the VM runner. `optimizer/run_clone.py` is **struck** — with it go the provisioner,
the clone options, the ownership question, the resume design and the `REPO_ROOT` re-resolution that
made Phase 4 *"not implementable by a fresh session."*

✅ **Three consequences worth stating.** Gate H (`check_run_scope.py`) is now **satisfied rather than
retired** — it refuses when residue is present, and the reset removes the residue before it looks, so
the gate keeps asserting instead of disappearing. The OQ9-as-written worry that *"Phase 1e's optimizer
mounts are defined against the clone"* **evaporates**: the clone was never the write boundary — this
plan already says so (*"a clone with no container around the optimizer is a fresh tree the optimizer
can still walk out of"*) — and 1e's real mechanism is rad-eval's temp writable staging plus copy-back,
which needs no clone. And the split question falls away: there is no large Phase 4 left to split, so
Phases 0-4 land as one plan.

⚠ **One thing the clone gave for free that a reset does not: the `program-v*` tag namespace.** Tags
are repo-global, so a second run re-mints `program-v1..v5` over the first run's. Two ways out, and
this is the only genuinely open detail left: **(a)** namespace the tags per run (`run-<id>/program-v<n>`),
or **(b)** stop using tags as the version identity and rely on the manifest's `combined_hash`, which
already identifies a program version uniquely and is committed. *Recommendation: (b)* — it is one
fewer mechanism, and the hash is the thing the pin (Phase 3) already keys on. Decide it before Phase 4
is implemented; it is a ten-line decision, not a design.

**OQ5 — ✅ RESOLVED 2026-09-14 (Phil): allow it to fail; the optimizer determines and fixes it.**
No Runner-side retry and no scoring around the failure. A dispatch that produces no verdict fails the
claim, and that failure is surfaced to the optimizer as feedback — because the delivery path is
optimizer-editable (NF8), a no-task dispatch is a delivery defect inside the program the optimizer
owns, and the optimize loop exists to catch and fix exactly that. The refuse-to-score gate still
stands (never read the stale verdict, never silently return 0.0 for the whole batch); the failure is
recorded under a distinguishable delivery-failure count, keyed only on `UNREADABLE:`, so it is never
reported as program quality. Dropping the retry also removes the probe-cache trap, the
session/claim-count desync, and any tension with Gate F. ⚠ Plan A's baseline recut runs on this.

**OQ1 — ✅ RESOLVED 2026-09-14 (Phil, against this plan's recommendation): eliminate the driver
session — option (ii).** Phil: *"it feels like what you're describing is the dispatcher, which doesn't
need to be an agent because it's deterministic, right?"* Correct, and checking the file settles it:
`.claude/commands/sarol-eval-item.md` is 224 lines of prose executed by a Claude session whose entire
output is (1) fill slots into the frozen prompt, (2) dispatch **exactly one** general-purpose subagent
with the filled text as its whole prompt (`:134`), (3) one `Bash` call to check the output file exists
(`:142`). Step 1 is what 0c already moves into Python; step 2 is a `claude --print` invocation; step 3
is what the Runner already does at `adapter.py:907`. There is no judgement left in it — so it is a
dispatcher, and a model is the wrong thing to implement a dispatcher with.

⚠ **"Eliminate the driver session" ≠ "take the delivery path away from the optimizer."** What is
removed is the **model**, not the **editability**: the driver file stays a manifest entry holding
optimizer-authored prompt text (`DRIVER` is in `JUDGE_SCOPE` on Plan A's tip, `profiles.py:50`,
`:58`), and the dispatcher reads it. What reaches the judge is 100% optimizer-authored either way.

⚠ **CORRECTED 2026-09-14 (Phil): the dispatcher itself is NOT optimizer-editable, and an earlier
sentence here said it was.** It read *"Phil's ruling that the optimizer may write Python covers the
dispatcher too."* That is wrong, and wrong in the direction that would defeat this entire plan.
**`dispatch_prompt.py` is runner code, not program.** Draw the line exactly where the manifest already
draws it: `src/commands/paper-trail.md` — the orchestrator — sits in `deliberately_excluded` with the
reason *"orchestrator = fixed runner code, not editable program."* The dispatcher is the same
category, and it has a harder reason: **it is the thing that builds the container command** (Phase
1c). An isolation boundary the isolated party can edit is not a boundary. So:

| Surface | Who owns it | Why |
|---|---|---|
| The **prompt text** in the driver file | **the optimizer** — fully editable | it is what the judge is *told*; optimizing it is the point |
| The **rubric / adjudicator prompt** (`JUDGE_SCOPE`) | **the optimizer** | same |
| **`dispatch_prompt.py`** — slot-filling, refusal, invoking the judge | ⚠ **the harness. Never the optimizer** | it applies the container prefix; editable enforcement is not enforcement |
| The **scorer**, gold, the manifest | the harness | unchanged, and outside both containers |

⚠ **And Phil's 2026-09-11 "the optimizer may write Python" ruling is not in tension with this** — it
scopes to the *program*. The optimizer may author Python **inside its own program fileset** (a
retrieval helper, say). It may not author the runner that contains it. Keeping those two straight is
the difference between a program-model question and a security boundary.

✅ **What this buys, beyond the ~10% of spend.** It removes the entire **no-task failure class**
structurally: both observed delivery bugs (`$dispatch_prompt` unexpanded; `$(cat …_$$.txt)` with an
unexpanded `$$`) were authored by the driver *model* at run time, differently each run, and 13 of 561
sessions started with no task. Python cannot improvise a broken heredoc. It also retires the driver's
prohibitions **by construction** rather than by prose — "never repair the subagent's output", "never
write the verdict yourself", "never retry" stop being instructions a model might skim past and become
code nobody wrote. That is this plan's whole thesis applied one level up.

✅ **And it collapses three open unknowns.** `--allowedTools` no longer needs `Task`, so the warning
that an allowlist omitting it *"kills every dispatch while looking like a permissions tightening"*
goes away. **`--bare` becomes available** — its omission of `Task` was the blocker, and it covers the
whole auto-memory / `CLAUDE.md` / dynamic-section row in one verified flag. **V2i is moot**: there is
no Task subagent whose policy inheritance needs demonstrating, which was a named halt condition.

⚠ **Two costs, both real, neither new.** First, **the measured condition changes** — the judge stops
being a Task subagent and becomes a top-level `claude --print` session, so iterations 1-5 are not
comparable across it. But this plan already owes Plan A a baseline recut on the post-isolation
instrument (61% of iter-5 judges read a stale verdict), so the recut absorbs the topology change at no
extra cost; it does not get to be *cheap*, it gets to be **bundled**. Second, **`--bare` refuses
OAuth/keychain auth** and paper-trail authenticates with `CLAUDE_CODE_OAUTH_TOKEN` — an env var, not a
keychain read, but unverified. **V0b tests it; pre-encoded fork:** token survives `--bare` → use it;
does not → drop `--bare` and set the row's flags individually, which is what §2c lists anyway.

✅ **No manifest re-freeze to 9 entries, and no five-selftest break** — the earlier warning assumed the
driver file disappeared. It does not: it stays at the same path as entry #10, holding the prompt text
the dispatcher reads. Its *contents* change; the entry **count** and scope do not, so the five
count/scope selftests are untouched.

⚠ **"Same path — doesn't it just get overwritten?" (Phil, 2026-09-14). In the working tree yes; in
every frozen version no — and that distinction is the whole versioning model, so it is written out
here rather than assumed.** A program version is **a git commit plus a `program-v<n>` tag**, not a
directory of current files. `engine/materialize.py` builds a version's snapshot by reading each
manifest entry's bytes **out of git at that version's SHA** — `git show <version_sha>:<path>` — and
writing them into a per-version read-only tree (`_make_read_only` chmods files *and* directories, so
nothing can be added either). Consequences:

- Editing the driver **does** overwrite the working-tree copy. That is the only thing overwritten.
- `program-v0`'s bytes stay pinned at `program-v0`'s commit forever. `git show program-v0:<path>`
  returns the old text no matter how many times the file is edited afterwards.
- So a v0 dispatch and a v1 dispatch read from **different materialised snapshots**, each holding its
  own version's bytes. Nothing is lost and nothing is shared.

✅ That is also exactly why **Phase 2a makes the judge's working directory the per-version snapshot**
rather than a fixed folder — the snapshot *is* the version-addressing, already on disk, already
read-only. "Ordinary new-version event" means: edit the file → freeze → `program-v1` exists with the
new bytes, `program-v0` still resolves to the old ones.

**OQ2 — ✅ RESOLVED 2026-09-14 (Phil, against this plan's recommendation): per-iteration folders, via
the engine change.** Phil: *"We should have folders based on iteration, right? … each run should have
its own iteration folder that starts fresh. Is that not what we're doing?"*

⚠ **Direct answer: no — not on the held-out path, and that asymmetry is the defect.** TRAIN does get
per-iteration inputs; VAL does not. Verified in the engine at `c2dd0b3` (`run_loop` at `:183`):
`engine/loop.py:193-194` types `train_inputs: RunInputs | Callable[[int], RunInputs]` but
`val_inputs: RunInputs`, documented
at `:257` as *"fixed for the whole run, as always"*, and `:377` (plus the probe at `:475`) reuses the
one object every iteration. Both batch ids are iteration-free (`dispatcher.py:898`, `:816`). Proven on
disk: batches `i1` and `i5` point claim `1059-13` at the identical staging dir, and one verdict file
carries mtime `06:51` in a directory created `01:42` — **overwritten in place**. So iteration 5's
judge ran in iteration 1's folder, on top of iteration 1's verdict. (Note the citations moved: this
plan quoted `:193-194`, `:255`, `:345` against an older engine SHA.)

**So the engine change is the answer, and OQ4 is why it stops being a close call.** This plan
recommended the consumer-side archive on the grounds that *"the defect is ours and the engine change
touches three other consumers."* OQ4 overturns that reasoning explicitly: sort by **where it should
live**, not who owns the defect. Any consumer whose runner keys staging on a claim id hits the
identical in-place overwrite — crc included — so per-iteration held-out staging is a shared-engine
property, not a paper-trail patch.

✅ **And it is small, because the precedent is in the same signature.** Widen `val_inputs` to
`RunInputs | Callable[[int], RunInputs]` and resolve it at `:377` and `:475` exactly as `:375` already
resolves `train_inputs`. ✅ **A second precedent landed the same day** (`ee26d80`):
`manifest_for_version: Callable[[str], ProgramManifest] | None` (`:217`), a per-version callable in
this same signature that **fails closed** rather than reusing a stale value — so the shape is now
idiomatic here, not novel. Backward compatible — a plain `RunInputs` still works, so the other two
consumers need no change. ⚠ One implementation detail to decide at the seam, not here: `:475` is the
*probe* on a newly materialised program, so which iteration index it passes needs stating rather than
inferring.

✅ **Phase 0a shrinks to its cheap half.** With an iteration-scoped root, a stale verdict from
iteration N cannot sit where iteration N+1 reads, so the archive-then-move step is unnecessary; what
remains is the assertion — the live path **must be absent** before dispatch — which stays, because
per NF3 that assertion is the precondition that makes 0b's refuse-to-score meaningful. The prior
iteration's verdict is preserved for free by living in its own folder, which is the preservation
property 0a was built to recover.

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

> **Phil's follow-up, and the answer.** *"Does this change any of what's in this plan currently? …
> we're discussing these things, but what are we building concretely?"*
>
> **It changes the filing, not the build — with one exception.** Every item OQ4 re-filed as
> shared-engine work is something this plan already declined to build: bucket-mode storage, hook
> wiring, audit rows from container sessions, the isolation-label validation. They move from *"a gap we
> noted"* to *"named backlog crc will need"*, and none of them enters scope. The exception is **OQ2**:
> OQ4's reasoning is what flipped per-iteration held-out staging from a consumer-side workaround to a
> small upstream change in `engine/loop.py`, because *"the defect is ours"* stopped being the deciding
> argument.
>
> **It adds one design constraint, which is not extra work.** The judge/dispatcher container is the one
> thing nobody has built anywhere, and crc designed the identical gold-holding sibling. So
> `optimizer/isolation.py` is written with its mount-set builder and path map **generic, with
> paper-trail's paths as data** — shaped to lift, not lifted now. That is a way of writing the module,
> not a second module.
>
> **And it is why *What we are building* now exists** at the top of this plan. The concrete answer is
> those twelve items. This section answers *where each one should eventually live*, which is a
> different question and was being read as the same one.

**OQ6 — ✅ RESOLVED 2026-09-14 (Phil): retire the tag-scoped settings file. Hooks are *not* retired.**
Phil: *"we can retire it unless you think that there are hooks that do things that are non-redundant
with the Docker container."* This is the recorded decision the question asked for.

**Retire the file.** `NEXT.md:463` says a tag-scoped `--settings` file should be committed; NF1 proves
it never existed, so nothing regresses. What it was *for* was delivering hook config and permission
settings into a session invoked with `--setting-sources project` and no config on disk. The container
plus explicit CLI flags — `--permission-prompts none`, a non-bypass `--permission-mode`, an
`--allowedTools` list — deliver those same controls directly, on the command line, where the
configuration hash (Phase 3) can pin them. A settings file would additionally be *on disk inside the
program tree the optimizer edits*, which is the wrong place for a control the optimizer must not move.
`--settings` therefore joins `--tools default` and `--agents` as a permanently-omitted Rule 3 piece
rather than a pending one.

**Now the "unless" — and the honest answer is a split, not a flat no.** Hooks do one thing the
container cannot: decide **per call**, on the call's *content*. `--allowedTools` is all-or-nothing per
tool; `engine/policy.py`'s `evaluate_bash(command, …)` and `evaluate_webfetch(url, …)` inspect the
command string and the URL. The network profile sees a **host**; the hook sees the **URL**. This is not
hypothetical — the engine's own egress plan records that rad-eval retains `WebFetch` *precisely
because* a real `PreToolUse` hook denies every URL unconditionally, and that **"Docker mode has no hook
wiring at all, so that same app-layer policing doesn't exist"**
(`2026-07-30-docker-vertex-only-egress-allowlist.md:123`).

- **On the judge's path: redundant.** Its allowlist has `Bash` absent-or-reduced and `WebFetch` /
  `WebSearch` absent (and, per OQ1, no longer needs `Task`). With those tools ungranted there is no
  per-call decision left for a hook to make. ✅ Retiring the file costs the judge nothing.
- **On the optimizer's path: non-redundant, and a live gap.** The optimizer needs `Bash` — it edits and
  runs things — so `evaluate_bash`'s per-command granularity has real work to do that the mount set and
  a tool allowlist cannot. That gap is inherited knowingly by going container-first, and it is already
  in the residuals table as the second landing. Retiring the settings *file* does not retire it.

⚠ The distinction to keep: what is retired is a **delivery mechanism** that never shipped, superseded
by a better one. What is deferred is a **capability** whose decision logic exists (16 tests) and whose
wiring does not. Collapsing those two into "hooks: dropped" would be the exact move this plan's
root-cause table is made of.

**OQ7 — ✅ RESOLVED 2026-09-14 (Phil): the injected fake prefix, as recommended.** Phil's one-word
answer. So: the 19 selftest sites opt out by passing an explicit sentinel **plus an injected fake
prefix**, which keeps the argv assertions real — the selftests still exercise the path translation
rather than skipping it — and leaves no production-reachable branch that disables the boundary. The
rejected shape is recorded with it: a boolean `isolation_mode` flag, because a keyword that silently
disables the boundary is the mechanism this plan's root-cause table is made of. The original question,
for reference:

⚠ Narrower than it looks, because the
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

> **Phil's follow-up, and the answer.** *"Is this a large design change to the Agentic Label Opt
> project? As well as this one."*
>
> **No, on both counts — and the engine surface is the smaller of the two.** What this plan actually
> asks the engine to build is five things, all small: a by-name credential env form
> (`inherit_env=(…)` → `--env NAME`, ~20 lines in `isolation/docker_prefix.py`, which today only emits
> `-e KEY=VALUE` at `:439`); the generic half of the seal negative control plus its test, both additive
> and reusing `run_probe`; a `CLAUDE_CODE_VERSION` re-pin in the `Dockerfile` and README; and — new as
> of OQ2 — widening `val_inputs` in `engine/loop.py` to accept a callable, which is a two-line type
> change mirroring `train_inputs` five lines above it and is backward compatible, so the other two
> consumers are untouched. ⚠ That last one **corrects this plan's earlier "✅ no change to `engine/`"**,
> which was true before OQ2 and is not now.
>
> **What *is* a design change is a change of ownership, not of architecture.** OQ4 and OQ8 say four
> capabilities — bucket-mode storage, hook wiring, container-mode audit rows, isolation-label
> validation — are the engine's to own because crc needs them too. None of them is built here, none is
> designed here, and the engine's plans already name three of the four as explicitly deferred. So the
> engine's **backlog** grows; its **design** does not.
>
> **The one genuine architectural addition is paper-trail's, not the engine's:** the gold-holding
> judge/dispatcher container, which crc's umbrella plan designed (`2026-07-10-…:60`, `:232-237`) and no
> repo has shipped. It gets built here, generically, so crc can adopt it rather than rebuild it — which
> is a change *in* the engine's direction, not a change *to* the engine.

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
| **V2c** | a refusal that only covers the sites we remembered ⇒ green while an ungated judge ships | assert the **count** of direct `SarolRunner` constructions (⚠ **22**, NF11) and classify each as containerized or explicitly opted out. ⚠ Count by constructor reachability, not by grep — a subclass inheriting `__init__` is bound by the refusal and matches no text search |
| **V4** | pin container emptied by a `cmd_write` refactor; pin read from the worktree; **a host-only hash ⇒ a swapped container leaves it unmoved** | round-trip re-freeze test; pin read from `git show HEAD:`; one divergence case per container component, image by **digest** not tag |
| **V3b** | an exact-fileset assertion passes on a **single shared** cwd serving two program versions | V3b keeps the fileset assertion; **V3d** asserts each version's own driver bytes reached its own verdict |
| **V1c** | a manifest with no matching entry leaves nothing to compare | assert the manifest resolves and the entry is present before comparing bytes |
| **V3a** | a truncated forbidden set ⇒ fewer cases ⇒ still green | assert the set's **length**, one case per entry including the two absolute ones |
| **V3c** | an empty `--add-dir` set trivially satisfies "no entry is an ancestor of `$REPO`" | assert the set equals **exactly** the two expected paths |
| **V2e** | a `trace_ref` field that exists but points nowhere | non-empty file **and** the claim id present in its content; at run scale, trace count equals dispatch count |
| **V2f** | grepping for a token that was never set ⇒ nothing found ⇒ green | assert the variable **name** is present in the argv before asserting the **value** is absent |
| **V2h** (⚠ V2i struck by OQ1) | every attempt failing ⇒ green, but a broken container looks identical to a sealed one | each result attributed to a **named layer**, plus a positive control that must **succeed** (staging read). ⚠ V2i's own removal is the rule applied to this plan: it is struck, not reported green, because its subject no longer exists |
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
the real topology**, which OQ1 simplified: `dispatch_prompt.py` rendering the prompt and invoking the
judge directly, launched by the **same per-dispatch prefix factory** production uses (1c) — no driver
session, no Task subagent. A hand-built `docker run` measures a fixture
and tells us nothing about Phase 1c — and Phase 1c is where the review found the design could not
work. ✅ Add one assertion the older topology could not make: **no subagent is spawned**, since `Task`
is now off the allowlist and a dispatch that still spawns one means the driver prose was not fully
retired. One claim,
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
inventory:** the count of direct `SarolRunner` constructions equals **22** (NF11 — 19 in `adapter.py`,
plus `dispatcher.py:554`, `canary.py:257`, `scripts/run_baseline.py:119`), and each one is classified
as containerized or explicitly opted out — a source-level census in the selftest, so a new ungated
site added later fails the suite instead of running ungated. ⚠ Without the count assertion this gate
is green-by-absence: a refusal that applies to the sites we remembered is exactly what the first draft
shipped. ⚠ **The census must count subclasses, not text matches** — `_RealInvokerRunner`
(`adapter.py:2770`) inherits `__init__` and so is bound by the refusal while matching no grep for
`SarolRunner(`. A census that greps returns 22 and silently omits it; the assertion should be written
against constructor reachability.
⚠ **One negative control per production entry point**, not one for the class — and there are
**three**, not two: `build_components` (`dispatcher.py:554`), the **`components=` bypass**
(`run_optimization` accepts pre-built components and skips `build_components` entirely —
`dispatcher.py:604`/`:748`, exercised at `:1222`), and the baseline recut. The canary needs a case too,
though it already accepts an injected runner today. A test-only fake invoker must stay possible **without** creating a
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

⚠ **~~V2i — what the Task subagent inherits~~ — STRUCK by OQ1 (Phil, 2026-09-14).** It asked whether
the driver's policy reaches the Task subagent the judge used to be. With the driver session eliminated
the judge is the top-level session, the policy applies to it directly, and there is nothing to inherit
through. **Struck rather than marked green**, because a gate that passes for want of a subject is
green-by-absence — the failure mode this plan's own rule names. ✅ What replaces it is smaller and
stronger: V0c asserts **no subagent is spawned at all**, and V2h already probes the same four attempts
against the judge session itself. ⚠ If a future change reintroduces a subagent in the delivery path,
this gate comes back with it — rad-eval removed `Agent` from its allowlist precisely until inheritance
was demonstrated, and that precedent is unchanged.

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
- **V0b shows `--bare` refuses the `CLAUDE_CODE_OAUTH_TOKEN` env var** → drop `--bare` and set §2c's
  last row flag by flag, recording the two unverified env-var names as a residual. ✅ The older form of
  this fork (`--bare` omits `Task`, so it conflicts with keeping the driver) is **closed**: OQ1
  eliminated the driver, the judge needs no `Task`, and the omission is now a narrowing.
- **A delivery failure fires mid-run (OQ5 fail-and-feed)** → the iteration returns the failure to the
  optimizer rather than a score; record the delivery-failure count in the release breakdown so it is
  never read as a program-quality drop.
- **V5's number drops** → expected, not a regression. Record the new baseline as the honest one.
- **V2a-seal leaks** → halt at Step 2 under any schedule pressure.
- **V2a-seal's mount-set allowlist keeps needing entries** → each addition is a boundary widening and
  gets a written reason next to it; three or more means the mount set was designed wrong, so re-derive
  it from what the judge reads rather than appending.
- **V2c's census finds more than 22 construction sites** → the count moved under us; update the
  assertion *and* say which sites appeared, because a new ungated judge is the defect this plan is
  about. ⚠ The baseline is **22** (NF11), not the 21 earlier drafts asserted, and the census must
  count `SarolRunner` **subclasses** too — `_RealInvokerRunner` (`adapter.py:2770`) reaches an
  `__init__` refusal while matching no search for `SarolRunner(`.
- **V2f shows the by-name env form is not available on the pinned engine revision** → the engine
  change is a prerequisite (1b), so land it upstream first; do **not** ship the `-e KEY=VALUE` form
  with a note to fix later, which is how `optimizer_isolation_hash` became a literal string.
- **V2g finds the optimizer needs write access to something in the deny set** → name the file and ask,
  rather than widening. The scorer and the manifest are not negotiable (Phil); anything else is a
  design question about what the program *is*.
- ✅ **~~V2i — the Task subagent does not inherit the driver's policy~~ → MOOT.** This was a named halt
  condition whose resolution was *"drop the subagent path"*; OQ1 dropped it up front, so there is no
  subagent whose inheritance needs demonstrating and every flag applies to the judge directly. ⚠ V2i
  is struck from the gate list rather than left green-by-absence — a gate that passes because its
  subject no longer exists must say so, not report a pass.
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

**Landing gate.** ✅ **OQ1–OQ9 are all resolved** (2026-09-14), so what this gate now waits on is
`/read-plan` sign-off on the resolved plan — plus the one detail OQ9 left open, the `program-v*` tag
namespace (recommendation: key on `combined_hash`), which is a decision to record, not a phase to
design. Then: the five findings archived (a
Phase 4 precondition and the only copy); Step 0's probes run and recorded; **V2a-seal green,
including its negative control** — a land with either red is not a land; **V2c's 22-site census
green**, so no ungated judge ships; **V2d and V3d green**, because a reused prefix or a shared cwd
mis-attributes one program's behaviour to another and nothing downstream would show it; **V2h green with every result attributed to a layer**, since it covers the
threats the mount set cannot (⚠ **V2i is struck, not waived** — OQ1 removed the Task subagent it
tested); **V2e green**, so a containerized run is still auditable; the credential-by-name engine
change **landed upstream first** (Phase 1b is a prerequisite, not a follow-up); then `/review-implementation` → `/commit-review` → `/phi-vet`. No PHI is
expected anywhere here (claim ids and sentinel strings only), but the repo is gated. ✅ Codex credits
are restored, and this is a **rewrite** of a plan whose only review covered a different structure — a
cross-model pass is worth running.

**Merge sequence.** Plan A finished first, so: this plan rebases onto its tip, implements against a
10-entry manifest (`combined_hash 7431a5bc98a9`) and Plan A's three new preflight gates, then lands
after it. ⚠ **Rebase before you read the manifest — verified 2026-09-14.** On *this* branch the
manifest has **8 entries, `combined_hash 0a02710cbd88`, and does not contain the driver file at all**;
the 10-entry manifest carrying `.claude/commands/sarol-eval-item.md` exists only on Plan A's branch
(`origin/feat/optimizer-prompt-latitude`, tip `f02d761`). So an implementer who starts here will find
that the file OQ1's whole argument rests on is not a manifest entry, and conclude the plan is wrong.
It is not — it is forward-referencing, deliberately, and this is the line that says so. Plan B stays parked behind both, and must not start while Gate F's `KNOWN_DEFERRED` holds
six live contradictions in the stages it would enable. ⚠ Adding or removing a manifest entry breaks
five count/scope selftests (`adapter.py:1668`, `:1773` and its retrieval-scope assertion;
`profiles.py:262` and its retrieval-scope assertion) — update them individually.

**Contract owed to Plan A's baseline recut.** It must run on the **post-isolation** instrument: 61% of
iter-5 judges read a stale verdict, so a baseline measured today measures the contamination. The
landing order satisfies this. ✅ Its dependencies are now settled rather than pending: OQ5
(fail-and-feed) and OQ7 (injected fake prefix — so `run_baseline.py` takes the shipping factory and
gets **no** opt-out, which is what makes the recut and the iterations comparable at all). ⚠ Add OQ1 to
the list: the recut also runs on the no-driver topology, so it absorbs both the containerization and
the delivery-path change in one measurement.

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

**Cleanup on land.** ⚠ **Owed first: a naming consistency pass.** Phil's 2026-09-14 correction renamed
the contained principal from *the judge* to *the program* (see *Who is who*), and the body below still
says *judge* ~120 times — usually meaning the adjudicator stage, occasionally the program. The
definitions section governs; the body has not been swept. Do that before implementation starts, not
after, because the two readings differ exactly where it matters (a per-stage mount set versus a
per-claim one). Then `/land` prunes the branch (local + remote) and the worktree, marks this plan
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
