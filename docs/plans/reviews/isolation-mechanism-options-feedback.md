Reference: docs/claude_ops.md

# Adjudication: which isolation mechanism for paper-trail (Codex)

## Recommendation

Use a staged version of Option C, but make Docker the first enforcement layer and defer hooks until the filesystem, network, credential, and trace paths work end to end. The strongest argument is that Docker can make gold and scoring code absent or read-only at the kernel boundary, while the OS-account design leaves its whole optimizer clone writable. The strongest argument against is integration risk: paper-trail still needs dynamic per-claim mounts, safe token injection, and host-side trace capture before a real run is trustworthy.

## Corrections to the options write-up

- The Docker substrate has had a consumer. A rad-eval Docker agent builds the prefix, runs the agent, and copies back only staged writable files (`/home/philadamson/code/rad-eval/.claude/worktrees/docker-gate/src/optimizer_loop/docker_agent.py:59-64`, `:92-140`). A later rad-eval branch wires it into the dispatcher (`/home/philadamson/code/rad-eval/.claude/worktrees/radgraph-modifier-composition/src/optimizer_loop/dispatcher.py:2823-2839`, `:2953-2969`). The VM record says one real dispatcher run passed (`/home/philadamson/code/agentic-label-opt/docs/vm-status/2026-08-05-902cfb0.md:3-10`, `:37-40`). It is fair to say no current production path calls the substrate. It is wrong to say no consumer has ever called it.

- OS permissions do not police Write and Edit inside rad-eval's loop clone. Provisioning changes ownership of the whole clone to the optimizer account (`/home/philadamson/code/rad-eval/scripts/provision_loop_clone.py:123-128`, `:280-292`), while Write and Edit remain available (`/home/philadamson/code/rad-eval/src/optimizer_loop/allowed_tools.py:20-26`). The outer operator process and its private mounts remain protected, but copies of scoring code in the optimizer-owned clone are writable. A literal port does not establish paper-trail's required write boundary.

- The statement that the OS-account option has “no kernel backstop” is too broad. Unix ownership and the FUSE mount permissions are kernel-enforced for data outside the optimizer-owned tree (`/home/philadamson/code/rad-eval/docs/plans/optimizer-isolation-protocol.md:139-152`). What it lacks is a mount namespace and a kernel network backstop.

- The OS-account option does not control everything the network may reach. It removes WebSearch and Agent, and its hook rejects WebFetch (`/home/philadamson/code/rad-eval/src/optimizer_loop/allowed_tools.py:9-26`, `/home/philadamson/code/rad-eval/hooks/policy.py:729-756`). It still allows the optimizer to run the Python file that the optimizer edits (`/home/philadamson/code/rad-eval/hooks/policy.py:508-551`). That program can make ordinary socket or HTTP calls without a WebFetch tool call. Only a network namespace or host firewall closes that path.

- Conversely, the Docker substrate can control network reach. It supports no network, unrestricted bridge networking, and a kernel-backed hostname allowlist (`/home/philadamson/code/agentic-label-opt/isolation/docker_prefix.py:465-480`, `/home/philadamson/code/agentic-label-opt/isolation/network_allowlist.py:1-6`). The present named allowlist is Vertex-specific (`/home/philadamson/code/agentic-label-opt/isolation/vertex_profile.py:46-57`). The accurate criticism is that paper-trail's proposed open profile provides no network seal (`/home/philadamson/code/agentic-label-opt/isolation/open_profile.py:1-17`), not that Docker cannot provide one.

- Per-version trees come from materialization. Per-claim trees do not. The materializer writes one manifest at one SHA into a caller-supplied destination (`/home/philadamson/code/agentic-label-opt/engine/materialize.py:40-58`). paper-trail creates claim-specific output and staging paths itself (`experiments/sarol-2024/optimizer/adapter.py:818-844`).

- The engine policy is not “wiring, not authoring, for the largest piece” without qualification. It deliberately omits rad-eval's Python, git, and grep validators (`/home/philadamson/code/agentic-label-opt/engine/policy.py:1-15`). It also has no hook entrypoints, settings, arming gate, audit writer, or consumer configuration. Those are material parts of the production mechanism.

