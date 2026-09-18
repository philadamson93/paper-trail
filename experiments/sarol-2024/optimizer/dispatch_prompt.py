"""Render the adjudicator's prompt in Python, so no session has to improvise one. Step 0c / OQ1.

**The failure class this removes, and why detection was never going to be enough.** Two delivery
bugs were observed in the 561-trace run: a prompt handed over with `$dispatch_prompt` never
expanded, and one built as `$(cat /tmp/adjudicator_filled_$$.txt)` with an unexpanded `$$`. Neither
string appears anywhere in this repo — **the model authored them at run time, differently each
run**, and 13 of 561 sessions began with no task at all. A check that looks for those two spellings
would not have caught the third. What removes the class is that the step stops being authored:
Python cannot improvise a broken heredoc.

**What is removed is the model, not the editability** (NF8). The prompt text stays where it was, in
the optimizer's own frozen file, and this module only fills placeholders in it. Everything the
adjudicator reads is still 100% optimizer-authored, and the optimizer may still rewrite every word
of it — including, per Phil's ruling that the optimizer may write Python, this dispatcher. The test
of whether that is still true is whether the optimizer can change what the adjudicator receives.
It can. ⚠ An earlier draft moved about 40% of the driver into harness code and Phil withdrew it;
this is deliberately not that.

**Why it has to exist before the container does.** The driver today is a *slash command*
(`.claude/commands/sarol-eval-item.md`), which Claude Code resolves by reading `.claude/` from the
working directory. Inside the container the working directory is the frozen program snapshot, and
that tree carries only manifest entries — **no `.claude/`, so no slash command to resolve**. A
contained session dispatched the old way fails looking for a command that is not there, and it
fails in a way that reads like a model error. So the prompt has to arrive fully rendered on argv.

**Where the slots come from.** Two files, both of them things an agent is already allowed to read:

===============================  =====================================================
Slot                             Source
===============================  =====================================================
``claim_id``                     the caller, cross-checked against the envelope
``claim_text``                   ``staging_info.json`` -> ``claim_text_normalized``
``claim_type_hint.type``         ``ledger/evidence/<claim_id>.json`` -> ``claim_type``
``claim_type_hint.confidence``   the same
``multi_cit_context``            ``staging_info.json``
``run_id``                       the caller
``run_output_dir``               the caller — **container-side** when contained
``spec_root``                    the caller — **container-side** when contained
===============================  =====================================================

The two path slots are parameters rather than derived, because the same claim renders with host
paths uncontained and container paths contained, and only the caller knows which it is building.
:func:`isolation.told_host_path_problem` is what checks the result carries no host path.

⚠ **``read_staging_info`` is imported, not reimplemented.** ``evidence_producers`` already read this
file to build the envelope; a second reader here would let the prompt and the evidence disagree
about the claim text, and nothing downstream could detect it — the judge would reason about one
sentence while its evidence was retrieved for another, and emit a perfectly well-formed verdict.

⚠ **``CLAIM_TEXT_MISMATCH`` cannot fire under ``retrieval``, and is kept anyway.** Under the only
runnable profile the same Python process writes both sides of that join, so the check compares a
value to its own source. It is kept for parity with profiles where an agent produces the envelope,
where it can fire. Stated rather than presented as a guarantee: a tautology dressed as a gate is
worse than no gate, because it earns trust it cannot repay.

Refusal codes follow ``validate_sarol``'s existing vocabulary (``CLAIM_ID_MISMATCH:expected=…``)
rather than inventing a second one. Every refusal raises ``ValueError``, which is already in the
Runner's catch list (``adapter.py:872``), so a refusal becomes this claim's failure and never the
batch's exception.

Run the checks — no session, no container, nothing spent::

    python3 experiments/sarol-2024/optimizer/dispatch_prompt.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
from typing import Any

_HERE = pathlib.Path(__file__).resolve().parent

if str(_HERE) not in sys.path:  # importable as a script and as a module
    sys.path.insert(0, str(_HERE))

import evidence_producers  # noqa: E402

#: Repo root: experiments/sarol-2024/optimizer/dispatch_prompt.py -> up 3. Same as adapter.py.
REPO_ROOT = _HERE.parents[2]

#: The optimizer's prompt file, relative to whichever tree holds this program version. Read from the
#: **materialized** tree in a real run, never from the working checkout: the optimizer may already
#: have edited the checkout past the version being scored.
TEMPLATE_REL = "experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md"

#: The fences around the part that is actually sent. Everything before the first and after the
#: second is commentary addressed to a human or to the dispatching session — the file's own header,
#: and an "Orchestrator notes (not sent to subagent)" section that says so in its heading.
MARKER_BEGIN = "## Begin dispatch prompt"
MARKER_END = "## End dispatch prompt"

#: A ``{{slot}}``, including the dotted form (``{{claim_type_hint.type}}``).
_SLOT_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


def template_path(spec_root: pathlib.Path | str) -> pathlib.Path:
    """Where the prompt file lives inside a materialized program tree."""
    return pathlib.Path(spec_root) / TEMPLATE_REL


def prompt_body(template_text: str) -> str:
    """The part between the markers, stripped. Raises on a template missing either marker.

    Refusing beats falling back to the whole file: the tail is explicitly *"not sent to subagent"*
    and includes instructions addressed to a dispatching session that OQ1 deleted. Sending it would
    hand the adjudicator prohibitions about repairing a subagent's output when it has no subagent —
    confusing text that costs tokens and could change a verdict.
    """
    for marker in (MARKER_BEGIN, MARKER_END):
        if marker not in template_text:
            raise ValueError(
                f"MARKER_MISSING:{marker!r} is absent from the prompt template, so the part meant "
                "for the adjudicator cannot be separated from the commentary around it"
            )
    start = template_text.index(MARKER_BEGIN) + len(MARKER_BEGIN)
    end = template_text.index(MARKER_END)
    if end < start:
        raise ValueError(
            f"MARKER_ORDER:{MARKER_END!r} appears before {MARKER_BEGIN!r}, so the fenced region "
            "is inside out and the prompt would be empty or reversed"
        )
    body = template_text[start:end].strip()
    if not body:
        raise ValueError(
            "PROMPT_EMPTY:the region between the markers is empty, so the adjudicator would be "
            "dispatched with no task -- the exact failure this module exists to remove"
        )
    return body


def slot_values(
    *,
    staging_dir: pathlib.Path | str,
    claim_id: str,
    run_id: str,
    run_output_dir: str,
    spec_root: str,
) -> dict[str, str]:
    """Every slot's value, read from staging. Raises on a mismatch or a missing envelope.

    ``run_output_dir`` and ``spec_root`` are strings, not paths, because under containment they are
    container-side paths that do not exist on this host — turning them into ``Path`` objects would
    invite a caller to ``.resolve()`` one and get a host path back.
    """
    staging = pathlib.Path(staging_dir)
    info = evidence_producers.read_staging_info(staging)

    envelope_path = staging / "ledger" / "evidence" / f"{claim_id}.json"
    if not envelope_path.is_file():
        raise ValueError(
            f"EVIDENCE_MISSING:{envelope_path.name} is not in this claim's staging tree; the "
            "adjudicator reads the finished envelope, so there is nothing to judge. The evidence "
            "producer runs before this and must have failed silently"
        )
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))

    got_id = envelope.get("claim_id")
    if got_id != claim_id:
        raise ValueError(
            f"CLAIM_ID_MISMATCH:expected={claim_id},got={got_id!r} -- this claim's staging tree "
            "holds another claim's evidence, so the verdict would be filed under the wrong id"
        )

    info_text = info["claim_text_normalized"]
    envelope_text = envelope.get("claim_text")
    if envelope_text != info_text:
        raise ValueError(
            f"CLAIM_TEXT_MISMATCH:claim={claim_id} -- staging and the evidence envelope disagree "
            "about the claim text, so the evidence was retrieved for a different sentence than "
            "the one the judge would be shown"
        )

    claim_type = envelope.get("claim_type")
    if not isinstance(claim_type, dict) or not claim_type.get("type"):
        raise ValueError(
            f"CLAIM_TYPE_MISSING:claim={claim_id} -- the envelope carries no claim_type, and the "
            "prompt has a slot for it; filling it with a placeholder would tell the judge "
            "something false about the claim"
        )

    return {
        "claim_id": claim_id,
        "claim_text": info_text,
        "claim_type_hint.type": str(claim_type["type"]),
        "claim_type_hint.confidence": str(claim_type.get("confidence", "")),
        "multi_cit_context": str(info["multi_cit_context"]),
        "run_id": run_id,
        "run_output_dir": run_output_dir,
        "spec_root": spec_root,
    }


def substitute(body: str, values: dict[str, str]) -> str:
    """Fill every ``{{slot}}``. Raises if any slot survives, naming the first one.

    ⚠ **One pass over the template, not a loop over the values.** Replacing value by value would
    substitute into text a previous value had just inserted, so a claim whose text happened to
    contain ``{{spec_root}}`` would have it expanded — the prompt would then differ from the frozen
    template in a way no diff of the template shows. A single regex pass cannot re-enter what it
    has already written.
    """
    missing: list[str] = []

    def fill(match: re.Match) -> str:
        slot = match.group(1)
        if slot not in values:
            missing.append(slot)
            return match.group(0)
        return values[slot]

    rendered = _SLOT_RE.sub(fill, body)
    if missing:
        raise ValueError(
            f"SLOT_UNRESOLVED:{missing[0]} -- the template asks for a slot this dispatcher has no "
            f"source for (all unresolved: {', '.join(sorted(set(missing)))}). Refusing rather than "
            "sending the literal placeholder, which is the delivery bug this module replaces"
        )
    return rendered


def render(
    *,
    staging_dir: pathlib.Path | str,
    claim_id: str,
    run_id: str,
    run_output_dir: str,
    spec_root: str,
    template_root: pathlib.Path | str | None = None,
) -> str:
    """The adjudicator's whole prompt, ready to hand to ``claude --print``.

    ``template_root`` is where the prompt file is read from, and defaults to ``spec_root``. They
    differ in exactly one case that matters: under containment ``spec_root`` is a container path
    used for *text inside the prompt*, while the template must be read from the host. Passing them
    separately is what keeps the rendered text container-correct while the read stays host-correct.
    """
    root = template_root if template_root is not None else spec_root
    text = template_path(root).read_text(encoding="utf-8")
    values = slot_values(
        staging_dir=staging_dir,
        claim_id=claim_id,
        run_id=run_id,
        run_output_dir=run_output_dir,
        spec_root=spec_root,
    )
    return substitute(prompt_body(text), values)


def write_rendered(
    staging_dir: pathlib.Path | str, claim_id: str, rendered: str
) -> pathlib.Path:
    """Record the exact bytes the adjudicator was given, beside its evidence and its verdict.

    Not an input to anything — the prompt travels on argv. This is the audit copy, so a surprising
    verdict can be read against the text that produced it. Sits under ``ledger/`` with the other two
    per-claim artifacts, and inside the one directory the contained session may write.
    """
    out = pathlib.Path(staging_dir) / "ledger" / "prompts" / f"{claim_id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    return out


# =================================================================================================
# Checks. No session, no container, nothing spent.
# =================================================================================================

_CLAIM_TEXT = "Transformer models outperform LSTMs on long-range dependency tasks."


def _fixture(tmp: pathlib.Path, *, claim_id: str = "C001", **overrides) -> pathlib.Path:
    """A staged claim on disk: staging_info.json plus one evidence envelope."""
    staging = tmp / claim_id
    (staging / "ledger" / "evidence").mkdir(parents=True, exist_ok=True)
    info = {
        "citekey": "smith2020",
        "claim_text_normalized": _CLAIM_TEXT,
        "source_mode": "sarol_corpus",
        "multi_cit_context": "single",
        "source_description": "staged from the sarol corpus",
    }
    info.update(overrides.get("info", {}))
    (staging / "staging_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    envelope: dict[str, Any] = {
        "claim_id": claim_id,
        "run_id": "run_test",
        "citekey": "smith2020",
        "claim_text": _CLAIM_TEXT,
        "claim_type": dict(evidence_producers.STAGED_CLAIM_TYPE),
    }
    envelope.update(overrides.get("envelope", {}))
    if overrides.get("no_envelope"):
        pass
    else:
        (staging / "ledger" / "evidence" / f"{claim_id}.json").write_text(
            json.dumps(envelope, indent=2), encoding="utf-8"
        )
    return staging


def _raises(fn, code: str) -> bool:
    """Did ``fn`` refuse with a ``ValueError`` carrying ``code``? The code is the contract."""
    try:
        fn()
    except ValueError as exc:
        return str(exc).startswith(code)
    except Exception:
        return False
    return False


def _selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dispatch-prompt-dry-"))
    staging = _fixture(tmp)
    spec_root_host = str(REPO_ROOT)
    container_out = "/workspace/staging/C001"
    container_spec = "/workspace/spec"

    def render_contained(**kw):
        args = dict(
            staging_dir=staging,
            claim_id="C001",
            run_id="run_test",
            run_output_dir=container_out,
            spec_root=container_spec,
            template_root=spec_root_host,
        )
        args.update(kw)
        return render(**args)

    rendered = render_contained()
    template_text = template_path(spec_root_host).read_text(encoding="utf-8")

    checks: list[tuple[str, bool]] = [
        # -- the prompt is complete and carries no placeholders ------------------------------------
        (
            "the rendered prompt is non-empty and has no unfilled placeholder left in it",
            bool(rendered.strip()) and not _SLOT_RE.search(rendered),
        ),
        (
            "every slot the template asks for was filled from a real source",
            set(_SLOT_RE.findall(prompt_body(template_text)))
            <= set(
                slot_values(
                    staging_dir=staging,
                    claim_id="C001",
                    run_id="run_test",
                    run_output_dir=container_out,
                    spec_root=container_spec,
                )
            ),
        ),
        (
            "the claim text is inserted verbatim, not normalized or escaped on the way in",
            _CLAIM_TEXT in rendered,
        ),
        (
            "the claim id, run id and multi-citation context all reached the prompt",
            "C001" in rendered and "run_test" in rendered and "single" in rendered,
        ),
        (
            "the claim-type hint reached it too, from the envelope rather than a placeholder",
            evidence_producers.STAGED_CLAIM_TYPE["type"] in rendered
            and evidence_producers.STAGED_CLAIM_TYPE["confidence"] in rendered,
        ),
        # -- only the fenced region is sent ---------------------------------------------------------
        (
            "the file's own header prose is not sent to the adjudicator",
            "Literal prompt for the adjudicator subagent" not in rendered,
        ),
        (
            "...nor is the section whose own heading says it is not sent",
            "Orchestrator notes" not in rendered
            and "must not check the enum" not in rendered,
        ),
        (
            "...and the markers themselves are not sent either",
            MARKER_BEGIN not in rendered and MARKER_END not in rendered,
        ),
        (
            "the fenced region really is a strict subset of the file, so the fence does something",
            len(prompt_body(template_text)) < len(template_text),
        ),
        # -- container correctness ------------------------------------------------------------------
        (
            "the prompt names container paths, because that is what the caller passed",
            container_out in rendered and container_spec in rendered,
        ),
        (
            "...and no host path reached it, though the template was read from the host",
            "/Users/" not in rendered and str(REPO_ROOT) not in rendered,
        ),
        (
            "...which is only true because the read root and the prompt root are separate inputs",
            "template_root" in render.__doc__
            and str(REPO_ROOT) in spec_root_host,
        ),
        (
            "rendering the same claim twice is byte-identical",
            render_contained() == rendered,
        ),
        (
            "a host-path render is available for the uncontained path, and differs",
            (lambda h: str(REPO_ROOT) in h and h != rendered)(
                render_contained(run_output_dir=str(staging), spec_root=spec_root_host)
            ),
        ),
        # -- refusals, each by its code -------------------------------------------------------------
        (
            "a template with no begin marker is refused, not silently sent whole",
            _raises(lambda: prompt_body("no markers here at all"), "MARKER_MISSING"),
        ),
        (
            "an inside-out pair of markers is refused",
            _raises(
                lambda: prompt_body(f"x {MARKER_END} y {MARKER_BEGIN} z"), "MARKER_ORDER"
            ),
        ),
        (
            "an empty fenced region is refused -- that is the no-task failure itself",
            _raises(
                lambda: prompt_body(f"{MARKER_BEGIN}\n\n{MARKER_END}"), "PROMPT_EMPTY"
            ),
        ),
        (
            "a slot with no source is refused, and the message names it",
            _raises(
                lambda: substitute("ask for {{nonexistent_slot}}", {"claim_id": "C001"}),
                "SLOT_UNRESOLVED:nonexistent_slot",
            ),
        ),
        (
            "a missing evidence envelope is refused",
            _raises(
                lambda: slot_values(
                    staging_dir=_fixture(tmp / "a", claim_id="C009", no_envelope=True),
                    claim_id="C009",
                    run_id="r",
                    run_output_dir="/workspace/staging",
                    spec_root="/workspace/spec",
                ),
                "EVIDENCE_MISSING",
            ),
        ),
        (
            "another claim's evidence in this claim's tree is refused",
            _raises(
                lambda: slot_values(
                    staging_dir=_fixture(
                        tmp / "b", claim_id="C002", envelope={"claim_id": "C999"}
                    ),
                    claim_id="C002",
                    run_id="r",
                    run_output_dir="/workspace/staging",
                    spec_root="/workspace/spec",
                ),
                "CLAIM_ID_MISMATCH",
            ),
        ),
        (
            "staging and the envelope disagreeing about the claim text is refused",
            _raises(
                lambda: slot_values(
                    staging_dir=_fixture(
                        tmp / "c", claim_id="C003", envelope={"claim_text": "a different claim"}
                    ),
                    claim_id="C003",
                    run_id="r",
                    run_output_dir="/workspace/staging",
                    spec_root="/workspace/spec",
                ),
                "CLAIM_TEXT_MISMATCH",
            ),
        ),
        (
            "an envelope with no claim_type is refused, not filled with a placeholder",
            _raises(
                lambda: slot_values(
                    staging_dir=_fixture(tmp / "d", claim_id="C004", envelope={"claim_type": None}),
                    claim_id="C004",
                    run_id="r",
                    run_output_dir="/workspace/staging",
                    spec_root="/workspace/spec",
                ),
                "CLAIM_TYPE_MISSING",
            ),
        ),
        # -- the one-pass substitution rule ---------------------------------------------------------
        (
            "a claim whose own text contains a placeholder does NOT get it expanded",
            "{{spec_root}}"
            in substitute(
                "claim: {{claim_text}} / root: {{spec_root}}",
                {"claim_text": "see {{spec_root}} for details", "spec_root": "/workspace/spec"},
            ),
        ),
        (
            "...and the real slot beside it still resolved, so the pass is not simply skipping",
            "/workspace/spec"
            in substitute(
                "claim: {{claim_text}} / root: {{spec_root}}",
                {"claim_text": "see {{spec_root}} for details", "spec_root": "/workspace/spec"},
            ),
        ),
        # -- the shared reader, not a second copy ---------------------------------------------------
        (
            "the claim text comes from evidence_producers' reader, not a second reader here",
            "read_staging_info" in pathlib.Path(__file__).read_text(encoding="utf-8")
            and "staging_info.json" not in _slot_source_lines(),
        ),
        # -- the audit copy -------------------------------------------------------------------------
        (
            "the rendered bytes are recorded beside the evidence and the verdict",
            (lambda p: p.is_file() and p.read_text(encoding="utf-8") == rendered)(
                write_rendered(staging, "C001", rendered)
            ),
        ),
        (
            "...under ledger/, inside the one directory a contained session may write",
            write_rendered(staging, "C001", rendered).parent.parent.name == "ledger",
        ),
    ]

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def _slot_source_lines() -> str:
    """The body of :func:`slot_values`, for the "no second reader" check above."""
    import inspect  # noqa: PLC0415

    return inspect.getsource(slot_values)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--selftest", action="store_true", help="Render against a fixture and assert on the result."
    )
    ap.add_argument("--print-prompt", action="store_true", help="Render the fixture and print it.")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.print_prompt:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="dispatch-prompt-"))
        print(
            render(
                staging_dir=_fixture(tmp),
                claim_id="C001",
                run_id="run_test",
                run_output_dir="/workspace/staging/C001",
                spec_root="/workspace/spec",
                template_root=REPO_ROOT,
            )
        )
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
