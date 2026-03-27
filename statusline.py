"""Claude Code Statusline — real-time HUD for your terminal.

Shows model, git branch, context usage, rate limits, session duration,
and warns when you cross the 200k token threshold.

Install: curl -sL https://raw.githubusercontent.com/desaflow/claude-statusline/main/install.py | python3
"""
import json, sys, os, subprocess


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("? no data")
        return

    # Model
    model = data.get("model", {}).get("display_name", "?")

    # Context: show absolute tokens + percentage
    ctx = data.get("context_window", {})

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
            return f"\033[31m{label}: {pct_round}%\033[0m"  # red
        elif pct >= 50:
            return f"\033[33m{label}: {pct_round}%\033[0m"  # yellow
        else:
            return f"\033[32m{label}: {pct_round}%\033[0m"  # green

    five_str = color_pct(five_pct, "5h")
    seven_str = color_pct(seven_pct, "7d")

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

    # Cost (API-equivalent, informational)
    cost_usd = cost.get("total_cost_usd")
    cost_str = f"${cost_usd:.2f}" if cost_usd is not None else ""

    # Lines changed
    added = cost.get("total_lines_added", 0)
    removed = cost.get("total_lines_removed", 0)
    lines_str = ""
    if added or removed:
        lines_str = f"+{added}/-{removed}"

    # Build the line
    parts = [f"\033[1m{model}\033[0m"]
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
    if lines_str:
        parts.append(lines_str)

    print(" | ".join(parts))


if __name__ == "__main__":
    main()
