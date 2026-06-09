One-shot bootstrap for the `/paper-trail` dependency stack. Probes each dependency, reports what's missing, and offers to install/start the ones that can be automated — with explicit per-step confirmation. Safe to re-run; idempotent.

Intended entry point: the user runs `/paper-trail-init` on a fresh machine before their first `/paper-trail` audit. Also auto-invoked by `/paper-trail`'s preflight when blocking dependencies are missing (see `.claude/commands/paper-trail.md`).

## 1. Probe all dependencies

Report a status table before doing anything. Check each of the following **without side effects**:

- **`pdftotext`** — run `which pdftotext` (or `command -v pdftotext`). Required for Phase 0 PDF reading and Phase 2.5 `pdftotext_fallback` ingest. If missing, `/paper-trail` cannot start.
- **Docker** — run `command -v docker && docker info >/dev/null 2>&1`. Only required as a dependency of GROBID; if the user doesn't want GROBID, Docker is optional.
- **GROBID** — probe `http://localhost:8070/api/isalive` with a 3-second timeout. Required for full-fidelity Phase 2.5 ingest (per-section structure + figure metadata). Optional — `pdftotext_fallback` covers most claim types.
- **`papersflow` MCP** — run `claude mcp list` and grep for `papersflow`. Optional but strong upgrade for `/verify-bib`: 474M+ paper coverage and deterministic DOI/author matching.
- **`pdf-reader` MCP (any)** — run `claude mcp list` and look for anything matching `pdf-reader` / `pdf_reader` / similar. Optional; Phase 3 grounding uses `Read` on the ingested `content.txt` if no MCP is present. Do **not** try to auto-install — there is no single canonical package, and the right choice depends on the user's other workflows.
- **`paper-search` MCP (any)** — same pattern: look for `paper-search` / `arxiv-mcp-server` / similar. Optional; Phase 2 falls back to CrossRef open-access and direct arXiv HTTP.

Print the result as a compact table:

```
paper-trail dependency status
  ✓ pdftotext           /opt/homebrew/bin/pdftotext
  ✓ docker              (running)
  ✗ grobid              not reachable at http://localhost:8070
  ✗ papersflow MCP      not configured
  - pdf-reader MCP      not configured (optional)
  - paper-search MCP    not configured (optional)
```

(`✓` installed, `✗` missing-but-installable, `-` missing-optional-no-action.)

## 2. Detect the platform

Detect the host platform once so install commands are correct:

- macOS: `uname` returns `Darwin`; prefer `brew` for package installs.
- Linux (Debian/Ubuntu): `uname` returns `Linux`; check for `apt`.
- Linux (Fedora/RHEL): check for `dnf` or `yum`.
- Other: don't invent install commands; print the canonical package name and stop.

Record the detected platform; surface it in the summary output so the user can correct if auto-detection is wrong.

## 3. Resolve each missing dependency — one at a time

For every `✗` in the status table, run the corresponding resolver. For every `-`, skip silently (user asks explicitly if they want them). **Never batch**: ask one question, act on it, probe to confirm, then move on.

### 3.1 `pdftotext`

If missing, ask via `AskUserQuestion`:

> `pdftotext` (from poppler) is required for Phase 0 PDF reading and Phase 2.5 fallback ingest. Install now?

Options (platform-conditional):
- **Yes** — run the platform-appropriate install command, then re-probe:
  - macOS: `brew install poppler`
  - Debian/Ubuntu: `sudo apt-get install -y poppler-utils`
  - Fedora/RHEL: `sudo dnf install -y poppler-utils`
- **Skip** — record as skipped; warn that `/paper-trail` will fail to read PDFs without it.

If the user says Yes but the install fails (network, permissions, etc.), don't retry silently — surface the error verbatim and ask whether to retry or skip.

### 3.2 Docker

If missing, ask:

> Docker is needed to run GROBID (the recommended ingest path). Install Docker Desktop now?

Options:
- **Yes** (macOS only — `brew install --cask docker`, then tell the user they must launch Docker Desktop once to accept its license; this is a one-time manual step).
- **Skip** — proceed without GROBID; `/paper-trail` will use `pdftotext_fallback`.

On Linux, do **not** attempt auto-install — Docker installation varies widely by distro and typically requires `usermod -aG docker $USER` + re-login. Print the official install URL (`https://docs.docker.com/engine/install/`) and mark GROBID as skipped.

### 3.3 GROBID

If Docker is present and GROBID isn't reachable, ask:

> Start GROBID via Docker now? This pulls `lfoppiano/grobid:0.8.2` (~2 GB on first run) and exposes it on localhost:8070.

Options:
- **Yes** — run:

  ```bash
  docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2
  ```

  Then poll `/api/isalive` every 5 seconds up to 90 seconds (first-run init is slow). Report when it comes up; re-probe before continuing.
- **Skip** — record; `/paper-trail` will use `pdftotext_fallback`.

If the `docker run` fails because a container named `grobid` already exists (e.g., stopped), run `docker start grobid` first; if that also fails, `docker rm -f grobid && docker run ...`.

### 3.4 `papersflow` MCP

If missing, ask:

> Add the `papersflow` MCP? It provides 474M+ paper coverage for `/verify-bib` and `/fetch-paper`. Adds to your user-scope Claude Code settings.

Options:
- **Yes** — run:

  ```bash
  claude mcp add papersflow --transport streamable-http https://doxa.papersflow.ai/mcp
  ```

  Mark a `mcp_added` flag so the summary can tell the user to restart Claude Code.
- **Skip** — proceed without it; `/verify-bib` falls back to CrossRef + arXiv REST.

### 3.5 Optional MCPs (`pdf-reader`, `paper-search`)

Do **not** offer to install these. In the summary, include a one-liner:

> Optional: `pdf-reader` and `paper-search` MCPs improve PDF reading and fetch fallbacks. No single canonical package exists — browse `https://mcpservers.org/` or `https://github.com/modelcontextprotocol/servers` and add whichever you prefer via `claude mcp add`.

## 4. Summary

Print a final block:

```
paper-trail init complete

  installed / started:
    - pdftotext (poppler)
    - docker
    - grobid (container: grobid, port 8070)
    - papersflow MCP

  skipped:
    - (none)

  unchanged:
    - (none)

  next steps:
    - MCPs were added: restart Claude Code to load papersflow before running /paper-trail.
    - Optional: browse mcpservers.org for a pdf-reader / paper-search MCP.

  run /paper-trail <path-to-pdf> to start an audit.
```

Only mention the "restart Claude Code" line if at least one MCP was added this run.

## 5. Do not

- **Never** run `sudo` or install system packages without explicit confirmation for each step. No `brew install` / `apt-get install` / `claude mcp add` without the user's Yes.
- **Never** auto-pick a `pdf-reader` or `paper-search` MCP. The ecosystem has several; the right choice is user-dependent.
- **Never** skip the probe step. A re-run on an already-fully-initialized machine should print the status table and exit, not prompt for any installs.
- **Never** modify project files. `/paper-trail-init` only touches system packages, the GROBID container, and the user's Claude Code MCP settings — not anything in the working directory.
- **Never** proceed past a failed install silently. If `brew install poppler` errors, surface the error and ask whether to retry / skip.
