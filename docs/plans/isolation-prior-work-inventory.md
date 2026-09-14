Reference: docs/claude_ops.md

# Isolation: what already exists, across all four repos

**Written 2026-09-12** from a four-agent sweep of `agentic-label-opt`, `rad-eval`,
`crc-extraction-agent` and `paper-trail` — every branch, every worktree, every plan, and the VM
readbacks that record real runs. Commissioned because two sessions in a row concluded something was
unbuilt when it was already built and running.

## How to use this document

**The rule that makes it useful: current code beats every document, including this one.** Three
times in one day a doc said a thing was unbuilt and the code disagreed —
`agentic-label-opt/isolation/README.md:38-42` was six weeks stale about a parameter that ships with
a dedicated test; `rad-eval`'s protocol doc still calls a landed git parser "aspirational"; crc's
`docs/next.md:35-36` still says a VM verify is pending that passed on 2026-08-24. Prose goes stale
while code moves. Before trusting a line here, re-run the check in the *Evidence* column.

**Search every ref and every worktree, not just the checkout in front of you.** `rad-eval` has 19
worktrees; a Docker agent was declared absent because one `src/` was grepped. `agentic-label-opt`
has 6. Two isolation docs exist only on paper-trail's `main` and are invisible from the sarol
branches.

---

## 1. The ledger — capability, location, status

**BUILT** = code exists · **RUN** = evidence it executed on hardware · **DESIGNED** = a plan says so.

### In the shared engine (`agentic-label-opt`, `main` @ `c2dd0b3`) — depend on this, do not rebuild

| Capability | Where | Status |
|---|---|---|
| Container image, pinned CLI (`2.1.218`), non-root, probe tools guaranteed present | `isolation/Dockerfile` | BUILT + RUN |
| Mount/argv renderer — read-only program tree, per-file writable overlays, generic `extra_ro_mounts`/`writable_mounts`, `workdir`, `env`, `container_user`, `adc_path` | `isolation/docker_prefix.py:311-441` | BUILT, 54 tests |
| Mount-collision guards — reserved paths, ancestor targets, cross-list duplicate mode conflicts | `docker_prefix.py:66-71`, `:219-277` | BUILT |
| Network policy registry — `{none, vertex-only, open}`; an unknown name **raises** rather than silently sealing nothing; `_UNRESTRICTED_NETWORK_POLICIES` is machine-readable | `docker_prefix.py:47`, `:54`, `:526-532` | BUILT |
| Host-allowlist egress stack — `--internal` network with no route out + Squid CONNECT-only sidecar, caller-supplied host list, idempotent teardown | `isolation/network_allowlist.py:55-272` | BUILT, 24 tests + 3 leak tests; RUN |
| Squid ACL renderer — hostname-only (no reverse DNS), CONNECT-to-443 only, trailing deny-all, never MITMs | `isolation/squid/render_acl.py:16-53` | BUILT |
| Proxy-env precedence hardening — six vars, upper **and** lower case, applied over caller `env` so a caller cannot redirect the proxy. Lowercase is load-bearing: curl ignores uppercase for plaintext | `network_allowlist.py:142-163` | BUILT |
| Credential **file** mount — ADC read-only at a fixed path, explicit `GOOGLE_APPLICATION_CREDENTIALS`, container uid derived from the file's owner, uid-owned `0700` tmpfs HOME, `adc_path=None` drops all three atomically | `isolation/gcp_credentials.py:21-116` | BUILT + RUN |
| Read-only `.git`-free materialisation — files `0444`, directories non-writable so new files can't be created either; sha256-verified | `engine/materialize.py:40-113` | BUILT, 26 tests |
| Negative-control harness — built from the *real* materialise/commit primitives; `docker_available()` distinguishes "no daemon" from "no binary" so a skip can't pass as a pass | `isolation/negative_control.py:44-273` | BUILT, 15 tests; RUN |
| Tool-policy **decision logic** — fail-closed; parse failure denies, command substitution denies, `WebFetch`/`WebSearch`/`Agent` always denied, unmapped tool denied | `engine/policy.py:100-259` | BUILT, 16 tests — **decision logic only, no hook** |
| Merkle-chained audit ledger — sizes never content, canonical JSON, `verify_chain` | `engine/audit.py:41-156` | BUILT — **writer never called by engine code** |
| Four loop tripwires — broken chain, a final-evaluation row appearing mid-loop, an allowed-but-should-have-been-blocked path, denial count over threshold | `engine/loop.py:492-523` | BUILT, 7 tests |
| Materialised path threading into the agent call | `engine/loop.py:192`, `:426-431` | BUILT, 2 tests — ⚠ the README says otherwise and is stale |
| Release payload phase discrimination — a train payload structurally cannot carry validation metrics | `engine/schemas.py:207-235` | BUILT |
| PHI-shaped-breakdown denylist + size cap | `engine/schemas.py:26-42` | BUILT, heuristic by design |
| Out-of-process worker transport — designed so a two-container socket split swaps in without changing the protocol | `engine/worker_transport.py` | BUILT, 9 tests |

