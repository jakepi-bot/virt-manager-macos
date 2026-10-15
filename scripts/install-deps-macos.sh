#!/usr/bin/env bash
# Install the Homebrew dependencies needed to run virt-manager (master) from a
# source checkout on Apple Silicon macOS, then locate a usable python.
#
# The component set mirrors Homebrew's own virt-manager formula.  It does NOT
# pin a python version: Homebrew migrates its pythons regularly, so the script
# installs the stack and then probes every Homebrew python for a working
# `gi` + `Gtk 3.0` + `libvirt` import, exporting the winner as $VM_PYTHON
# (also written to $GITHUB_ENV when running in GitHub Actions).
set -euo pipefail

command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
[ "$(uname -m)" = "arm64" ] || echo "WARNING: not Apple Silicon (uname -m=$(uname -m)) — arm64 is the supported target"

pkgs=(
  gtk+3                # GTK 3 GUI toolkit (Quartz backend on macOS)
  pygobject3           # Python GObject bindings (gi)
  py3cairo             # cairo bindings used by GTK drawing
  gtksourceview4       # XML editor syntax highlighting (GtkSource 4)
  vte3                 # serial/text console widget (Vte 2.91)
  gtk-vnc              # VNC display widget (GtkVnc 2.0)
  spice-gtk            # SPICE display client (SpiceClientGtk 3.0)
  libosinfo            # OS detection database (Libosinfo 1.0)
  osinfo-db            # the data for libosinfo
  libvirt-glib         # libvirt GLib integration (LibvirtGLib 1.0)
  libvirt-python       # python libvirt bindings
  adwaita-icon-theme   # icon theme
  cpio
)

echo "== installing: ${pkgs[*]}"
brew install "${pkgs[@]}"

GTK_TYPELIBS="$(brew --prefix)/lib/girepository-1.0"

probe() {  # $1 = python path; succeeds when gi + Gtk 3.0 + libvirt all import
  "$1" - <<'PYEOF' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: F401
import libvirt  # noqa: F401
PYEOF
}

candidates=()
for v in 3.10 3.11 3.12 3.13 3.14 3.15 3.16; do
  candidates+=("$(brew --prefix)/opt/python@$v/libexec/bin/python3")
  candidates+=("$(brew --prefix)/opt/python@$v/bin/python3.$v")
done
candidates+=("$(brew --prefix)/bin/python3")

FOUND=""
NEED_TYPELIBS=""
for py in "${candidates[@]}"; do
  [ -x "$py" ] || continue
  if probe "$py"; then
    FOUND="$py"; break
  elif GI_TYPELIB_PATH="$GTK_TYPELIBS" probe "$py"; then
    FOUND="$py"; NEED_TYPELIBS="$GTK_TYPELIBS"; break
  fi
done

if [ -z "$FOUND" ]; then
  echo "ERROR: no Homebrew python with gi + Gtk 3.0 + libvirt found."
  echo "Probe results:"
  for py in "${candidates[@]}"; do
    [ -x "$py" ] || continue
    echo "--- $py"
    "$py" -c 'import sys; print(sys.version)' 2>&1 || true
    "$py" -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk; print("gi+Gtk OK")' 2>&1 || true
    "$py" -c 'import libvirt; print("libvirt OK")' 2>&1 || true
  done
  exit 1
fi

# virt-manager's virtinst package imports `requests` at import time
# (virtinst.install.urlfetcher).  Homebrew's virt-manager formula ships
# requests inside its venv; when running from a checkout, install it into the
# selected interpreter so `import virtinst` works.
if ! "$FOUND" -m pip install --break-system-packages --quiet requests; then
  echo "system pip install failed; retrying with --user"
  "$FOUND" -m pip install --user --break-system-packages --quiet requests
fi
"$FOUND" -c 'import requests; print("requests", requests.__version__)'

if [ -n "$NEED_TYPELIBS" ]; then
  echo "note: this python needs GI_TYPELIB_PATH=$NEED_TYPELIBS (exporting)"
  export GI_TYPELIB_PATH="$NEED_TYPELIBS"
fi

echo "== selected python: $FOUND"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "VM_PYTHON=$FOUND" >> "$GITHUB_ENV"
  if [ -n "$NEED_TYPELIBS" ]; then
    echo "GI_TYPELIB_PATH=$NEED_TYPELIBS" >> "$GITHUB_ENV"
  fi
fi

echo
echo "Run virt-manager from a checkout with:"
echo "   $FOUND /path/to/virt-manager/virt-manager"
