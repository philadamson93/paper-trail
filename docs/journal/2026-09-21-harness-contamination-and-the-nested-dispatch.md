# 2026-09-21 — the grader scored the old version, and did not escape its box

Two things turned up in `hillclimb-2026-09-20c`, the first run to complete a full iteration. One is
a real defect that makes a whole iteration's numbers unusable. The other looked like the grader
breaking out of its container and, on inspection, is not that. Both were found by the optimizer
itself, not by any check we wrote.

## The short version

- **Iteration 2's numbers are unusable.** Nine in ten graders could not save their answer, so the
  previous version's answers were scored instead — and the graders that *did* save had read the
  previous version's answer first and were swayed by it.
- **The grader did not escape.** It re-ran a command that is part of the program it was given,
  inside its own container. It never had a route to the gold answers or the scorer.
- **The baseline survives.** Two independent first-pass measurements agree, and first passes are
  the clean case.

## What went wrong

The grader reads a claim, decides whether the cited paper supports it, and saves its answer.

On a first pass that file does not exist, so saving it is *creating* a file, which the grader is
allowed to do. On a second pass the file is already there, so saving means *replacing* a file — and
replacing needs someone to approve it. Nothing is watching a headless run, so it is refused
automatically. Being refused, the grader is told to read the file first; the file contains the
previous version's answer.

The answers are kept in one folder shared by every iteration, and nothing clears it. So:

| pass | folder state | saves refused |
|---|---|---:|
| training, iteration 1 (baseline version) | empty | 1 of 51 |
| training, iteration 2 (new version) | full, from iteration 1 | **46 of 51** |
| validation, baseline version | empty | 1 of 51 |
| validation, new version | full | **45 of 51** |

Same signature on both halves, both passes.

Twenty-one of the fifty training rows scored for the new version are the baseline version's answers
outright. The other twenty-nine came from graders that had read the baseline's answer out of their
own output folder before deciding. On one claim the record shows the grader reaching the right
answer on its own, then noting that the file disagreed, and changing its mind to match. The file
was wrong.

So no row of that pass is clean, and an improving change would have been measured as flat.

Confirmed three independent ways: the run label stored inside each saved answer, file timestamps
showing iteration-2 graders that ran for an hour and saved nothing, and the refusal message quoted
verbatim in the records.

## Why nothing caught it

Before each run we grade one test claim whose answer we already know, to prove the machinery works.
It passed both times. It runs in its own folder, which is always empty, so it only ever exercises
the case that works — creating a file. It cannot fail the way the real batch fails.

That is the lesson worth keeping: **a check that cannot fail the way the thing it guards fails is
not a check.** This is the second time in two days the same shape has cost us. The container mounts
were silently empty for three runs while every test passed, because the tests use temporary folders
that were shared with the container and the real run used folders that were not.

## The fix

The harness already rotates per iteration — just not for the answers:

| what | where it lives | rotated per iteration |
|---|---|---|
| grader records | `train/iter1-current/traces/`, `iter2-current/…` | yes |
| the frozen program | `iter1-current`, `iter2-current` | yes |
| **the answers** | `train/staging/<claim>/ledger/claims/…` | **no — one shared folder** |

So: archive each iteration's answers alongside its records, then clear them, exactly as the run
already does for the lessons sheet at the start of a run. Saving is then always *creating* a file,
which is already permitted, and no previous answer is left lying around to read. One change removes
both the refusals and the copying.

Widening permissions so the grader may replace files would stop the refusals but leave the previous
answer in place to be read and copied, so it fixes only half.

The smoke test should also move to the end and run against a folder that already holds an answer,
and check the run label on what comes back.

## The thing that looked like an escape

While its saves were being refused, the grader found the harness's "grade one item" command and used
it to start a second grader inside itself, whose answer was recorded.

That reads alarmingly, and it is not an escape:

- **That command is part of the program.** It is one of the frozen files handed to the grader, and
  it is one of the files the optimizer is allowed to rewrite. Re-running it stayed inside the
  program.
- **The gold answers are not reachable.** The container gets the frozen program, read-only, and the
  one claim's staged files. Gold is not mounted, and that is asserted explicitly, with a control
  proving the assertion is not vacuous — mounting gold's parent folder is caught.
- **The scorer never runs in the container.** Comparing answers against gold happens outside it.

What is left is smaller and worth fixing anyway: one claim was graded by a differently shaped
invocation than the other forty-nine, which is a consistency problem in the measurement rather than
a leak. It happened only because the save was refused, so fixing the contamination above most likely
removes it. Worth re-checking once that lands, rather than treated as a hole in the seal.

## What survives

The baseline is trustworthy. First passes run against an empty folder and were refused once in
fifty-one, and two independent first passes agree:

| run | training | validation |
|---|---|---|
| `hillclimb-2026-09-20b` | 0.52 | 0.42 |
| `hillclimb-2026-09-20c` | 0.531 | 0.4286 |

Three-way macro-F1 is 0.435, against the published MultiVerS 0.52 and GPT-4 0.45. Worth repeating
that the program scores **below its own do-nothing floor** on nine-class accuracy — 0.52 against
0.62 — so quote the three-way figure against the published baselines, not the nine-class one.

## The cheapest next run

Re-score the **unchanged** new version against the same fifty training claims once the answers are
cleared. The claim roster is identical between the two iterations, so it is a paired comparison
against iteration 1, and it settles the eight predictions iteration 1 made that could not be graded
this time.
