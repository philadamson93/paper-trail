Reference: docs/claude_ops.md

# Feedback: The isolation protocol (Codex review)

## Verdict

Blocked. The rewrite correctly reuses the engine's generic mount renderer, and OS mount permissions are sufficient to keep an unmounted scorer unwritable, but the proposed shipping path cannot yet construct the per-claim/per-version container correctly and it defers the still-uncontained optimizer principal that the plan itself calls half of isolation. Several claimed proofs are also vacuous against alternate mount targets, ephemeral container traces, mutable image contents, and open-egress credential exfiltration.

## Critical Gaps

- Severity: Critical | Gap: The plan defers the optimizer write boundary on a false engine premise. The pinned engine already passes `materialized_path=current_materialized` to `agent.run`; it has done so since `10c2e33`, and `82f547d` contains both the call and a dedicated test. The remaining work is the consumer-side DockerAgent/copy-back integration, not threading a missing engine argument. | Why it matters: paper-trail's current `OptimizerAgent` still runs at the live repo root with `--dangerously-skip-permissions`, and `build_components` still constructs it directly. It can edit scorer/harness Python and run artifacts even if the judge is sealed. The plan therefore lands only one principal while claiming the no-cheating boundary is structural. | Evidence: /home/philadamson/engine-82f547d/engine/loop.py:192, /home/philadamson/engine-82f547d/engine/loop.py:399, /home/philadamson/engine-82f547d/tests/test_materialized_path_threading.py:76, experiments/sarol-2024/optimizer/dispatcher.py:381, experiments/sarol-2024/optimizer/dispatcher.py:415, experiments/sarol-2024/optimizer/dispatcher.py:570, docs/plans/isolation-protocol.md:79 | Required fix: move the DockerAgent/copy-out/copy-back work into this plan as blocking paper-trail consumer work, modeled explicitly on rad-eval's landed consumer implementation, or rename/scope the deliverable to “judge read isolation” and add a hard refusal that prevents any optimizer run or baseline recut until the write boundary lands.

- Severity: Critical | Gap: Phase 1c describes a Docker prefix bound in `build_components`, but the required mount inputs do not exist there. `materialized_path` changes on every Runner call and `claim.staging_dir` changes on every claim; `_stage_command` currently embeds their host absolute paths in the slash-command text. | Why it matters: a prefix constructed once cannot mount the correct per-version spec tree or per-claim writable staging tree. Even if Docker starts, the in-container command receives host paths that do not resolve to the engine's `/workspace/...` mount targets. This invalidates the central “driver and Task subagent are transitively containerized” execution path. | Evidence: experiments/sarol-2024/optimizer/adapter.py:700, experiments/sarol-2024/optimizer/adapter.py:708, experiments/sarol-2024/optimizer/adapter.py:840, experiments/sarol-2024/optimizer/adapter.py:866, experiments/sarol-2024/optimizer/adapter.py:868, experiments/sarol-2024/optimizer/dispatcher.py:553, /home/philadamson/engine-82f547d/isolation/docker_prefix.py:407, /home/philadamson/engine-82f547d/isolation/docker_prefix.py:434, docs/plans/isolation-protocol.md:340 | Required fix: specify a per-dispatch prefix factory owned by `SarolRunner.process(claim)` (or an equivalent callable seam), define canonical container paths for staging/spec/cwd, translate every prompt and `--add-dir` path to those container paths, and test two claims plus two materialized versions to prove neither prefix is reused incorrectly.

- Severity: Critical | Gap: a fixed minimal `working_checkout` cannot preserve the now-editable driver across iterations. The plan builds/passes it at component construction, while the correct driver bytes live in each `materialized_path`. | Why it matters: if the snapshot cannot be cwd and a one-time copy is used, every later program version silently executes the baseline driver; if it is copied from the live repo, it can instead execute bytes ahead of the version being scored. Either failure breaks the program-version contract while the manifest and metric still look valid. | Evidence: experiments/sarol-2024/optimizer/adapter.py:628, experiments/sarol-2024/optimizer/adapter.py:643, experiments/sarol-2024/optimizer/adapter.py:734, experiments/sarol-2024/optimizer/adapter.py:868, docs/plans/isolation-protocol.md:352, docs/plans/isolation-protocol.md:535 | Required fix: make cwd version-addressed. Prefer the current materialized snapshot if V0c proves it works; otherwise construct a per-Runner-call working directory from that snapshot's command blob, never a once-per-`build_components` copy. Add a negative control where v0 and v1 drivers emit distinct markers and assert each call executes its own marker.

