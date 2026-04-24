# Advisor-pitch rewrite — user-dictated narrative flow (part 1 of N)

**Context.** Yesterday's in-progress `docs/plans/advisor-pitch.md` (45 lines, structured as *The problem / Why this is new / Proposed contribution / The opportunity*) is being abandoned. **Human 2026-04-24:** wants to start from scratch, dictating the narrative flow explicitly so Agent can then read the authoritative plan-doc cluster (NEXT.md, the framework doc, eval-arm-isolation, optimization-loop-hygiene, tier-0-resolution, paper-writeup-items, archive-and-eval-framework, etc.) and draft against a structure the user already owns — rather than inheriting yesterday's structure.

**Working mode for this journal entry.** Human is dictating in real time via Wispr Flow; this captures part 1 of the narrative flow, with an explicit pause before the "challenge" section continuation. More dictation to come in the same session. Agent should NOT draft the actual rewrite yet — just capture the flow faithfully.

---

## Scoping decisions (Human, before the flow itself)

**Main-text altitude.** Keep the pitch very high level. Do not dive into specifics of the isolation mechanisms beyond **two to three examples, one to two words each**, of exactly how we isolate. The point of naming them in the main text is to signal that the work has been done — not to explain the mechanisms.

**Appendix as evidence of rigor.** Create a one-page appendix the advisor can glance at to confirm the sleuthing has actually been done. It contains:
- The **canonical invocation command(s)** we intend to use for evaluation — the literal shell invocation shape, without diving into *why* each flag is there.
- The **eval-test isolation** framing (likely what the user transcribed as "Val test isolation" — reading charitably as eval-arm / evaluation-time IN-vs-OUT isolation, which is what `experiment-sarol-eval-arm-isolation.md` documents).

The main text will reference the appendix with a sentence along the lines of: Claude Code is not natively designed to be conducive to the workflow of optimizing an agentic program, but we believe we have a solution based on (a) sleuthing of Claude Code documentation and forums and (b) an extended series of Claude-Code-driven canary tests of these invocations. *Details in Appendix.*

**Why this split.** The advisor needs to see that we've thought about the intrinsic complexity of doing this on Claude Code — not walk through the mechanisms. The appendix is the "I've looked at it" glance-check; the main text preserves altitude.

---

## Working title — Human-proposed, feedback requested

**Proposed working title:** *"Optimization of agentic programs requires more flexible agentic ecosystems."*

**Human's self-critique:** "flexible" is not quite right. The intended notion is closer to "structured" or "rigid in a way" — the point being that Claude Code is not *explicitly designed* for this optimization workflow. So "flexible" is pointing at the wrong property.

**Ask to Agent:** propose alternatives once the full narrative flow is in hand. Parking this; we'll come back to it.

---

## Narrative flow — Human's dictation, part 1 (preserved faithfully)

The narrative below is Human's prose, lightly transcription-cleaned per the Wispr Flow convention (e.g., "agentive program" → "agentic program"). Structural ambiguities Human flagged in-voice are preserved with [bracketed notes]. The flow was interrupted by an explicit pause before the "challenge" section continuation.

### Opening — the ecosystem framing

Claude Code provides a powerful ecosystem which, while currently used to solve arbitrary coding tasks, promises in the near future to be able to solve arbitrary complex workflows.

Slash commands — or, in the settings, agentic programs — serve as a natural invocation point for these complex [but related / structured — phrasing TBD] workflows, in that they can serve as **single entry points**: by opening a fresh Claude session and typing, for example, `/paper-trail`, the user launches the agentic program.

Such an agentic program may:
- Prompt the user to ask questions from a context.
- Initialize an environment check and installation script as needed — to install Python packages, for example.
- Prompt the user for any necessary tokens (e.g., API keys) to be input in separate terminals.

