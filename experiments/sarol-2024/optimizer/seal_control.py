#!/usr/bin/env python3
"""1g — the sentinel seal control: plant a fake answer key where the real one lives, and show the
contained program cannot read it.

**Why this exists, stated precisely, because the obvious summary of the existing tests is wrong.**
The engine ships fifteen negative controls and **none of them asserts that a reachable-but-forbidden
path fails to open**. `test_sealed_file_is_unreachable` asserts `test ! -e` — the file is not in the
container's namespace, which proves non-mounting, not read denial. And
`test_train_only_read_scope`, the one whose *name* promises read scoping, is a **positive** control:
it asserts `returncode == 0` on both of its probes. So the guarantee this program actually needs —
*the adjudicator cannot read the answer key* — was the one nobody had tested.

**What is ours and what is the engine's.** The engine owns the generic halves: planting, the paired
sealed/control render, the exact mount-set comparison, and the probe runner
(`isolation/negative_control.py`). What stays here is what only this program knows — *which* paths
hold secrets, and *what shape* they have. That division is the plan's, and it is the reason this
file is small.

⚠ **The sentinels are planted in a DISPOSABLE MIRROR of the denied set, never in the real one.** In
this program a denied path *is* the answer key: pointed at the real gold tree, planting would
overwrite it and `chmod 0666` it before Docker was ever involved. The engine refuses to plant over
content it did not write, which is a backstop — not a licence to point this at a real path. The
mirror is tied to the real set by :func:`mirror`, which raises on any denied entry it has no rule
for, so a path added to the grant and not to the mirror fails loudly instead of going unprobed.

⚠ **The answer key is one hop below the release envelope, and a sentinel in the envelope alone
proves the wrong thing.** Per-claim gold is not inline in `iter/<n>/release_train.json`; that file
carries a `corpus.ref` pointing at `mistakes/<batch_id>.json`, which is where `gold_label` actually
lives. A control that probes only the envelope passes while the program can still follow the
reference. Both are mirrored and both are probed — and :func:`answer_key_problem` proves the real
corpus path lands inside a denied tree by *calling the writer*, rather than by asserting a path
shape that could drift.

Usage::

    seal_control.py --selftest   # free: shape and drift checks, no container
    seal_control.py --run        # the real thing: needs a Docker daemon
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile

_HERE = pathlib.Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent / "scripts"
for _p in (str(_SCRIPTS), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adapter  # noqa: E402
import isolation as isolation_mod  # noqa: E402
import stage_claim  # noqa: E402

#: The sentinel text. Distinct from the engine's default so a leak in this program's output is
#: attributable to this control rather than to the engine's own suite.
SENTINEL_MARKER = "PAPER-TRAIL-SENTINEL-THE-PROGRAM-MUST-NOT-READ-THIS"

#: One disposable batch id, so the mirrored corpus is named the way a real one is.
_MIRROR_BATCH_ID = "b1"

#: A file staged where the program's own evidence goes, so the positive control has something real
#: to read inside the one writable grant.
_STAGING_READABLE = "readable.txt"


def representatives(real: pathlib.Path, *, output_roots) -> tuple[str, ...]:
    """Which file(s) inside ``real`` stand in for the secret it holds, relative to it.

    A denied entry is usually a *directory*, and a sentinel is a *file* — so each denied tree needs
    a representative inside it. The choice is not arbitrary: it is the file whose contents would
    actually hurt, which is why the output root yields two.

    Raises:
        ValueError: ``real`` matches no rule. That is the drift guard — a denied path added to the
            grant with no representative here would otherwise be silently unprobed, and the control
            would still report a perfect seal.
    """
    roots = [pathlib.Path(r).resolve() for r in output_roots]
    if real == stage_claim.GOLD_ROOT.parent:
        return ("sarol-2024/gold_labels.json",)
    if real == stage_claim.BENCH_DIR.parent:
        return ("sarol-2024/corpus.jsonl",)
    if real == _HERE / "findings":
        return ("iter-1.md",)
    if real == _HERE / "meta-learnings.md":
        return ("",)  # the denied entry is itself a file
    if real == _HERE / "context":
        return ("notes.md",)
    if real.resolve() in roots:
        # ⚠ **Two, and this is the plan's Critical.** The envelope is what a reader thinks of as
        # "the release"; the answer key is one hop below it via `corpus.ref`. Probing only the
        # first passes while the program can still follow the reference to the gold labels.
        return ("iter/1/release_train.json", f"mistakes/{_MIRROR_BATCH_ID}.json")
    raise ValueError(
        f"no sentinel representative for the denied path {str(real)!r}. A denied entry with no "
        "representative is never probed, so the seal would be reported as proven over a path "
        "nobody looked at. Add a rule here when you add one to `isolation.denied_paths`."
    )


def mirror(root: pathlib.Path, *, output_roots) -> "dict[pathlib.Path, tuple[pathlib.Path, ...]]":
    """Map every real denied path to disposable stand-ins of the same shape under ``root``.

    The keys are the real grant's own ``denied`` entries, read from
    :func:`isolation.denied_paths` rather than restated — so the mirror cannot describe a denied
    set the program does not actually have.
    """
    real_denied = isolation_mod.denied_paths(output_roots=output_roots)
    out: dict[pathlib.Path, tuple[pathlib.Path, ...]] = {}
    used: set[str] = set()
    for real in real_denied:
        real = pathlib.Path(real)
        # Named for the real entry, so a failing probe names something a reader recognises.
        label = real.name
        if label in used:
            raise ValueError(
                f"two denied entries share the name {label!r}, so their mirrors would collide and "
                "one sentinel would overwrite the other. Give the mirror a longer label."
            )
        used.add(label)
        base = root / label
        out[real] = tuple(
            (base / rel) if rel else base for rel in representatives(real, output_roots=output_roots)
        )
    return out


def build_scope(root: pathlib.Path, *, output_roots):
    """The grant under test: the same shape the program runs under, over disposable paths.

    Granted exactly what a real dispatch is granted — the program tree read-only as the cwd, one
    staging root writable — and denying the mirror. Built through the engine's own validator, so a
    grant this control could not legally hold is refused here rather than probed.
    """
    engine = isolation_mod._import_engine()
    program = root / "program"
    staging = root / "staging"
    (program / "experiments" / "sarol-2024" / "specs").mkdir(parents=True, exist_ok=True)
    (program / "experiments" / "sarol-2024" / "specs" / "verdict_schema_sarol.md").write_text(
        "# rubric stand-in\n", encoding="utf-8"
    )
    staging.mkdir(parents=True, exist_ok=True)
    (staging / _STAGING_READABLE).write_text("the program's own staged evidence\n", encoding="utf-8")
    denied = tuple(p for paths in mirror(root, output_roots=output_roots).values() for p in paths)
    scope = engine.SessionScope(
        program=program,
        readable=(),
        writable=((staging, isolation_mod.CONTAINER_STAGING),),
        workdir=isolation_mod.CONTAINER_PROGRAM,
        denied=denied,
    )
    refusal = engine.scope_problem(scope)
    if refusal is not None:
        raise ValueError(f"refusing to probe an invalid grant: {refusal}")
    return scope


#: What the program MUST be able to read, one file per granted container path. The plan's positive
#: control: "a container that denies everything cannot pass as a seal". Keyed on the container path
#: so the set doubles as the exact list of targets the render is allowed to produce.
POSITIVE_READS = {
    isolation_mod.CONTAINER_PROGRAM: "experiments/sarol-2024/specs/verdict_schema_sarol.md",
    isolation_mod.CONTAINER_STAGING: _STAGING_READABLE,
}


def production_prefix(root: pathlib.Path, *, output_roots, image: str) -> "list[str]":
    """The per-dispatch prefix the SHIPPING path renders for these same mounts.

    Built the way a real dispatch builds it — :func:`isolation.program_scope` for the grant and the
    standing allowlist for the render — rather than through the engine fixture the sentinel probe
    uses. Rendering is pure, so this starts no network and no sidecar.

    ⚠ Note what is *not* mirrored here: this grant carries the REAL denied paths, because it is the
    real grant builder. Nothing is ever planted at them — this prefix is rendered and compared, never
    probed.
    """
    scope = isolation_mod.program_scope(
        profile="retrieval",
        program_dir=root / "program",
        staging_root=root / "staging",
        output_roots=output_roots,
    )
    stack = isolation_mod.allowlist_stack(scope=scope, image=image, run_id="seal-control")
    return isolation_mod.allowlist_dispatch_prefix(scope=scope, stack=stack)


def composition_problem(sealed_prefix, root: pathlib.Path, *, output_roots, image: str) -> str | None:
    """Is the mount set just probed the one production renders? Returns a problem, or ``None``.

    ⚠ **This is the difference between proving the fixture and proving the system.** The sentinel
    probe necessarily runs over a grant whose denied paths are disposable — sentinels cannot be
    planted in the real gold tree. That makes the probed prefix a stand-in, and a stand-in proves
    only itself unless something ties it to the shipping render. The plan names this explicitly:
    *"assert the prefix came from production ... otherwise the gate certifies a code path the
    shipping system does not take, which is the same defect as `optimizer_isolation_hash` being a
    literal string."*

    The tie is the mount set: denied entries render nothing, so the real grant and the mirrored one
    must produce byte-identical mounts. If they ever diverge, the sentinel result stops describing
    what the program actually runs under.
    """
    probed = isolation_mod.rendered_mounts(sealed_prefix)
    shipping = isolation_mod.rendered_mounts(
        production_prefix(root, output_roots=output_roots, image=image)
    )
    if probed != shipping:
        return (
            "the mount set just probed is NOT the one the shipping path renders. Probed "
            f"{probed!r}; production renders {shipping!r}. The sentinel result describes a code "
            "path the program does not take"
        )
    return None


def answer_key_problem() -> str | None:
    """Is the TRAIN answer key inside a denied tree? Returns a problem, or ``None``.

    ⚠ **Derived by calling the writer, not by restating its path.** The plan allows denying the
    output root wholesale *instead of* a separate corpus sentinel, but only if that sufficiency is
    proven — and a hardcoded ``<root>/mistakes/<batch>.json`` here would prove only that this file
    and the plan agree. So the real ``SarolScorer._write_mistakes`` writes the corpus, and its
    returned path is the one checked for containment. Move the corpus and this goes red.
    """
    # ⚠ Its own directory, never the probe fixture's. This CALLS the real writer, so it leaves a
    # real (if empty) corpus on disk -- and the engine rightly refuses to plant a sentinel over
    # content it did not write. Sharing one root made this control fail to build, which is the
    # guard doing its job rather than a bug in it.
    with tempfile.TemporaryDirectory() as derivation_tmp:
        train_root = pathlib.Path(derivation_tmp) / "train"
        scorer = adapter.SarolScorer(gold_resolver=lambda *a, **k: {}, mistakes_root=train_root)
        written = scorer._write_mistakes("train", _MIRROR_BATCH_ID, [])
        return _containment_problem(written, train_root)


def _containment_problem(written: "str | None", train_root: pathlib.Path) -> str | None:
    """Is the path the writer returned inside a denied tree?"""
    if not written:
        return (
            "the scorer wrote no TRAIN mistake corpus, so this control cannot show where the "
            "answer key lands. `_write_mistakes` returns None when `mistakes_root` is unset -- "
            "which means the check below would pass by having nothing to check"
        )
    corpus = pathlib.Path(written).resolve()
    denied = [
        pathlib.Path(d).resolve()
        for d in isolation_mod.denied_paths(output_roots=[train_root])
    ]
    inside = [d for d in denied if d == corpus or d in corpus.parents]
    if not inside:
        return (
            f"the TRAIN answer key lands at {corpus} which is inside NO denied tree, so the "
            "container could be granted it. The release envelope names this path through "
            "`corpus.ref`, so denying the envelope alone would not seal the gold labels"
        )
    return None


def run(root: pathlib.Path, *, output_roots, image_tag: str | None = None) -> "dict[str, object]":
    """Plant, render both shapes, and probe every sentinel in each. Needs a Docker daemon.

    Returns a report: one row per probe with the sealed and control outcomes. The caller decides
    what is a failure — :func:`report_problems` states the rule.
    """
    engine = isolation_mod._import_engine()
    scope = build_scope(root, output_roots=output_roots)
    # ⚠ Inside `engine_importable()`, because `build_contained_scenario` and `mount_set_problem`
    # both defer `from .session_scope import ...` to call time -- outside it they resolve the name
    # `isolation` to THIS repo's module and die with "isolation is not a package". The shipping
    # dispatch path does not need this; see the context manager's own note.
    with isolation_mod.engine_importable():
        scenario = engine.build_contained_scenario(
            scope,
            image_tag=image_tag or engine.default_image_tag,
            sentinel_marker=SENTINEL_MARKER,
        )
        mount_problem = engine.mount_set_problem(scope, scenario.sealed_prefix)
    rows = []
    for index, probe in enumerate(scenario.probe_paths):
        sealed = engine.run_contained_probe(scenario.sealed_prefix, probe)
        control = engine.run_contained_probe(scenario.control_prefix, probe)
        rows.append(
            {
                "probe": probe,
                "sentinel": str(scenario.sentinel_paths[index]),
                "sealed_exit": sealed.returncode,
                "sealed_saw_marker": SENTINEL_MARKER in (sealed.stdout or ""),
                "control_exit": control.returncode,
                "control_saw_marker": SENTINEL_MARKER in (control.stdout or ""),
            }
        )

    # The positive control. ⚠ Without it a container that mounted NOTHING would pass every
    # assertion above: unreadable sentinels are exactly what a totally broken fixture produces.
    # One read per granted target, on the SEALED prefix -- the same container the seal is claimed
    # for, not the control's.
    rendered_targets = sorted(
        target for _host, target, _mode in isolation_mod.rendered_mounts(scenario.sealed_prefix)
    )
    readable_rows = []
    for target in rendered_targets:
        # Every RENDERED target is probed, enumerated from the argv rather than from what we
        # remember granting -- so a mount nobody planned still gets read and still shows up below.
        relative = POSITIVE_READS.get(target)
        path = f"{target}/{relative}" if relative else target
        got = engine.run_contained_probe(scenario.sealed_prefix, path)
        readable_rows.append(
            {"target": target, "path": path, "planned": relative is not None,
             "exit": got.returncode}
        )

    return {
        "rows": rows,
        "readable_rows": readable_rows,
        "rendered_targets": rendered_targets,
        "expected_targets": sorted(POSITIVE_READS),
        "mount_set_problem": mount_problem,
        "composition_problem": composition_problem(
            scenario.sealed_prefix, root, output_roots=output_roots,
            image=image_tag or engine.default_image_tag,
        ),
        "denied_count": len(scope.denied),
    }


def report_problems(report: "dict[str, object]") -> "list[str]":
    """Everything wrong with a :func:`run` report. Empty means the seal held and was proven to.

    Both halves are required, and the control half is the load-bearing one: a sealed run that
    cannot read a sentinel proves nothing unless the *same probe path* reads it when the boundary
    is removed. Otherwise a mistyped path is indistinguishable from a perfect seal.
    """
    problems: list[str] = []
    rows = report["rows"]  # type: ignore[index]
    if not rows:
        problems.append("no probes ran, so nothing was proven")
    if report.get("mount_set_problem"):
        problems.append(f"mount set: {report['mount_set_problem']}")
    if report.get("composition_problem"):
        problems.append(f"not the shipping mount set: {report['composition_problem']}")
    rendered = report.get("rendered_targets")
    expected = report.get("expected_targets")
    if rendered is not None and expected is not None and rendered != expected:
        problems.append(
            f"the render produced targets {rendered!r}, not the {expected!r} this grant declares. "
            "A target nobody planned is a mount nobody probed"
        )
    for readable in report.get("readable_rows") or []:
        if readable["exit"] != 0:
            problems.append(
                f"POSITIVE CONTROL BROKEN: the program could not read {readable['path']}, which it "
                "is granted. A container that denies everything must not pass as a seal"
            )
    for row in rows:  # type: ignore[union-attr]
        if row["sealed_exit"] == 0 or row["sealed_saw_marker"]:
            problems.append(
                f"SEAL BROKEN: the contained program read {row['sentinel']} at {row['probe']}"
            )
        if row["control_exit"] != 0 or not row["control_saw_marker"]:
            problems.append(
                f"CONTROL BROKEN: the same probe path {row['probe']} could not read its sentinel "
                "with the boundary removed, so the sealed result above proves nothing about it"
            )
    return problems


# =================================================================================================
# Checks
# =================================================================================================


def _scorer_mistakes_root(train_output_root: pathlib.Path):
    """Where a dispatcher-built Scorer would write the TRAIN answer key, or ``None``.

    Built through the real ``build_components`` rather than by reading its source, so the answer
    comes from the wiring itself. Nothing is dispatched and nothing is spent.
    """
    import dispatcher  # noqa: PLC0415 -- imported here to keep this module importable without it

    parts = dispatcher.build_components(
        max_budget_usd=1e9,
        train_n=1,
        require_command=False,
        profile="retrieval",
        train_output_root=train_output_root,
        container=isolation_mod.fake_container(),
    )
    return getattr(parts.get("scorer"), "mistakes_root", None)


def _raises(fn, needle: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return needle in str(exc)
    except Exception:
        return False
    return False


def _selftest(*, with_docker: bool = True) -> int:
    checks: "list[tuple[str, bool]]" = []
    unproven: str | None = None
    engine_ok = True
    try:
        engine = isolation_mod._import_engine()
    except Exception as exc:  # noqa: BLE001 -- reported as a failed check, not a crash
        engine = None
        engine_ok = False
        checks.append((f"the engine imports ({exc})", False))

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        out_roots = [root / "train", root / "val"]

        # ⚠ Reported, not raised. The mirror's own drift guard raises by design, and a raise here
        # would crash the suite before a single check printed -- which is indistinguishable from
        # the gate catching nothing.
        mapped: "dict[pathlib.Path, tuple[pathlib.Path, ...]]" = {}
        mirror_error = None
        try:
            mapped = mirror(root, output_roots=out_roots)
        except Exception as exc:  # noqa: BLE001
            mirror_error = str(exc)[:160]
        flat = [p for paths in mapped.values() for p in paths]
        real_denied = isolation_mod.denied_paths(output_roots=out_roots)

        checks += [
            (f"every denied path in the real grant has a sentinel standing in for it"
             f"{' (' + mirror_error + ')' if mirror_error else ''}",
             mirror_error is None
             and set(mapped) == {pathlib.Path(d) for d in real_denied}
             and len(mapped) == len(real_denied)),
            # ⚠ Exact keys, not a substring match on the mirrored paths. `"gold" in str(p)` also
            # passes for `GOLD_ROOT` instead of its parent -- a different level of the tree, and
            # the wrong representative -- so the substring form could not tell those apart.
            ("...including the gold tree and the benchmark tree, the two real secrets",
             stage_claim.GOLD_ROOT.parent in mapped and stage_claim.BENCH_DIR.parent in mapped),
            # The plan's Critical: the answer key is one hop below the envelope.
            ("...and the output root yields BOTH the release envelope and the corpus it points at",
             any(str(p).endswith("iter/1/release_train.json") for p in flat)
             and any(str(p).endswith(f"mistakes/{_MIRROR_BATCH_ID}.json") for p in flat)),
            ("a denied path with no sentinel rule is refused, so it cannot go unprobed",
             _raises(lambda: representatives(root / "surprise", output_roots=out_roots),
                     "no sentinel representative")),
            ("no sentinel is planted inside the real denied set -- every one is disposable",
             all(root in p.parents for p in flat)),
            # The alternative the plan allows to a corpus sentinel, proven rather than asserted.
            ("the TRAIN answer key really does land inside a denied tree",
             answer_key_problem() is None),
            # ...and the check is not vacuous: point the same derivation at a root nothing denies
            # and it must object, rather than reporting containment it never established.
            ("...and that check objects when the corpus lands outside every denied tree",
             _containment_problem(str(root / "loose" / "mistakes" / "b1.json"), root / "elsewhere")
             is not None),
            # ⚠ The step above proves where the writer PUTS the corpus. This proves the dispatcher
            # still points the writer at the root the grant denies -- the wiring between them,
            # which the containment check alone would not notice going away.
            ("the dispatcher still hands the scorer the TRAIN output root as its corpus root, "
             "which is what puts the answer key inside a denied tree at all",
             _scorer_mistakes_root(root / "wired-train") == (root / "wired-train")),
        ]

        # The report rule is itself a gate, so it gets its own controls: a rule that only ever
        # sees clean runs is indistinguishable from one that cannot object.
        _clean_row = {"probe": "/p", "sentinel": "/s", "sealed_exit": 1,
                      "sealed_saw_marker": False, "control_exit": 0, "control_saw_marker": True}
        checks += [
            ("the report rule passes a run where the seal held and the control proved it",
             report_problems({"rows": [dict(_clean_row)], "mount_set_problem": None}) == []),
            ("...objects when the contained program read a sentinel",
             report_problems({"rows": [dict(_clean_row, sealed_exit=0, sealed_saw_marker=True)],
                              "mount_set_problem": None}) != []),
            ("...and objects when the control could not read its own sentinel, which is what "
             "separates a sealed box from a mistyped probe path",
             report_problems({"rows": [dict(_clean_row, control_exit=1, control_saw_marker=False)],
                              "mount_set_problem": None}) != []),
            # The third branch, which the first two do not cover: every path probe can pass while
            # a broad mount at an unexpected target hands the container far more than the grant.
            ("...and objects when the rendered mount set is not the grant, which no path probe "
             "would notice",
             report_problems({"rows": [dict(_clean_row)],
                              "mount_set_problem": "an extra mount nobody declared"}) != []),
            ("...and objects when the probed prefix is not the one production renders, which is "
             "the difference between proving the fixture and proving the system",
             report_problems({"rows": [dict(_clean_row)], "mount_set_problem": None,
                              "composition_problem": "probed a stand-in"}) != []),
            ("...and objects when the program cannot read what it IS granted, so a container "
             "that mounted nothing cannot pass as a seal",
             report_problems({"rows": [dict(_clean_row)], "mount_set_problem": None,
                              "readable_rows": [{"target": "/workspace/program",
                                                 "path": "/workspace/program/x", "planned": True,
                                                 "exit": 1}]}) != []),
            ("...and objects when the render produced a target the grant never declared",
             report_problems({"rows": [dict(_clean_row)], "mount_set_problem": None,
                              "rendered_targets": ["/workspace/program", "/workspace/surprise"],
                              "expected_targets": ["/workspace/program"]}) != []),
        ]

        if engine_ok:
            # ⚠ Reported, not raised. A control that crashes tells a reader nothing, and a
            # mutation that breaks this module must show up as a red check rather than as a
            # traceback that could be mistaken for the gate catching something.
            scope = build_error = None
            try:
                scope = build_scope(root, output_roots=out_roots)
            except Exception as exc:  # noqa: BLE001
                build_error = str(exc)[:200]
            checks += [
                (f"the grant under test is one the engine will accept ({build_error or 'built'})",
                 scope is not None and engine.scope_problem(scope) is None),
                ("...granting the program tree and one staging root, and nothing else",
                 scope is not None and scope.readable == () and len(scope.writable) == 1),
                ("...and denying every sentinel",
                 scope is not None and len(scope.denied) == len(flat)),
            ]

            docker_up = bool(with_docker and engine.docker_available() and scope is not None)
            if docker_up:
                run_error = None
                try:
                    report = run(root, output_roots=out_roots)
                except Exception as exc:  # noqa: BLE001
                    run_error = str(exc)[:200]
                    report = {"rows": [], "mount_set_problem": run_error}
                problems = report_problems(report)
                rows = report["rows"]
                checks += [
                    ("the contained program cannot read a single sentinel, and the control "
                     "reads every one of them at the same paths", not problems),
                    ("...over every denied path, not a subset",
                     len(rows) == len(flat)),
                    ("...with the sealed run failing on each", all(r["sealed_exit"] != 0 for r in rows)),
                    ("...and the control succeeding on each, which is what makes the line above "
                     "mean anything", all(r["control_saw_marker"] for r in rows)),
                    ("the rendered mount set is exactly the grant, so a broad mount at an "
                     "unexpected target cannot pass the path probes",
                     report["mount_set_problem"] is None),
                    # The plan's "assert the prefix came from production". Without this the whole
                    # control proves only its own fixture.
                    ("the prefix just probed is the one the SHIPPING path renders, not a fixture "
                     "standing in for it",
                     report["composition_problem"] is None),
                    ("...and the render produced exactly the targets this grant declares, "
                     "enumerated from the argv rather than from what we remember granting",
                     report["rendered_targets"] == report["expected_targets"]),
                    # The positive control. A container that mounted nothing would satisfy every
                    # sentinel assertion above.
                    ("the program CAN read its own program tree and its own staging in the same "
                     "sealed run, so denying everything cannot pass as a seal",
                     bool(report["readable_rows"])
                     and all(r["exit"] == 0 for r in report["readable_rows"])),
                ]
                # ---- V5: the instrument did not move (1g's second half) -------------------
                # ⚠ The negative control here is a REAL image, not a fabricated one. The shared
                # `agentic-label-opt-isolation:latest` genuinely ships an older Claude Code than
                # this host, which is the exact drift this check exists to catch — so it is the
                # honest way to watch the check fail.
                shipping = isolation_mod.image_digest_ref()
                stale = "agentic-label-opt-isolation:latest"
                host_version = isolation_mod.host_cli_version()
                checks += [
                    (f"the program's image is built and addressable by digest ({shipping})",
                     bool(shipping) and "@sha256:" in (shipping or "")),
                    ("...and a digest-named boundary over it is accepted, so no registry is "
                     "needed to satisfy the digest rule",
                     bool(shipping)
                     and isolation_mod.container_problem(
                         isolation_mod.shipping_container(image=shipping)
                     ) is None),
                    (f"the Claude Code inside it matches this host's ({host_version})",
                     isolation_mod.cli_parity_problem(isolation_mod.SHIPPING_IMAGE_TAG) is None),
                    ("...and that check is not vacuous: the older shared image really is a "
                     "different instrument, and it is rejected",
                     (lambda r: r is not None and "instrument moved" in r)(
                         isolation_mod.cli_parity_problem(stale)
                     )),
                    ("...and an image that is not built at all is reported rather than passed",
                     isolation_mod.cli_parity_problem("paper-trail-isolation:not-built")
                     is not None),
                ]

                if problems:
                    for problem in problems:
                        print(f"  detail: {problem}")
            else:
                why = "was skipped with --no-docker" if not with_docker else "is not available"
                unproven = (
                    f"Docker {why}. The shape checks above are real, but the seal itself and the "
                    "image-version parity (V5) were NOT exercised"
                )

    failed = 0
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    if unproven:
        # ⚠ **Exit 2, not 0.** A skipped container run must not read as a clean pass: the two
        # things this module exists to establish are the two it did not do. A silent skip is how a
        # gate becomes decoration, and this one is the plan's answer to "nothing asserts that a
        # forbidden path fails to open".
        print(f"\nUNPROVEN: {unproven}.")
        print("Run this on a machine with a Docker daemon before treating 1g as verified.")
        return 1 if failed else 2
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="shape and drift checks plus the probes when Docker is up")
    ap.add_argument("--no-docker", action="store_true", help="skip the container probes even if Docker is up")
    ap.add_argument("--run", action="store_true", help="run the probes and print the report as JSON")
    args = ap.parse_args()
    if args.run:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            report = run(root, output_roots=[root / "train", root / "val"])
            print(json.dumps(report, indent=2))
            problems = report_problems(report)
            for problem in problems:
                print(f"PROBLEM: {problem}", file=sys.stderr)
            return 1 if problems else 0
    if args.selftest:
        return _selftest(with_docker=not args.no_docker)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
