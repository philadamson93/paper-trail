Reference: docs/claude_ops.md

# Implementation Feedback: papertrail-optimizer Part C6 retrofit

## Verdict

Revise before commit. The core profile/evidence/validator modules mostly implement C6, but the real dispatcher CLI does not pass the selected profile into the run, and the TRAIN/VAL output-root plumbing needed for the mistake corpus and VAL isolation is optional/unexposed rather than explicit.

## Plan Coverage

| Slice / section | Status | Evidence: path:line | Notes |
|---|---|---|---|
| C6.1 profile ladder | Partial | `experiments/sarol-2024/optimizer/profiles.py:95`; `experiments/sarol-2024/optimizer/profiles.py:109`; `experiments/sarol-2024/optimizer/profiles.py:124`; `experiments/sarol-2024/optimizer/adapter.py:590` | Profiles encode retrieval=adjudicator only, agentic/paperclip=all stages, and Runner dispatches `self.profile.stages`. CLI integration drops `--profile`; see Critical Drift. |
| C6.1 editable paths | Done | `experiments/sarol-2024/optimizer/profiles.py:48`; `experiments/sarol-2024/optimizer/adapter.py:193` | Path lists live in `profiles.py`; `SarolProgramStore.editable_paths(profile)` intersects them with non-contract manifest entries, so the contract partition remains in one implementation point. |
| C6.2 evidence envelope | Done | `experiments/sarol-2024/optimizer/evidence_producers.py:131`; `experiments/sarol-2024/optimizer/evidence_producers.py:160`; `experiments/sarol-2024/optimizer/evidence_producers.py:182` | Producer emits the skeleton fields, including `schema_version`, `source_mode`, `claim_type`, `sub_claims`, `attestation.selector`, `stage`, and no fake padding beyond the one BM25 query. |
| C6.2 line/source conventions | Done | `experiments/sarol-2024/optimizer/evidence_producers.py:48`; `experiments/sarol-2024/optimizer/evidence_producers.py:213`; `experiments/sarol-2024/optimizer/evidence_producers.py:218` | Reads staged `staging_info.json` and `content.txt` line prefixes; does not re-open benchmark rows. |
| C6.2 `section: content` deviation | Defensible deviation | `docs/plans/papertrail-optimizer-requirements.md:205`; `experiments/sarol-2024/optimizer/evidence_producers.py:29`; `experiments/sarol-2024/optimizer/evidence_producers.py:152` | Plan skeleton shows `"abstract"`, but C6.1 says Sarol's field name is a SciFact misnomer and `content.txt` is the real source. Emitting `"content"` consistently is defensible. |
| C6.5 profile identity | Partial | `experiments/sarol-2024/optimizer/adapter.py:657`; `experiments/sarol-2024/optimizer/adapter.py:972`; `experiments/sarol-2024/optimizer/adapter.py:963`; `experiments/sarol-2024/optimizer/dispatcher.py:572` | Run manifest, both release payloads, hard fields, and schema bump exist. CLI does not pass the selected profile into `run_optimization`; see Critical Drift. |
| C6.6 cost model | Done | `experiments/sarol-2024/optimizer/dispatcher.py:105`; `experiments/sarol-2024/optimizer/dispatcher.py:121`; `experiments/sarol-2024/optimizer/dispatcher.py:140` | `CostModel.for_profile()` derives `stages_per_claim`; canary sessions are counted in session and dollar estimates. |
| C6.7 optimizer docs | Done | `experiments/sarol-2024/optimizer/context/playbook.md:26`; `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:49`; `experiments/sarol-2024/optimizer/meta-learnings.md:56` | Docs now describe profile-dependent scope and P1 being unreachable under retrieval. |
| C6.8 mistake corpus | Partial | `docs/plans/papertrail-optimizer-requirements.md:277`; `experiments/sarol-2024/optimizer/adapter.py:722`; `experiments/sarol-2024/optimizer/adapter.py:759`; `experiments/sarol-2024/optimizer/adapter.py:994` | Scorer can write per-claim TRAIN mistakes and VAL writes none, but the file shape is not the exact list the plan specifies, and the CLI path config means real runs default to no mistake file. |
| C6.9 VAL root isolation | Partial | `docs/plans/papertrail-optimizer-requirements.md:291`; `experiments/sarol-2024/optimizer/dispatcher.py:430`; `experiments/sarol-2024/optimizer/dispatcher.py:445`; `experiments/sarol-2024/optimizer/dispatcher.py:887` | There is a useful negative control for a generic configured inside-repo root, but explicit roots are optional and not exposed on the CLI. |
| OQ13 source-mode variant gate | Done | `experiments/sarol-2024/optimizer/validate_sarol.py:131`; `experiments/sarol-2024/optimizer/validate_sarol.py:143`; `experiments/sarol-2024/optimizer/validate_sarol.py:266` | Frozen native source-mode set remains unchanged in code; `sarol_corpus` is admitted only by the experiment validator. No diff touched `src/specs/verdict_schema.md`. |
| `/sarol-eval-item` command contract | Drifted | `.claude/commands/sarol-eval-item.md:76`; `.claude/commands/sarol-eval-item.md:153`; `experiments/sarol-2024/optimizer/adapter.py:457` | Stage command arguments match the command's named inputs and all frozen prompt slots are resolvable, but the command contains stale claims and only implements adjudicator while `agentic` remains a selectable profile. |

