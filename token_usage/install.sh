#!/usr/bin/env bash
# install.sh — sets up the Claude token monitor for iTerm2
set -e

SCRIPTS_DIR="$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch"
CACHE_DIR="$HOME/.cache"

echo "📦 Installing Claude Token Monitor..."

# 1. Create directories
mkdir -p "$SCRIPTS_DIR" "$CACHE_DIR"

# 2. Copy files (run from the directory containing this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/claude_proxy.py"        "$HOME/.local/bin/claude_proxy.py" 2>/dev/null || \
cp "$SCRIPT_DIR/claude_proxy.py"        "$HOME/claude_proxy.py"

cp "$SCRIPT_DIR/claude_token_monitor.py" "$SCRIPTS_DIR/claude_token_monitor.py"

echo "✅ Status bar script → $SCRIPTS_DIR/claude_token_monitor.py"

# 3. Create a launchd plist to auto-start the proxy on login
PLIST="$HOME/Library/LaunchAgents/com.anthropic.claude-proxy.plist"
PROXY_PATH="$(which python3)"
PROXY_SCRIPT="$HOME/claude_proxy.py"

# Prefer ~/.local/bin if it exists
[ -f "$HOME/.local/bin/claude_proxy.py" ] && PROXY_SCRIPT="$HOME/.local/bin/claude_proxy.py"

cat > "$PLIST" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.anthropic.claude-proxy</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PROXY_PATH</string>
    <string>$PROXY_SCRIPT</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$HOME/.cache/claude_proxy.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.cache/claude_proxy.log</string>
</dict>
</plist>
PLIST_EOF

echo "✅ LaunchAgent plist → $PLIST"

# 4. Load the proxy now
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load   "$PLIST"
echo "✅ Proxy started (port 4080)"

# 5. Print shell config instructions
SHELL_RC="$HOME/.zshrc"
[[ "$SHELL" == *bash* ]] && SHELL_RC="$HOME/.bash_profile"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👉 Add this to $SHELL_RC:"
echo ""
echo "   export ANTHROPIC_BASE_URL=http://localhost:4080"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Then in iTerm2:"
echo "  1. Scripts → AutoLaunch → claude_token_monitor.py  (first launch)"
echo "  2. Settings → Profiles → Session → Configure Status Bar"
echo "  3. Drag 'Claude Tokens' into the active components bar"
echo ""
echo "Done! 🎉"
