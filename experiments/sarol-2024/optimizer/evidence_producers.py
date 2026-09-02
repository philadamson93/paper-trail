"""Mechanical evidence producers — the Phase 1 half of the C6.1 ladder.

The adjudicator never reads the source paper (C6.0): its only input is
``ledger/evidence/<claim_id>.json``. Under the `agentic` profile the extractor subagent writes that
file. Under `retrieval` there is no extractor, so **this module writes it** — with no model in the
loop at all. That is the whole point of the rung: a fixed, mechanical, reproducible evidence budget
against which agentic acquisition can be measured.

**This module is the single owner of ``ledger/evidence/<claim_id>.json`` under mechanical
profiles.** The plan is explicit that it should exist only on that condition, so nothing else may
write that path when the profile is mechanical.

Three properties this producer has that an agentic one cannot, and which are the reason Phase 1 is
the only rung comparable to the published baselines:

* **Deterministic.** Same claim, same corpus, same k, same bytes out. No sampling, no model.
* **Budgeted.** Exactly *k* passages reach the judge (C6.3). Sarol's MultiVerS 0.52 used BM25 +
  MonoT5 top-20, so ``k=20`` matches its retrieval budget. Report *k* with every number.
* **Honest about what it did.** It declares ``attestation.selector`` so a reader can tell mechanical
  retrieval from an agentic search, and ``phrasings_tried`` holds the queries it *actually issued* —
  one, the claim text. It never pads that list to clear a floor written for agents.

⚠ **No decomposition, and a null indirect check.** The envelope carries exactly one sub-claim
holding the whole citing sentence, and ``attestation.indirect_attribution_check`` is ``None``. Both
are real differences from Phase 2, not oversights, and both must be reported as confounds when the
Phase 1 → Phase 2 delta is quoted (C6.4, C6.7). The named INDIRECT remedy is extractor-side and is
therefore structurally out of reach in Phase 1.

⚠ **One deliberate deviation from the C6.2 skeleton, worth stating.** That skeleton shows
``"section": "abstract"`` on an evidence item while its own ``section_checklist`` in the same
object says ``{"section": "content", "read": true}``. The two disagree. This producer emits
``"content"`` in both places: the text genuinely comes from ``content.txt``, and the plan itself
records at length that Sarol's per-chunk ``abstract`` field is a SciFact-inherited misnomer holding
that chunk's sentences rather than the paper's abstract. Writing ``"abstract"`` would reintroduce
exactly the confusion C6.1 spent a paragraph killing.
"""

from __future__ import annotations

import json
import math
import pathlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

#: `stage_claim.py` writes `content.txt` as `f"L{i+1} [p?]: {line}"`. Parsed rather than re-derived
#: from the benchmark rows, so this producer stays behind the same blinding boundary staging sets:
#: it never opens `claims-<split>.jsonl`, never sees a split, and never touches gold.
CONTENT_LINE = re.compile(r"^L(\d+)\s*\[([^\]]*)\]:\s?(.*)$")

#: Okapi BM25's usual constants. Fixed, not tuned: a tuned retriever would make Phase 1 a retrieval
#: experiment, and the experiment is about the judge.
BM25_K1 = 1.5
BM25_B = 0.75

SCHEMA_VERSION = "1.1"