[**Human's own note:** the token-prompting detail is probably too much specificity for the pitch. Keep the sense of it — "bootstraps its own environment" — without listing mechanisms.]

### Example span — from paper-trail to healthcare harmonization

Examples of such agentic workflows include, for example, **paper-trail** — [borrow the actual shipped tagline from the paper-trail README / product docs; Human's rough phrasing was "agentic toolkit for automated citation provenance or whatever we called it" — Agent should look up the canonical phrasing when drafting].

But this pattern may scale to more complex and heterogeneous — *but still programmatically related* — tasks, such as **harmonizing complex healthcare stale data sets into reproducible machine-learning-ready environments**. (Harmony [the harmonization tool / example] demonstrates this is the right example.)

In the latter setting, the agentic program — while initially built at a single hospital, learning from the particular nuances and documentation of that system — may be **continuously adapted and learn as it is invoked at other hospitals** to harmonize increasingly large sets of data which share related but idiosyncratic differences. These adaptations require both human input and shared learnings, i.e., a **dynamic program that learns over time across sites**.

### [Section break — Human flagged uncertainty] The challenge

[**Human's own note on structure:** "then, like, a new section or something, or maybe this was previous already two sections, sort of like the challenge" — i.e., it's unclear whether what follows is its own section or continues the framing. Agent to propose structure when drafting.]

Since the shippable unit — the testable unit — is in and of itself an **agentic program operating within a full Claude Code environment in its intended setting**, it is desirable to be able to test this single program *in agentic ways*, in order to deliver from the initial user site a minimum viable product.

Much like other agentic optimization schemas which already exist to optimize code, this requires an iterative process by which **the agent invokes, in this case, a Claude Code slash command in a fresh and isolated Claude Code environment**, and then reports back performance as a function of these macro optimization steps of the agentic workflow.

This, of course, requires some sort of **verifiable reward signal** and a check term on that — and Human flags that this phrase is loaded; people think of math when they hear "verifiable reward," which is not quite the right anchoring. In the case of paper-trail, the reward signal points to a labeled dataset. In the case of a hospital setting, it may be a subset of clean, gold-standard, manually vetted / curated, machine-learning-ready data.

---

## End of part 1 — Human pause

Human explicitly paused here — "so it's not too much at once" — and will continue the narrative flow in a follow-up dictation in the same session. Agent: do not draft the rewrite yet. Capture the next dictation into this same journal entry (append a "part 2" section), then draft once the full flow is in hand.

---

## Narrative flow — Human's dictation, part 2

Continuation from part 1. Human's prose, lightly transcription-cleaned per Wispr Flow convention (e.g., "Gentech program" → "agentic program"; "MAC" → "MCC" per standard ML metric pairing alongside F1; "ClaudeMD" → "CLAUDE.md"; "Claude Code/command store" → "Claude Code slash-command store"). Structural ambiguities preserved in [bracketed notes].

### The Claude Code substrate problem

Claude Code, however, is not natively designed to support such optimization workflows of agentic programs — because the agentic program needs to live in **complete isolation from the agentic optimizer**, which also, in principle, is best built using Claude Code by the same user.

In other words, there is a **massive front for experimental information leakage** which should only be privy to the optimizer but hidden entirely from the agentic program — including, but not limited to, CLAUDE.md files, auto-memory, and a wide variety of hidden Claude folders.

Likewise, these Claude sessions require being launched in `--bare` mode, which — while tractable in some settings — [**Human in-voice uncertainty, flagged to Agent:** "does not allow the invocation of sub-agents. Is that true?"]. Anyways, we can maybe outline a few problems with `--bare` as we see it, if there are any.

### The sleuthing-and-canary framing

While I believe I have designed a reasonable attempt at building this rigid experimental separation and isolation of the agentic program, such an attempt was only possible through **deep sleuthing of Claude Code documentation** as well as **rigorous canary tests of various assumptions**.

It is also quite likely that what I propose below does not work, as it is still a work in progress — and due to the **closed-box nature of Claude Code**, it is impossible for a user at this time to have full confidence that the system they have built is behaving [scientifically / as-advertised — phrasing TBD, Human cut the sentence in voice].

### The ask — Claude Code should explicitly support this usage mode

We therefore propose that Claude Code, in order to enable both scientific experimentation and minimum-viable-product engineering work on agentic programs, should **explicitly enable such usage modes for its users** — in order to extend the Claude Code slash-command store, if you will, from beyond just MCP servers and commands that are designed for coding, **to commands which are explicitly agentic programs** that solve a wide variety of complex workflows well beyond the way people are currently using Claude Code to, well, write Python code.

### Train/val/test — the second isolation axis

[**Human in-voice structural note:** "maybe there needs to be something about the train-VAL testing." Agent: this is the second orthogonal axis from yesterday's draft — flag whether to keep or cut for altitude.]

We want to point briefly to **the Berkeley paper** (Wang et al. 2026, Berkeley RDI's audit of eight top agent benchmarks) at some point — something to the effect of: *this kind of experimental setting has been considered before, but in those settings the optimization target is very often deterministic Python, rather than an agentic program itself.*

These require **rigorous train/val/test data-set isolation**. In our setting of agentic programming:
- The optimizer **can see**, for the training split, per-sample labels and traces.
- For the **validation** split — to avoid collapsing into the train set — the optimizer should only receive back aggregate **MCC or F1 scores** (i.e., scalar evaluation metrics), via a **deterministic Python dispatcher sitting between the optimizer and the agentic program**.
- [Test split implicit in Human's flow but not restated here: sealed until the final landmark evaluation. Cross-reference: Rule 2 in `experiment-sarol-optimization-loop-hygiene.md` / Tier 3 sealing in `agentic-pipeline-optimization-framework.md`.]

### Human's close

*"Okay, let's document that into the journal, and then — am I missing anything conceptually?"*

See "Agent's answer to Human's closing question" section below.

---

## Agent's answer to the `--bare` sub-agent question

**Human's exact question, flagged in-voice:** "these Claude sessions require being launched in bare, which … does not allow the invocation of sub-agents. Is that true?"

**Short answer: no, that's not quite true as stated — and the true story is more interesting.** Subagents *can* be invoked under `--bare`, but via explicit flag plumbing. The real incompatibilities are elsewhere. Sources: `tier-0-resolution-2026-04-22.md` Gate 3; `experiment-sarol-eval-arm-isolation.md` §Iteration-tier + §Residual investigation items; D44 canary findings in `docs/journal/2026-04-22-memblind-oauth-findings.md`.

**What's actually true about `--bare` and subagents:**
- `--bare`'s default toolset omits the Task tool (the subagent-spawn mechanism). But `--tools default` re-enables Task under `--bare`. Custom subagents load under `--bare` via `--agents '<json>'` inline. So: subagents *do* work under `--bare`, you just need explicit flags.
- Empirically verified under non-bare OAuth in our D44 canary; under `--bare` on Vertex it's pending the `canary-runbook-vertex.md` runs but docs support it.

**The actual incompatibilities worth naming in the pitch:**
1. **`--bare` refuses OAuth subscription-token auth.** The iteration-tier (subscription-billed) path *can't* use `--bare`; must use `CLAUDE_CODE_OAUTH_TOKEN` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` + `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` as a non-bare functional equivalent. This forces a two-tier architecture: iteration tier non-bare for speed/cost; landmark tier `--bare` on Vertex/API for full reproducibility.
2. **`--bare` alone still leaks dynamic-system-prompt sections** (cwd path, git status, environment info) — needs `--exclude-dynamic-system-prompt-sections` as a companion flag.
3. **No binary-version pinning under `--bare`** — drift across invocations is possible without a Docker pin.
4. **Subagent-side persistent memory under `--bare` is assumed suppressed-by-inheritance but not yet empirically canary-tested** at the subagent-specific memory path.
5. **User and project CLAUDE.md files + session-local `.claude/`** are not *all* disappeared by `--bare` alone on every Claude Code version — the detailed sweep is what surfaces the residual vectors.

**How to phrase in the pitch.** Don't claim "`--bare` does not allow subagents" — an advisor could check. Instead land the true story: *"`--bare` goes most of the way but not all of the way, and is mutually exclusive with the subscription-token auth path we need for iteration-tier evaluation. Closing the remaining gaps took a sweep over environment variables, flag combinations, and a wrapper-script invocation shape — detailed in the appendix."*

---

## Agent's answer to "am I missing anything conceptually?"

**Proactively surfacing six items** the current narrative flow either omits entirely or lands weakly relative to yesterday's draft. Human to triage keep-for-altitude vs. cut-deliberately. Ordered roughly by how much each item would change an advisor's reading.

### 1. Paper-trail is the *case study*, not the *contribution*

Yesterday's draft made this explicit ("The methodology itself is the contribution; the case study exists to demonstrate it works on a non-trivial real pipeline"). The current flow foregrounds paper-trail as the worked example, which is correct, but without the case-study framing an advisor may read this as "the paper-trail paper" rather than "the methodology paper with paper-trail as case study." These are very different submission lanes. **Recommend: keep an explicit one-liner somewhere in the pitch.**

### 2. Optimizer / optimization-target substrate co-location as a novel problem class

Human did land this in part 2 — *"the agentic optimizer which also, in principle, is best built using Claude Code by the same user"* — but in a parenthetical. Yesterday's draft elevated it: *"when the optimizer is also a Claude Code agent, the optimizer and the artifact it is optimizing co-locate on the same substrate. The same ambient channels that leak host state into the artifact can, in principle, leak between optimizer and artifact. This is a class of concern no prior agent-as-optimizer substrate has to address."* That last sentence is paper-positioning gold — makes the contribution non-incremental rather than "Claude Code variant of known hygiene." **Recommend: elevate from parenthetical to its own one-sentence claim.**

### 3. The M and N design dials

Yesterday's draft made the methodology accommodate **M** (optimizer iterations between human check-ins) and **N** (held-out samples per revision) as dials. M = 1 → tight human-in-the-loop; M → ∞ → fully agent-only. The current flow dropped this. May be intentional for altitude, but these dials are how the methodology generalizes beyond one specific experimental configuration — and the human-in-the-loop vs. agent-only axis is itself a contribution-adjacent story the paper-writeup-items thread cares about. **Recommend: confirm intentional cut, or add one sentence.**

### 4. Two orthogonal isolation axes, not one

Yesterday's draft framed the methodology as resting on **two orthogonal axes**: (a) host-state isolation at the invocation boundary (IN-system vs. OUT-of-system content), and (b) split access control for the optimizer across train/val/test. Current flow has both axes present but doesn't name them as two axes. Naming them makes the contribution legible in 30 seconds. **Recommend: one sentence up front that says "two orthogonal axes of isolation" then briefly each.**

### 5. The related-work positioning has two streams, not one

Human's part-2 flow cites "the Berkeley paper" and frames it as the prior experimental-setting reference. But there are really **two distinct related-work streams** the methodology extends:
- (a) **Agent-as-optimizer** (VeRO, Karpathy autoresearch, Meta-Harness, AlphaEvolve, ADAS, AFlow, Sakana AI Scientist, MAPRO, MA-SAPO, MASS — 13-paper survey per yesterday's draft). These target deterministic Python / SWE-agent-family scaffolds. **Zero** target Claude Code. This is the "optimizing-agentic-systems" lineage.
- (b) **Benchmark-integrity** (Wang et al. 2026 Berkeley RDI; Zhu et al. 2025 arxiv 2507.02825 Agentic Benchmark Checklist). Evaluator-side integrity — structured scoring, sandboxed ground truth, adversarial probes. This is the "making-benchmarks-trustworthy" lineage.
- Our work is (a) × (b) on a novel substrate (Claude Code). Specifically: *substrate-side* integrity is a category neither stream covers.

The current flow mentions (b) but not (a) as distinct streams, and doesn't flag the gap both share. **Recommend: decide whether to invoke one or both. For altitude, one paragraph naming both streams + the gap each leaves may be right.**

### 6. The shipped deliverable — what is this pitch actually asking for?

Yesterday's draft split this into "Research" and "Product" layers. Research = methodology paper. Product = a list of primitives Claude Code could ship first-class (real eval mode, binary-version pin convention, granular scope-disable, decoupled config-dir/keychain, default `.gitignore` template for `.claude/`). The current flow lands the research ask implicitly but pivots to a general "Claude Code should enable this" without enumerating what "this" looks like as shippable Anthropic product work. **Recommend: at minimum decide whether the advisor pitch is (i) methodology-paper framing only, (ii) methodology-paper + Claude Code product suggestions, or (iii) explicit two-layer as yesterday's draft had. This is a big enough scoping decision to surface before drafting.**

---

## End of part 2 — Agent's return-of-ball to Human

Two parts of narrative flow captured; appendix scope agreed (canonical invocation commands + eval-test isolation); working title still open; six conceptual-gap items flagged above. **Human to respond on:**
- Which of the six items to keep vs. cut for altitude.
- Whether part 2 completes the narrative flow or more is coming.
- Whether to proceed to drafting or continue dictation.

---

## Human's triage of the six conceptual gaps + pending inputs (part 3)

Wispr Flow cleanup: "LLN" → "LLM"; "agenda programs" → "agentic programs"; "Anna banana" / "Net-a-Banana" → "Nano Banana" (Google's Gemini image model, recently re-branded); "MNN" → "M/N". Structural ambiguities preserved in [brackets].

### Item 1 — paper-trail as case study not contribution: ACCEPT, and diversify the examples

**Human:** *"No, I mean, that needs to be clear. It's more like, for example, or by way of example, paper-trail."*

Widen the example set beyond paper-trail + healthcare harmonization to a third concrete illustration: a **project-management workflow tool** that ingests meeting notes, cascades them to the documentation of different GitHub repositories, checks them against cross-office task lists, marks items complete as inferred by the meeting notes, raises questions or permission prompts to the user, and asks whether new tasks should be added or GitHub issues raised to specific people — "an interactive but purely project-management-style agentic workflow."

**Human's own hedge:** *"I don't know; that's way too many details, but there are many examples of this."*

**Agent interpretation for the draft:** keep the PM example short (one sentence, not the full feature list above) to convey breadth. The three examples together span (a) scientific / citation integrity, (b) healthcare / data harmonization, (c) knowledge-work / project management — which is a stronger scoping claim than "paper-trail-plus-one-more."

### Item 2 — optimizer-target substrate co-location as novel: ACCEPT

**Human:** *"Yes, the agentic program as the optimizer target, I believe, is a novel contribution."*

Elevate from parenthetical to a one-sentence standalone claim in the main text.

### Item 3 — M and N dials: ACCEPT, with references pending

**Human:** *"Yes, M/N dials and references to the paper, which I will drop in the system prompt for [the draft], but I'll have a Gemini or a Nano Banana [generate] the figure for all of this to ground."*

Include M / N dial framing. Human will provide the paper reference list in a forthcoming system-prompt drop. Nano Banana (Google's Gemini image model) is being used to generate the accompanying figure; the figure work is gated on the system prompt being finalized.

### Item 4 — "two orthogonal axes" framing: DEFER pending v7 figure

**Human:** *"Yeah, I don't know if they're axes. This is what can make me more clear when I give you the updated v7 of the figure, which is still in progress."*

Hold the axes-vs.-something-else framing open until the v7 figure lands. The figure will be load-bearing for how the relationship between host-state isolation and train/val/test split is communicated. **Agent: do not commit to "two orthogonal axes" prose pre-figure.**

### Item 5 — two related-work streams: ACCEPT, with sharp distinction

**Human:** *"We can say 'optimizer agent' as 'optimizer' and say that this is going to optimize LLM prompts as well as Pythonic code, but not agentic programs living in a Claude Code environment themselves. That's clearly prior art."*

Distinction to draw in the pitch: existing agent-as-optimizer work (the 13-paper survey lineage — VeRO, ADAS, AFlow, Karpathy autoresearch, Meta-Harness, AlphaEvolve, Sakana AI Scientist, MAPRO, MA-SAPO, MASS, etc.) targets **LLM prompts** and **Pythonic code** as optimization targets. Our contribution targets **agentic programs living in a Claude Code environment**, which is the category those systems do not cover. *"That's clearly prior art"* is Human flagging that prompt optimization and Python-code optimization should be explicitly named as prior art, not subsumed into our contribution claim.

The Berkeley-paper (benchmark-integrity lineage) citation from part 2 stays — it addresses evaluator-side integrity as distinct prior art that our substrate-side isolation extends orthogonally.

### Item 6 — audience / deliverable scope: ACCEPT BOTH, ONE DOCUMENT

**Human:** *"It's simultaneously both to describe concretely what it is that I am working on. But also something for my advisor to pass along to Anthropic — to let them know what we think, maybe to get funding set up, a collaboration, something along those lines. It's also meant for my advisors as context for what this paper may look like."*

Decision: **single document, two audiences.** Audience (a) = the user's advisors, for whom this is a preview of what the paper will look like. Audience (b) = Anthropic (via the advisor's network), for whom this is framed as a call to action + potential funding / collaboration seed.

**Human's framing refinement:** *"Regardless, whatever people we have could be a call to action to these companies to do so — although really it's just a product for themselves."*

I.e., the call to action lands even without Anthropic explicitly being the audience, because the product-primitive suggestions (Claude Code should ship these as first-class flags) are things Anthropic would want to ship anyway. This softens the "ask" tone into a "here's what the ecosystem needs" tone.

**Human's parenthetical:** *"Maybe we should make the call to action to [open source community / OpenAI / be OS-agnostic — Wispr-ambiguous, Human flagged it doesn't matter], but it doesn't matter."*

Agent interpretation: Human is noting in passing that the methodology is substrate-agnostic in principle (applies to any closed-substrate agentic platform), but not making that a drafting requirement. Keep the pitch Claude Code-specific.

### Closing — pending inputs from Human

**Human:** *"Yeah, I think that's most of it. I'll try to pass you that system prompt as soon as I'm happy with the figure and the figure prompt for Nano Banana too. I can also pass you the figure itself if helpful once complete, which will be [sentence cut off — more may follow]."*

**Inputs Human will send before drafting proceeds:**
1. **System prompt for the drafting pass** — will contain the paper references (for the M/N dials + related-work streams items) that Human wants the draft to ground in.
2. **Figure prompt** — the Nano Banana prompt Human is using to generate v7 of the figure (not the figure itself, but the prompt specification; Human may also share the resulting figure once rendered).
3. **Figure v7** (optional) — if Human deems it helpful to share the rendered figure, they will. This is what will decide the "two orthogonal axes" vs. alternative framing in item 4.

**Agent's posture until these inputs arrive:** do not draft `advisor-pitch.md`. The triage above + the pending inputs collectively resolve enough scoping that a complete first draft is possible once the system prompt drops, but the v7 figure may change the structure of how the two isolation concerns are composed. Premature drafting would cost a rewrite.

---

## Revised open items / parking lot (supersedes part-1 parking lot)

Items dispositioned in part 3 above are marked ✅; those still open are marked ☐.

1. ☐ **Working title.** Still open. "Flexible" is wrong word per Human. Candidates noted: *structured, disciplined, reproducibility-hardened, isolation-capable, instrumentable.* Workshop once full inputs land.
2. ✅ **Paper-trail canonical tagline to borrow.** Still need to look up the shipped phrasing when drafting; unchanged.
3. ✅ **Structure for "the challenge" section.** Agent will propose once drafting; user flagged no strong preference.
4. ☐ **Appendix outline.** One-pager: canonical iteration-tier + landmark-tier invocation shapes + eval-test IN/OUT isolation. Source: `experiment-sarol-eval-arm-isolation.md`. **Agent to draft the appendix outline in parallel with main-text draft, since its scope is settled.**
5. ☐ **"Verifiable reward" phrasing risk.** Still open. May still soften to "objective performance signal" or similar in main text; reserve "verifiable reward" for related-work framing where the 2025-26 literature context makes the term load-bearing.
6. ☐ **Two-to-three one-to-two-word isolation-mechanism examples** for the main text. Candidates: *fresh config dir, pinned binary, scrubbed env, sealed test split, locked output schema.* Pick once drafting.
7. ☐ **`--bare` problems list.** Answered in Agent's part-2 note (subscription-auth incompat; dynamic-prompt leakage; no binary pin; subagent-memory untested). Decide how many of these to name in the main text vs. push to appendix.
8. ☐ **Third case-study example — PM workflow tool.** Human gave the full feature list; draft needs to compress to one sentence. Triangulate with paper-trail + healthcare-harmonization examples for breadth.
9. ☐ **Call-to-action framing.** Single-document, two-audience, soft-ask tone per item-6 triage. Agent to prototype 1–2 closing paragraphs at draft time.
10. ⏳ **Pending input — system prompt with paper references.** Blocks M/N dial citations + related-work stream citations.
11. ⏳ **Pending input — v7 figure (and/or figure prompt).** Blocks "two orthogonal axes" vs. alternative composition framing in item 4.

---

## End of part 3 — Agent's return-of-ball to Human

All six conceptual-gap items triaged. Drafting is gated on two pending inputs: the system prompt (for paper references) and the v7 figure (for the isolation-composition framing). Agent will wait for both before drafting the main text. In the meantime, the **appendix outline** can be drafted independently — its scope is fully settled. **Human to respond on:** whether Agent should go ahead and draft the appendix outline now while waiting for the two pending inputs, or wait and do everything in one pass once the inputs land.

---

## Part 4 — figure landed, cleanup, framing update

**Figure is now in the repo** at `docs/plans/figures/v1.jpg`, with the prompt at `docs/plans/figures/v1.md`. In-voice the figure was referred to as "v7" during parts 1–3 because Human was mid-iteration; Human then cleaned up the figures directory in a separate window, deleting the unused v1–v6 prompt drafts and renumbering what was v7 → v1 since only one lives. The `figures/README.md` now reflects the trimmed state.

**Framing update triggered by looking at the actual figure.** Looking at v1.jpg (the rendered figure) rather than the prompt, the "two orthogonal axes" language I floated in the part-2 conceptual-gap list is *actively wrong*. The figure shows host-state isolation and train/val/test access as **cooperative mechanisms in one spatial composition** — not as independent axes. Specifically:
- The *spatial* composition (walls around the agentic program vs. the optimizer's ambient-context cluster) carries the host-state isolation.
- The *arrow weights and the sealed lockbox* (thick train arrow with traces, thin val arrow with macro-F1-only, dashed test-access line to the locked container) carry the train/val/test access discipline.
- Both live in a single integrated picture. Calling them "two orthogonal axes" implies they're decomposable and separately necessary, which misrepresents the architecture.

**Better candidate phrasings** for the main-text drafting pass:
- *"a two-mechanism isolation architecture"* — names the two mechanisms without forcing them onto perpendicular axes.
- *"the architecture"* — singular, lets the figure do the work of showing the two mechanisms.
- *"host-state isolation at the invocation boundary, paired with split-differentiated scoring return"* — more words, but names what each mechanism does concretely.

Agent to pick among these at drafting time; default to *"two-mechanism isolation architecture"* absent Human objection.

### Revised status of pending inputs (supersedes parking lot items 10–11)

- ✅ **Figure landed** (`docs/plans/figures/v1.jpg`). Parking lot item 11 closed.
- ⏳ **System prompt with paper references still pending.** Blocks drafting the main text (needed for M/N dial citations + related-work stream citations). Parking lot item 10 remains open.
- ⏳ **Appendix outline** can be drafted now, independent of the system prompt. Human asked to confirm whether to proceed on the appendix in parallel with waiting for the system prompt, or hold and do one pass.

### Carry-forward for the drafting pass

When `advisor-pitch.md` is rewritten, it should reference the figure as:
- Path: `docs/plans/figures/v1.jpg` (image) + `docs/plans/figures/v1.md` (caption + prompt of record)
- Caption source of truth: the "Caption" block in `v1.md` — reuse verbatim or adapt.
- Replace the old `advisor-pitch.md` line 45 pointer (currently `docs/plans/figures/v5.md` — stale from yesterday's draft) with the new v1 path.

---

## Open items / parking lot (for Agent follow-up after full flow captured)

1. **Working title alternatives.** Propose 3–5 options that land the "Claude Code is not explicitly designed for optimizing agentic programs" claim more precisely than "flexible." Candidates to prototype around: *structured*, *disciplined*, *reproducibility-hardened*, *isolation-capable*, *instrumentable*, etc. Confirm the right word with Human before drafting.
2. **Paper-trail canonical tagline to borrow.** Look up the shipped phrasing in `README.md` / the paper-trail product docs rather than inventing. Human flagged the exact wording ("agentic toolkit for automated citation provenance or whatever we called it") as a placeholder.
3. **Structure for "the challenge" section.** Human uncertain whether this is a new section or a continuation of the framing. Agent to propose once full flow is in hand.
4. **Appendix outline.** One-pager containing (a) the canonical iteration-tier / landmark-tier invocation shapes (verbatim shell), (b) the eval-test IN/OUT isolation framing. Source of truth: `docs/plans/experiment-sarol-eval-arm-isolation.md` (§canonical invocation shapes + §alternatives-evaluated catalog).
5. **Phrasing risk on "verifiable reward."** Human flagged this as loaded — audience may anchor on math. Consider softening to "an objective performance signal" or "a gold-standard comparison target" in the main text, with "verifiable reward" reserved for the appendix / related-work framing where the 2025–26 agent-as-optimizer literature context makes the term load-bearing.
6. **"Two to three examples, one to two words each" of isolation mechanisms.** Candidates from the plan-doc cluster: *fresh config dir*, *pinned binary*, *scrubbed env*, *sealed test split*, *locked output schema*. Pick the 2–3 that land hardest on an advisor who'll glance once.

---

## Meta — why this narrative restart is load-bearing

Human's framing throughout the session has emphasized altitude: the existing `advisor-pitch.md` (yesterday's draft) opens with "On Claude Code, a slash command is the entry point to a tag-scoped assembly — the command definition, subagent YAML files, tool-permission settings, MCP-server configuration…" which is a paragraph of mechanism before the reader understands why any of it matters. Human's restart moves the mechanism detail to an appendix and leads with the *ecosystem → example → challenge → reward-signal* arc that an advisor can follow in one read.

**Preserve this instinct.** The rewrite should resist the pull back toward mechanism-first exposition even when Agent's plan-doc reading surfaces tempting structural detail.
