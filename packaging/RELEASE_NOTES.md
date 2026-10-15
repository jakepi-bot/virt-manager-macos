# Prebuilt app (draft notes; the release body is generated from this file)

**Self-contained virt-manager for Apple Silicon Macs** — the whole GTK/Python
stack lives inside the `.app`; no Homebrew, no X11, no Rosetta required.

## Requirements

- Apple Silicon (M1+), macOS 15 Sequoia or newer

## Install

1. Download `virt-manager-macos-arm64-*.zip` below and unzip it.
2. Drag **Virtual Machine Manager.app** to /Applications (or anywhere).
3. First launch: right-click → **Open** (the app is ad-hoc signed, not
   notarized). Or: `xattr -dr com.apple.quarantine "/Applications/Virtual Machine Manager.app"`

## Use

macOS has no KVM — connect to a Linux hypervisor running libvirt:

```
qemu+ssh://youruser@your-hypervisor/system
```

## What's inside

virt-manager 5.1.0 + Python 3.15, GTK 3 (Quartz), GtkSourceView4, VTE,
gtk-vnc, spice-gtk, libosinfo, libvirt(-glib/-python), requests — arm64
binaries from Homebrew bottles, re-linked to run from inside the bundle.

SHA-256 checksums for the archives are attached (`SHA256SUMS.txt`).

Build + verification: see the repository README and `VERIFICATION.md`.
Unofficial build; virt-manager itself is GPL-2.0-or-later (see `NOTICE.txt`
inside the archive).