- Severity: Critical | Gap: mounts alone do not cover the credential/network threat created by `network_policy="open"`. The engine renders every `env` value as `-e KEY=VALUE` in the host-visible Docker argv, and the plan gives a Bash-capable, optimizer-editable driver an OAuth token plus unrestricted egress while deferring both the network allowlist and hook wiring. | Why it matters: the judge or Task subagent can read/exfiltrate `CLAUDE_CODE_OAUTH_TOKEN`; the token can also leak through process listings, logs, captured argv, or test failures. rad-eval's production layering exists specifically because filesystem permissions do not restrict Bash/WebFetch/network behavior: `--allowedTools` removes whole tools and PreToolUse hooks fail closed per call. | Evidence: /home/philadamson/engine-82f547d/isolation/docker_prefix.py:437, /home/philadamson/engine-82f547d/isolation/docker_prefix.py:504, /home/philadamson/code/rad-eval/src/optimizer_loop/allowed_tools.py:3, /home/philadamson/code/rad-eval/src/optimizer_loop/allowed_tools.py:20, /home/philadamson/code/rad-eval/.claude/settings.json:7, /home/philadamson/code/rad-eval/hooks/policy.py:404, /home/philadamson/code/rad-eval/hooks/policy.py:729, docs/plans/isolation-protocol.md:319 | Required fix: make credential-safe injection and egress control a landing prerequisite. Define an exact least-privilege tool surface (including the required Task tool), prove `env`/`printenv`, arbitrary Bash, WebFetch, and outbound token exfiltration fail, and use a token transport that does not place its value in argv (for example inherited named env with sanitized `Popen(env=...)` plus Docker `--env NAME`, or a tightly permissioned mounted secret). This may require an engine API change; do not preserve “zero diff” at the expense of the secret.

- Severity: Critical | Gap: containerization discards the judge traces Plan A requires. `find_transcript` searches host `~/.claude/projects`, but a `--rm` container with a fresh in-container `CLAUDE_CONFIG_DIR` writes its transcript into an ephemeral filesystem unless that state is mounted and mapped back. The proposed mount set has no trace/config mount and V5 does not assert trace survival. | Why it matters: `trace_ref` becomes null for every containerized claim, undoing Plan A's central “ground blame in traces” capability and making the fixed instrument less diagnosable than the defective one. | Evidence: experiments/sarol-2024/optimizer/adapter.py:427, experiments/sarol-2024/optimizer/adapter.py:438, experiments/sarol-2024/optimizer/adapter.py:869, experiments/sarol-2024/optimizer/adapter.py:891, docs/plans/optimizer-prompt-investigative-latitude.md:163, docs/plans/isolation-protocol.md:408, docs/plans/isolation-protocol.md:786 | Required fix: define a per-invocation host-backed trace/config directory inside the allowed writable staging/run-output surface, pass its container path as `CLAUDE_CONFIG_DIR`, teach transcript resolution the host mapping (or persist normalized stream-json directly), and require non-null readable `trace_ref` in V2a-live/V5.

- Severity: Critical | Gap: V2a-seal is not a complete proof of the mount seal. Probing a host path at the same absolute path inside the container misses an accidental broad bind mounted at a different container target; the sentinel remains readable under that alternate target while every named `cat <host-path>` probe fails. | Why it matters: the plan can certify the exact over-broad mount defect it is intended to catch. The configuration hash can even bless that bad mount, because a pin proves consistency, not safety. | Evidence: /home/philadamson/engine-82f547d/isolation/docker_prefix.py:352, /home/philadamson/engine-82f547d/isolation/docker_prefix.py:434, /home/philadamson/engine-82f547d/isolation/negative_control.py:266, docs/plans/isolation-protocol.md:707 | Required fix: assert the rendered `-v` source/target/mode set equals an exact allowlist before running probes, reject ancestor host sources, and probe sentinels through every rendered mount target (or search every mounted readable root by sentinel content). Add the negative control “mount the repo/home at an unexpected container target” and require V2a-seal to fail.

