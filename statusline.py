"""Desaflow OS statusline — persistent HUD at bottom of Claude Code."""
import json, sys, os, re, subprocess


# --- Model detection from transcript (bypasses stale settings.json) ---

MODEL_CONTEXT_SIZES = {
    "opus": {"default": 200_000, "1m": 1_000_000},
    "sonnet": {"default": 200_000, "1m": 1_000_000},
    "haiku": {"default": 200_000},
}

def detect_model_from_transcript(transcript_path):
    """Read the session JSONL backward to find the real model."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None, None

    try:
        # Read last 200KB of the file (enough to find recent model info)
        file_size = os.path.getsize(transcript_path)
        read_start = max(0, file_size - 200_000)

        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            if read_start > 0:
                f.seek(read_start)
                f.readline()  # skip partial line
            lines = f.readlines()

        # Scan backward for /model switch or assistant response
        model_name = None
        model_id = None
        context_size = None

        for line in reversed(lines):
            if not line.strip():
                continue

            # Check for /model command output (e.g. "Set model to Opus 4.6 (1M context)")
            if "Set model to" in line:
                match = re.search(r"Set model to\s+\\?\*?\[?1m\]?(.+?)\\?\*?\[?22m\]?", line)
                if not match:
                    match = re.search(r"Set model to\s+(.+?)(?:\\n|\")", line)
                if match:
                    raw = match.group(1).strip()
                    # Strip ANSI codes
                    raw = re.sub(r"\x1b\[[0-9;]*m", "", raw)
                    raw = re.sub(r"\[/?[0-9]*m\]?", "", raw).strip()
                    model_name = raw
                    if "1m" in raw.lower() or "1M" in raw:
                        context_size = 1_000_000
                    else:
                        context_size = 200_000
                    break

            # Check for assistant message with model field
            if model_id is None and '"message"' in line and '"model"' in line:
                try:
                    obj = json.loads(line)
                    msg = obj.get("data", {}).get("message", {}).get("message", {})
                    mid = msg.get("model", "")
                    if mid and mid.startswith("claude-"):
                        model_id = mid
                        # Derive display name
                        if "opus" in mid:
                            model_name = "Opus 4.6"
                        elif "sonnet" in mid:
                            model_name = "Sonnet 4.6"
                        elif "haiku" in mid:
                            model_name = "Haiku 4.5"
                        # Check context from model id
                        if "[1m]" in mid or "1m" in mid:
                            context_size = 1_000_000
                        # Don't break — keep looking for /model switch which is more authoritative
                except Exception:
                    pass

            # If we found a /model switch, that's definitive
            if model_name and context_size:
                break

        return model_name, context_size
    except Exception:
        return None, None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("? no data")
        return

    # Model — try transcript first, fall back to JSON data
    model_data = data.get("model", {})
    model = model_data.get("display_name", "?")
    model_id = model_data.get("id", "")

    transcript_path = data.get("transcript_path", "")
    real_model, real_ctx_size = detect_model_from_transcript(transcript_path)
    if real_model:
        model = real_model

    # Context window
    ctx = data.get("context_window", {})

    # Override context_window_size if transcript gave us the real one
    if real_ctx_size and real_ctx_size != ctx.get("context_window_size", 0):
        ctx = dict(ctx)  # don't mutate original
        old_size = ctx.get("context_window_size", 200_000)
        ctx["context_window_size"] = real_ctx_size
        # Recalculate percentage based on real context size
        usage = ctx.get("current_usage", {})
        input_tok = usage.get("input_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        total_tok = input_tok + cache_create + cache_read
        if real_ctx_size > 0 and total_tok > 0:
            ctx["used_percentage"] = round(total_tok / real_ctx_size * 100)

    ctx_pct = ctx.get("used_percentage")

    # Rate limits (Pro/Max only)
    rl = data.get("rate_limits", {})
    five_h = rl.get("five_hour", {})
    seven_d = rl.get("seven_day", {})
    five_pct = five_h.get("used_percentage")
    seven_pct = seven_d.get("used_percentage")

    def color_pct(pct, label):
        if pct is None:
            return f"{label}: ?"
        pct_round = round(pct)
        if pct >= 80:
            return f"\033[31m{label}: {pct_round}%\033[0m"
        elif pct >= 50:
            return f"\033[33m{label}: {pct_round}%\033[0m"
        else:
            return f"\033[32m{label}: {pct_round}%\033[0m"

    five_str = color_pct(five_pct, "5h")
    seven_str = color_pct(seven_pct, "7d")

    # Context: show absolute tokens + percentage
    def format_ctx(ctx):
        pct = ctx.get("used_percentage")
        size = ctx.get("context_window_size", 0)
        usage = ctx.get("current_usage", {})
        input_tok = usage.get("input_tokens", 0)
        cache_create = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        total_tok = input_tok + cache_create + cache_read

        def fmt_k(n):
            if n >= 1_000_000:
                return f"{n / 1_000_000:.1f}m"
            elif n >= 1_000:
                return f"{n / 1_000:.0f}k"
            return str(n)

        size_str = fmt_k(size) if size else "?"
        tok_str = fmt_k(total_tok) if total_tok else "?"
        pct_str = f" ({pct}%)" if pct is not None else ""
        label = f"{tok_str}/{size_str}{pct_str}"

        if pct is None:
            return f"ctx: {label}"
        if pct >= 80:
            return f"\033[31mctx: {label}\033[0m"
        elif pct >= 50:
            return f"\033[33mctx: {label}\033[0m"
        else:
            return f"\033[36mctx: {label}\033[0m"

    ctx_colored = format_ctx(ctx)

    # Profile detection
    profile = os.environ.get("CLAUDE_PROFILE", "")
    profile_str = f"[{profile}]" if profile else ""

    # Git branch
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2,
            cwd=data.get("cwd", ".")
        ).stdout.strip()
    except Exception:
        branch = ""

    # Session duration
    cost = data.get("cost", {})
    duration_ms = cost.get("total_duration_ms", 0)
    if duration_ms:
        mins = int(duration_ms / 60000)
        hrs = mins // 60
        mins = mins % 60
        dur_str = f"{hrs}h{mins:02d}m" if hrs else f"{mins}m"
    else:
        dur_str = ""

    # 200k warning
    over_200k = data.get("exceeds_200k_tokens", False)
    warn_str = "\033[31;1m!! >200k !!\033[0m" if over_200k else ""

    # Cost — current session + rolling weekly/monthly totals
    cost_usd = cost.get("total_cost_usd")
    cost_str = f"${cost_usd:.2f}" if cost_usd is not None else ""

    # Persist session cost to log for weekly/monthly tracking
    from datetime import datetime, timedelta
    cost_log_path = os.path.join(os.path.expanduser("~"), ".claude", "cost-log.json")
    week_total = 0
    month_total = 0
    try:
        cost_log = {}
        if os.path.exists(cost_log_path):
            with open(cost_log_path, "r", encoding="utf-8") as f:
                cost_log = json.load(f)

        session_id = data.get("session_id", "")
        today = datetime.now().strftime("%Y-%m-%d")

        # Update current session
        if session_id and cost_usd is not None:
            cost_log[session_id] = {"date": today, "cost": cost_usd}
            with open(cost_log_path, "w", encoding="utf-8") as f:
                json.dump(cost_log, f)

        # Sum weekly and monthly
        now = datetime.now()
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        for sid, entry in cost_log.items():
            d = entry.get("date", "")
            c = entry.get("cost", 0)
            if d >= week_ago:
                week_total += c
            if d >= month_ago:
                month_total += c
    except Exception:
        pass

    week_str = f"wk:${week_total:.0f}" if week_total > 0 else ""
    month_str = f"mo:${month_total:.0f}" if month_total > 0 else ""

    # Lines changed
    added = cost.get("total_lines_added", 0)
    removed = cost.get("total_lines_removed", 0)
    lines_str = ""
    if added or removed:
        lines_str = f"+{added}/-{removed}"

    # Build the line
    parts = [f"\033[1m{model}\033[0m"]
    if profile_str:
        parts.append(f"\033[35m{profile_str}\033[0m")
    if branch:
        parts.append(f"\033[34m{branch}\033[0m")
    parts.append(ctx_colored)
    if warn_str:
        parts.append(warn_str)
    parts.append(five_str)
    parts.append(seven_str)
    if dur_str:
        parts.append(dur_str)
    if cost_str:
        parts.append(cost_str)
    if week_str:
        parts.append(week_str)
    if month_str:
        parts.append(month_str)
    if lines_str:
        parts.append(lines_str)

    print(" | ".join(parts))


if __name__ == "__main__":
    main()
