"""Score gxl's paperclip claim checker on paper-trail's 50 VAL claims, beside paper-trail itself.

Plan: ``planning/paper-trail/2026-10-06-gxl-claim-checker-baseline.md`` (approved 2026-10-07). A
**baseline, not a tool in our run** (Phil 2026-10-06): our runs use only paperclip's plain
text-reading tools; gxl's model-backed verifier is something to compare against.

Three phases, kept apart so the verdicts are fixed before any gold is read:

1. **Run** (default). Recompute the seeded VAL draw and check it equals the roster file; build each
   claim from its staging folder (``claim_text_normalized`` -- never gold); attach every claim to one
   paperclip repo as a structured claim and ``git_commit {verify: true}`` in batches. Every raw gxl
   response is saved under ``raw/`` *before* anything is parsed, then ``verdicts.json`` is written.
   A smoke on the two demo claims runs first, in its own throwaway repo, and must parse cleanly.
2. **Reparse** (``--reparse``). Rebuild ``verdicts.json`` from ``raw/`` without calling gxl, so a
   parser fix never costs another verify pass against the 100-task daily cap.
3. **Score** (``--score-only``). Refuses without ``verdicts.json``. Only now reads gold
   (``sampling.gold_labels("dev")``), and scores gxl, paper-trail v8 / v9 and always-ACCURATE the
   same ways on the same claims, then writes ``scores.json`` and ``card.md``.

**Reading gxl's output.** Its verdict is per claim: ``[OK]`` supported, ``[X]`` rejected, ``[!]`` an
infrastructure error (gxl's own legend). The exact layout of ``git_status`` / ``git_commit`` text is
not documented, so the parser is strict rather than clever: a claim gets a verdict only when exactly
one kind of marker sits in its own block, and anything else is recorded as unparsed, never guessed.
Claims carry a ``pt-`` prefixed id so ``1-31`` can never match inside ``11-31``.

Exit codes: 0 done; 2 roster or input problem; 3 rate-limited (resume with ``--resume``); 4 some
claims have no readable verdict; 5 gxl errors above 5%; 6 a scoring sanity check failed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import time
from typing import Any

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "optimizer"))

import paperclip_mcp  # noqa: E402
import stage_claim  # noqa: E402

RUNS = pathlib.Path.home() / ".paper-trail" / "runs"
DEFAULT_ROSTER = RUNS / "hillclimb-2026-09-22c" / "val" / "val_draw.json"
ROSTER_MD5 = "8e73ac3e"  # md5 of ",".join(sorted(claim_ids)), first 8 hex -- the plan's fingerprint
VAL_N = 50
SPLIT = "dev"

#: The only guidance gxl gets: which field to check and what the marker means. No Sarol label
#: definitions -- this measures gxl's checker as shipped (OQ2, deferred).
VERIFIER_CONTEXT = (
    "Verify the `text` field; `claim_id` is a label. A `[CIT]` marker is where this paper is cited."
)

#: The two smoke claims from the 2026-10-06 hands-on demo: one cited paper, two citing sentences.
SMOKE_PAPER = "PMC3179858"
SMOKE_FILES = ("PMC3142215_4", "PMC3142215_2")

#: paper-trail runs on the same 50 claims (local manifests, Haiku, retrieval profile).
PT_RUNS = {
    "paper-trail v8": RUNS / "hillclimb-2026-09-22a/val/iter1-program-v8/run_manifest.json",
    "paper-trail v9": RUNS / "hillclimb-2026-09-22c/val/iter1-current/run_manifest.json",
    "paper-trail v9 (re-measure)": RUNS / "measure-v9-2026-09-22/val/val/mat-v9/run_manifest.json",
    # The original hand-written program, before any optimization (Phil 2026-10-07: "our v1"). These
    # hill-climbs started from program-v0, so their `iter1-current` VAL run measures it. 09-21d is
    # left out: 21 of its 50 calls failed. Both ran on the 09-20 harness, two days before v8's.
    "paper-trail v0 (original, 09-20b)": RUNS / "hillclimb-2026-09-20b/val/iter1-current/run_manifest.json",
    "paper-trail v0 (original, 09-20c)": RUNS / "hillclimb-2026-09-20c/val/iter1-current/run_manifest.json",
}
NOISE = 0.08  # the two v9 runs differ by this much on the same program and claims, in the 2-way view

#: The headline view (Phil 2026-10-07, replacing 2-way accuracy as the go/no-go): 3-way macro-F1 over
#: the claims whose gold label every system can give, i.e. dropping the irrelevant class, which gxl's
#: yes/no cannot express. Macro-F1 rather than accuracy because with those claims gone ~80% of gold is
#: ACCURATE, and answering ACCURATE every time out-scores every real system on accuracy.
HEADLINE = "3-way macro-F1 on the claims whose gold every system can give"


def headline(r: dict[str, Any]) -> float:
    return r["3way_irrelevant_dropped"]["macro_f1"]

MARKER = re.compile(r"\[(OK|X|!)\]")
MARKER_NAME = {"OK": "OK", "X": "REJECTED", "!": "ERROR"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def _tag(claim_id: str) -> str:
    return f"pt-{claim_id}"


# -------------------------------------------------------------------------------------------------
# Roster and claims -- structure only, no gold
# -------------------------------------------------------------------------------------------------


def roster_ids(path: pathlib.Path) -> list[str]:
    ids = json.loads(path.read_text(encoding="utf-8"))["0"]
    if len(ids) != VAL_N:
        raise SystemExit(f"[roster] {path} holds {len(ids)} claims, expected {VAL_N}")
    return list(ids)


def check_roster(ids: list[str]) -> str:
    """Recompute the seeded draw (`sampling.val_inputs_for` draws iteration 0, `fresh`) and compare."""
    import sampling  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        drawn = sampling.resolve_batch(
            0, n=VAL_N, mode="fresh", split=SPLIT, history_path=pathlib.Path(tmp) / "h.json"
        )
    recomputed = sorted(u.claim_id for u in drawn)
    md5 = hashlib.md5(",".join(sorted(ids)).encode()).hexdigest()[:8]
    if recomputed != sorted(ids):
        raise SystemExit(f"[roster] recomputed draw differs from the roster file (md5 {md5})")
    print(f"[roster] recomputed draw matches the roster file: {VAL_N} claims, md5 {md5}")
    return md5


def build_claims(ids: list[str], staging_root: pathlib.Path) -> list[dict[str, Any]]:
    claims = []
    for cid in ids:
        info = json.loads((staging_root / cid / "staging_info.json").read_text(encoding="utf-8"))
        bucket = int(cid.split("-")[1])
        ref = stage_claim.find_references_txt(SPLIT, bucket)
        if ref is None:
            raise SystemExit(f"[claims] no references file for bucket {bucket} ({cid})")
        pmcid = ref.stem.split("_", 1)[1]
        if not pmcid.startswith("PMC"):
            raise SystemExit(f"[claims] unexpected references file name {ref.name} for {cid}")
        claims.append(
            {
                "claim_id": cid,
                "tag": _tag(cid),
                "pmcid": pmcid,
                "text": info["claim_text_normalized"],
                "multi_cit_context": info.get("multi_cit_context"),
            }
        )
    return claims


def smoke_claims() -> list[dict[str, Any]]:
    folder = next((stage_claim.BENCH_DIR / "annotations" / "Dev" / "citations").glob(f"*_{SMOKE_PAPER}"))
    out = []
    for name in SMOKE_FILES:
        ann = json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))
        context = ann["citation_context"]
        if isinstance(context, list):  # a list of {"text", "start", "end"} spans
            context = " ".join(s["text"] if isinstance(s, dict) else str(s) for s in context)
        out.append(
            {
                "claim_id": f"smoke-{name}",
                "tag": _tag(f"smoke-{name}"),
                "pmcid": SMOKE_PAPER,
                "text": stage_claim.normalize_claim_text(context),
                "multi_cit_context": None,
            }
        )
    return out


# -------------------------------------------------------------------------------------------------
# Talking to gxl -- every response saved raw before it is read
# -------------------------------------------------------------------------------------------------


class Session:
    def __init__(self, out: pathlib.Path, repo: str):
        self.out, self.repo = out, repo
        self.raw = out / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.log_path = out / "calls.jsonl"

    def call(self, label: str, tool: str, args: dict[str, Any]) -> str:
        started = time.monotonic()
        try:
            # git_init names the new repo in `name`; passing `repo` too makes the server look the
            # not-yet-existing repo up first and fail with "path or document was not found".
            scoped = args if tool == "git_init" else {**args, "repo": self.repo}
            text = paperclip_mcp.call(tool, scoped)
            error = None
        except paperclip_mcp.PaperclipError as exc:
            text, error = "", exc
        seconds = round(time.monotonic() - started, 2)
        (self.raw / f"{label}.txt").write_text(text if error is None else f"ERROR: {error}", encoding="utf-8")
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": _now(), "label": label, "tool": tool, "seconds": seconds,
                                 "error": None if error is None else str(error)}) + "\n")
        if error is not None:
            raise error
        return text


def _progress(out: pathlib.Path) -> dict[str, Any]:
    path = out / "progress.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_progress(out: pathlib.Path, progress: dict[str, Any]) -> None:
    (out / "progress.json").write_text(json.dumps(progress, indent=1), encoding="utf-8")


def verify(claims: list[dict[str, Any]], out: pathlib.Path, repo: str, batch_size: int, resume: bool) -> None:
    """Attach the claims and verify them, `batch_size` at a time. Resumable after a cap stop."""
    out.mkdir(parents=True, exist_ok=True)
    progress = _progress(out)
    if progress and not resume:
        raise SystemExit(f"[run] {out} already holds a run; pass --resume to continue it")
    if resume and progress.get("repo") not in (None, repo):
        raise SystemExit(f"[run] {out} belongs to repo {progress['repo']!r}, not {repo!r}")
    session = Session(out, repo)
    (out / "claims.json").write_text(json.dumps(claims, indent=1), encoding="utf-8")
    if not progress:
        session.call("init", "git_init", {"name": repo, "description": "paper-trail baseline: Sarol 2024 VAL claims"})
        progress = {"repo": repo, "added": [], "commits": 0, "started_at": _now()}
        _save_progress(out, progress)

    # Number commits after any already on disk, so a resumed run never overwrites an earlier raw file.
    progress["commits"] = max(progress["commits"], len(list(session.raw.glob("commit-*.txt"))))

    def commit(note: str) -> None:
        progress["commits"] += 1
        try:
            session.call(f"commit-{progress['commits']:02d}", "git_commit", {
                "message": f"paper-trail baseline: {note}", "verify": True, "verifier_context": VERIFIER_CONTEXT})
        except paperclip_mcp.RateLimited:
            raise
        except paperclip_mcp.PaperclipError as exc:
            # The hosted server caps a command at 180 s (10 claims hit it on 2026-10-07). A timed-out
            # pass is not fatal: gxl re-verifies only unresolved claims, so `settle` reads the status
            # and commits again for whatever is still unchecked.
            if "timed out" not in str(exc):
                raise
            print(f"[run] verify pass {progress['commits']} hit the server's time limit; checking status")
        _save_progress(out, progress)

    def settle(batch: list[dict[str, Any]], note: str, tries: int = 3) -> None:
        """Commit until every claim in `batch` shows a verdict marker, or `tries` passes are spent."""
        for attempt in range(1, tries + 1):
            commit(note if attempt == 1 else f"{note} (pass {attempt})")
            status = session.call(f"status-c{progress['commits']:02d}", "git_status", {})
            found = blocks_by_tag(status, [c["tag"] for c in batch])
            unchecked = [t for t, v in found.items() if v["verdict"] in ("NO_MARKER", "MISSING")]
            if not unchecked:
                return
            print(f"[run] {len(unchecked)}/{len(batch)} claims still unchecked after pass {attempt}")

    if resume and progress["added"]:
        settle([c for c in claims if c["claim_id"] in progress["added"]], "resume: verify claims left unresolved")
    pending = [c for c in claims if c["claim_id"] not in progress["added"]]
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        for c in batch:
            payload = json.dumps({"type": "sarol_claim", "claim_id": c["tag"], "text": c["text"]})
            session.call(f"add-{c['claim_id']}", "git_add", {"paper_ids": [c["pmcid"], payload], "as_json": True})
            progress["added"].append(c["claim_id"])
            _save_progress(out, progress)
        settle(batch, f"verify {len(batch)} claims ({len(progress['added'])}/{len(claims)} attached)")
        print(f"[run] verified batch: {len(progress['added'])}/{len(claims)} claims attached")

    session.call("status-final", "git_status", {})
    first = parse_verdicts(claims, out)
    retry = [cid for cid, v in first.items() if v["verdict"] in ("ERROR", "NO_MARKER")]
    if retry:
        print(f"[run] {len(retry)} claims errored or unverified; one retry pass")
        commit("retry claims with infrastructure errors")
        session.call("status-retry", "git_status", {})
    try:
        session.call("export-csv", "git_export", {"format": "csv"})
    except paperclip_mcp.PaperclipError as exc:  # a convenience copy; the verdicts do not depend on it
        print(f"[run] csv export failed (kept going): {exc}")


# -------------------------------------------------------------------------------------------------
# Parsing -- strict, from the saved raw text only
# -------------------------------------------------------------------------------------------------


def blocks_by_tag(text: str, tags: list[str]) -> dict[str, dict[str, Any]]:
    """For each tag, the marker in its block, or why there is none.

    A marker on the tag's own line wins. Otherwise the marker sits either after its claim (block =
    the tag's line up to the next tag's line) or before it (block = after the previous tag's line
    up to the tag's line). Which one is a property of the whole response, not of one claim -- read
    per claim, "after" would hand each claim its successor's marker in a marker-first layout -- so
    both readings are tried and the one that gives more claims exactly one kind of marker is used.
    A tie in which the readings disagree, two tags on one line, or two kinds of marker in a block
    is AMBIGUOUS: recorded, never guessed.
    """
    lines = text.splitlines()
    first_line: dict[str, int] = {}
    for tag in tags:
        pat = re.compile(rf"(?<![\w-]){re.escape(tag)}(?![\w-])")
        for i, line in enumerate(lines):
            if pat.search(line):
                first_line[tag] = i
                break
    order = sorted(first_line.items(), key=lambda kv: kv[1])

    def kinds_in(lo: int, hi: int) -> set[str]:
        return {m.group(1) for line in lines[lo:hi] for m in MARKER.finditer(line)}

    def reading(direction: str) -> dict[str, dict[str, Any]]:
        res: dict[str, dict[str, Any]] = {}
        for k, (tag, i) in enumerate(order):
            if any(j == i for t, j in order if t != tag):
                res[tag] = {"verdict": "AMBIGUOUS", "why": "several claims on one line"}
                continue
            if direction == "after":
                lo, hi = i, (order[k + 1][1] if k + 1 < len(order) else len(lines))
            else:
                lo, hi = (order[k - 1][1] + 1 if k > 0 else 0), i + 1
            kinds = kinds_in(i, i + 1) or kinds_in(lo, hi)
            block = "\n".join(lines[lo:hi]).strip()
            if len(kinds) == 1:
                res[tag] = {"verdict": MARKER_NAME[kinds.pop()], "block": block}
            elif not kinds:
                res[tag] = {"verdict": "NO_MARKER", "block": block}
            else:
                res[tag] = {"verdict": "AMBIGUOUS", "why": f"markers {sorted(kinds)} in one block", "block": block}
        return res

    after, before = reading("after"), reading("before")

    def clean(res: dict[str, dict[str, Any]]) -> int:
        return sum(1 for v in res.values() if v["verdict"] in MARKER_NAME.values())

    if clean(after) != clean(before):
        out = after if clean(after) > clean(before) else before
    else:
        out = {
            tag: after[tag] if after[tag]["verdict"] == before[tag]["verdict"]
            else {"verdict": "AMBIGUOUS", "why": "marker-before and marker-after readings disagree"}
            for tag in after
        }
    for tag in tags:
        out.setdefault(tag, {"verdict": "MISSING"})
    return out


def parse_verdicts(claims: list[dict[str, Any]], out: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Per claim: the latest status's verdict if it has one, else the latest commit that named it."""
    raw = out / "raw"
    tags = [c["tag"] for c in claims]
    sources = sorted(raw.glob("commit-*.txt")) + sorted(raw.glob("status-*.txt"))  # later wins
    best: dict[str, dict[str, Any]] = {t: {"verdict": "MISSING", "source": None} for t in tags}
    for path in sources:
        for tag, found in blocks_by_tag(path.read_text(encoding="utf-8"), tags).items():
            if found["verdict"] != "MISSING":
                best[tag] = {**found, "source": path.name}
    return {c["claim_id"]: best[c["tag"]] for c in claims}


def write_verdicts(claims: list[dict[str, Any]], out: pathlib.Path, md5: "str | None") -> dict[str, Any]:
    parsed = parse_verdicts(claims, out)
    counts: dict[str, int] = {}
    for v in parsed.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    doc = {
        "written_at": _now(),
        "repo": _progress(out).get("repo"),
        "roster_md5": md5,
        "verifier_context": VERIFIER_CONTEXT,
        "counts": counts,
        "claims": [{**c, **parsed[c["claim_id"]]} for c in claims],
    }
    (out / "verdicts.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"[verdicts] {out / 'verdicts.json'}: {counts}")
    return doc


def verdict_exit(doc: dict[str, Any]) -> int:
    counts, n = doc["counts"], len(doc["claims"])
    unreadable = sum(counts.get(k, 0) for k in ("NO_MARKER", "AMBIGUOUS", "MISSING"))
    if unreadable:
        print(f"[verdicts] {unreadable}/{n} claims have no readable verdict -- read raw/ and fix the parser, then --reparse")
        return 4
    if counts.get("ERROR", 0) > 0.05 * n:
        print(f"[verdicts] {counts['ERROR']}/{n} gxl errors, above the plan's 5% -- stop and come back")
        return 5
    return 0


# -------------------------------------------------------------------------------------------------
# Scoring -- the only place gold is read
# -------------------------------------------------------------------------------------------------

#: gxl's verdict as a 9-class label for `score_sarol3.score`. Only the 3-way collapse of these is
#: read; the 9-way numbers from them are never reported (OQ1: gxl's 9-way is an upper bound only).
GXL_AS_LABEL = {"OK": "ACCURATE", "REJECTED": "NOT_SUBSTANTIATE"}
MISS = "GXL_ERROR"  # an error or unreadable verdict: a miss, counted


def two_way(label: str) -> "str | None":
    from parse_verdict import SAROL_9  # noqa: PLC0415

    if label not in SAROL_9:
        return None
    return "ACCURATE" if label == "ACCURATE" else "NOT_ACCURATE"


def views(pairs: list[tuple[str, str]], *, nine_way_is_real: bool) -> dict[str, Any]:
    import score_sarol3  # noqa: PLC0415
    from parse_verdict import to_3way  # noqa: PLC0415

    full = score_sarol3.score(pairs)
    kept = [(p, g) for p, g in pairs if to_3way(g) != "IRRELEVANT"]
    dropped = score_sarol3.score(kept)
    two = [(two_way(p), two_way(g)) for p, g in pairs]
    positives = [(p, g) for p, g in two if g == "NOT_ACCURATE"]
    flagged = [(p, g) for p, g in two if p == "NOT_ACCURATE"]
    caught = sum(1 for p, _ in positives if p == "NOT_ACCURATE")
    acc2 = sum(1 for p, g in two if p == g) / len(two)
    return {
        "n": len(pairs),
        "n_misses_invalid": full["n_invalid"],
        "3way_all": {"macro_f1": full["macro_f1_3way"], "accuracy": full["micro_f1"]},
        "3way_irrelevant_dropped": {
            "n": len(kept),
            # Macro over the two buckets this view keeps; dividing by 3 would cap it at 2/3.
            "macro_f1": (dropped["per_class_f1"]["ACCURATE"] + dropped["per_class_f1"]["NOT_ACCURATE"]) / 2,
            "accuracy": dropped["micro_f1"],
        },
        "2way_accuracy": acc2,
        "9way_accuracy": full["primary_metric"] if nine_way_is_real else None,
        "9way_upper_bound": None if nine_way_is_real else acc2,
        "binary": {
            "n_gold_flagged": len(positives),
            "caught": caught,
            "passed_flagged": sum(1 for p, _ in positives if p == "ACCURATE"),
            "recall": caught / len(positives) if positives else 0.0,
            "precision": caught / len(flagged) if flagged else 0.0,
        },
    }


def gold_evidence(ids: list[str]) -> dict[str, list[dict[str, str]]]:
    """Sarol's annotated evidence per claim: the cited paper's sentences and the label each supports.

    Read only in the scoring phase, like gold. ``claims-<split>.jsonl`` names sentence indices per
    corpus document (``{doc_id: [{"sentences": [i], "label": ...}]}``); the text is the document's
    ``abstract`` list in ``corpus.jsonl``. Only documents in the claim's cited bucket count. The
    ETIQUETTE / IRRELEVANT classes are defined by having no such evidence, so they come back empty.
    """
    rows = {int(r["id"]): r for r in stage_claim.load_claims(SPLIT)}
    corpus = stage_claim.load_corpus()
    out: dict[str, list[dict[str, str]]] = {}
    for cid in ids:
        row_id, bucket = (int(x) for x in cid.split("-"))
        found = []
        for doc_id, spans in sorted((rows[row_id].get("evidence") or {}).items()):
            doc = corpus.get(int(doc_id))
            if int(doc_id) // 1000 != bucket or not spans or doc is None:
                continue
            for span in spans:
                text = " ".join(doc["abstract"][i].strip() for i in span.get("sentences", []) if i < len(doc["abstract"]))
                found.append({"label": span.get("label", ""), "text": text})
        out[cid] = found
    return out


def pt_predictions(manifest: pathlib.Path) -> dict[str, str]:
    m = json.loads(manifest.read_text(encoding="utf-8"))
    out = {}
    for r in m["claims"]:
        if r.get("status") == "failed":
            out[r["claim_id"]] = "FAILED_CALL"
        else:
            out[r["claim_id"]] = (r.get("validation") or {}).get("overall_verdict") or "INVALID_OUTPUT"
    return out


def score_only(out: pathlib.Path) -> int:
    vpath = out / "verdicts.json"
    if not vpath.exists():
        print(f"[score] refusing: {vpath} does not exist, so gold would be read before the verdicts are fixed")
        return 2
    verdicts = json.loads(vpath.read_text(encoding="utf-8"))
    gold_read_at = _now()
    import sampling  # noqa: PLC0415

    gold_all = sampling.gold_labels(SPLIT)
    ids = [c["claim_id"] for c in verdicts["claims"]]
    gold = {cid: gold_all[tuple(int(x) for x in cid.split("-"))] for cid in ids}

    gxl_pred = {c["claim_id"]: GXL_AS_LABEL.get(c["verdict"], MISS) for c in verdicts["claims"]}
    systems: dict[str, dict[str, str]] = {"gxl claim checker": gxl_pred}
    for name, path in PT_RUNS.items():
        preds = pt_predictions(path)
        if set(preds) != set(ids):
            print(f"[score] {name}: claim set differs from the roster")
            return 2
        systems[name] = preds
    systems["always ACCURATE"] = {cid: "ACCURATE" for cid in ids}
    results = {
        name: views([(p[cid], gold[cid]) for cid in ids], nine_way_is_real=name != "gxl claim checker")
        for name, p in systems.items()
    }

    floor, v8 = results["always ACCURATE"], results["paper-trail v8"]
    sanity = [
        ("always-ACCURATE scores 0.70 on this roster", round(floor["9way_accuracy"], 2) == 0.70),
        ("program-v8 reproduces 0.66 9-way", round(v8["9way_accuracy"], 2) == 0.66),
        ("program-v8 reproduces 0.595 3-way macro-F1", round(v8["3way_all"]["macro_f1"], 3) == 0.595),
        ("verdicts were written before gold was read", verdicts["written_at"] < gold_read_at),
    ]
    for n, ok in sanity:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    two_way_gap = results["gxl claim checker"]["2way_accuracy"] - v8["2way_accuracy"]
    # Noise is the gap between two runs of the same program (v9) on the SAME view it is applied to.
    noise = abs(headline(results["paper-trail v9"]) - headline(results["paper-trail v9 (re-measure)"]))
    gap = headline(results["gxl claim checker"]) - headline(v8)
    v0_runs = [headline(r) for n, r in results.items() if n.startswith("paper-trail v0")]
    lift = headline(v8) - max(v0_runs)  # against the better original run, so the lift is not flattered
    readout = (
        "gxl is ahead of paper-trail v8 by more than the noise: rethink what paper-trail's optimization is for"
        if gap >= noise else
        "paper-trail v8 is ahead of gxl by more than the noise"
        if gap <= -noise else
        "same ballpark: gxl's shipped checker is the bar paper-trail's hill-climb has to beat"
    )
    disagree = [
        {"claim_id": cid, "gold": gold[cid], "paper-trail v8": systems["paper-trail v8"][cid],
         "gxl": next(c["verdict"] for c in verdicts["claims"] if c["claim_id"] == cid)}
        for cid in ids if two_way(gxl_pred[cid]) != two_way(systems["paper-trail v8"][cid])
    ]
    doc = {"scored_at": _now(), "gold_read_at": gold_read_at, "verdicts_written_at": verdicts["written_at"],
           "roster_md5": verdicts.get("roster_md5"), "gxl_counts": verdicts["counts"],
           "sanity": {n: ok for n, ok in sanity}, "two_way_gap_gxl_minus_v8": two_way_gap, "readout": readout,
           "headline": {"metric": HEADLINE, "n_claims": results["gxl claim checker"]["3way_irrelevant_dropped"]["n"],
                        "gap_gxl_minus_v8": gap, "noise": noise, "lift_v8_over_best_v0": lift,
                        "v0_range": [min(v0_runs), max(v0_runs)]},
           "results": results, "disagreements": disagree}
    (out / "scores.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    (out / "card.md").write_text(card(doc), encoding="utf-8")
    (out / "card.html").write_text(card_html(doc, verdicts, systems, gold, gold_evidence(ids)), encoding="utf-8")
    print(f"[score] {HEADLINE}: gxl {headline(results['gxl claim checker']):.3f} vs v8 {headline(v8):.3f} "
          f"(noise {noise:.3f}) -> {readout}; v8 over best v0 +{lift:.3f}")
    print(f"[score] wrote {out / 'scores.json'}, {out / 'card.md'} and {out / 'card.html'}")
    return 0 if all(ok for _, ok in sanity) else 6


def card(doc: dict[str, Any]) -> str:
    def f(x: "float | None", star: bool = False) -> str:
        return "--" if x is None else f"{x:.3f}" + (" (upper bound)" if star else "")

    rows = []
    for name, r in doc["results"].items():
        b = r["binary"]
        rows.append(
            f"| {name} | {f(r['2way_accuracy'])} | {f(r['3way_all']['accuracy'])} | {f(r['3way_all']['macro_f1'])} "
            f"| {f(r['3way_irrelevant_dropped']['accuracy'])} | {f(r['3way_irrelevant_dropped']['macro_f1'])} "
            f"| {f(r['9way_accuracy']) if r['9way_accuracy'] is not None else f(r['9way_upper_bound'], True)} "
            f"| {b['caught']}/{b['n_gold_flagged']} | {f(b['precision'])} | {r['n_misses_invalid']} |"
        )
    dis = "\n".join(f"| {d['claim_id']} | {d['gold']} | {d['paper-trail v8']} | {d['gxl']} |" for d in doc["disagreements"])
    return f"""# gxl claim checker vs paper-trail -- Sarol 2024, 50 VAL claims

Plan: `planning/paper-trail/2026-10-06-gxl-claim-checker-baseline.md`. Roster md5 `{doc['roster_md5']}`.
Verdicts written {doc['verdicts_written_at']}; gold first read {doc['gold_read_at']}. gxl verdict counts: {doc['gxl_counts']}.

**Headline ({doc['headline']['metric']}, {doc['headline']['n_claims']} claims): gxl minus v8 {doc['headline']['gap_gxl_minus_v8']:+.3f}
against {doc['headline']['noise']:.3f} run-to-run noise -- {doc['readout']}.** Optimization lifted paper-trail by
{doc['headline']['lift_v8_over_best_v0']:+.3f} over its better original (v0) run. (2-way accuracy over all 50, the earlier
go/no-go: gxl minus v8 {doc['two_way_gap_gxl_minus_v8']:+.3f}.)

| System | 2-way acc | 3-way acc | 3-way macro-F1 | 3-way acc, irrelevant dropped | macro-F1, irrelevant dropped | 9-way acc | caught flagged | precision | misses |
|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

- gxl says only supported or not. In the 3-way views its "not supported" counts as NOT_ACCURATE, so the 7
  irrelevant-class claims (gold ETIQUETTE, INDIRECT_NOT_REVIEW or IRRELEVANT) are always wrong for it in "3-way, all 50".
- 2-way: an irrelevant-class gold or prediction counts as not accurate, for every system.
- gxl's 9-way figure is an upper bound (equal to its 2-way accuracy): the best any label mapping could do.
- "caught flagged": claims Sarol labels anything but ACCURATE that the system also flagged. Misses = gxl errors or
  unreadable verdicts (gxl) / failed or invalid calls (paper-trail), each scored wrong.

## Where gxl and paper-trail v8 disagree (2-way)

| claim | gold | paper-trail v8 | gxl |
|---|---|---|---|
{dis}
"""


_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>gxl Checker Baseline</title>
<style>
:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--bar:#2a78d6;--band:#eef3fb;--line:#e1e0d9;--code:#f0efec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--bar:#3987e5;--band:#1d2633;--line:#2c2c2a;--code:#262624}}
:root[data-theme="dark"]{--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
--bar:#3987e5;--band:#1d2633;--line:#2c2c2a;--code:#262624}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:26px;line-height:1.2;margin:0 0 4px}h2{font-size:18px;margin:40px 0 8px}
.sub{color:var(--ink2);margin:0 0 24px}
.answer{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;font-size:16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile .v{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums}.tile .k{color:var(--ink2);font-size:13px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;overflow-x:auto}
svg text{font-family:inherit}
table{border-collapse:collapse;width:100%;font-size:13.5px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--ink2);font-weight:600}td.n{text-align:right}th.n{text-align:right}
.note{color:var(--ink2);font-size:13.5px}ul.note{padding-left:18px}
details{border-bottom:1px solid var(--line);padding:8px 0}summary{cursor:pointer}
.q{background:var(--code);border-radius:6px;padding:8px 10px;margin:6px 0;white-space:pre-wrap;font-size:13px}
code{background:var(--code);border-radius:4px;padding:1px 4px;font-size:12.5px;word-break:break-all}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--page);font-size:12.5px;padding:6px 8px;border-radius:6px;display:none;max-width:280px}
</style></head><body><main>
%%BODY%%
</main><div id="tip"></div>
<script>
(function(){var t=document.getElementById('tip');document.querySelectorAll('[data-tip]').forEach(function(el){
el.addEventListener('mousemove',function(e){t.textContent=el.getAttribute('data-tip');t.style.display='block';
t.style.left=Math.min(e.clientX+12,window.innerWidth-290)+'px';t.style.top=(e.clientY+12)+'px';});
el.addEventListener('mouseleave',function(){t.style.display='none';});});})();
</script></body></html>
"""


def _bar_chart(results: dict[str, Any], metric, label: str, noise: float) -> str:
    """Horizontal bars of one metric, one hue, the always-ACCURATE floor dashed, v8's noise band shaded."""
    import html  # noqa: PLC0415

    names = list(results)
    left, width, row, top = 250, 440, 34, 28
    height = top + row * len(names) + 30

    def x(v: float) -> float:
        return left + v * width

    floor = metric(results["always ACCURATE"])
    v8_value = metric(results["paper-trail v8"])
    lo, hi = max(0.0, v8_value - noise), min(1.0, v8_value + noise)
    parts = [f'<svg viewBox="0 0 {left + width + 60} {height}" width="100%" role="img" '
             f'aria-label="{html.escape(label)} by system; the table below has every number">']
    parts.append(f'<rect x="{x(lo):.1f}" y="{top - 8}" width="{x(hi) - x(lo):.1f}" height="{row * len(names) + 8}" fill="var(--band)"/>')
    parts.append(f'<text x="{x(lo) + 4:.1f}" y="{top - 12}" font-size="11" fill="var(--ink2)">within {noise:.2f} of v8</text>')
    for t in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        parts.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 8}" y2="{top + row * len(names)}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{x(t):.1f}" y="{top + row * len(names) + 18}" font-size="11" fill="var(--muted)" text-anchor="middle">{t:.1f}</text>')
    parts.append(f'<line x1="{x(floor):.1f}" x2="{x(floor):.1f}" y1="{top - 8}" y2="{top + row * len(names)}" '
                 f'stroke="var(--ink2)" stroke-width="1.5" stroke-dasharray="4 3"/>')
    for i, name in enumerate(names):
        r = results[name]
        v, y = metric(r), top + i * row + 8
        w, h = max(v * width, 4), 18
        path = (f"M{left},{y} h{w - 4:.1f} a4,4 0 0 1 4,4 v{h - 8} a4,4 0 0 1 -4,4 h{-(w - 4):.1f} z")
        tip = (f"{name}: {label} {v:.2f} · caught {r['binary']['caught']}/{r['binary']['n_gold_flagged']} "
               f"Sarol-flagged claims")
        parts.append(f'<g data-tip="{html.escape(tip)}"><rect x="0" y="{y - 8}" width="{left + width + 60}" height="{row}" fill="transparent"/>'
                     f'<text x="{left - 10}" y="{y + 13}" font-size="13" fill="var(--ink)" text-anchor="end">{html.escape(name)}</text>'
                     f'<path d="{path}" fill="var(--bar)"/>'
                     f'<text x="{x(v) + 6:.1f}" y="{y + 13}" font-size="12.5" fill="var(--ink2)" stroke="var(--surface)" '
                     f'stroke-width="4" paint-order="stroke">{v:.2f}</text></g>')
    parts.append(f'<text x="{x(floor) - 4:.1f}" y="{top - 12}" font-size="11" fill="var(--ink2)" text-anchor="end">always ACCURATE {floor:.2f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def card_html(doc: dict[str, Any], verdicts: dict[str, Any], systems: dict[str, dict[str, str]],
              gold: dict[str, str], gold_ev: "dict[str, list[dict[str, str]]] | None" = None) -> str:
    """The comparison card as one self-contained HTML page (no external files, light and dark)."""
    import html  # noqa: PLC0415

    e = html.escape
    res = doc["results"]
    gxl, v8 = res["gxl claim checker"], res["paper-trail v8"]
    hd = doc["headline"]
    v0 = hd["v0_range"]
    by_id = {c["claim_id"]: c for c in verdicts["claims"]}

    def f(x: "float | None") -> str:
        return "–" if x is None else f"{x:.3f}"

    rows = "".join(
        f"<tr><td>{e(n)}</td><td class=n>{f(r['2way_accuracy'])}</td><td class=n>{f(r['3way_all']['accuracy'])}</td>"
        f"<td class=n>{f(r['3way_all']['macro_f1'])}</td><td class=n>{f(r['3way_irrelevant_dropped']['accuracy'])}</td>"
        f"<td class=n>{f(r['3way_irrelevant_dropped']['macro_f1'])}</td>"
        f"<td class=n>{f(r['9way_accuracy']) if r['9way_accuracy'] is not None else f(r['9way_upper_bound']) + '*'}</td>"
        f"<td class=n>{r['binary']['caught']}/{r['binary']['n_gold_flagged']}</td><td class=n>{r['binary']['passed_flagged']}</td>"
        f"<td class=n>{f(r['binary']['precision'])}</td><td class=n>{r['n_misses_invalid']}</td></tr>"
        for n, r in res.items()
    )

    def evidence(c: dict[str, Any]) -> str:
        # The block runs to the next claim's line, so it can end with the NEXT paper's header
        # (`[X] PMC… title`); a line that opens with a verdict marker ends this claim's evidence.
        lines = []
        for ln in (c.get("block") or "").splitlines()[1:]:
            if MARKER.match(ln.strip()):
                break
            if ln.strip():
                lines.append(ln.strip())
        return "\n".join(lines) or "(gxl gave no evidence text)"

    def sarol(cid: str) -> str:
        found = (gold_ev or {}).get(cid) or []
        if not found:
            why = {
                "ETIQUETTE": "means it is unclear what is being cited to this paper",
                "IRRELEVANT": "means nothing in the cited paper is relevant to the claim",
            }.get(gold[cid], "carries no annotated evidence for this claim")
            return (f"<div class=note>Sarol's evidence: none. {e(gold[cid])} {why}, so annotators mark no "
                    "evidence sentences for it.</div>")
        items = "".join(f"<div class=q><b>{e(x['label'])}</b> · {e(x['text'])}</div>" for x in found)
        return f"<div class=note>Sarol's evidence (the cited-paper sentences annotators marked, with each one's label):</div>{items}"

    dis = "".join(
        f"<details><summary><b>{e(d['claim_id'])}</b> — gold {e(d['gold'])} · v8 {e(d['paper-trail v8'])} · gxl {e(d['gxl'])}</summary>"
        f"<div class=note>Claim sent to gxl (cited paper {e(by_id[d['claim_id']]['pmcid'])}):</div>"
        f"<div class=q>{e(by_id[d['claim_id']]['text'])}</div><div class=note>gxl's evidence:</div>"
        f"<div class=q>{e(evidence(by_id[d['claim_id']]))}</div>{sarol(d['claim_id'])}</details>"
        for d in doc["disagreements"]
    )
    cols = [n for n in systems if n != "always ACCURATE"]
    head = "".join(f"<th>{e(n.replace('paper-trail ', 'pt ').replace('gxl claim checker', 'gxl'))}</th>" for n in cols)
    all_rows = "".join(
        f"<tr><td>{e(cid)}</td><td>{e(gold[cid])}</td>"
        + "".join(f"<td>{e(by_id[cid]['verdict'] if n == 'gxl claim checker' else systems[n][cid])}</td>" for n in cols)
        + "</tr>"
        for cid in by_id
    )
    v8_right = sum(1 for d in doc["disagreements"] if two_way(d["paper-trail v8"]) == two_way(d["gold"]))
    body = f"""
<h1>gxl's claim checker vs paper-trail</h1>
<p class=sub>Sarol 2024 citation-integrity benchmark · the same 50 validation claims paper-trail's hill-climb uses (roster md5
<code>{e(str(doc['roster_md5']))}</code>) · scored {e(doc['scored_at'][:10])}</p>
<div class=answer><b>Optimization lifted paper-trail from {v0[0]:.2f}–{v0[1]:.2f} to {headline(v8):.2f}</b>
(3-way macro-F1 on the {hd['n_claims']} claims whose gold label every system can give), a gain of {hd['lift_v8_over_best_v0']:.2f}
over the better original run against {hd['noise']:.2f} run-to-run noise. gxl's shipped checker scores {headline(gxl):.2f}:
{e(doc['readout'])}. Answering "accurate" every time scores {headline(res['always ACCURATE']):.2f}.</div>
<div class=tiles>
<div class=tile><div class=v>{v0[0]:.2f}–{v0[1]:.2f}</div><div class=k>paper-trail v0 (original), two runs</div></div>
<div class=tile><div class=v>{headline(v8):.2f}</div><div class=k>paper-trail v8 (best optimized)</div></div>
<div class=tile><div class=v>{headline(gxl):.2f}</div><div class=k>gxl claim checker, as shipped</div></div>
<div class=tile><div class=v>{headline(res['always ACCURATE']):.2f}</div><div class=k>always answer "accurate"</div></div>
</div>
<h2>The headline measure, by system</h2>
<p class=note>3-way macro-F1 (accurate / not accurate / irrelevant, each class weighted equally) on the {hd['n_claims']} claims
whose gold is not in Sarol's irrelevant class. Those 7 are left out because gxl can only say supported or not, so it can never
give that label. Macro-F1 rather than accuracy because, with them gone, {res['always ACCURATE']['3way_irrelevant_dropped']['accuracy']:.0%}
of the claims are ACCURATE and answering "accurate" every time out-scores every system on accuracy. Hover a bar for how many
flagged claims it caught.</p>
<div class=card>{_bar_chart(res, headline, "3-way macro-F1, irrelevant dropped", hd['noise'])}</div>
<p class=note>On the earlier go/no-go, accurate vs not over all 50: v8 {v8['2way_accuracy']:.2f}, gxl {gxl['2way_accuracy']:.2f},
always-"accurate" {res['always ACCURATE']['2way_accuracy']:.2f}. That view counts the irrelevant class as "not accurate", which
credits paper-trail for flagging claims gxl has no way to label.</p>
<h2>Every view</h2>
<div class=card><table><thead><tr><th>System</th><th class=n>2-way acc</th><th class=n>3-way acc</th><th class=n>3-way macro-F1</th>
<th class=n>3-way acc, irrel. dropped</th><th class=n>macro-F1, irrel. dropped</th><th class=n>9-way acc</th>
<th class=n>caught flagged</th><th class=n>passed flagged</th><th class=n>precision</th><th class=n>misses</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<ul class=note>
<li>gxl only says supported or not. In "3-way, all 50" its "not supported" counts as NOT_ACCURATE, so the 7 claims in
Sarol's irrelevant class are always wrong for it. The "irrelevant dropped" columns score the other 43.</li>
<li>* gxl's 9-way figure is an upper bound (equal to its 2-way accuracy): the best any mapping of its yes/no onto Sarol's nine labels could do.</li>
<li>"Caught flagged": of the 15 claims Sarol labels anything but ACCURATE, how many the system also flagged. "Passed flagged": how many it called accurate.</li>
<li>Misses are gxl errors or unreadable verdicts, or paper-trail calls that failed; each is scored wrong.</li>
</ul>
<h2>Where gxl and paper-trail v8 disagree</h2>
<p class=note>{len(doc['disagreements'])} claims on accurate vs not; v8 matches gold on {v8_right} of them. Open one to see the sentence gxl checked, the evidence gxl quoted, and the
evidence Sarol's annotators based the gold label on.</p>
<div class=card>{dis}</div>
<h2>All 50 claims</h2>
<details><summary>Show every claim's gold label and each system's answer</summary>
<div class=card><table><thead><tr><th>claim</th><th>gold</th>{head}</tr></thead><tbody>{all_rows}</tbody></table></div></details>
<h2>How this was measured</h2>
<ul class=note>
<li>gxl: each claim attached to one paperclip repo (<code>{e(str(verdicts.get('repo')))}</code>) against its cited paper's
PMC full text, then verified with gxl's checker as shipped. The only guidance: "{e(VERIFIER_CONTEXT)}" No Sarol label definitions.
Verdicts: {e(str(doc['gxl_counts']))}.</li>
<li>No peeking: verdicts were saved at {e(doc['verdicts_written_at'][:19])} UTC, before gold was first read at {e(doc['gold_read_at'][:19])} UTC.</li>
<li>paper-trail rows are saved runs on the same 50 claims (Haiku, retrieval profile). v8 and v9 ran on the 09-22 harness;
v0 on 09-20, so part of the v0 → v8 gain may come from harness fixes rather than the prompt. The two v9 runs differ by
{hd['noise']:.2f} on the headline measure ({NOISE:.2f} on accurate-vs-not); that is the noise figure used above.</li>
<li>Scoring checks passed: {e(', '.join(n for n, ok in doc['sanity'].items() if ok))}.</li>
<li>Plan: <code>planning/paper-trail/2026-10-06-gxl-claim-checker-baseline.md</code>. Code: paper-trail
<code>experiments/sarol-2024/scripts/baseline_gxl_verify.py</code>.</li>
</ul>"""
    return _HTML.replace("%%BODY%%", body)


# -------------------------------------------------------------------------------------------------


def main() -> int:
    today = dt.date.today().isoformat()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--claims-from", type=pathlib.Path, default=DEFAULT_ROSTER)
    ap.add_argument("--staging-root", type=pathlib.Path, default=None,
                    help="default: val-staging/ beside the roster file")
    ap.add_argument("--date", default=today, help="names the repo and the output folder; pass the first day's date to resume")
    ap.add_argument("--repo", default=None, help="default: pt-sarol-val50-<date>")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="default: ~/.paper-trail/baselines/gxl-verify-<date>")
    ap.add_argument("--batch-size", type=int, default=5, help="10 hit the server's 180 s command limit on 2026-10-07")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--no-smoke", action="store_true", help="skip the two-claim smoke before the run")
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--reparse", action="store_true", help="rebuild verdicts.json from raw/, no gxl calls")
    ap.add_argument("--score-only", action="store_true")
    args = ap.parse_args()

    out = args.out or pathlib.Path.home() / ".paper-trail" / "baselines" / f"gxl-verify-{args.date}"
    repo = args.repo or f"pt-sarol-val50-{args.date}"
    if args.score_only:
        return score_only(out)

    ids = roster_ids(args.claims_from)
    md5 = check_roster(ids)
    if args.claims_from == DEFAULT_ROSTER and md5 != ROSTER_MD5:
        print(f"[roster] md5 {md5} is not the plan's {ROSTER_MD5}")
        return 2
    claims = build_claims(ids, args.staging_root or args.claims_from.parent / "val-staging")
    if args.reparse:
        return verdict_exit(write_verdicts(claims, out, md5))

    try:
        if not (args.no_smoke or args.resume):
            smoke_out = out.with_name(out.name + "-smoke")
            sc = smoke_claims()
            verify(sc, smoke_out, f"pt-sarol-smoke-{args.date}", batch_size=len(sc), resume=False)
            smoke = write_verdicts(sc, smoke_out, None)
            for c in smoke["claims"]:
                print(f"[smoke] {c['claim_id']}: {c['verdict']} (from {c.get('source')})")
            if any(c["verdict"] not in ("OK", "REJECTED") for c in smoke["claims"]):
                print(f"[smoke] FAILED: a demo claim has no clean verdict; read {smoke_out / 'raw'}")
                return 4
            if args.smoke_only:
                return 0
        verify(claims, out, repo, args.batch_size, args.resume)
    except paperclip_mcp.RateLimited as exc:
        print(f"[run] rate-limited, progress saved: {exc}\n[run] resume later with: --date {args.date} --resume")
        return 3
    return verdict_exit(write_verdicts(claims, out, md5))


if __name__ == "__main__":
    sys.exit(main())