**Nothing is built-but-unlanded in the engine.** Verified four ways: every local branch is an
ancestor of `main`, `origin/main` matches, all 6 worktrees are clean, no stashes. One dangling
commit is a superseded pre-rebase draft containing no files `main` lacks.

### In rad-eval — the production consumer; copy its shapes

| Capability | Where | Status |
|---|---|---|
| **Docker agent** — prefix delegated to the engine, fresh temp writable staging, copy-back into the live clone, reduced tool set | `main:src/optimizer_loop/docker_agent.py` (198 lines) | BUILT + RUN; **copy this, don't invent one** |
| Dispatcher wiring — `--docker-agent`, `--network-policy` defaulting to the restrictive value | `main:src/optimizer_loop/dispatcher.py:2823-2968` | BUILT + RUN |
| OS-account sandbox — cross-user prefix, 15-var auth scrub, explicit `PATH`, arming flag | `dispatcher.py:723-790` | BUILT + RUN (production) |
| Per-run clone provisioning — `--no-local` forces pack transport (`--single-branch` alone leaves the object store hardlinked and report text recoverable via `git cat-file`), ownership hand-off, tag pruning, post-state assertions | `scripts/provision_loop_clone.py:203-259`, `:92-98` | BUILT + RUN |
| Permission hooks — thin interceptors over a decision engine; read whitelist, subtree prefixes, hard-denied absolute prefixes, bash command whitelist, git subcommand parser | `hooks/pretooluse_*.py`, `hooks/policy.py` (828 lines) | BUILT, tested — ⚠ the protocol doc calls the git parser "aspirational"; stale |
| Audit broker — single append point under an exclusive lock so hook processes extend one chain rather than forking it | `hooks/audit_broker.py:58-99` | BUILT + RUN |
| **Runtime syscall denial for agent-authored Python** — a Python audit hook installed *before* the program loads, denying the **actions** `os.system`, `subprocess.Popen`, `socket.__new__`. Hooking the action, not the import, means reflective construction still trips | `src/optimizer_loop/materialized_worker.py:127-144` | BUILT — **the answer to "agent code opens a socket"** |
| Static deny-list scan at freeze time, with its own limits documented | `src/optimizer_loop/deny_list_scan.py` | BUILT |

### In crc — a *filesystem* fence, proven; and the two-container design

| Capability | Where | Status |
|---|---|---|
| Stage-2 container — one per entity, **no agent inside it** | `agent/optimizer/docker/factory.py` (286 lines) | BUILT + RUN GREEN 2026-08-24, 64 tests |
| **Gold sealed by absence at three layers** — absent from both mount lists, explicitly not baked (`Dockerfile:12-15` "Do not `COPY eval_pipeline/` wholesale"), and `.dockerignore`d. Verified empirically on the VM by `find` returning empty | `factory.py:214-221`, `docker/Dockerfile:12-15` | BUILT + RUN — **the cheapest known answer** |
| Explicit 8-key env allowlist, replacing a whole-environment splat that had been leaking the host env onto the argv | `factory.py:151-160` | BUILT |
| Split leakage guard — raises on any prediction whose subject isn't in the claimed split | `adapter.py:608-616` | BUILT, tested |
| Train-only batch invariant; train-only corpus routing at the engine seam | `dispatcher.py:615-621`; `engine/loop.py:407-409` | BUILT, tested |
| Content-addressed bucket object store for optimizer-authored artifacts — create-only, read-back verified, git keeps only pointers | `agent/optimizer/run_store_bucket.py` | BUILT, 31 tests; plan Approved/Reviewed 2026-09-09 |

### In paper-trail — three real mechanisms, and five months of unbuilt drafts