- `--rm` does not itself destroy traces. It destroys files that exist only in the container. Traces survive if they are streamed to the host or written through a host mount. The current paper-trail invoker already receives the stream but discards it after extracting metadata (`experiments/sarol-2024/optimizer/adapter.py:469-503`). The options write-up correctly identifies a missing design, but attributes it too narrowly to `--rm`.

- The vision's list of Docker, Git isolation, and permissions is a list of examples, not a requirement to deploy all three. Option C should be chosen because its layers cover named threats, not because the sentence is conjunctive (`docs/session/isolation-mechanism-options.md:8-11`).

## Question-by-question

1. **Is Docker alone sufficient?**

   For the exact scientific requirement, a correctly wired Docker boundary is sufficient without a command hook. Gold must not be mounted. Scoring code must either stay on the host or appear only through a read-only bind. The program snapshot is `.git`-free and read-only (`/home/philadamson/code/agentic-label-opt/engine/materialize.py:100-113`), and the renderer mounts that snapshot read-only while mounting only named editable copies read-write (`/home/philadamson/code/agentic-label-opt/isolation/docker_prefix.py:405-435`). Arbitrary Bash inside that namespace cannot read an absent host path or alter a read-only host bind.

   The substrate as a library is not sufficient. paper-trail must call it for every optimizer and judge launch, must reject broad or alternate-target mounts, and must not mount the Docker socket. paper-trail currently does none of this: both the judge and optimizer use bypass permissions, and the optimizer runs at the live repository root (`experiments/sarol-2024/optimizer/adapter.py:700-731`, `experiments/sarol-2024/optimizer/dispatcher.py:381-438`).

   The other layers cover different threats:

   - A tool allowlist and hooks reduce accidental reads within allowed mounts, reject known shell forms, remove unproved subagents, and can produce a per-call audit. rad-eval wires only Read, Bash, and WebFetch (`/home/philadamson/code/rad-eval/.claude/settings.json:6-35`). They do not constrain syscalls made by optimizer-authored Python.
   - A Docker network policy limits socket egress even from such Python. It is required if protected labels are reachable through a network service. No such service appears here; paper-trail reads gold from a local external directory (`experiments/sarol-2024/scripts/parse_verdict.py:48-64`). It is still prudent operationally because the agent receives a reusable credential.
   - Safe credential transport prevents disclosure in host process listings and logs. It does not stop the Claude process, or a child that inherits its environment, from seeing the token. Preventing that would require a credential-holding proxy or another broker, not a hook that merely rejects `printenv`.

   Thus open-network Docker plus `KEY=VALUE` argv is not a safe shipping configuration. But hooks are defense in depth for the stated gold/scorer lock, not its foundation.

2. **Which hook layer?**

   Use the engine policy as the shared decision core. Do not copy 758 rad-eval-specific lines into paper-trail. Its path resolution, fail-closed parser behavior, substitutions, redirects, command names, and unknown-tool denial are already generic and tested (`/home/philadamson/code/agentic-label-opt/engine/policy.py:38-108`, `:155-227`, `:246-259`; `/home/philadamson/code/agentic-label-opt/tests/test_policy.py:34-115`).

   It is not ready to wire unchanged. Its configuration exposes only read patterns, deny patterns, and command names (`/home/philadamson/code/agentic-label-opt/engine/schemas.py:244-252`). A whitelisted command with no positional path is allowed. It has no git subcommand policy, no Python invocation policy, no per-command flag policy, and no paper-trail configuration. It imports `bashlex` opportunistically rather than providing rad-eval's vendored parser (`/home/philadamson/code/agentic-label-opt/engine/policy.py:116-123`). It also lacks the production shell around the decisions: thin hook programs, armed versus unarmed behavior, fail-closed exception handling, and serialized audit writes (`/home/philadamson/code/rad-eval/hooks/pretooluse_bash.py:1-17`, `/home/philadamson/code/rad-eval/hooks/audit_broker.py:142-201`).

   The right reuse boundary is: shared engine decision core and generic hook/audit adapter; paper-trail-owned policy data and any deep command validators it actually needs. rad-eval is the behavioral reference, not the source file to port wholesale.