## Failure Modes

- Scenario: the Runner uses one prefix for claim A and then claim B or for `iter1-current` and `iter2-current` | Why the plan misses it: prefix construction is assigned to `build_components`, outside both dynamic scopes | What to add: a two-claim/two-version spy test that captures exact host sources, container targets, cwd, prompt paths, and `--add-dir` values for all four dispatches.

- Scenario: the driver launches correctly, but the Task tool is omitted by `--bare`/`--allowedTools`, or a Task subagent does not inherit the intended CLI policy | Why the plan misses it: V0b tests flag observables generically and V2a-live asks only for a valid verdict; rad-eval explicitly removed Agent until inheritance was proven | What to add: a purpose-built driver→Task negative control in which the inner subagent attempts one allowed staging read, one forbidden sentinel read, one forbidden scorer write, and one outbound request; assert each layer's result.

- Scenario: the first no-task attempt and the one re-dispatch both fail | Why the plan misses it: option (a) says coverage “holds by construction,” but a retry does not guarantee output; the final batch status aggregation at `adapter.py:1111-1122` is not included in the lockstep surfaces | What to add: define terminal semantics after retry exhaustion and test the Runner record status, batch `RunArtifacts.status`, scorer denominator, `n_invalid`, new `n_infra`, release reduction, and mistake-corpus exclusion together.

- Scenario: retrying in Runner Python changes the sampling distribution despite the driver still saying “Never retry a stage” | Why the plan misses it: the plan relies on Gate F's blind spot—Gate F scans prose outside prompt markers, not Python—to call the prohibition “literally true from the driver's vantage” | What to add: treat OQ5(a) as an explicit system-contract change, not a placement trick; update the invariant/gate vocabulary to distinguish one dispatch per attempt from at-most-two attempts per claim and record attempt count in the manifest.

- Scenario: an uncontainerized direct `SarolRunner` is constructed by `canary.py`, `run_baseline.py`, or an adapter selftest | Why the plan misses it: V2c requires Runner-level refusal, but Files to Modify accounts only for seven `build_components` callers and one baseline call; there are more than twenty direct constructions in `adapter.py` plus a live construction in `canary.py` | What to add: choose one refusal locus, inventory every direct constructor, and require explicit `isolation_mode="test"`/injected fake prefix only in offline tests; no production opt-out.

- Scenario: the same image tag is rebuilt with a different CLI, user, base image, or Dockerfile, or `network_policy`/exact allowed-tools changes | Why the plan misses it: Phase 3's hash enumerates fileset, add-dir, env names, mount manifest, and permission mode only; V4's “changing any component” cannot fail for omitted components | What to add: hash a canonical security-config schema including image digest, CLI version, network policy, container user, workdir, exact flags/tool patterns, canonical mount roles/targets/modes, trace mount, and refusal mode; exclude secret values but include required secret names.

- Scenario: Phase 4 computes a run-scoped path but never provisions the clone, verifies the source SHA/object scope, or directs dispatcher/release/tag operations into it | Why the plan misses it: rad-eval's `default_loop_clone` only returns a path; its separate provisioning and safe-directory machinery do the security work, and no Phase-4 implementation file is listed | What to add: name the paper-trail provisioning module/script, source ref, clone options, ownership, resume behavior, tag policy, all consumers of `REPO_ROOT`, and tests proving two run ids isolate releases/tags/findings.

## Contract Checks

- paper-trail | `SarolRunner` invocation contract: add a dynamic prefix/path-map seam without widening the three-argument `Invoker` spies accidentally; define separately the sanitized host `Popen` environment and the container environment. Current owner surfaces are `adapter.py:332`, `adapter.py:444`, `adapter.py:700`, `adapter.py:840`, and `adapter.py:868`.

- paper-trail | Output contract: OQ5 changes must update per-claim records, `write_manifest.requested_count`, batch status aggregation, `SarolScorer` coverage, `_VAL_BREAKDOWN_ALLOWED`, `SarolReleaseBuilder`, mistake-corpus routing, and any run-summary consumers. The plan currently names only a subset (`adapter.py:1006`, `:1371`, `:1382`, `:1414`).