## Critical Drift

- Severity: Critical | Plan says Phase 1 is selected by profile and `--profile retrieval` is how the dispatcher asks for it; code parses `--profile` but never passes it into `run_optimization`, so `build_components(profile=None)` resolves to the default `agentic`. Evidence: plan says "Phase 1 must opt in explicitly with `--profile retrieval`" at `docs/plans/papertrail-optimizer-requirements.md:191` / `docs/plans/papertrail-optimizer-requirements.md:364`; CLI parses `--profile` at `experiments/sarol-2024/optimizer/dispatcher.py:1024` but the `--run` call omits it at `experiments/sarol-2024/optimizer/dispatcher.py:1058`. Required fix: pass `profile=args.profile` through the CLI run path and add a test that a CLI-style invocation/build uses retrieval when requested.

- Severity: Critical | Plan says the mistake corpus must be persisted to `<train_output_root>/mistakes/<batch_id>.json` and `corpus.ref` must point there; code makes `train_output_root` optional, exposes no CLI flag for it, and falls back to the run manifest when no `mistakes_ref` exists. Evidence: plan at `docs/plans/papertrail-optimizer-requirements.md:277`; optional root at `experiments/sarol-2024/optimizer/dispatcher.py:473`; scorer receives `mistakes_root=train_output_root` at `experiments/sarol-2024/optimizer/dispatcher.py:519`; fallback to manifest at `experiments/sarol-2024/optimizer/adapter.py:1008`. Required fix: make TRAIN output root an explicit required runtime input for `--run` or derive a concrete TRAIN root and pass it as `mistakes_root`; remove the manifest fallback for TRAIN scoring paths.

- Severity: Critical | Plan says the VAL root must be specified explicitly and lie outside optimizer-readable mounts; code treats `val_output_root=None` as acceptable and the CLI exposes no way to set it. Evidence: plan at `docs/plans/papertrail-optimizer-requirements.md:291`; `val_isolation_problem(None, repo)` returns no problem at `experiments/sarol-2024/optimizer/dispatcher.py:445`; the selftest pins that permissive behavior at `experiments/sarol-2024/optimizer/dispatcher.py:885`; CLI arguments stop at `--materialize-root` at `experiments/sarol-2024/optimizer/dispatcher.py:1038`. Required fix: require explicit `val_output_root` for real runs, wire a CLI flag, and test the concrete run-manifest path that the runtime will write.

## Missing Pieces

- The `agentic` profile is declared as the Phase 2 pipeline, but `/sarol-eval-item` aborts `extractor` and `verifier` as not implemented. Evidence: profile stages at `experiments/sarol-2024/optimizer/profiles.py:109`; command abort section at `.claude/commands/sarol-eval-item.md:153`; Runner dispatches every stage in `self.profile.stages` at `experiments/sarol-2024/optimizer/adapter.py:590`. Either make `agentic` non-runnable/backlog until those stages exist or implement the command paths for the extractor and verifier.

