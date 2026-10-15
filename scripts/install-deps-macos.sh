#!/usr/bin/env bash
# Install the Homebrew dependencies needed to run virt-manager from a source
# checkout on Apple Silicon macOS (arm64, Quartz — no X11).
#
# These are the same components Homebrew's own `virt-manager` formula depends
# on, so `brew install virt-manager` remains the simpler option; use this
# script when you want to run upstream master from git.
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
  python@3.15          # python runtime the brew bindings are built against
  cpio                 # used by virt-manager's formula deps
)

echo "== installing: ${pkgs[*]}"
brew install "${pkgs[@]}"

echo
echo "== done. Use this interpreter to run virt-manager from a checkout:"
echo "   $(brew --prefix)/bin/python3"