- paper-trail | Version contract: the driver is a non-contract manifest entry, so cwd/command discovery must resolve the driver from the exact materialized version being scored. `command_path()` against a fixed checkout is no longer a valid implementation.

- paper-trail | Trace contract: `InvocationResult.session_id`, `find_transcript`, per-stage `trace_ref`, copied trace artifacts, and Plan A's optimizer instructions must remain usable after Docker `--rm`.

- paper-trail | Cache/budget contract: preserve `CachingRunner` and `BudgetGuard`, but make retry attempt costs and cache eligibility explicit. A claim-local retry happens inside the cached batch execution and must be included in `sub_invocation_count` and `cost_usd`.

- paper-trail | Baseline/canary contract: `run_baseline.py` and `canary.py` construct `SarolRunner` directly and bypass `build_components`; both need the same shipping isolation factory, not a reasoned opt-out, because both produce or guard reportable numbers.

- agentic-label-opt | Public mount renderer: the judge shape is expressible with `edit_agent_mounts=None`, `extra_ro_mounts`, `writable_mounts`, `workdir`, `container_user`, `adc_path=None`, and `env`; no judge dataclass is needed. Correct. However, `writable_mounts` is directory-oriented and host preparation is explicitly separate (`prepare_writable_mounts`), so paper-trail must own permissions and test the real uid.

- agentic-label-opt | Claimed shared footprint: it is not one file. Adding controls to `isolation/negative_control.py` requires corresponding assertions in `tests/test_isolation_negative_control.py`; reproducibly changing the image's pinned CLI also implicates `isolation/Dockerfile` and `isolation/README.md`. More importantly, paper-trail-specific sentinels/auth belong in paper-trail unless the upstream change is made genuinely generic and tested there.

- agentic-label-opt | Engine loop: `materialized_path` threading is already complete in the pinned SHA. No `loop.py` change is owed for that. A consumer DockerAgent can hold cwd/env/repo-root state at construction just as rad-eval's does.

- rad-eval | Enforcement precedent: its hooks police Read/Bash/WebFetch, `--allowedTools` removes WebSearch/Agent, and OS permissions—not hooks—police Write/Edit. Therefore the plan's narrow statement “an unmounted scorer cannot be written” is correct, but the broader implication “mounts alone provide the whole isolation protocol” is false for command, egress, credential, audit, and subagent-inheritance threats.

- rad-eval | Per-run clone precedent: `src/optimizer_loop/run_artifacts.py::default_loop_clone` is only path derivation. `scripts/provision_loop_clone.py`, ownership, `--no-local`, safe-directory reads, dispatcher adoption, and resume rules are part of the landed contract and must be evaluated before copying the pattern.

- crc and MedVAL | No sibling consumer needs a source change for a paper-trail consumer using existing mount parameters. A change to engine env transport or a generic refusal API would be additive, but it must retain current flat/bundled mount call shapes and the `resolved_cmd_prefix` union contract.

- Plan A coordination | `94a376f` is not the current tip of `feat/optimizer-prompt-latitude`; that branch is at `f02d761` and contains later gate hardening and baseline fixes. At exactly `94a376f`, the measured suite is not 447/447: sampling is 48/50, yielding 445 passing checks. At `f02d761`, the seven modules do produce 447/447. The new plan must name the real integration base or explicitly explain why the later fixes are excluded.

## Re-use vs. building something you don't need yet

- Decision point: `inner_scope_problem` | Plan's current choice: new predicate in `optimizer/isolation.py` that copies `val_isolation_problem`'s resolve/parent idiom | Reusable alternative + the realistic use case: extract one tested path-containment primitive used by both checks; VAL isolation and judge-readable-scope checks need the same symlink-resolved containment semantics | Recommendation: factor the primitive and retain two thin, domain-named policies/messages.

- Decision point: judge mount-set builder | Plan's current choice: consumer builder over engine generic parameters | Reusable alternative + the realistic use case: call `build_docker_cmd_prefix` directly from a thin per-dispatch paper-trail configuration object; the engine already owns mount validation/rendering | Recommendation: keep only canonical roles/container-path selection and hashing in paper-trail; do not re-render `-v`, revalidate collisions, or introduce a `JudgeMounts` mirror.