3. **Does the OS-account head start outweigh later migration?**

   No. Much of the work would be transitional: account provisioning, sudo prefixes, cross-user HOME, ownership repair, and safe-directory handling. The engine plan explicitly calls that approach a stopgap and Docker the intended end state (`/home/philadamson/code/agentic-label-opt/docs/plans/2026-07-22-isolation-docker-substrate.md:9-19`, `:40-56`). More importantly, a literal port of rad-eval's whole-clone ownership does not satisfy the scorer-write requirement.

   The head start is also smaller than the options write-up says. A Docker agent with staging, copy-back, dispatcher wiring, structural tests, and one real VM run already exists on rad-eval's non-current branch. paper-trail still has different plural editable files and per-claim judge mounts, but it is adapting a tested consumer pattern rather than inventing the first one.

4. **How should the token avoid argv?**

   Docker has a suitable transport: `--env NAME` copies a named variable from the Docker client's environment without putting its value in argv. The current engine API cannot express it. Its mapping always renders `-e KEY=VALUE` (`/home/philadamson/code/agentic-label-opt/isolation/docker_prefix.py:370-372`, `:437-440`). This is worse than process-list exposure because the engine wrapper records the complete command in `meta.json` (`/home/philadamson/code/agentic-label-opt/engine/claude_wrapper.py:342-365`, `:684-695`).

   The minimal engine change is a separate sequence such as `inherit_env=("CLAUDE_CODE_OAUTH_TOKEN",)`, rendered as `--env CLAUDE_CODE_OAUTH_TOKEN`. The host launcher supplies a curated environment through the existing process environment seam (`/home/philadamson/code/agentic-label-opt/engine/claude_wrapper.py:594-600`, `:617-625`). A consumer could splice raw tokens into the returned argv, or manage an `--env-file`, but that bypasses the public renderer and creates its own redaction and cleanup contract. I would not count either as a supported no-change solution.

   This fixes host argv and log disclosure only. The token remains visible inside the Claude process. If the threat model says optimizer-authored code must not read it, the minimal named-env change is insufficient; authentication must move to a credential-holding proxy or broker.

5. **What preserves judge transcripts?**

   No compliant option preserves them without added design. Option A preserves the present lookup only if the judge remains the operator user, which also leaves that judge outside the proposed isolation. A cross-user judge writes under the other account's HOME (`/home/philadamson/code/rad-eval/src/optimizer_loop/dispatcher.py:686-704`), while paper-trail searches the operator's `~/.claude/projects` (`experiments/sarol-2024/optimizer/adapter.py:427-440`). Options B and C leave the container's home ephemeral unless it is mounted.

   The cheapest fix is to persist the stream JSON that paper-trail already captures on the host and use that file as `trace_ref`. The invoker currently has all stdout in memory, extracts only session and cost, and drops the rest (`experiments/sarol-2024/optimizer/adapter.py:469-503`). The Runner already owns the stable per-claim trace destination (`experiments/sarol-2024/optimizer/adapter.py:866-896`). This is cheaper and less coupled to Claude's private home-directory layout than mounting `CLAUDE_CONFIG_DIR` and rediscovering its project slug.

6. **Is there a fourth option?**

   Yes. Use “Docker boundary first, hooks second.” This is less than Option C at the first landing, but stronger than Option B as written.

   First, keep the deterministic scorer and gold on the host. Containerize both agentic principals through the existing Docker substrate. Give the optimizer only the materialized program, named writable copies, released TRAIN feedback, and required public context. Give each judge only its claim staging and the exact materialized version. Use the generic host-allowlist network stack with a paper-trail host list, a narrow CLI tool surface, named-env credential injection, exact-mount refusal, and host-captured traces. The generic network primitive already accepts caller-supplied hosts (`/home/philadamson/code/agentic-label-opt/isolation/network_allowlist.py:55-118`).

   Then wire the shared policy and audit layer. That second landing improves auditability and reduces ambient behavior inside permitted mounts. It need not block the scoring lock, because the kernel boundary already enforces the two stated assets. This sequence also avoids building OS-account machinery that Docker is meant to replace.

