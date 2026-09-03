"""Evidence-acquisition profiles — the C6.1 ladder, as data.

The experiment is: **hold the judge constant, vary who acquires the evidence.** A profile is the
consumer-side selector that makes that concrete. It fixes three things and nothing else:

* **which stages run** — and therefore how many nested sessions a claim costs;
* **who writes** ``ledger/evidence/<claim_id>.json`` — a mechanical producer, or the extractor;
* **which frozen files the optimizer may edit** — you cannot optimize a stage you do not run.

Two things this module deliberately is *not*.

It is **not a plugin registry.** The plan asks for typed constants plus validation against the
manifest, and that is all this is. Three named profiles, checked against the freeze at import-test
time. Anything more elaborate would be scaffolding for a generality nobody has asked for.

It is **not profile-awareness in the freeze.** `program-v0` stays 8 entries at ``combined_hash``
``391f54fae7c5`` under every profile; the engine's materializer still sees all 8 and
``commit_new_version()`` still stages all 8. A profile narrows what the *optimizer* is allowed to
touch, which is a consumer-side policy question, not a property of the frozen program. No engine
change is needed and none is requested.

⚠ **What does NOT vary across the ladder: the source text.** Every profile evaluates the same claim
against the same cited paper, and ``stage_claim.py`` stages it identically in all of them — Sarol's
``cited_doc_ids`` is *all* chunks of the cited paper (mean 72), written to
``pdfs/<citekey>/content.txt`` as numbered sentence lines, byte-identical across profiles. What
varies is only **who selects which of those sentences reach the judge**, and that selection is
unavoidable: the adjudicator never reads ``content.txt`` (C6.0), so something must always stand
between the paper and the judge. `retrieval` is not "different evidence from a different source";
it is *the same corpus, selected by BM25 instead of by an agent*. This was misread on first reading
of the plan (Open Questions §11), so it is restated wherever the ladder is defined.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass

# -- the frozen fileset, by role ------------------------------------------------------------------
# Spelled out rather than globbed: a typo here silently widens or narrows the optimizer's reach,
# and `validate_against_manifest` is what catches that.

ADJUDICATOR = "experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md"
RUBRIC_GUIDANCE = "experiments/sarol-2024/specs/verdict_schema_sarol.md"
EXTRACTOR_PDF = "src/prompts/extractor-dispatch-pdf.md"
EXTRACTOR_PAPERCLIP = "src/prompts/extractor-dispatch-paperclip.md"
VERIFIER = "src/prompts/verifier-dispatch.md"

#: The judge, and the guidance it reads. Editable under **every** profile — optimizing the
#: adjudicator is the one thing common to the whole ladder.
JUDGE_SCOPE = (ADJUDICATOR, RUBRIC_GUIDANCE)

#: Everything the agentic profiles add: the evidence-acquisition surface.
ACQUISITION_SCOPE = (EXTRACTOR_PDF, EXTRACTOR_PAPERCLIP, VERIFIER)

ALL_STAGES = ("extractor", "adjudicator", "verifier")

#: Stages `.claude/commands/sarol-eval-item.md` can actually dispatch today. The command implements
#: the Phase 1 adjudicator path and aborts `extractor` / `verifier` with `STAGE_NOT_IMPLEMENTED`,
#: so a profile requiring them cannot complete a run however well-formed it is.
#:
#: This exists because a profile being *selectable* and a profile being *runnable* are different
#: facts, and conflating them means the failure surfaces per-claim, mid-run, after money has been
#: spent -- rather than at the preflight. Widen this tuple in the same change that implements those
#: stages, not before.
IMPLEMENTED_STAGES: tuple[str, ...] = ("adjudicator",)


@dataclass(frozen=True)
class Profile:
    """One rung of the ladder. Frozen: a profile is part of a run's identity (C6.5)."""

    name: str
    phase: str
    #: Stages the Runner dispatches per claim, in order. Drives `stages_per_claim` in `CostModel`.
    stages: tuple[str, ...]
    #: The optimizer's EDIT scope. Intersected with the manifest's non-contract entries by
    #: `SarolProgramStore.editable_paths()` — this module names them, that one enforces the
    #: contract-file partition, so the partition logic lives in exactly one place.
    editable: tuple[str, ...]
    #: Who writes `ledger/evidence/<claim_id>.json`. "extractor" means the extractor stage does it
    #: as part of the run; anything else names a mechanical producer that must run before dispatch.
    evidence_producer: str
    #: `attestation.selector` the producer must declare. None when an agent did the searching —
    #: the validator keys the `phrasings_tried` floor off this rather than assuming a search.
    selector: str | None
    #: Retrieval budget, and a required part of any reported number (C6.3). None when not mechanical.
    retrieval_k: int | None
    #: What the envelope declares as provenance. `sarol_corpus` is legal only under the Sarol
    #: rubric variant (Open Questions §13, resolved 2026-09-02 — variant-gated in `validate_sarol`).
    source_mode: str

    @property
    def sessions_per_claim(self) -> int:
        return len(self.stages)

    @property
    def is_mechanical(self) -> bool:
        return self.evidence_producer != "extractor"