#: What staging fixes for every Sarol claim. `stage_claim.py` has no claim-type classifier, so this
#: is a staging convention rather than an observation -- recorded here because the exit validator's
#: phrasing floor keys off it.
STAGED_CLAIM_TYPE = {"type": "PARAPHRASED", "confidence": "medium"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass(frozen=True)
class Passage:
    line: int
    page: str
    text: str


def read_content(handle: pathlib.Path) -> list[Passage]:
    """Parse `pdfs/<citekey>/content.txt` into numbered passages.

    Lines that do not match the staging prefix are skipped rather than guessed at: a malformed
    corpus should retrieve nothing and be visibly empty, not silently retrieve garbage.
    """
    path = pathlib.Path(handle) / "content.txt"
    passages: list[Passage] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = CONTENT_LINE.match(raw)
        if m and m.group(3).strip():
            passages.append(Passage(line=int(m.group(1)), page=m.group(2), text=m.group(3).strip()))
    return passages


def bm25_rank(query: str, passages: "list[Passage]") -> list[tuple[float, Passage]]:
    """Okapi BM25 over the passages. Returns (score, passage), best first.

    Written out rather than pulled from a library on purpose: it is ~20 lines, it removes a
    dependency from the reproducibility surface of a frozen experiment, and the ranking is part of
    the measured condition rather than an implementation detail.

    Ties break on line number, so the output is a total order and the producer is deterministic.
    """
    docs = [_tokens(p.text) for p in passages]
    if not docs:
        return []
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))

    q_terms = _tokens(query)
    scored: list[tuple[float, Passage]] = []
    for doc, passage in zip(docs, passages):
        freqs = Counter(doc)
        dl = len(doc)
        score = 0.0
        for term in q_terms:
            f = freqs.get(term, 0)
            if not f:
                continue
            # Okapi IDF, floored at zero: a term in >half the docs otherwise scores negative and
            # can make a passage rank *worse* for containing a query word.
            idf = max(0.0, math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1.0))
            denom = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl)
            score += idf * (f * (BM25_K1 + 1)) / denom
        if score > 0:
            scored.append((score, passage))
    scored.sort(key=lambda sp: (-sp[0], sp[1].line))
    return scored


def build_envelope(
    *,
    claim_id: str,
    run_id: str,
    citekey: str,
    claim_text: str,
    passages: "Iterable[Passage]",
    k: int,
    selector: str,
    source_mode: str,
) -> dict[str, Any]:
    """The C6.2 evidence envelope, conforming to the extractor half of `verdict_schema.md`.

    ``schema_version`` is present and is not optional — it is in the exit validator's
    ``REQUIRED_TOP_LEVEL``, and because the adjudicator preserves every other field from this file,
    omitting it here fails *every* claim downstream. An earlier draft of the C6.2 skeleton did omit
    it; that is why it is called out rather than merely written.
    """
    handle = f"pdfs/{citekey}/"
    evidence = [
        {
            "section": "content",
            "line": p.line,
            "snippet": p.text,
            "source_mode": source_mode,
            "locator": f"{handle}content.txt#L{p.line}",
        }
        for p in passages
    ]
    return {
        "claim_id": claim_id,
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "citekey": citekey,
        "source_mode": source_mode,
        "handle": handle,
        "paperclip_handle": None,
        "ingest_mode": None,
        "claim_text": claim_text,
        "claim_type": dict(STAGED_CLAIM_TYPE),
        "sub_claims": [
            {
                # No decomposition in Phase 1 (C6.2). One sub-claim, the whole citing sentence, so
                # the adjudicator's worst-wins rollup is trivially that sub-claim's verdict.
                "sub_claim_id": f"{claim_id}.a",
                "text": claim_text,
                "evidence": evidence,
                "figures_checked": [],
                "verdict": None,
            }
        ],
        "attestation": {
            # Exactly the queries issued -- one. BM25 top-k is a single query returning k results,
            # not k queries, and padding this to clear a floor written for agentic search would be
            # the one dishonesty this whole rung exists to avoid.
            "phrasings_tried": [claim_text],
            "section_checklist": [{"section": "content", "read": True}],
            "indirect_attribution_check": None,
            "out_of_context_check": None,
            "closest_adjacent": None,
            # The field that tells a reader -- and the exit validator -- that no agent searched.
            "selector": selector,
            "retrieval_k": k,
            "n_passages_available": None,
        },
        "stage": "grounding",
    }