- Decision point: prompt marker parsing | Plan's current choice: new `dispatch_prompt.py` reads text between markers | Reusable alternative + the realistic use case: Plan A's `check_orchestrator_consistency.py::orchestrator_region` already owns the same two marker constants and split semantics | Recommendation: factor a shared `dispatch_region()`/marker module and have both the gate and renderer call it; otherwise malformed/duplicate markers can be interpreted differently by the verifier and shipping renderer.

- Decision point: slot-source loading | Plan's current choice: new renderer rereads `staging_info.json` and evidence JSON | Reusable alternative + the realistic use case: `evidence_producers.produce` already owns `staging_info.json` loading and `claim_text_normalized`; multiple profiles need one join contract | Recommendation: implement the plan's proposed shared slot-source helper and make both producer/renderer call it. Reusing only error strings such as `CLAIM_ID_MISMATCH` is not logic reuse.

- Decision point: committed pin read/refusal | Plan's current choice: new configuration hash gate modeled on `canary.py` | Reusable alternative + the realistic use case: Plan A now has multiple committed-byte readers (`check_run_scope.stub_bytes`, manifest generator selftest); every preflight pin needs the same `git show HEAD:path`, missing-key, and malformed-value semantics | Recommendation: factor a small committed-JSON reader or state why isolation is intentionally separate; do not duplicate another subtly different fallback to worktree bytes.

- Decision point: optimizer DockerAgent | Plan's current choice: defer it as engine work | Reusable alternative + the realistic use case: rad-eval's `DockerAgent` already demonstrates materialized input, temp writable copies, allowed tools, prefix construction, copy-back, and structural tests; paper-trail needs the plural-file version now | Recommendation: model the consumer implementation and tests directly on that sister file. Raise to user only if the intent is deliberately to land judge-only isolation.

- Decision point: per-run clone | Plan's current choice: “adopt `default_loop_clone`” with no implementation surface | Reusable alternative + the realistic use case: either extract a generic engine clone-provisioning helper after comparing rad-eval's ownership/PHI constraints, or build a paper-trail provisioner modeled on both `run_artifacts.py` and `provision_loop_clone.py` | Recommendation: do not copy the path helper alone; specify the complete lifecycle first. Phase 4 is not build-ready today.

## Verification Gaps

- The green-by-absence table is incomplete. It omits V0b, V0c, V1a, V1b, V2a-live, V2c, and V5, even though several can pass without exercising the shipping seam. Add every named gate and state its independent anti-vacuity observation.

- V0b needs exact candidate-count and exact shipping-argv assertions. A matrix row can disappear and the remaining rows still pass; a flag can work in a scratch CLI probe yet be dropped by `_stage_command`.

- V0c must use the real driver→Task topology and the same per-dispatch prefix factory as production. A direct judge prompt or hand-built Docker command does not verify Phase 1c.

- V1a needs collision-proof archive naming and error-sidecar behavior. Assert two archived attempts cannot overwrite, live verdict/error paths are absent before each attempt, and archives never enter the judge's readable mount unless intended.

- V1b must cover all three OQ5 options at the full Runner→RunArtifacts→Scorer→Release seam before one is chosen. Option (c) is already close to current behavior: an unreadable verdict under `invalid_output` is scored as `INVALID_OUTPUT` and is not appended to `joined`, so it is already excluded from the mistake corpus. State what new field/metric it adds rather than presenting it as wholly new.

- V1c's “zero shell metacharacters remaining” is not a coherent prompt contract: ordinary claim/evidence text can legitimately contain shell metacharacters. Assert no unresolved template tokens and no shell evaluation because the prompt is passed as one argv element; do not reject content characters.

- V2a-seal needs exact mount-source/target/mode assertions and an alternate-target broad-mount negative control, as above. It also needs to assert the production Runner used that exact prefix factory; a standalone engine fixture proves only the fixture.

- V2a-live/V5 need non-null persisted traces, explicit Task-tool availability, exact in-container CLI/image digest, OAuth-token non-disclosure, and an adversarial forbidden-read/write/egress attempt. A valid verdict alone proves functionality, not isolation.