#: **Phase 1.** The only rung comparable to the published baselines: Sarol's MultiVerS 0.52 used
#: BM25 + MonoT5 top-20, so *k*=20 matches its retrieval budget (Open Questions §10). One session
#: per claim — the judge, and nothing else. Report *k* alongside every number; a macro-F1 without
#: the *k* is not a result.
RETRIEVAL = Profile(
    name="retrieval",
    phase="1",
    stages=("adjudicator",),
    editable=JUDGE_SCOPE,
    evidence_producer="bm25",
    selector="bm25-top20",
    retrieval_k=20,
    source_mode="sarol_corpus",
)

#: **Phase 2.** The pipeline as landed: the extractor searches and decomposes, the verifier
#: spot-checks. Three sessions per claim. Reported as a delta over Phase 1's *optimized*
#: adjudicator, never head-to-head against the published baselines (C6.3).
AGENTIC = Profile(
    name="agentic",
    phase="2",
    stages=ALL_STAGES,
    editable=JUDGE_SCOPE + ACQUISITION_SCOPE,
    evidence_producer="extractor",
    selector=None,
    retrieval_k=None,
    source_mode="pdf",
)

#: **Backlog** (C6.10). Same edit scope as `agentic`; the extractor queries the paper
#: conversationally instead of reading a staged flat file. Blocked on a prerequisite the others do
#: not have — the cited papers must first be ingested into a paperclip corpus — at which point the
#: `paperclip_cli` pin in `runtime_pins` becomes load-bearing at run time, not merely recorded.
PAPERCLIP = Profile(
    name="paperclip",
    phase="backlog",
    stages=ALL_STAGES,
    editable=JUDGE_SCOPE + ACQUISITION_SCOPE,
    evidence_producer="paperclip",
    selector=None,
    retrieval_k=None,
    source_mode="paperclip",
)

PROFILES: dict[str, Profile] = {p.name: p for p in (RETRIEVAL, AGENTIC, PAPERCLIP)}

#: The landed pipeline. Deliberately the default so that adding profiles changes **no** existing
#: behaviour: Phase 1 must opt in explicitly with `--profile retrieval`. A default of `retrieval`
#: would silently re-point every un-migrated caller at a different experiment.
DEFAULT_PROFILE = AGENTIC.name


def get(profile: "str | Profile | None") -> Profile:
    """Resolve a name, a `Profile`, or None (-> the default) to a `Profile`. Raises on unknown."""
    if profile is None:
        return PROFILES[DEFAULT_PROFILE]
    if isinstance(profile, Profile):
        return profile
    try:
        return PROFILES[profile]
    except KeyError:
        raise KeyError(
            f"unknown profile {profile!r}; known: {sorted(PROFILES)}"
        ) from None


def unrunnable_reason(profile) -> str | None:
    """Why this profile cannot complete a run today, or None if it can.

    Selectable != runnable. `agentic` and `paperclip` are fully specified and correctly priced, but
    their extractor/verifier stages have no command implementation yet, so a real run would abort on
    the first claim. Checked at the preflight so that is a refusal, not a wasted paid run.
    """
    prof = get(profile)
    missing = [s for s in prof.stages if s not in IMPLEMENTED_STAGES]
    if not missing:
        return None
    return (
        f"profile {prof.name!r} needs stage(s) {', '.join(missing)}, which "
        f"/sarol-eval-item does not implement (it aborts them with STAGE_NOT_IMPLEMENTED). "
        f"Runnable today: {', '.join(sorted(runnable_profiles()))}"
    )