- The mistake corpus file is an object with metadata plus `claims`, not "a list of `{claim_id, citekey, ...}`" as specified. Evidence: plan says "as a list" at `docs/plans/papertrail-optimizer-requirements.md:277`; code writes `{batch_id, split, n_scored, n_correct, n_mistakes, claims}` at `experiments/sarol-2024/optimizer/adapter.py:761`. Required fix: either write the exact list or update the plan and release consumer to explicitly accept the wrapper.

## Contract Violations

- `/sarol-eval-item` has stale failure text that is false against the committed code. It says the mechanical producer "does not exist yet" at `.claude/commands/sarol-eval-item.md:76`, but `evidence_producers.py` exists and is called by the Runner at `experiments/sarol-2024/optimizer/adapter.py:576`. It says `adapter.py` still loops over all three stages unconditionally at `.claude/commands/sarol-eval-item.md:161`, but the Runner uses `self.profile.stages` at `experiments/sarol-2024/optimizer/adapter.py:590`. Required fix: update the command text so abort diagnostics describe the current contract.

- `SarolRunner._stage_command()` passes staging/spec-root paths inside one slash-command string with no quoting or structured escaping. Evidence: prompt construction at `experiments/sarol-2024/optimizer/adapter.py:460`; command requires `--flag value` parsing from `$ARGUMENTS` at `.claude/commands/sarol-eval-item.md:17`. Because this repository path itself contains spaces, any materialize/staging path under the checkout will split into invalid arguments. Required fix: quote/escape values in the prompt string or use a path root guaranteed not to contain spaces and test it.

## Test Gaps

- Dispatcher selftests cover `CostModel.for_profile("retrieval")`, but not the actual `main() --run` path that drops `args.profile`. Evidence: cost tests at `experiments/sarol-2024/optimizer/dispatcher.py:852`; CLI run call omission at `experiments/sarol-2024/optimizer/dispatcher.py:1058`.

- C6.9's test is a generic inside-repo root check, not the "concrete VAL run-manifest path the selected runtime actually uses" required by the plan. Evidence: plan at `docs/plans/papertrail-optimizer-requirements.md:291`; test uses `inside = repo / "runs" / "val"` at `experiments/sarol-2024/optimizer/dispatcher.py:875`.

- The mistake-corpus selftest asserts the implementation's wrapper shape, not the plan's exact list shape. Evidence: test reads `corpus_file["claims"][0]` at `experiments/sarol-2024/optimizer/adapter.py:1296` and asserts `n_mistakes` / `n_correct` at `experiments/sarol-2024/optimizer/adapter.py:1305`; plan specifies the file itself is a list at `docs/plans/papertrail-optimizer-requirements.md:277`.

- The docs-vs-code gate in `profiles.py` is brittle prose grepping. Evidence: it checks substrings such as `"five files"` and `"costs three nested"` at `experiments/sarol-2024/optimizer/profiles.py:309`. A doc can become wrong without using those exact strings, and a correct doc can fail by mentioning them in a warning. Prefer checking generated profile tables or exact path/profile facts.

## Defensible Deviations

- Evidence item `"section": "content"` is better than the skeleton's `"abstract"` here. The plan itself explains that Sarol's `abstract` field is a schema-name artifact and the staged source is `content.txt`; the producer keeps `evidence[].section` and `section_checklist` consistent at `experiments/sarol-2024/optimizer/evidence_producers.py:152` and `experiments/sarol-2024/optimizer/evidence_producers.py:187`.

- Defaulting the profile constants to `agentic` is defensible for backwards compatibility at the library level (`experiments/sarol-2024/optimizer/profiles.py:137`), but only if the CLI honors an explicit `--profile retrieval` and does not silently run the default.

## Suggested Code Edits

- In `dispatcher.main()`, pass `profile=args.profile`, `train_output_root=...`, and `val_output_root=...` into `run_optimization()`; add required CLI flags for the two roots or derive explicit roots before calling.

- Make `build_components()` reject `val_output_root is None` for real optimization runs, or provide a separate test-only escape hatch so the production path cannot rely on derived defaults.