## What would change my mind

I would choose the OS-account approach as a time-boxed bridge if a real paper-trail driver-to-Task probe cannot authenticate and complete through Docker with the required host allowlist, or if a required execution machine cannot support Docker reliably. That bridge would need a different layout from rad-eval: scoring code and gold must remain in operator-owned paths outside the optimizer-owned clone, the judge must also be isolated, and the plan must name a removal date. I would instead require hooks in the first Docker landing if Phil decides that a Merkle-style per-tool audit is part of the requirement, rather than a separate paper-grade assurance claim.

## Audit Trail

- docs/claude_ops.md
- docs/session/isolation-mechanism-options.md
- docs/plans/isolation-protocol.md
- docs/plans/reviews/isolation-protocol-feedback.md
- experiments/sarol-2024/optimizer/adapter.py
- experiments/sarol-2024/optimizer/dispatcher.py
- experiments/sarol-2024/optimizer/profiles.py
- experiments/sarol-2024/scripts/parse_verdict.py
- experiments/sarol-2024/scripts/stage_claim.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/dispatcher.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/allowed_tools.py
- /home/philadamson/code/rad-eval/src/optimizer_loop/run_artifacts.py
- /home/philadamson/code/rad-eval/hooks/policy.py
- /home/philadamson/code/rad-eval/hooks/audit_broker.py
- /home/philadamson/code/rad-eval/hooks/pretooluse_read.py
- /home/philadamson/code/rad-eval/hooks/pretooluse_bash.py
- /home/philadamson/code/rad-eval/hooks/pretooluse_webfetch.py
- /home/philadamson/code/rad-eval/.claude/settings.json
- /home/philadamson/code/rad-eval/scripts/provision_loop_clone.py
- /home/philadamson/code/rad-eval/docs/plans/optimizer-isolation-protocol.md
- /home/philadamson/code/rad-eval/.claude/worktrees/docker-gate/src/optimizer_loop/docker_agent.py
- /home/philadamson/code/rad-eval/.claude/worktrees/docker-gate/src/optimizer_loop/tests/test_docker_agent.py
- /home/philadamson/code/rad-eval/.claude/worktrees/radgraph-modifier-composition/src/optimizer_loop/dispatcher.py
- /home/philadamson/code/rad-eval/.claude/worktrees/radgraph-modifier-composition/src/optimizer_loop/allowed_tools.py
- /home/philadamson/code/agentic-label-opt/engine/policy.py
- /home/philadamson/code/agentic-label-opt/engine/schemas.py
- /home/philadamson/code/agentic-label-opt/engine/materialize.py
- /home/philadamson/code/agentic-label-opt/engine/claude_wrapper.py
- /home/philadamson/code/agentic-label-opt/engine/loop.py
- /home/philadamson/code/agentic-label-opt/isolation/Dockerfile
- /home/philadamson/code/agentic-label-opt/isolation/docker_prefix.py
- /home/philadamson/code/agentic-label-opt/isolation/open_profile.py
- /home/philadamson/code/agentic-label-opt/isolation/vertex_profile.py
- /home/philadamson/code/agentic-label-opt/isolation/network_allowlist.py
- /home/philadamson/code/agentic-label-opt/tests/test_policy.py
- /home/philadamson/code/agentic-label-opt/docs/plans/2026-07-22-isolation-docker-substrate.md
- /home/philadamson/code/agentic-label-opt/docs/vm-status/2026-08-05-902cfb0.md
- /home/philadamson/engine-82f547d/engine/policy.py
- /home/philadamson/engine-82f547d/isolation/docker_prefix.py