- V2b's claimed baseline cannot be rerun in this sandbox because access to `/var/run/docker.sock` is denied. The implementation handoff should record the actual engine SHA, image digest, Docker version, full pytest counts, and zero skips on the VM rather than rely on the historical 104 number.

- V2c needs a negative control for every production constructor (`build_components`, canary pinning, baseline recut, CLI runner), not only `CachingRunner` wrapping. A test-only fake invoker must remain possible without creating a production bypass.

- V3b must assert driver bytes equal the matching materialized manifest entry for each call, not merely exact fileset/no `.git`/no `CLAUDE.md`.

- V3c must distinguish host launcher env from container env and must inspect secrets redacted. Asserting `functools.partial.keywords` risks printing the OAuth token in a failing test; compare key sets and redacted values only.

- V4 is the third clear green-by-absence hole: its hash omits security-relevant configuration and a mutable tag is not an image identity. Add the canonical schema and a mutation test for every field, plus a test that rebuilding the same tag to a different digest fails.

- V5's “zero no-task sessions” is stochastic and cannot be a stable success criterion for a small batch; the load-bearing criterion is that any induced no-task result is detected and handled according to OQ5. Keep the observational zero as telemetry, not the sole gate.

- The baseline claim needs correction: `adapter.py` without `AGENTIC_LABEL_OPT` does print `PASS ... engine-facing checks SKIPPED` and `32/32 passed`, as stated. With the engine set, 447/447 reproduces at `f02d761`, not at the declared `94a376f` base.

## Handoff Readiness

- Question unanswered: Where and when is the Docker prefix built when both claim and materialized version are dynamic? Proposed fix: specify the Runner callable seam, canonical container path map, lifecycle, and two-claim/two-version test.

- Question unanswered: Which bytes provide the slash command on iteration N? Proposed fix: bind cwd to N's materialized snapshot or build N's working directory from it and assert byte identity.

- Question unanswered: How do container-generated transcripts survive `--rm` and map back to `trace_ref`? Proposed fix: define the mounted config/trace directory and host/container mapping contract.

- Question unanswered: How is the OAuth token passed without appearing in argv, and what prevents the agent from exfiltrating it over open egress? Proposed fix: make secure env transport plus egress/tool negative controls part of Phase 1.

- Question unanswered: What exact files implement Phase 4 clone creation/adoption/resume/cleanup? Proposed fix: add the provisioner, VM runner, dispatcher/root-resolution, tests, and docs to Files to Modify with the sister files and line ranges from rad-eval.

- Question unanswered: Where does the uncontainerized-run refusal live, and how do canary/baseline/tests comply? Proposed fix: inventory every constructor and define a single production-default fail-closed policy with explicit test injection.

- Question unanswered: What is the schema-of-record for isolation configuration? Proposed fix: write the canonical JSON shape in the plan, including all hash fields, normalization rules, committed pin key, redaction rule, and re-pin command.

- Question unanswered: What happens after the permitted re-dispatch also produces no verdict? Proposed fix: define attempt exhaustion through record, batch, score, release, corpus, and comparison semantics before implementation.

- Question unanswered: Which Plan A commit is the actual merge base? Proposed fix: rebase onto the current reviewed/accepted tip, rerun the seven-module baseline there, and update all line references/counts; if `94a376f` is intentionally authoritative, explain why the later fixes through `f02d761` are excluded.

## Suggested Revisions

- Replace “What the engine still owes” item 1 with the verified state: materialized-path threading is landed in `82f547d`; paper-trail owes a plural-file consumer DockerAgent. Classify it as blocking if this document continues to promise the optimizer write boundary.

- Rewrite Phase 1c around a per-dispatch prefix factory and an explicit host→container path map. Show the exact example argv for one claim, including mounts, container cwd, prompt arguments, `--add-dir`, sanitized env transport, image digest, and tool list.

- Resolve the versioned-driver problem before implementation. Make “snapshot as cwd” the default design if V0c works; otherwise specify per-version construction rather than leaving two architectures in one phase.

- Narrow the “mounts, not hooks” statement: mounts are authoritative for filesystem reachability and scorer writability; tool policy and egress are separate enforced layers. Do not defer both while passing a reusable OAuth credential into an open-egress container.

- Move the paper-trail sentinel/live-agent controls into paper-trail tests, or define a truly generic upstream API plus its engine test. Correct the shared footprint to include every modified engine code/test/doc/image file.

