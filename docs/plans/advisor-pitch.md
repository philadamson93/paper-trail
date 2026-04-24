# Optimization of agentic programs requires instrumentable agentic ecosystems

*Rough draft, 2026-04-24. Speech-to-text origin, not ready to send. Full bibliographic entries for the agent-as-optimizer cluster are pending a follow-up system-prompt drop. Figure 1 is at `docs/plans/figures/v1.jpg`, with caption and prompt of record in `docs/plans/figures/v1.md`.*

---

## Claude Code as an ecosystem for agentic programs

Claude Code today is used primarily for coding assistance. A growing tail of non-coding agentic programs has begun to appear alongside that, spanning marketing and content operations, regulatory compliance, publishing pipelines, and research tooling. The ecosystem is poised to scale further into more complex workflows.

A slash command in Claude Code, or in the settings vernacular an "agentic program," serves as a single invocation point for such a workflow. A user opens a fresh Claude Code session, types `/paper-trail` for example, and launches the program. The program may prompt the user, run an environment check or installation script, and bootstrap its own context.

Many published slash commands are qualitative aids, useful in the hands of a human collaborator but without a quantifiable objective an optimizer can compare revisions against. The methodology below targets a narrower slice. It applies to agentic programs whose outputs can be validated against human-labeled ground truth, so that iterative optimization against that signal is tractable. Paper-trail is one such program. It audits the references in a scientific manuscript for citation integrity, and the Sarol-2024 benchmark (Sarol et al., 2024), a human-annotated citation-verification corpus in the SciFact family (Wadden et al., 2020), would supply the labeled signal against which paper-trail's outputs can be scored. A second example is an agentic clinician-in-the-loop clinical labeling workflow that reasons over longitudinal patient notes to structure variables like cancer recurrence, progression, or disease status as a function of time. Those variables can be human-labeled by chart review, then aggregated into a gold-standard cohort. The common theme is a dynamic Claude Code native program, invoked as one entry point, whose outputs are scorable against a labeled benchmark.

The methodology below is the contribution. Paper-trail is the planned case study for evaluating the methodology on a non-trivial real pipeline; the case study has not yet been run.

## The challenge of testing an agentic program

The shippable and testable unit is itself an agentic program operating inside a full Claude Code environment in its intended setting. Testing that single program in agentic ways would use the same iterative shape existing agentic optimization schemas use to optimize code. An agentic optimizer would invoke the program in a fresh, isolated Claude Code environment, observe how it performs against an objective performance signal, and propose revisions. For paper-trail the signal would be the Sarol-2024 citation-verification corpus. For the clinical-labeling program it would be a chart-reviewed cohort of adjudicated cancer-status trajectories.

This is familiar territory conceptually. The 2025-26 agent-as-optimizer literature has established the shape (13-paper survey, see References). That literature optimizes LLM prompts and Pythonic code harnesses as targets, not agentic programs living in a Claude Code environment. Those adjacent targets are clearly prior art. Ours is not.

## Why Claude Code makes this hard

Claude Code is not natively designed to support such optimization workflows. The agentic program needs to live in complete isolation from the agentic optimizer, which, in principle, is itself best built using Claude Code by the same user. This leaves a large front for experimental information leakage. Content that should be privy only to the optimizer, and hidden from the agentic program, includes CLAUDE.md files, auto-memory, hooks, plugins, dynamic system-prompt sections, and a variety of hidden `.claude/` folders. Launching Claude sessions in `--bare` mode is one option but is mutually exclusive with subscription-token authentication. `--bare` also leaves residual leakage surfaces untouched, including binary-version drift, dynamic-system-prompt content, and subagent-side persistent memory.

I believe I have designed a reasonable attempt at building this experimental separation (see Figure 1). That attempt was only possible through deep sleuthing of Claude Code documentation and forums, paired with a long series of Claude-Code-driven canary tests of various assumptions. It is quite possible that the proposed stack does not yet work comprehensively. The work is in progress, and due to the closed-box nature of Claude Code, it is impossible for a user at this time to have full confidence that the system they have built is behaving as they intend. Canonical invocation shapes and canary-test findings are summarized in the appendix.

## Proposed architecture

