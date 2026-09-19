Reference: docs/claude_ops.md

# Implementation Feedback: Isolation Protocol — Phase 2

## Verdict
Revise before commit. The main production path now uses the materialized program tree for command discovery and the V5 host-vs-image gate has been correctly replaced, but the Phase 2 gates do not yet prove the full V3b/V3d contract and `command_path()` still accepts locations the plan itself says a nested command cannot resolve.

## Plan Coverage

| Slice / section | Status | Evidence: path:line | Notes |
|---|---|---|---|
| Re-scope note: 2a version-addressed cwd already delivered | Done | docs/plans/isolation-protocol.md:1345; experiments/sarol-2024/optimizer/isolation.py:381; experiments/sarol-2024/optimizer/isolation.py:410 | Code mounts `program_dir` as the scope program and sets workdir to `/workspace/program`; this matches the re-scope claim. |
| 2a command discovery resolves against version being scored | Partial | docs/plans/isolation-protocol.md:1406; experiments/sarol-2024/optimizer/adapter.py:1197; experiments/sarol-2024/optimizer/adapter.py:1266 | `run()` passes `materialized_path`, which is the right production direction. See Contract Violations and Test Gaps for the remaining broad path and coverage issues. |
| 2b scope check / refusal locus already delivered | Done | docs/plans/isolation-protocol.md:1347; experiments/sarol-2024/optimizer/isolation.py:423; experiments/sarol-2024/optimizer/adapter.py:1045 | Re-scope note is defensible: `program_scope()` validates the grant, and every Runner construction is covered by `container_problem()`. |
| 2c `--no-session-persistence` | Done | docs/plans/isolation-protocol.md:1351; experiments/sarol-2024/optimizer/isolation.py:509; experiments/sarol-2024/optimizer/isolation.py:520 | Flag is on the actual `inner_command()` argv. The selftest checks both membership and ordering after `--print` at `isolation.py:1413`. |
| 2c omit `--exclude-dynamic-system-prompt-sections` | Done | docs/plans/isolation-protocol.md:1355; experiments/sarol-2024/optimizer/isolation.py:1432 | The re-scope rationale is sound: relocating per-machine content into the first user message is not isolation. The assertion is in the right place, over the built inner argv. |
| V3a scope check gate | Done | docs/plans/isolation-protocol.md:2555; experiments/sarol-2024/optimizer/isolation.py:1315; experiments/sarol-2024/optimizer/isolation.py:1333; experiments/sarol-2024/optimizer/isolation.py:1689 | The gate has real red cases for empty denied, denied-path reachability, repo-root program mounts, and the stricter secret-root overlap rule. |
| V3b working-directory contents | Partial | docs/plans/isolation-protocol.md:2565; experiments/sarol-2024/optimizer/adapter.py:2751; experiments/sarol-2024/optimizer/adapter.py:2856 | The missing-command and hash checks are useful, but the gate does not assert `command_path(root)` resolves inside the materialized tree as V3b requires. |
| V3d version-specific driver bytes | Partial | docs/plans/isolation-protocol.md:2577; experiments/sarol-2024/optimizer/adapter.py:2804; experiments/sarol-2024/optimizer/adapter.py:2833 | The current check proves rendered dispatch prompt bytes vary by `materialized_path`; it does not dispatch two versions or assert a verdict/cwd observation as the gate specifies. |
| V3c invocation shape | Done for Phase 2 delta | docs/plans/isolation-protocol.md:2584; experiments/sarol-2024/optimizer/isolation.py:526; experiments/sarol-2024/optimizer/isolation.py:1413 | The new Phase 2 argv delta is covered. Broader env/prefix exposure was already Phase 1/re-scope scope and is not newly changed here. |
| V5 image parity replacement | Done | docs/plans/isolation-protocol.md:1312; experiments/sarol-2024/optimizer/isolation.py:808; experiments/sarol-2024/optimizer/seal_control.py:596 | `cli_parity_problem` is gone; `host_cli_version()` is recorded in `describe()` and not gated. The tag regex does not accidentally parse digest refs. |

## Critical Drift

None found. I did not find a re-scope item falsely declared done in a way that lets Phase 2 ship an uncontained scoring path.