| Capability | Where | Status |
|---|---|---|
| Gold + benchmarks out of the tree; opaque claim keys (`sha256("split\|claim_id\|bucket")[:6]`) | `scripts/stage_claim.py:41-63`; `parse_verdict.py:48-64` is the sole gold boundary | BUILT + RUN |
| Test split physically sealed, with a negative-controlled tripwire | `~/.paper-trail-sealed/sarol-2024-test` | BUILT + RUN 2026-09-09 — had been sitting *unsealed*; re-sealed and proven load-bearing |
| Validation reduced to a scalar; validation outputs outside the repo, gated so the loop cannot be wired without the check | `adapter.py:1482-1513`; `dispatcher.py:467-500` raised at `:549-551` | BUILT + RUN |
| Contract-file immutability — re-hash after the edit pass, exit 91 → halt before scoring or commit | `adapter.py:1591-1626`, enforced at construction `dispatcher.py:523-526` | BUILT |
| Per-call and per-agent hard spend caps; strict MCP config | `dispatcher.py:431-433`; `adapter.py:726-733` | BUILT |
| Rule-3 invocation stack (`env -i`, fresh config dir, `--add-dir`, clean cwd, session-persistence and dynamic-prompt flags, tool allowlist, `--bare`) | specified `experiment-sarol-eval-arm-isolation.md` | **NONE BUILT** — zero of those appear in any file on any ref |
| Frozen eval arm (`eval-harness/`), pre-commit seal hook, the six-directory layout, `dev/isolation/` | specified in three docs | **NONE BUILT** — the directories have never existed on any ref |

---

## 2. Decisions already made — do not re-litigate

