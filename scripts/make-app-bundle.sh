#!/usr/bin/env bash
# Generate "Virtual Machine Manager.app" — a thin .app wrapper that launches
# the Homebrew-installed virt-manager natively on macOS (Quartz, arm64).
# No admin rights needed; the bundle is a launcher, not a copy of the stack.
#
# Usage: make-app-bundle.sh [output_dir]     (default: ~/Applications)
set -euo pipefail

OUT="${1:-$HOME/Applications}"
APP="$OUT/Virtual Machine Manager.app"

command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
VM_BIN="$(command -v virt-manager || true)"
if [ -z "$VM_BIN" ]; then
  echo "virt-manager not found. Install first:  brew install virt-manager"
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Virtual Machine Manager</string>
  <key>CFBundleDisplayName</key><string>Virtual Machine Manager</string>
  <key>CFBundleIdentifier</key><string>org.virt-manager.virtmanager.launcher</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleIconFile</key><string>virt-manager</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/launcher" <<EOF
#!/bin/bash
# Thin launcher for the Homebrew-provided virt-manager.
export PATH="$(brew --prefix)/bin:\$PATH"
# Quiet the macOS fork-safety abort for processes that fork after GTK/ObjC
# initialization (virt-manager forks for SSH console tunnels).
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY="\${OBJC_DISABLE_INITIALIZE_FORK_SAFETY:-YES}"
exec "$VM_BIN" --no-fork "\$@"
EOF
chmod +x "$APP/Contents/MacOS/launcher"

# Icon: convert the app's PNG to .icns if we can find it
ICON_SRC=""
for c in "$(brew --prefix)/share/icons/hicolor/256x256/apps/virt-manager.png" \
         "$(brew --prefix)/share/virt-manager/icons/256x256/apps/virt-manager.png"; do
  if [ -f "$c" ]; then ICON_SRC="$c"; break; fi
done

if [ -n "$ICON_SRC" ]; then
  TMPD="$(mktemp -d)"
  ICONSET="$TMPD/virt-manager.iconset"
  mkdir -p "$ICONSET"
  for s in 16 32 128 256 512; do
    sips -z "$s" "$s" "$ICON_SRC" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null 2>&1
    d=$((s * 2))
    sips -z "$d" "$d" "$ICON_SRC" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
  done
  if iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/virt-manager.icns" 2>/dev/null; then
    echo "icon: generated from $ICON_SRC"
  else
    echo "icon: iconutil failed; continuing without icon"
  fi
  rm -rf "$TMPD"
else
  echo "icon: virt-manager PNG not found; continuing without icon"
fi

echo "created: $APP"
echo "open with:  open \"$APP\"    (or drag it to /Applications)"
