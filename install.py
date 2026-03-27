"""One-command installer for claude-statusline.

Usage:
  curl -sL https://raw.githubusercontent.com/desaflow/claude-statusline/main/install.py | python3

What it does:
  1. Downloads statusline.py to ~/.claude/
  2. Adds the statusLine config to ~/.claude/settings.json
  3. Done. Restart Claude Code to see it.
"""
import json, os, sys, urllib.request, shutil

SCRIPT_URL = "https://raw.githubusercontent.com/desaflow/claude-statusline/main/statusline.py"
CLAUDE_DIR = os.path.expanduser("~/.claude")
SCRIPT_PATH = os.path.join(CLAUDE_DIR, "statusline.py")
SETTINGS_PATH = os.path.join(CLAUDE_DIR, "settings.json")


def main():
    # Ensure ~/.claude/ exists
    os.makedirs(CLAUDE_DIR, exist_ok=True)

    # Download statusline.py
    print("Downloading statusline.py...")
    try:
        urllib.request.urlretrieve(SCRIPT_URL, SCRIPT_PATH)
    except Exception as e:
        # If running from pipe, the script is local — copy from same dir
        print(f"Download failed ({e}), checking local...")
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "statusline.py")
        if os.path.exists(local):
            shutil.copy2(local, SCRIPT_PATH)
        else:
            print("ERROR: Could not find statusline.py")
            sys.exit(1)
    print(f"  Saved to {SCRIPT_PATH}")

    # Detect python path
    python_path = sys.executable.replace("\\", "/")

    # Read or create settings.json
    settings = {}
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                print(f"WARNING: {SETTINGS_PATH} has invalid JSON, creating backup...")
                shutil.copy2(SETTINGS_PATH, SETTINGS_PATH + ".bak")
                settings = {}

    # Check if statusLine already configured
    if "statusLine" in settings:
        print(f"  statusLine already configured in settings.json — updating...")

    # Add statusLine config
    script_path_unix = SCRIPT_PATH.replace("\\", "/")
    settings["statusLine"] = {
        "type": "command",
        "command": f"{python_path} {script_path_unix}",
        "padding": 2
    }

    # Write settings.json
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    print(f"  Updated {SETTINGS_PATH}")

    print()
    print("Done! Restart Claude Code to see your statusline.")
    print()
    print("What you'll see:")
    print("  Model | branch | ctx: 124k/1.0m (12%) | 5h: 34% | 7d: 8% | 1h22m | $1.23 | +473/-279")
    print()
    print("Colors: green (<50%) | yellow (50-80%) | red (>80%)")
    print("Red '!! >200k !!' warning when tokens exceed 200k threshold.")


if __name__ == "__main__":
    main()
