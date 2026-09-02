# Release format — what you are handed each iteration

Two files land per iteration, written by the engine before your session starts:
`iter/<n>/release_train.json` and `iter/<n>/release_val.json`. They are deliberately not the same
shape, and the difference is the whole leakage design.

## TRAIN release — Tier 1, fully open

```json
{
  "schema_version": "0.1.0",
  "phase": "train",
  "iter": 3,
  "produced_at_utc": "2026-09-01T18:04:11+00:00",
  "optimizer_isolation_hash": "sarol-2024",
  "corpus": {
    "ref": "<path to the run manifest for this batch>",
    "counts": { "invalid_label": 0 },
    "metrics": {
      "primary_metric_name": "sarol_3way_macro_f1",
      "primary_metric": 0.41,
      "breakdown": {
        "micro_f1": 0.76,
        "per_class_f1": { "ACCURATE": 0.86, "NOT_ACCURATE": 0.37, "IRRELEVANT": 0.0 },
        "confusion_matrix": { "ACCURATE": {...}, "NOT_ACCURATE": {...}, "IRRELEVANT": {...} },
        "error_class_counts": { "invalid_label": 0 },
        "n_total": 50, "n_scored": 50, "n_invalid": 0,
        "requested_count": 50, "n_unresolved": 0,
        "scored": true, "split": "train"
      }
    },
    "frontier": { "best_tag": "...", "best_metric_value": 0.44,
                  "current_tag": "...", "current_metric_value": 0.41 },
    "budget":   { "spent_usd": 212.40, "spent_input": ..., "spent_output": ..., ... }
  }
}
```

`corpus.ref` points at the run manifest, from which the per-claim mistake corpus is reachable:
adjudicator reasoning, the extractor's evidence quotes, and the verifier's bounce history for
every TRAIN claim. TRAIN is fully open — read all of it.

## VAL release — Tier 2, scalar only

```json
{
  "schema_version": "0.1.0",
  "phase": "val",
  "iter": 3,
  "produced_at_utc": "2026-09-01T18:19:52+00:00",
  "optimizer_isolation_hash": "sarol-2024",
  "metrics": {
    "primary_metric": { "name": "sarol_3way_macro_f1", "value": 0.39,
                        "higher_is_better": true },
    "breakdown": { "scored": true, "n_total": 316, "n_invalid": 0,
                   "requested_count": 316, "split": "val" }
  }
}
```

That is the entire VAL surface. **No per-class F1, no confusion matrix, no error-class counts, no
per-example anything.** The scalar plus enough metadata to distinguish a real score from a partial
batch.

`n_invalid` is the one borderline field, and it is included deliberately: it is a bare count of
malformed predictions, never a distribution over classes, so it tells you *that* output was
unparseable and nothing about *which* claims or which gold classes. Without it a VAL run could be
half-garbage and still report `scored: true`.

This is not an oversight to be worked around. Per-class structure on the held-out split is exactly
the signal an optimizer overfits to, and the divergence between the TRAIN curve and the VAL curve
is the experiment's stopping rule — a rule that stops meaning anything if VAL's error structure is
visible while you are editing. The reduction is enforced in `adapter.SarolReleaseBuilder`, and
`adapter.py --selftest` runs the same scored batch through both tiers to prove the difference is
the boundary rather than a difference in the underlying numbers.

If you find yourself wanting VAL's per-class breakdown: that want is the mechanism working. Use
TRAIN's.

## Reading `scored`

`scored: false` means **the number in `primary_metric` is not a result.** It is 0.0 as a
placeholder, with `reason` saying why — a coverage shortfall, an unresolvable claim, a non-finite
metric, or a run that timed out or errored. Do not treat it as a regression and do not react to it
with a prompt edit; it is an infrastructure signal, not a program signal.

The distinction matters because a failed batch scored as a real 0.0 would poison the frontier: it
would look like a catastrophic regression, trigger a step-back, and revert a program that was
never actually the problem.

## `frontier` and `budget`

- **`frontier`** carries best-so-far versus current, so you can tell "worse than my last edit" from
  "worse than the best we have ever had". Only the scalar, on both sides.
- **`budget`** is the engine's own accounting of the *optimizer session's* token spend. It does not
  include the Runner's cost, which is where nearly all real spend lives — that is bounded
  separately and consumer-side by `dispatcher.py`. If a run stops for budget reasons it will say so
  explicitly; you will not see it coming in this field.

## `followups`

When your previous change note named target verdict classes, the next TRAIN release reports how
those specific classes moved, previous versus current. This only works if you named them, which is
the practical reason the playbook asks you to.

## Schema stability

`schema_version` is `0.1.0`. The engine validates that a train-phase call returns a train payload
and a val-phase call returns a val payload, and stops the run if they are crossed — so a change to
these shapes is a real change, not a cosmetic one.