## Missing Pieces

### V3d does not exercise the behavioural contract it names

Plan says: “Two program versions whose `sarol-eval-item.md` emits a distinct marker, dispatched in one process. Expected: each verdict carries its own version’s marker, and the cwd the program saw resolves under that version’s snapshot” (docs/plans/isolation-protocol.md:2577).

Code does: edit `dispatch_prompt.TEMPLATE_REL`, call `_inner_command()` directly, and inspect the last argv element (experiments/sarol-2024/optimizer/adapter.py:2808, experiments/sarol-2024/optimizer/adapter.py:2833). That proves prompt rendering reads from `materialized_path`, but it does not run the dispatch path, does not produce or inspect a verdict, and does not observe the cwd seen by the program.

This is not a production break by itself; `_inner_command()` legitimately renders from `materialized_path` at experiments/sarol-2024/optimizer/adapter.py:1143. It is a gate gap against the named V3d stop condition.

## Contract Violations

### `command_path()` still accepts non-discoverable command locations

Plan says the program session needs `.claude/commands/sarol-eval-item.md` in cwd (docs/plans/isolation-protocol.md:1381) and V3b expects “the command file is present” and `command_path()` resolves inside the working dir (docs/plans/isolation-protocol.md:2565). The code itself also says `src/commands/` and `experiments/sarol-2024/commands/` would satisfy preflight but “still fail at dispatch” because Claude only discovers `.claude/commands/` from the session cwd (experiments/sarol-2024/optimizer/adapter.py:2720).

Code does: `command_path()` still searches all three locations and `missing_command_error(root)` passes if any one exists (experiments/sarol-2024/optimizer/adapter.py:1212, experiments/sarol-2024/optimizer/adapter.py:1235). So a materialized version with no `.claude/commands/sarol-eval-item.md` but with a stale copy under `src/commands/` would pass the Phase 2 preflight. If the command file remains a manifest-completeness gate rather than a dispatched slash command after OQ1, this may be intentionally permissive, but that is drift from the text currently under audit.

## Test Gaps

### V3b does not assert `command_path(root)` returns a path under `root`

Plan says V3b should assert “`command_path()` resolves inside it” (docs/plans/isolation-protocol.md:2567). The new gate checks `missing_command_error(_v3_full) is None` and hashes `_v3_cmd_file`, but never asks `command_path(_v3_full)` for the resolved path or checks its parentage (experiments/sarol-2024/optimizer/adapter.py:2786, experiments/sarol-2024/optimizer/adapter.py:2856).

This matters because `command_path()` still has a no-root fallback to `working_checkout` (experiments/sarol-2024/optimizer/adapter.py:1211). The production `run()` caller is correct at experiments/sarol-2024/optimizer/adapter.py:1266, but the gate should make the path-addressing invariant explicit so a future caller cannot silently restore the old behaviour.

### V3d has no cwd observation

Plan says the V3d verdict should prove “the cwd the program saw resolves under that version’s snapshot” (docs/plans/isolation-protocol.md:2579). The current V3d checks only marker presence/absence in the prompt string returned from `_inner_command()` (experiments/sarol-2024/optimizer/adapter.py:2862). It never inspects the rendered prefix or a process-visible cwd. A prefix/cwd regression could therefore be missed if prompt rendering still used the right template root.

## Defensible Deviations

### V5 no longer gates on the host CLI

Old verification text still says “in-container CLI version == host version” (docs/plans/isolation-protocol.md:2626), but the dated V5 note supersedes it: “the image is no longer held to the host” and host version is only provenance (docs/plans/isolation-protocol.md:1298, docs/plans/isolation-protocol.md:1316). Code follows the superseding text: `host_cli_version()` is used in `shipping_container().describe()` at experiments/sarol-2024/optimizer/isolation.py:877 and no `cli_parity_problem` reference remains.

### Digest-named refs are not misparsed as version tags

