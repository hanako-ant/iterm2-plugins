#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import glob
from datetime import datetime, timezone, timedelta
import iterm2

CLAUDE_DIR = os.path.expanduser("~/.claude/projects")
REFRESH_CADENCE = 10  # seconds - just reads local files, zero cost

# 5-hour rolling window (Claude Code's billing window)
WINDOW_HOURS = 5


def _parse_block_start(ts_str):
    """Round a timestamp down to the start of its 5-hour block."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        # Claude uses rolling 5-hour windows from first message
        return dt
    except Exception:
        return None


def read_usage():
    """
    Read all JSONL files under ~/.claude/projects/ and sum tokens
    used in the last 5 hours (Claude Code's rolling window).
    Returns (tokens_used, window_start, oldest_entry_in_window).
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=WINDOW_HOURS)

    input_tokens  = 0
    output_tokens = 0
    cache_read    = 0
    cache_write   = 0
    oldest_in_window = None
    newest_in_window = None

    pattern = os.path.join(CLAUDE_DIR, "**", "*.jsonl")
    files = glob.glob(pattern, recursive=True)

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    ts_str = rec.get("timestamp") or rec.get("ts") or ""
                    if not ts_str:
                        continue

                    dt = _parse_block_start(ts_str)
                    if dt is None or dt < cutoff:
                        continue

                    # Usage is in assistant messages under .message.usage
                    usage = None
                    msg = rec.get("message") or {}
                    if isinstance(msg, dict):
                        usage = msg.get("usage")
                    if usage is None:
                        usage = rec.get("usage")
                    if not isinstance(usage, dict):
                        continue

                    input_tokens  += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    cache_read    += usage.get("cache_read_input_tokens", 0)
                    cache_write   += usage.get("cache_creation_input_tokens", 0)

                    if oldest_in_window is None or dt < oldest_in_window:
                        oldest_in_window = dt
                    if newest_in_window is None or dt > newest_in_window:
                        newest_in_window = dt

        except (OSError, PermissionError):
            continue

    return {
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cache_read":    cache_read,
        "cache_write":   cache_write,
        "total":         input_tokens + output_tokens,
        "oldest":        oldest_in_window,
        "newest":        newest_in_window,
        "window_end":    oldest_in_window + timedelta(hours=WINDOW_HOURS) if oldest_in_window else None,
    }


def _fmt_tokens(n):
    if n >= 1000000:
        return "{:.1f}M".format(n / 1000000)
    if n >= 1000:
        return "{:.1f}k".format(n / 1000)
    return str(n)


def _fmt_remaining(window_end):
    """Time until the oldest entry in the window falls out (= reset time)."""
    if not window_end:
        return ""
    now = datetime.now(timezone.utc)
    secs = max(0, int((window_end - now).total_seconds()))
    if secs >= 3600:
        return "{}h{:02d}m".format(secs // 3600, (secs % 3600) // 60)
    if secs >= 60:
        return "{}m{:02d}s".format(secs // 60, secs % 60)
    return "{}s".format(secs)


def build_texts(data):
    if data["total"] == 0 and data["oldest"] is None:
        return [
            "Claude: no usage in last 5h",
            "Claude: idle",
            "Claude: -",
        ]

    total_str  = _fmt_tokens(data["total"])
    input_str  = _fmt_tokens(data["input_tokens"])
    output_str = _fmt_tokens(data["output_tokens"])
    reset_str  = _fmt_remaining(data["window_end"])

    reset_part = " reset:{}".format(reset_str) if reset_str else ""

    return [
        "Claude: {} (in:{} out:{}){}".format(total_str, input_str, output_str, reset_part),
        "Claude: {} in:{} out:{}".format(total_str, input_str, output_str),
        "Claude: {}{}".format(total_str, reset_part),
        "Claude: {}".format(total_str),
    ]


async def main(connection):
    component = iterm2.StatusBarComponent(
        short_description="Claude Tokens",
        detailed_description="Token usage in the last 5h rolling window. Reads ~/.claude/projects/ JSONL files. Zero API calls.",
        knobs=[],
        exemplar="Claude: 42.1k (in:30k out:12k) reset:2h15m",
        update_cadence=REFRESH_CADENCE,
        identifier="com.anthropic.iterm2.claude-token-monitor-v3",
    )

    @iterm2.StatusBarRPC
    async def coro(knobs):
        data = read_usage()
        return build_texts(data)

    await component.async_register(connection, coro)


iterm2.run_forever(main)
