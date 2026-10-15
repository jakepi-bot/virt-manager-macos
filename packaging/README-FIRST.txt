Virtual Machine Manager — macOS (Apple Silicon) — README FIRST
==============================================================

This is an unofficial, self-contained build of virt-manager for Apple
Silicon Macs. Everything it needs is inside the app bundle — no Homebrew,
no X11, no Rosetta.

REQUIREMENTS
------------
- Apple Silicon Mac (M1 or later)
- macOS 15 (Sequoia) or newer

INSTALL
-------
1.  Unzip this archive.
2.  Drag "Virtual Machine Manager.app" into /Applications (or anywhere you
    like — the app is relocatable).
3.  First launch: right-click the app -> Open -> Open.
    (The app is ad-hoc signed, not notarized, so Gatekeeper asks once.)
    Alternatively, in Terminal:
       xattr -dr com.apple.quarantine "/Applications/Virtual Machine Manager.app"
    then double-click it.

USING IT
--------
macOS has no KVM, so virt-manager here is a *remote administration* client.
Connect to a Linux hypervisor running libvirt, e.g.:

    qemu+ssh://youruser@your-hypervisor/system

(File -> Add Connection…, or pass --connect on the command line.) The app
stores connections between runs. SSH key auth is recommended.

WHAT'S INSIDE
-------------
- virt-manager 5.1.0 (https://virt-manager.org, GPL-2.0-or-later)
- Python 3.15 runtime, PyGObject, libvirt-python, requests
- GTK 3 (Quartz) stack, GtkSourceView, VTE, gtk-vnc, spice-gtk, libosinfo,
  libvirt, libvirt-glib and all their dependencies — copied out of Homebrew
  arm64 bottles and re-linked to live inside the bundle.

KNOWN LIMITS
------------
- libguestfs VM inspection is unavailable; the feature degrades.
- The system tray icon is unavailable (needs Ayatani AppIndicator).
- The UI is GTK, not AppKit — that is what virt-manager is.
- Unsigned/unnotarized: Gatekeeper will warn on first launch (see above).

UNINSTALL
---------
Delete the .app. It keeps settings in ~/Library/Preferences (org.virt-manager)
and caches in ~/Library/Caches; remove those too for a clean slate.

BUILT BY
--------
https://github.com/jakepi-bot/virt-manager-macos — build scripts, patch
sources and CI verification for this bundle live there.