The V5 implementation claims versions only from a final `:<semver>` suffix (experiments/sarol-2024/optimizer/isolation.py:798). A digest ref such as `repo@sha256:...` does not match that regex, so it is not accidentally treated as a versioned tag. Digest identity is still enforced separately by `container_problem()` requiring `@sha256:` (experiments/sarol-2024/optimizer/isolation.py:714), which matches the plan’s warning that V5 is not a digest pin (docs/plans/isolation-protocol.md:1319).

## Suggested Code Edits

1. Narrow `command_path(root)` to the actual discoverable `.claude/commands/{command_name}.md` for Phase 2’s preflight, or explicitly rename/split the legacy broad search if it is still needed for a different structural check.
2. Add a V3b assertion that `runner.command_path(_v3_full)` is not `None` and is under `_v3_full / ".claude" / "commands"`.
3. Rework V3d so it exercises the dispatch surface, not only `_inner_command()`: two materialized versions in one Runner/process, a spy or fixture that captures the rendered command/prefix, and an assertion tying each observed cwd/program mount to the matching version. If verdict text is no longer meaningful after OQ1, update the plan language or assert the equivalent observable produced by the current direct-adjudicator path.

## Questions For The Author

1. After OQ1, is `.claude/commands/sarol-eval-item.md` still a load-bearing completeness check, or only a human-readable frozen artifact? The answer determines whether the broad `src/commands/` fallback is a bug or a stale legacy affordance.
2. Should V3d be updated to the current direct-prompt architecture, or should the implementation produce a synthetic verdict marker so the existing verification wording remains literal?

## Audit Trail

- Read `docs/claude_ops.md`.
- Read `docs/plans/isolation-protocol.md` Phase 2, its 2026-09-19 re-scope note, Step 3 Phase 2 gates, and V5 note.
- Reviewed `git diff` for `docs/plans/isolation-protocol.md`, `adapter.py`, `isolation.py`, and `seal_control.py`.
- Inspected call sites for `command_path()`, `missing_command_error()`, `host_cli_version()`, `mislabelled_image_problem()`, and `SarolRunner(...)`.
- Ran `python3 -m py_compile experiments/sarol-2024/optimizer/adapter.py experiments/sarol-2024/optimizer/isolation.py experiments/sarol-2024/optimizer/seal_control.py`.
- Ran `git diff --check`.

---

## Author responses (2026-09-19)

All three findings were **agreed and applied**. No finding was dismissed.

**Q1 — is `.claude/commands/sarol-eval-item.md` load-bearing, or a stale legacy affordance?**
Neither, exactly: since OQ1 it is *not dispatched* (the adjudicator gets its prompt on argv), but it
*is* manifest entry #10 and so remains a completeness statement about the frozen version. That makes
the broad three-location search a genuine hole rather than a permissive affordance — `materialize`
only ever writes manifest paths, so the `src/commands/` and `experiments/sarol-2024/commands/` arms
could not match anything legitimate, while they *could* let an incomplete tree pass. Discovery is now
narrowed to the manifest's one path (`adapter.COMMAND_REL_TEMPLATE`), with a negative control that a
copy anywhere else does not make an incomplete version look complete.

**Q2 — update V3d to the current architecture, or synthesise a verdict?**
Updated the plan, did not synthesise. A verdict needs two paid model calls and would assert the model
rather than the wiring. V3d now asserts the two observables that are free and load-bearing: each
dispatch's rendered prompt carries its own version's marker (inside the fence — a marker on the tail
is dropped by `dispatch_prompt.prompt_body`, which the first draft got wrong), and the program mount
in each rendered prefix resolves under that same version's snapshot. The second half is exactly the
gap this review identified.

**Applied:** 3 Codex findings (narrow command discovery; assert `command_path(root)` resolves under
the root; observe per-version cwd in V3d), plus two stale plan lines the review surfaced (V5's
"== host version", V3d's pre-OQ1 wording). **Dismissed:** none.

**Re-verified after the edits:** 587 checks green across nine suites (`--selftest`, every one
exiting 0), and **14 deliberate breakages across three mutation sets, all 14 caught by a named
check** — including one that reverts command discovery to the three-location search and one that
mounts both versions from a single tree. A fifteenth mutation from the pre-review set no longer
applies: narrowing `command_path` deleted the code it patched, and it is superseded by "command_path
ignores the root it was handed", which is caught.