def runnable_profiles() -> list[str]:
    """Profiles that can complete a run against the command as it exists.

    Computed directly from `IMPLEMENTED_STAGES` rather than by calling `unrunnable_reason`, which
    would recurse -- that function names this list in its own message.
    """
    return sorted(
        n for n, p in PROFILES.items() if set(p.stages) <= set(IMPLEMENTED_STAGES)
    )


def validate_against_manifest(entries: "list[dict]", profiles=None) -> list[str]:
    """Check every profile's edit scope against the freeze. Returns problems, does not raise.

    Three ways a profile can be wrong, all of them silent at run time and all of them consequential:

    * it names a path that is **not in the manifest** — the optimizer is handed an edit scope
      pointing at a file the materialized tree does not contain;
    * it names a **contract file** — which would hand the optimizer a file the whole design says is
      immutable, and the re-hash would then fail the iteration for a reason nobody could read;
    * it runs a **stage that is not a real stage**, so the Runner would dispatch a command that
      aborts.

    A fourth check is deliberately *not* here: a manifest entry no profile can edit is fine.
    `verdict_schema.md` and the enum contract are exactly that, on purpose.
    """
    problems: list[str] = []
    known = {e["path"] for e in entries}
    contract = {e["path"] for e in entries if e.get("contract_file")}
    for profile in (PROFILES.values() if profiles is None else profiles):
        for path in profile.editable:
            if path not in known:
                problems.append(f"{profile.name}: {path!r} is not a manifest entry")
            elif path in contract:
                problems.append(f"{profile.name}: {path!r} is a contract file and must stay read-only")
        for stage in profile.stages:
            if stage not in ALL_STAGES:
                problems.append(f"{profile.name}: {stage!r} is not a dispatchable stage")
        if not profile.stages:
            problems.append(f"{profile.name}: no stages, so nothing would be dispatched")
        if "adjudicator" not in profile.stages:
            # The judge is the constant the whole ladder is built around.
            problems.append(f"{profile.name}: does not run the adjudicator, so it measures nothing")
    return problems


def as_dict(profile: Profile) -> dict:
    """Serialisable form, for `run_manifest.json` and the release payloads (C6.5)."""
    return dataclasses.asdict(profile)


# =================================================================================================
# Selftest
# =================================================================================================