- Add trace persistence to the mount/config design and all end-to-end gates.

- Replace V2a's same-path probes with an exact rendered-mount assertion plus alternate-target adversarial control. State that a pin detects drift, not safety.

- Expand Phase 3's hash schema to every security-relevant field and use an immutable image digest. Add every gate to the green-by-absence audit table.

- Reframe OQ5(a) as a deliberate retry-policy change. Do not use Gate F's Python blind spot as evidence the invariant remains true; update the invariant and record attempts.

- Add the missing batch-status, release, canary, trace, and direct-constructor surfaces to Files to Modify.

- Either fully specify Phase 4 from rad-eval's provisioner/adoption contract or split it into a separate reviewed plan. The current three paragraphs and absent file list are not implementable by a fresh session.

- Correct the Plan A base and measured baseline: 447/447 is reproducible at `f02d761`; `94a376f` produces 445 passing checks because sampling is 48/50.

## Questions For The Author

- Is protection of `CLAUDE_CODE_OAUTH_TOKEN`—from both host process-argv disclosure and agent-driven network exfiltration—part of this protocol's leakage threat model? If yes, the open profile cannot be the shipping configuration without another enforced layer.

- Is this landing intended to certify only judge read isolation, or may it be called the complete isolation protocol while the optimizer still runs uncontainerized? The current goal/architecture and landing gate answer this differently.

- Which commit is authoritative for Plan A integration: the stated `94a376f`, or the live branch tip `f02d761` that contains later gate hardening and is the commit where 447/447 actually reproduces?

## Audit Trail

- docs/claude_ops.md
- docs/session/2026-09-09-optimizer-loop-and-isolation-findings.md
- docs/plans/isolation-protocol.md
- /home/philadamson/code/agentic-label-opt/docs/plans/2026-07-22-isolation-docker-substrate.md
- /home/philadamson/code/agentic-label-opt/docs/plans/2026-08-10-optional-edit-agent-mounts.md
- docs/plans/optimizer-prompt-investigative-latitude.md
- experiments/sarol-2024/optimizer/adapter.py
- experiments/sarol-2024/optimizer/dispatcher.py
- experiments/sarol-2024/optimizer/profiles.py
- experiments/sarol-2024/optimizer/evidence_producers.py
- experiments/sarol-2024/optimizer/validate_sarol.py
- experiments/sarol-2024/optimizer/canary.py
- experiments/sarol-2024/optimizer/sampling.py
- experiments/sarol-2024/program-v0/manifest.json
- experiments/sarol-2024/scripts/freeze_program_v0.py
- experiments/sarol-2024/scripts/check_orchestrator_consistency.py
- experiments/sarol-2024/scripts/check_run_scope.py
- experiments/sarol-2024/scripts/run_baseline.py
- experiments/sarol-2024/scripts/vm/run_hillclimb_vm.sh
- .claude/commands/sarol-eval-item.md
- /home/philadamson/engine-82f547d/engine/loop.py
- /home/philadamson/engine-82f547d/engine/schemas.py
- /home/philadamson/engine-82f547d/engine/claude_wrapper.py
- /home/philadamson/engine-82f547d/engine/materialize.py
- /home/philadamson/engine-82f547d/isolation/docker_prefix.py
- /home/philadamson/engine-82f547d/isolation/open_profile.py
- /home/philadamson/engine-82f547d/isolation/negative_control.py
- /home/philadamson/engine-82f547d/isolation/Dockerfile
- /home/philadamson/engine-82f547d/tests/test_materialized_path_threading.py
- /home/philadamson/engine-82f547d/tests/test_isolation_negative_control.py
- /home/philadamson/code/rad-eval/hooks/policy.py
- /home/philadamson/code/rad-eval/hooks/audit_broker.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/allowed_tools.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/dispatcher.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/claude_wrapper.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/run_artifacts.py
- /home/philadamson/code/rad-eval/.claude/settings.json
- /home/philadamson/code/rad-eval/.claude/worktrees/docker-gate/src/optimizer_loop/docker_agent.py
- /home/philadamson/code/rad-eval/.claude/worktrees/docker-gate/src/optimizer_loop/tests/test_docker_agent.py