| Decision | Who / when | Where |
|---|---|---|
| **The dispatcher is deterministic Python, never an agent.** "It only ever reports back the F1 scores and does not allow the main optimizer agent to look at what those sub-agents did" | Phil, 2026-04-21 (D26) | `docs/journal/2026-04-21-tiered-leakage-framework-decisions.md:43-47` |
| Uniform subagent invocation across train and validation — "the subagent doesn't behave differently on train vs val. The dispatchers behave differently" | Phil, 2026-04-21 (D28) | same, `:57-61` |
| Train fully open including gold / validation scalar-only / test sealed | Phil, 2026-04-21 (D24) | same, `:34`; formalised `agentic-pipeline-optimization-framework.md:53-98` |
| Eval arm lives in the same repo subdirectory, not a separate repo | Phil | `experiment-sarol-archive-and-eval-framework.md:50-55` |
| **Docker for the per-claim tier rejected on startup cost**, adopted for the landmark tier only | 2026-04-23 | `experiment-sarol-eval-arm-isolation.md:174` — ⚠ **REVERSED 2026-09-12, see below** |
| Separate OS user deferred — "`CLAUDE_CONFIG_DIR` gets same cheaper" | 2026-04-23 | same, `:167` |
| Residual risk accepted: three exact leakage vectors named, "these require deliberate effort; the defenses make casual or accidental leakage structurally impossible" | 2026-04-23 | `experiment-sarol-hardening-implementation.md:78-84` |
| Threat model is honest optimisation, not an adversary | 2026-04-21 | `agentic-pipeline-optimization-framework.md:319` |
| **Least privilege comes from what is mounted, not from an extra permission check** — "it should just not be mentioned; it has no value" | Phil, 2026-09-03 (crc ruling I) | crc `2026-08-25-…md` Decision Log |
| Optimizer hard-coding to train is acceptable — "that is what optimizing on TRAIN means" | Phil, 2026-09-03 (crc ruling J) | same |
| Train chart quotes reaching the optimizer are intended signal, contained by train-only + private dataset + restricted egress | Phil, 2026-08-25 (crc Q6) | same |
| **Two-container boundary**: network-denied optimizer ⊕ a dispatcher sibling holding the *only* gold/test mount — "not the optimizer alone" | locked, umbrella plan | crc `2026-07-10-shared-optimization-engine-package.md:60`, `:232-237` — **DESIGNED, NEVER BUILT** |
| Docker was always the intended end state; the OS-account sandbox was deliberately interim | Phil | `agentic-label-opt/docs/plans/2026-07-22-…:9` |
| rad-eval is the precedent; paper-trail's own Docker sketches are not validated precedent | Phil | same, `:19` |
| Build the egress primitive generic, ship only one profile — don't build a one-off that becomes debt when other consumers need theirs | Phil, 2026-07-30 | egress plan |
| **The network profile is paper-trail's own to own** — adding a paper-trail policy to the engine's registry re-litigates a resolved question | Phil, 2026-08-18 | `2026-08-10-optional-edit-agent-mounts.md:137-146` |
| Editable-file set is plural **because of paper-trail** — "paper-trail is a future consumer and the shape is designed for it" | Phil, 2026-08-18 | same |
| Credential-file-optional supported, because paper-trail's tier authenticates with a token env var and no credential file | Phil, 2026-08-18 | same |
| Permission-hook wiring is a separate follow-up, not part of the substrate | Phil, 2026-07-22 | substrate plan `:54` |
| Negative controls are non-agentic probes in v1 | Phil, 2026-07-22 | same |
| Nested-agent sandboxing is a **general engine capability**, not a paper-trail bolt-on | Phil, 2026-07-20 (umbrella #22) | umbrella plan |
| Per-claim driver file is optimizer-editable, whole file | Phil, 2026-09-10 | `profiles.py:50-56` |
| A new guard is not done until you have watched it fail | Phil, 2026-09-02 | `NEXT.md:117` |

**Reversal, recorded deliberately.** On 2026-09-12 Phil reversed the 2026-04-23 rejection of
containers for the per-claim tier, on two grounds: the original was costed against *thousands* of
invocations where the real number is 561 (≈14 minutes on a multi-hour run), and it was explicitly
conditional on finding a concrete case where prose is insufficient — which the 2026-09-09 run
produced, when task-less sessions began enumerating the optimizer's own findings. Both agents are to
be containerised, scoring and gold kept outside, permission rules deferred to a second landing.

---

## 3. What is genuinely NOT built — the real scope

1. **No judge/dispatcher container anywhere.** The shipped shape everywhere is *one agent container*
   (+ a proxy sidecar). The runner, the scorer, the gold labels and the commit all live in the host
   process. crc's umbrella plan designed the gold-holding dispatcher sibling and it was never built.
   **This is the one place paper-trail's framing adds something new — and it is a deviation from the
   built substrate, so it must be stated as such rather than assumed to exist.**
2. **No consumer-side agent class in paper-trail**, and **no dependency on the engine at all** — two
   prose mentions, no package dependency. rad-eval pins it as a git revision.
3. **Credential *env vars* land in the container's command line.** The renderer always emits
   `-e KEY=VALUE`; there is no by-name form on any ref, and the wrapper records the full command to a
   metadata file. paper-trail's documented auth path is exactly this one.
4. **Docker sessions write zero audit rows** (`docker_agent.py:84` discards the ledger), so the four
   tripwires — including the one guarding against a final-evaluation record appearing mid-loop — are
   blind in container mode.
5. **No gold-shaped envelope rule.** The PHI denylist covers subject ids and chart text; nothing
   rejects `gold`, `label`, `truth`, or per-example list structures.
6. **No permission-hook wiring in any consumer.** The engine has decision logic and no hook; crc has
   neither; paper-trail has no settings file at all, so its `--setting-sources project` reads nothing.
7. **No seccomp/AppArmor** beyond Docker defaults. Start from rad-eval's existing spec, not scratch.
8. **paper-trail's own egress profile** — unbuilt by design, paper-trail's to own.

---

## 4. Traps

- **Advisor-facing prose claims isolation that does not exist.** `advisor-pitch.md:87-115` describes,
  in the present tense, a pinned binary in Docker with a scrubbed environment and session flags.
  None of it exists; only its test-seal row is true.
- **Nine other stale claims in paper-trail's own docs**, including a pre-commit hook recorded as
  enforcing the test seal (no hook of any kind exists), a "permission-locked" gold directory that is
  mode `0755` with the same owner, and `dispatcher.py:470`'s claim that the optimizer's readable
  scope is its tree — true of one tool, false of shell access under permission bypass.
- **A branch carrying real chart text.** crc's `pre-rewrite-pos` (`f4993e6`) is **not** an ancestor of
  the trunk and holds nine committed spec files containing real chart text. The umbrella plan carries
  a standing negative control: it must never be merge-base-selected or used as a program source,
  asserted by that SHA.
- **Don't mirror the operator's personal settings into a sandbox.** rad-eval's provisioning explicitly
  refuses to copy one file — the local auto-approve settings — because it would hand the agent a
  blanket permission override.
- **rad-eval's primary checkout is mid-reconciliation**: 80 staged paths rewinding the isolation stack,
  including a policy file at a blob matching neither HEAD nor main. Nothing unique is at risk, but do
  not run tree-wide git commands there without finding out whose session owns it.
- **Several copies of `isolation/` exist on this machine** (two gate checkouts, a vendored pin, eight
  cache archives). Pin to the installed package or to `agentic-label-opt` directly rather than
  whatever `find` returns first.
- **paper-trail's `main` and its sarol branches have nearly disjoint plan sets** — two isolation docs
  and a journal entry exist only on `main`, and each side has a different tracker. A reader on either
  side misses half the history.

## 5. Unverified — treat as open

- **The engine's negative-control suite has not been verified since the 2026-08-21 refactor.** That
  refactor touched the test file; the last real-Docker verification is 2026-08-05, before it. Both
  images exist on this box but no document records a run.
- **"Fake fixtures reproduce the property you thought to fake."** The suite once passed 15/15 while
  the real credential was unreadable, because the fixture used permissive modes where production used
  restrictive ones. Mirror production modes in any control written from here.
- Cross-uid writability of prepared mounts was never proven — the assertion is on mode bits only.
- The generic egress stack has never been exercised with a second host list against a real daemon.
- Whether anything redacts the session metadata file (which contains the full command) before it
  leaves the VM.
- Whether crc's real optimizer agent has ever executed.