The architecture in Figure 1 rests on a two-mechanism isolation discipline. First, host-state isolation at the invocation boundary around the agentic program, achieved through scrubbed env, fresh config dir, and a pinned binary version at the reproducibility-critical tier. Second, split-differentiated scoring return via a deterministic Python dispatcher that sits between the agentic optimizer and the agentic program. The training split will expose per-sample labels alongside full per-sample agent traces (each subagent's reasoning, intermediate verdicts, and final outputs), a case-by-case view of how the agentic program arrived at each answer. The validation split will return only aggregate scores (MCC or F1), to avoid collapse of validation into training. The test split will remain unexposed until a single terminal evaluation. This asymmetric access is what will make the observable evidence meaningful across optimizer revisions. Training macro-F1 and validation macro-F1 will be plotted as paired curves against revision index M, analogous to training and validation loss across epochs in classical machine learning. Divergence between the two curves would signal overfitting to the training set and serve as a natural stopping rule. The methodology also supports two dials. N is the number of held-out samples evaluated per revision. Human involvement ranges from in-loop review of every revision to fully autonomous optimization, and the planned case study will run in autonomous mode.

*Figure 1. Isolation around `/paper-trail` (the agentic program), evaluated by a filtering dispatcher. Left: one `--bare` invocation of `/paper-trail` tag v1, walled against ambient host context, invoked N times per revision, one item per invocation. Middle: a deterministic Python dispatcher with filtering locked at write-time that invokes the program, collects per-item verdicts, and returns per-split signal to the agentic optimizer (train: per-sample inputs + labels + traces; val: macro F1 only). Right: the agentic optimizer, a Claude Code session co-resident with the ambient host context (CLAUDE.md, auto-memory, hooks, plugins, dynamic system-prompt content) and using it by default. Below: the test set sealed, unsealed only at terminal evaluation. A stand-in agent supplies human-like input to the agentic program if needed. A human may drive the agentic optimizer at a configurable cadence, from in-loop at every revision to fully autonomous.*

## Where prior work stops

Agentic programs are beginning to take off. What is missing is a rigorous way to optimize and measure them systematically. Three adjacent points of comparison each leave a gap.

(1) Public ecosystem activity. Anthropic's official skills repository, the MCP Registry (10,000+ active servers as of early 2026), and community aggregators such as `awesome-claude-code`, `claude-skill-registry`, `SkillsMP`, and `scientific-agent-skills` show agentic programs being published at scale. Composition is tilted toward coding assistance at roughly 65 to 75% of catalogued material. A real non-coding tail carries the remainder. That tail covers marketing and content operations, regulatory compliance, publishing pipelines, research-adjacent tools (`paper2code`, `academic-research-skills`, economics-writing skills), and biomedical data-access MCPs (BioMCP, PubMed MCP, AACT Clinical Trials). The specific case-study categories named above, citation integrity and longitudinal clinical labeling, are absent from those registries. More relevant to this methodology, no published artifact in any of those registries is itself being iteratively optimized by another agent against a verifiable reward signal.

(2) Agent-as-optimizer literature (13-paper survey, see References). That work targets LLM prompts and Pythonic code harnesses. Zero of the 13 systems surveyed target Claude Code as substrate.

(3) Benchmark-integrity literature (Wang et al., 2026; Zhu et al., 2025). That work addresses evaluator-side integrity, including structured scoring, sandboxed ground truth, and adversarial probe agents.

Substrate-side integrity is a category none of the three cover. It is the execution runtime itself treated as a leakage surface between an optimizer and the agentic program it is optimizing, when both live in the same ecosystem.

## The ask

We propose that Claude Code explicitly support optimization workflows of the kind described here, to aid both scientific experimentation and minimum-viable-product engineering of the non-coding agentic programs the ecosystem is already beginning to publish. A short list of primitives would collapse the current stack of environment variables, fresh config directories, and wrapper scripts into a handful of flags. These primitives include a real "eval mode" that unifies `--bare` auto-discovery suppression with subscription-token authentication, a binary-version pin convention, granular scope-disable controls, decoupled `CLAUDE_CONFIG_DIR` and keychain-credential resolution, and a default `.gitignore` template for the `.claude/` subtree. These are not favors to the research community. They are product investments Anthropic would likely want anyway if the ecosystem continues to accrete around slash-command-as-program as a distribution unit for agentic software.

---

## Appendix A. Current-best-attempt isolation stack, work in progress, likely neither optimal nor comprehensive

Source of truth with full per-flag rationale is `docs/plans/experiment-sarol-eval-arm-isolation.md`. Everything below is a compressed gloss. Known gaps are listed at the end.

### Two-tier invocation

*Iteration tier* runs thousands of times during optimization. It uses subscription auth and non-`--bare` invocation, since `--bare` and subscription-token authentication are mutually exclusive.

```bash
EVAL_UUID=$(uuidgen)
mkdir -p /tmp/pt-eval-{cfg,wd}-$EVAL_UUID

env -i \
  HOME=$HOME PATH=/usr/bin:/bin:/usr/local/bin LANG=en_US.UTF-8 TZ=UTC \
  CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN \
  CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
  CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 \
  CLAUDE_CONFIG_DIR=/tmp/pt-eval-cfg-$EVAL_UUID \
  /bin/sh -c "cd /tmp/pt-eval-wd-$EVAL_UUID && claude \
    --add-dir $REPO \
    --print --model opus \
    --no-session-persistence \
    --exclude-dynamic-system-prompt-sections \
    --tools default \
    --agents '<tag-scoped-json>' \
    --settings <eval.settings.json> \
    --mcp-config <mcp.json> --strict-mcp-config \
    /sarol-eval-item --claim $CLAIM"

rm -rf /tmp/pt-eval-{cfg,wd}-$EVAL_UUID
```

*Landmark tier* is used for paper-reportable numbers only. It runs inside a Docker image with a pinned Claude Code binary, uses Vertex authentication, and permits `--bare` because subscription auth is not used.

```bash
# Dockerfile: FROM node:22; RUN npm install -g @anthropic-ai/claude-code@<pinned>
# Host env: CLAUDE_CODE_USE_VERTEX=1 + GCP creds

claude --bare --print --model opus \
  --no-session-persistence \
  --exclude-dynamic-system-prompt-sections \
  --tools default --agents '<tag-scoped-json>' \
  --settings <eval.settings.json> \
  --mcp-config <mcp.json> --strict-mcp-config \
  --add-dir /repo \
  /sarol-eval-item --claim $CLAIM
```

The two tiers exist because Docker cold-start latency multiplied by thousands of iteration calls and many optimizer revisions is prohibitive. Iteration tier achieves same-host-same-time determinism cheaply. Landmark tier closes the binary-version-drift gap once per paper-reportable number.

### What gets excluded, and by what

| Leakage vector | Mechanism |
|---|---|
| User and project `CLAUDE.md`, `.claude/rules/*.md` | `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` |
| Auto-memory | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (verified to propagate to Agent-tool subagents) |
| Hooks, skills, plugins | fresh `CLAUDE_CONFIG_DIR=/tmp/pt-eval-cfg-$EVAL_UUID` (structural, since these live under the config dir) |
| Session history | fresh-per-uuid config dir plus `--no-session-persistence` for redundancy |
| Dynamic system-prompt sections (cwd path, git state, env info) | clean cwd plus `--exclude-dynamic-system-prompt-sections` |
| Shell env (TZ, aliases, `LC_*`, venv state, inherited `CLAUDE_CODE_*`) | `env -i` plus explicit pins |
| Claude Code binary-version drift | `npm install -g @anthropic-ai/claude-code@<pinned>` inside Docker (landmark tier only) |
| Test-split access | physical seal at `$HOME/.paper-trail-sealed/`, unsealed once at terminal evaluation |

### Known gaps not yet verified

Subagent-side persistent memory is assumed suppressed by inheritance from main-session env vars, but has not been canary-tested at the subagent-scoped memory path. The `--exclude-dynamic-system-prompt-sections` flag has not been probed to confirm it covers every dynamic-prompt section (cwd, env, memory paths). Project `.claude/commands/` resolution under a fresh `CLAUDE_CONFIG_DIR` has not been empirically tested. The settings-merge fail-closed negative test, which would prove user `~/.claude/settings.json` is actually suppressed rather than merely overridden, has not been run. Cross-tier comparability, i.e. whether iteration-tier and landmark-tier numbers differ systematically on the same input, is to be measured at the `paper-trail-v1` smoketest.

### Candidate primitives Anthropic could ship first-class to collapse this stack

A real "eval mode" that unifies `--bare` auto-discovery suppression with subscription-token authentication, currently mutually exclusive. A binary-version pin convention analogous to `package-lock.json`. Granular scope-disable controls, for example "allow this slash command, disable all user-level skills." Decoupled `CLAUDE_CONFIG_DIR` and keychain credential resolution. A default `.gitignore` template for the `.claude/` subtree.

---

## References

Sarol JS et al. (2024). *Bioinformatics* 40(8): btae420. https://doi.org/10.1093/bioinformatics/btae420. Human-annotated citation-integrity corpus of 3,063 instances across 100 PMC-OA biomedical papers. Repository: github.com/ScienceNLP-Lab/Citation-Integrity.

Wadden D et al. (2020). Fact or Fiction: Verifying Scientific Claims. *EMNLP 2020*. Canonical scientific-claim-verification dataset; SciFact format is the parent of the format Sarol-2024 adopts. Repository: github.com/allenai/scifact.

Zhu Y et al. (2025). Establishing Best Practices for Building Rigorous Agentic Benchmarks. arXiv:2507.02825. Introduces the Agentic Benchmark Checklist (ABC).

Wang et al. (2026). How We Broke Top AI Agent Benchmarks. Berkeley Center for Responsible Decentralized Intelligence (RDI) audit of eight top agent benchmarks.

Agent-as-optimizer cluster, with full bibliographic entries pending a follow-up system-prompt drop. OPRO (Yang et al.), ADAS (Hu et al.), AFlow (Zhang et al.), MIPROv2 (Opsahl-Ong et al.), Sakana AI Scientist (Lu et al.), AlphaEvolve (Google DeepMind), Karpathy autoresearch, Meta-Harness, MAPRO, MA-SAPO, MASS, VeRO.