def _selftest() -> int:
    import json
    import pathlib
    import sys

    manifest = json.loads(
        (pathlib.Path(__file__).resolve().parents[1] / "program-v0" / "manifest.json")
        .read_text(encoding="utf-8")
    )
    entries = manifest["entries"]
    contract = {e["path"] for e in entries if e.get("contract_file")}
    non_contract = {e["path"] for e in entries if not e.get("contract_file")}

    checks = [
        # The gate that matters: profiles are checked against the actual freeze, not against a
        # remembered copy of it. A manifest change that renames a prompt fails here.
        ("every profile's edit scope validates against the freeze",
         validate_against_manifest(entries) == []),
        ("...and the freeze is the 8-entry program-v0", len(entries) == 8),

        # The ladder's shape.
        ("the ladder is retrieval -> agentic -> paperclip",
         sorted(PROFILES) == ["agentic", "paperclip", "retrieval"]),
        ("retrieval runs the judge alone", RETRIEVAL.stages == ("adjudicator",)),
        ("...so it is one session per claim", RETRIEVAL.sessions_per_claim == 1),
        ("agentic runs all three stages", AGENTIC.stages == ALL_STAGES),
        ("...so it is three, which is what makes the delta cost 3x",
         AGENTIC.sessions_per_claim == 3),
        ("every rung runs the adjudicator -- it is the constant being held",
         all("adjudicator" in p.stages for p in PROFILES.values())),

        # Edit scope. The invariant with teeth: you may not optimize a stage you do not run.
        ("retrieval may edit only the judge and its rubric",
         set(RETRIEVAL.editable) == {ADJUDICATOR, RUBRIC_GUIDANCE}),
        ("...and may NOT touch the extractor it does not run",
         EXTRACTOR_PDF not in RETRIEVAL.editable and VERIFIER not in RETRIEVAL.editable),
        ("agentic's scope is every non-contract entry",
         set(AGENTIC.editable) == non_contract),
        ("paperclip shares agentic's scope", set(PAPERCLIP.editable) == set(AGENTIC.editable)),
        ("no profile can reach a contract file",
         all(not (set(p.editable) & contract) for p in PROFILES.values())),

        # Provenance, tied to Open Questions §13.
        ("retrieval declares the corpus provenance it actually has",
         RETRIEVAL.source_mode == "sarol_corpus"),
        ("...and declares its selector, so a reader can tell it from an agentic search",
         RETRIEVAL.selector == "bm25-top20"),
        ("...at k=20, matching the budget MultiVerS's best result used",
         RETRIEVAL.retrieval_k == 20),
        ("an agentic profile declares no mechanical selector",
         AGENTIC.selector is None and AGENTIC.retrieval_k is None),
        ("retrieval is mechanical, agentic is not",
         RETRIEVAL.is_mechanical and not AGENTIC.is_mechanical),

        # The default, which is a compatibility guarantee.
        ("the default is the landed pipeline, so profiles changed nothing silently",
         DEFAULT_PROFILE == "agentic"),
        ("get(None) is the default", get(None) is PROFILES[DEFAULT_PROFILE]),
        ("get() round-trips a Profile", get(RETRIEVAL) is RETRIEVAL),
        ("an unknown profile raises rather than falling back to a default",
         _raises(lambda: get("nope"))),

        # Identity. A profile is part of what a number means.
        ("a profile is frozen, since a run's identity must not mutate under it",
         _raises(lambda: setattr(RETRIEVAL, "name", "x"))),
        ("as_dict round-trips for the run manifest",
         as_dict(RETRIEVAL)["name"] == "retrieval"),
    ]

    # Negative controls. These prove `validate_against_manifest` is doing work rather than always
    # returning [] -- each malformed profile must be REFUSED, never silently narrowed.
    def problems_for(**changes) -> list[str]:
        return validate_against_manifest(entries, [dataclasses.replace(RETRIEVAL, **changes)])

    checks += [
        ("a profile naming a contract file is refused",
         any("contract file" in x for x in
             problems_for(name="bad", editable=(ADJUDICATOR, "src/specs/verdict_schema.md")))),
        ("a profile naming a path outside the manifest is refused",
         any("not a manifest entry" in x for x in
             problems_for(name="ghost", editable=("src/prompts/does-not-exist.md",)))),
        ("a profile that does not run the adjudicator is refused",
         any("measures nothing" in x for x in
             problems_for(name="nojudge", stages=("extractor",)))),
        ("a profile dispatching a stage that does not exist is refused",
         any("not a dispatchable stage" in x for x in
             problems_for(name="odd", stages=("adjudicator", "summarizer")))),
    ]

    def _emits(token: str) -> bool:
        """Does any module in this package actually produce `token`?"""
        d = pathlib.Path(__file__).resolve().parent
        return any(
            token in (d / f).read_text(encoding="utf-8")
            for f in ("adapter.py", "dispatcher.py", "sampling.py")
        )

    def _unresolvable_doc_paths(docs: dict) -> list:
        """Every repo-relative `.md` path the optimizer-facing docs cite that does not exist.

        Resolved against the REPO ROOT, because that is the agent's working directory and the
        whole point of the defect this guards. EVERY backticked `.md` is checked, not just ones
        already rooted at a top-level directory -- checking only the latter would pass the exact
        bug it exists to catch, since `context/playbook.md` is precisely what the instructions
        used to say. A file named in prose but not present in this repo (an external reference)
        must therefore not be written as a code-formatted path.
        """
        root = pathlib.Path(__file__).resolve().parents[3]
        cited = set()
        for text in docs.values():
            cited.update(re.findall(r"`([A-Za-z0-9_./-]+\.md)`", text))
        return sorted(c for c in cited if not (root / c).exists())

    # -- C6.7: the optimizer's own docs must agree with this module --------------------------
    # The plan is explicit that these three files be updated *in the same change* that lands the
    # profile, because an optimizer reading "you own five files" while the edit scope grants two
    # will spend iterations editing files that are never read. This makes the agreement a gate
    # rather than a promise.
    here = pathlib.Path(__file__).resolve().parent
    docs = {
        "playbook.md": (here / "context" / "playbook.md").read_text(encoding="utf-8"),
        "optimizer-instructions.md": (here / "prompt" / "optimizer-instructions.md")
        .read_text(encoding="utf-8"),
        "meta-learnings.md": (here / "meta-learnings.md").read_text(encoding="utf-8"),
        # Added after a Codex-prompted check found this file still telling the optimizer that
        # `corpus.ref` points at the run manifest -- false since C6.8 -- while the gate did not
        # read it. A gate that covers three of four optimizer-facing docs gives false assurance.
        "release-format.md": (here / "context" / "release-format.md").read_text(encoding="utf-8"),
    }
    guidance = docs["playbook.md"] + docs["optimizer-instructions.md"]
    checks += [
        ("the optimizer's docs name every path the agentic scope grants",
         all(path in guidance for path in AGENTIC.editable)),
        ("...and both name the profile the scope depends on",
         "retrieval" in docs["playbook.md"] and "retrieval" in docs["optimizer-instructions.md"]),
        # Coarse by nature -- a prose gate cannot prove a doc is right, only catch a doc asserting
        # a scope or cost as though it were *unconditional*. The distinguishing feature of a
        # correct statement here is that it names the profile it applies to, so a count is only
        # flagged when its own line mentions no profile. (An earlier version keyed off the exact
        # phrases "five files" / "costs three nested" and would have passed any reworded drift;
        # a broader regex alone flagged the correct profile-qualified sentences instead.)
        ("no doc asserts a count of editable files without naming the profile",
         not _unqualified(r"\b(two|three|four|five|six)\s+files\b", guidance)),
        ("no doc asserts a per-claim session count without naming the profile",
         not _unqualified(r"costs?\s+(one|two|three)\s+nested", guidance)),
        ("...and both name the mechanical producer that replaces the extractor in Phase 1",
         "BM25" in guidance),

        # Sev 3, made permanent. `optimizer-instructions.md` told the agent to read
        # `context/playbook.md` and three siblings by BARE RELATIVE path, while the agent's cwd is
        # the REPO ROOT, where no `context/` exists. All four were missing from where it was sent.
        # It only worked because the per-turn prompt separately handed over an absolute context
        # dir and the agent was capable enough to reconcile two conventions in one document.
        # Resolving every cited path from the root is the check that keeps that fixed.
        ("every path the optimizer's docs cite resolves from the agent's cwd, the repo root",
         not _unresolvable_doc_paths(docs)),

        # The mirror of the Sev-1 class. `followups` had a whole section describing a channel that
        # scored the agent's predictions back to it; `grep -rn followups *.py` returned nothing,
        # and both procedure docs built the iteration loop on it. A doc that promises a mechanism
        # no code emits trains the reader to discount the doc. Keyed off whether code emits it, so
        # the gate relaxes on its own if the mechanism is ever actually built.
        ("no doc promises `followups` while no code emits it",
         _emits("followups") or "no `followups` key" in docs["release-format.md"]),
        ("meta-learnings warns that the P1 extractor-side fix is unreachable in Phase 1",
         "unreachable under the `retrieval` profile" in docs["meta-learnings.md"]),
        # C6.8 made `corpus.ref` point at the mistake corpus itself. The doc that tells the
        # optimizer where to look must say the same thing.
        ("release-format points the optimizer at the per-claim corpus, not the run manifest",
         "run manifest, from which" not in docs["release-format.md"]
         and "mistakes/<batch_id>.json" in docs["release-format.md"]),
        ("...and states the schema version the code actually emits",
         "0.2.0" in docs["release-format.md"] and "`0.1.0`." not in docs["release-format.md"]),
        ("...and does not promise verifier output that Phase 1 never produces",
         "no verifier runs at all" in docs["release-format.md"]),
    ]

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def _unqualified(pattern: str, text: str) -> list[str]:
    """Lines matching `pattern` that name no profile. A count is only meaningful with a rung."""
    names = tuple(PROFILES)
    return [
        line
        for line in text.splitlines()
        if re.search(pattern, line, re.I) and not any(n in line for n in names)
    ]


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:
        return True
    return False


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