def produce(
    staging_dir: "pathlib.Path | str",
    claim_id: str,
    *,
    run_id: str,
    profile,
    write: bool = True,
) -> dict[str, Any]:
    """Write ``ledger/evidence/<claim_id>.json`` for one staged claim. Returns the envelope.

    Reads only what staging exposes to an agent: `staging_info.json` and the `pdfs/<citekey>/`
    handle. It never reads the benchmark rows and never reads gold.
    """
    staging = pathlib.Path(staging_dir)
    info = json.loads((staging / "staging_info.json").read_text(encoding="utf-8"))
    citekey = info["citekey"]
    claim_text = info["claim_text_normalized"]

    passages = read_content(staging / "pdfs" / citekey)
    k = profile.retrieval_k
    ranked = bm25_rank(claim_text, passages)[:k]

    envelope = build_envelope(
        claim_id=claim_id,
        run_id=run_id,
        citekey=citekey,
        claim_text=claim_text,
        passages=[p for _, p in ranked],
        k=k,
        selector=profile.selector,
        source_mode=profile.source_mode,
    )
    envelope["attestation"]["n_passages_available"] = len(passages)

    if write:
        out = staging / "ledger" / "evidence" / f"{claim_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return envelope


#: Dispatch table. A profile names its producer; this maps the name to the callable. `extractor`
#: is deliberately absent — under `agentic` the extractor *stage* writes the envelope, so there is
#: no mechanical producer to call and the Runner must not call one.
PRODUCERS = {"bm25": produce}


def for_profile(profile):
    """The producer a profile needs, or None when its evidence comes from a dispatched stage."""
    return PRODUCERS.get(profile.evidence_producer)


# =================================================================================================
# Selftest
# =================================================================================================


def _stage(tmp: pathlib.Path, lines: "list[str]", claim: str) -> pathlib.Path:
    """A staged claim in `stage_claim.py`'s shape. Nothing here reads gold or the benchmark."""
    staging = tmp / "staging"
    handle = staging / "pdfs" / "ref_abc123"
    handle.mkdir(parents=True)
    (handle / "content.txt").write_text(
        "".join(f"L{i + 1} [p?]: {line}\n" for i, line in enumerate(lines)), encoding="utf-8"
    )
    (staging / "staging_info.json").write_text(
        json.dumps({
            "citekey": "ref_abc123",
            "claim_text_normalized": claim,
            "source_mode": "corpus",
            "multi_cit_context": "single",
            "source_description": f"corpus-chunks (N={len(lines)})",
        }),
        encoding="utf-8",
    )
    return staging


