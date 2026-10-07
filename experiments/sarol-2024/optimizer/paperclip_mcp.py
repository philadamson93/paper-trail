"""A minimal client for paperclip's (gxl.ai) hosted MCP server: one tool call, with Phil's API key.

**Why this exists rather than the `paperclip` CLI.** The CLI is broken with an API key (0.7.52 and
0.7.106, measured 2026-10-06): it wraps every command in ``tools/call name="paperclip"``, which the
server rejects as an unknown tool. Calling the server's individual tools directly works -- the same
JSON-RPC ``tools/call`` against ``/mcp``, with the key in the ``X-API-Key`` header the CLI's own
``APIKeyAuth`` sets. ``tools/list`` returns the ~45 tools and their input schemas.

It lives in ``optimizer/`` rather than inside the one baseline script that uses it today, so the
parked paperclip-as-evidence-source plan (``2026-10-06-paperclip-profile-on-engine.md``) can reuse
it if it comes back. It is stdlib-only on purpose: Python 3.13 cannot install the paperclip wheel
(``rookiepy``), and nothing here needs it.

**The key never leaves this module in readable form.** It is read from
``~/.paper-trail/credentials.env`` (``PAPERCLIP_API_KEY``), sent only as a header, and masked out of
every error message and every returned text before they reach a caller -- a server that echoes the
request back in an error would otherwise print it. ``--selftest`` pins the masking, and watches the
leak detector fire with masking switched off (a check that cannot fail proves nothing).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

ENDPOINT = "https://paperclip.gxl.ai/mcp"
CREDENTIALS = pathlib.Path.home() / ".paper-trail" / "credentials.env"
KEY_VAR = "PAPERCLIP_API_KEY"
MASK = "<paperclip-key>"

#: ``post(url, body_bytes, headers, timeout) -> (status, body_text)``. Injectable so the selftest
#: never touches the network.
Post = Callable[[str, bytes, "dict[str, str]", float], "tuple[int, str]"]


class PaperclipError(RuntimeError):
    """The server, the transport or the tool reported a failure. The message is already masked."""


class RateLimited(PaperclipError):
    """HTTP 429: the per-user verify cap or the daily task cap. Stop, save, resume later."""


def load_key(path: pathlib.Path = CREDENTIALS) -> str:
    """``PAPERCLIP_API_KEY`` from the environment, else from ``credentials.env``."""
    if os.environ.get(KEY_VAR):
        return os.environ[KEY_VAR]
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            name, _, value = line.strip().removeprefix("export ").partition("=")
            if name.strip() == KEY_VAR and value.strip():
                return value.strip().strip("'\"")
    except OSError as exc:
        raise PaperclipError(f"cannot read {path}: {exc.strerror}") from None
    raise PaperclipError(f"{KEY_VAR} is not set and not in {path}")


def _mask(text: str, key: str, *, enabled: bool = True) -> str:
    return text.replace(key, MASK) if enabled and key else text


def _urllib_post(url: str, body: bytes, headers: "dict[str, str]", timeout: float) -> "tuple[int, str]":
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _decode(body: str) -> dict[str, Any]:
    """A JSON-RPC response, sent either as plain JSON or as server-sent events (``data:`` lines)."""
    stripped = body.lstrip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    for line in body.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload.startswith("{"):
                return json.loads(payload)
    raise ValueError("no JSON-RPC message in the response body")


def call(
    tool: str,
    args: "dict[str, Any] | None" = None,
    *,
    key: "str | None" = None,
    timeout: float = 600.0,
    post: "Post | None" = None,
    _mask_enabled: bool = True,
) -> str:
    """Call one paperclip tool and return its text output (masked).

    Raises :class:`RateLimited` on HTTP 429 and :class:`PaperclipError` on any other HTTP failure,
    a JSON-RPC ``error``, or a tool result flagged ``isError`` -- a tool that failed must never be
    read as a tool that returned text.
    """
    key = key if key is not None else load_key()
    post = post or _urllib_post
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args or {}}}
    ).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "paper-trail-paperclip-mcp/1",
        "X-API-Key": key,
    }

    def masked(text: str) -> str:
        return _mask(text, key, enabled=_mask_enabled)

    try:
        status, text = post(ENDPOINT, body, headers, timeout)
    except (OSError, urllib.error.URLError) as exc:
        raise PaperclipError(masked(f"{tool}: transport error: {exc}")) from None
    if status == 429:
        raise RateLimited(masked(f"{tool}: HTTP 429: {text[:500]}"))
    if status >= 400:
        raise PaperclipError(masked(f"{tool}: HTTP {status}: {text[:500]}"))
    try:
        data = _decode(text)
    except ValueError as exc:
        raise PaperclipError(masked(f"{tool}: unreadable response ({exc}): {text[:300]}")) from None
    if "error" in data:
        err = data["error"]
        raise PaperclipError(masked(f"{tool}: JSON-RPC error {err.get('code')}: {err.get('message')}"))
    result = data.get("result") or {}
    out = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    if result.get("isError"):
        raise PaperclipError(masked(f"{tool}: tool error: {out[:500]}"))
    return masked(out)


def _selftest() -> int:
    """Payload shape, key masking (with a negative control), and every failure path surfaced."""
    key = "pk_test_SECRET_123"
    sent: dict[str, Any] = {}

    def fake(response: "tuple[int, str]") -> Post:
        def _post(url, body, headers, timeout):
            sent.update(url=url, body=json.loads(body), headers=headers)
            return response
        return _post

    def ok_result(text: str, *, is_error: bool = False, sse: bool = False) -> "tuple[int, str]":
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": text}], "isError": is_error}})
        return 200, (f"event: message\ndata: {msg}\n\n" if sse else msg)

    def raised(fn) -> "BaseException | None":
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 -- the selftest inspects whatever came out
            return exc
        return None

    out = call("git_status", {"repo": "r"}, key=key, post=fake(ok_result("[OK] c1")))
    shape_ok = (
        sent["url"] == ENDPOINT
        and sent["body"]["method"] == "tools/call"
        and sent["body"]["params"] == {"name": "git_status", "arguments": {"repo": "r"}}
        and sent["headers"]["X-API-Key"] == key
    )
    sse_out = call("git", {}, key=key, post=fake(ok_result("hello", sse=True)))
    echo = ok_result(f"you sent X-API-Key: {key}")
    echoed = call("git", {}, key=key, post=fake(echo))
    leak_unmasked = call("git", {}, key=key, post=fake(echo), _mask_enabled=False)
    http_err = raised(lambda: call("git", {}, key=key, post=fake((401, f"bad key {key}"))))
    rate = raised(lambda: call("git_commit", {}, key=key, post=fake((429, "slow down"))))
    rpc = raised(lambda: call("nope", {}, key=key, post=fake((200, json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": f"Unknown tool, key={key}"}})))))
    tool_err = raised(lambda: call("git_add", {}, key=key, post=fake(ok_result("repo missing", is_error=True))))
    garbage = raised(lambda: call("git", {}, key=key, post=fake((200, "<html>gateway</html>"))))

    def leaks(text: object) -> bool:
        return key in str(text)

    checks = [
        ("the request is a tools/call for the named tool, with its arguments and the key header", shape_ok),
        ("the tool's text comes back", out == "[OK] c1"),
        ("a server-sent-events response is decoded too", sse_out == "hello"),
        ("a response that echoes the key comes back masked", not leaks(echoed) and MASK in echoed),
        ("...and the leak check fires with masking off (negative control)", leaks(leak_unmasked)),
        ("an HTTP error raises, masked", isinstance(http_err, PaperclipError) and not leaks(http_err)),
        ("HTTP 429 raises RateLimited, so a caller can stop and resume", isinstance(rate, RateLimited)),
        ("a JSON-RPC error raises with its message, masked", isinstance(rpc, PaperclipError) and "Unknown tool" in str(rpc) and not leaks(rpc)),
        ("a tool result flagged isError raises rather than reading as text", isinstance(tool_err, PaperclipError) and "repo missing" in str(tool_err)),
        ("a non-JSON body raises", isinstance(garbage, PaperclipError)),
    ]
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if len(sys.argv) >= 2:
        # A hand check: `paperclip_mcp.py <tool> ['<json args>']`.
        print(call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
        raise SystemExit(0)
    print(__doc__)
