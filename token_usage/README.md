# Claude Token Monitor — iTerm2 Status Bar (Zero-Cost Edition)

Shows remaining Anthropic API tokens and reset countdown in your iTerm2 status bar.
**Makes zero extra API calls** — reads headers from your existing traffic.

```
⚡ ████████░░ 82.3k 82% · ↺0m42s · 48req (just now)
```

## Architecture

```
Your tool (Claude Code, curl, script)
        │  ANTHROPIC_BASE_URL=http://localhost:4080
        ▼
  claude_proxy.py  ←── background daemon (port 4080)
        │  forwards request transparently
        ▼
  api.anthropic.com
        │  response + anthropic-ratelimit-* headers
        ▼
  claude_proxy.py  ←── writes ~/.cache/claude_ratelimit.json
        ▼
  claude_token_monitor.py  ←── iTerm2 reads file every 5s, zero network I/O
        ▼
  ⚡ status bar updates
```

## Quick Install

```bash
chmod +x install.sh && ./install.sh
```

Add to `~/.zshrc`:
```bash
export ANTHROPIC_BASE_URL=http://localhost:4080
```

Then in iTerm2:
1. Scripts → AutoLaunch → claude_token_monitor.py
2. Settings → Profiles → Session → Configure Status Bar
3. Drag "Claude Tokens" into the active bar

## Files

| File | Purpose |
|---|---|
| `claude_proxy.py` | Local proxy on port 4080. Sniffs rate-limit headers, writes JSON cache |
| `claude_token_monitor.py` | iTerm2 daemon. Reads JSON every 5s. Zero network I/O. |
| `install.sh` | Installs everything + creates launchd agent for auto-start on login |

## Works with any tool that respects ANTHROPIC_BASE_URL
Claude Code, Anthropic Python/JS SDK, curl (point manually), LangChain, LiteLLM, etc.