- Change `_write_mistakes()` to write the exact list specified by C6.8, or revise the plan to bless the metadata wrapper and then update the selftest name accordingly.

- Update `/sarol-eval-item` to remove the stale "producer does not exist yet" and "adapter still loops unconditionally" diagnostics, and either implement or explicitly disable `agentic` until extractor/verifier stages are wired.

## Questions For The Author

- Should `paperclip` be selectable now? The profile exists and the CLI accepts it, but C6.10 marks it backlog and the command cannot run its stages.

- Is the mistake-corpus wrapper intentional? If yes, the plan should say the file is an object whose `claims` field is the specified list; if no, the implementation should drop the wrapper.

## Audit Trail

- Read `docs/claude_ops.md`.
- Read `docs/plans/papertrail-optimizer-requirements.md`, with targeted review of C6 and Open Questions 11-13.
- Audited `git diff d4d064a..HEAD` and read the three new files in full: `.claude/commands/sarol-eval-item.md`, `experiments/sarol-2024/optimizer/evidence_producers.py`, `experiments/sarol-2024/optimizer/profiles.py`.
- Checked frozen adjudicator prompt slots between `## Begin dispatch prompt` and `## End dispatch prompt`; every `{{slot}}` used there is named by `/sarol-eval-item`.
- Ran `python experiments/sarol-2024/optimizer/profiles.py` → 33/33 passed.
- Ran `python experiments/sarol-2024/optimizer/evidence_producers.py` → 26/26 passed.
- Ran `python experiments/sarol-2024/optimizer/validate_sarol.py --selftest` → 33/33 passed.
- Ran `python experiments/sarol-2024/optimizer/adapter.py --selftest` → 90/90 passed.
- Ran `python experiments/sarol-2024/optimizer/dispatcher.py --selftest` → 57/57 passed.

---

## Adjudication (author, 2026-09-02)

All three Critical findings **agreed and fixed**. Both Missing Pieces, both Contract Violations and
all four Test Gaps **agreed and fixed**. No finding was dismissed. Two notes for future readers:

- **The "repository path contains spaces" evidence is factually wrong.** Neither the checkout path
  nor the worktree path contains a space, so the described argument-splitting failure could not
  occur today, and the finding's stated evidence should not be trusted. The *underlying* concern was
  still valid (a staging or materialize root containing a space would split `--flag value` parsing),
  so the fix was applied anyway: `_stage_command` now double-quotes both path values and the command
  documents that they arrive quoted.

- **The mistake-corpus wrapper is intentional and the plan now says so** (Phil, 2026-09-02).
  C6.8 previously specified a bare list; it now specifies the object
  `{batch_id, split, n_scored, n_correct, n_mistakes, claims}` where `claims` is exactly the
  nine-field list. Rationale recorded in C6.8: a bare list has no denominator, so `n_mistakes: 3`
  reads identically at 3-of-10 and 3-of-300, and `n_correct` is the only in-file signal against
  fixing mistakes by breaking claims that already worked. The selftest now pins the wrapper keys and
  the nine per-claim fields explicitly.

**One drift this audit did not find, surfaced while acting on it.** Chasing "who actually consumes
`corpus.ref`" turned up `optimizer/context/release-format.md:49` still telling the optimizer that
*"`corpus.ref` points at the run manifest, from which the per-claim mistake corpus is reachable"* —
false since C6.8 pointed `corpus.ref` at the corpus itself. The same file promised "the verifier's
bounce history", which no `retrieval` run produces, and its examples still showed
`schema_version: 0.1.0`. The C6.7 docs pass had covered `playbook.md`,
`optimizer-instructions.md` and `meta-learnings.md` but not this fourth optimizer-facing doc, and
the `profiles.py` docs-vs-code gate did not read it either — so the gate was giving false assurance
over three of four files. Both the doc and the gate are fixed.

Gates after all fixes: profiles 37, evidence_producers 26, validator 33, adapter 92, dispatcher 65,
scorer 17 (**270 checks**, up from 256 pre-audit); freeze 8/8 vs the tag; materialize 8/8.
