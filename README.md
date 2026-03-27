# claude-statusline

Real-time HUD for Claude Code. Shows what matters at a glance — right at the bottom of your terminal.

```
Opus 4.6 | main | ctx: 124k/1.0m (12%) | 5h: 34% | 7d: 8% | 1h22m | $1.23 | +473/-279
```

When things get heavy:
```
Opus 4.6 | main | ctx: 660k/1.0m (67%) | !! >200k !! | 5h: 85% | 7d: 41% | 3h00m | $8.45 | +890/-120
```

## What it shows

| Field | What it means |
|-------|--------------|
| **Model** | Which Claude model you're using (bold) |
| **Branch** | Current git branch (blue) |
| **Context** | Tokens used / max window size + percentage |
| **!! >200k !!** | Warning when you cross 200k tokens (things get expensive fast) |
| **5h** | 5-hour rolling rate limit usage (Pro/Max only) |
| **7d** | 7-day rate limit usage (Pro/Max only) |
| **Duration** | How long you've been in this session |
| **Cost** | API-equivalent cost of your session |
| **Lines** | Lines of code added/removed |

## Colors

- **Green** — under 50%, you're good
- **Yellow** — 50-80%, heads up
- **Red** — over 80%, slow down or checkpoint

## Install

**One command:**

```bash
curl -sL https://raw.githubusercontent.com/desaflow/claude-statusline/main/install.py | python3
```

**Or manually:**

1. Download `statusline.py` to `~/.claude/`
2. Add this to `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py",
    "padding": 2
  }
}
```
3. Restart Claude Code

## Requirements

- Claude Code (any version with statusline support)
- Python 3.6+
- That's it. No dependencies, no npm, no build step.

## Windows

Works on Windows — the installer auto-detects your Python path. If you installed Python via Miniconda/Anaconda, it'll find it.

## Uninstall

Delete `~/.claude/statusline.py` and remove the `"statusLine"` block from `~/.claude/settings.json`.

## License

MIT — do whatever you want with it.