def _selftest() -> int:
    import sys
    import tempfile

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import profiles as profiles_mod
    import validate_sarol

    claim = "deep learning reconstruction reduces MRI acquisition time fourfold"
    corpus = [
        "a fourfold acceleration was achieved on the knee MRI protocol",   # L1 -- on point
        "the cohort consisted of patients recruited between 2015 and 2018",  # L2 -- off topic
        "deep learning reconstruction was compared against compressed sensing",  # L3 -- partial
        "figure 2 shows the acquisition time reduction achieved",           # L4 -- partial
        "",                                                                 # L5 -- blank, skipped
    ]

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        staging = _stage(tmp, corpus, claim)
        env = produce(staging, "C042", run_id="run_x", profile=profiles_mod.RETRIEVAL)
        written = json.loads(
            (staging / "ledger" / "evidence" / "C042.json").read_text(encoding="utf-8")
        )
        passages = read_content(staging / "pdfs" / "ref_abc123")
        ranked = bm25_rank(claim, passages)

        # k=2 to prove the budget actually truncates, against a 4-passage corpus.
        small = produce(
            staging, "C043", run_id="run_x",
            profile=dataclasses_replace(profiles_mod.RETRIEVAL, retrieval_k=2), write=False,
        )

        # What the adjudicator would add on top, so the whole round trip is checked rather than
        # just the producer's half.
        verdict = dict(env)
        verdict["sub_claims"] = [{**env["sub_claims"][0], "verdict": "ACCURATE"}]
        verdict.update(
            overall_verdict="ACCURATE", rubric_variant="sarol_2024_9class", stage="adjudication"
        )
        result = validate_sarol.validate_obj(
            verdict,
            expect_claim_id="C042",
            rubric_path=pathlib.Path(__file__).resolve().parents[1]
            / "specs" / "verdict_schema_sarol.md",
        )

        checks = [
            # -- the gate the whole rung depends on -------------------------------------------
            ("a produced envelope survives the exit validator once adjudicated", result.ok),
            ("...with no violations at all", result.violations == []),
            ("...including schema_version, whose omission would fail every claim",
             env["schema_version"] == "1.1"),

            # -- retrieval actually retrieves --------------------------------------------------
            ("blank corpus lines are skipped, not retrieved as empty evidence",
             len(passages) == 4),
            # BM25 is lexical overlap, not meaning: L3 shares three query terms
            # (deep/learning/reconstruction) and wins, while L1 -- the passage that actually
            # *supports* "fourfold" -- shares two and comes third. That is not a bug to fix here;
            # it is precisely the Phase 1 condition, and precisely the limitation Phase 2's
            # agentic acquisition is hypothesised to beat. Pinned so nobody "improves" the
            # retriever and quietly changes what the experiment is comparing.
            ("BM25 ranks by lexical overlap, so the highest-overlap passage wins",
             ranked[0][1].line == 3),
            ("...and the supporting-but-lower-overlap passage still makes the top-k",
             any(pg.line == 1 for _, pg in ranked)),
            ("...while a passage sharing no query terms is excluded entirely",
             all(pg.line != 2 for _, pg in ranked)),
            ("the budget truncates to k", len(small["sub_claims"][0]["evidence"]) == 2),
            ("...and k is recorded, since a macro-F1 without it is not a result",
             env["attestation"]["retrieval_k"] == 20),
            ("evidence carries a resolvable locator back into content.txt",
             env["sub_claims"][0]["evidence"][0]["locator"]
             == f"pdfs/ref_abc123/content.txt#L{ranked[0][1].line}"),
            ("...and evidence order follows the ranking",
             [e["line"] for e in env["sub_claims"][0]["evidence"]]
             == [pg.line for _, pg in ranked]),
            ("...and is labelled 'content', matching its own section_checklist",
             env["sub_claims"][0]["evidence"][0]["section"] == "content"
             and env["attestation"]["section_checklist"][0]["section"] == "content"),

            # -- honesty about what it did -----------------------------------------------------
            ("the selector is declared, so a reader can tell this from an agentic search",
             env["attestation"]["selector"] == "bm25-top20"),
            ("phrasings_tried holds the one query actually issued, unpadded",
             env["attestation"]["phrasings_tried"] == [claim]),
            ("provenance says the corpus, not a PDF ingest that never happened",
             env["source_mode"] == "sarol_corpus"),
            ("...and no paperclip handle is claimed", env["paperclip_handle"] is None),

            # -- the Phase 1 confounds, present on purpose -------------------------------------
            ("no sub-claim decomposition happens in Phase 1", len(env["sub_claims"]) == 1),
            ("...the single sub-claim carries the whole citing sentence",
             env["sub_claims"][0]["text"] == claim),
            ("...and it carries no verdict; the judge assigns that",
             env["sub_claims"][0]["verdict"] is None),
            ("indirect_attribution_check is null, which is why the INDIRECT fix is out of reach",
             env["attestation"]["indirect_attribution_check"] is None),

            # -- determinism -------------------------------------------------------------------
            ("the producer is deterministic", produce(
                staging, "C042", run_id="run_x", profile=profiles_mod.RETRIEVAL, write=False
            ) == env),
            ("...and what it returned is what it wrote", written == env),

            # -- the dispatch table ------------------------------------------------------------
            ("retrieval has a mechanical producer",
             for_profile(profiles_mod.RETRIEVAL) is produce),
            ("agentic has none, because its extractor stage writes the envelope",
             for_profile(profiles_mod.AGENTIC) is None),

            # -- degenerate input ---------------------------------------------------------------
            ("an empty corpus retrieves nothing rather than inventing evidence",
             bm25_rank(claim, []) == []),
            ("a claim sharing no terms with the corpus retrieves nothing",
             bm25_rank("xylophone bassoon", passages) == []),
        ]

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def dataclasses_replace(obj, **kw):
    import dataclasses

    return dataclasses.replace(obj, **kw)


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
