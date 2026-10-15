#!/usr/bin/env python3
"""Print availability of every GObject-Introspection binding virt-manager uses.

Run with the same python that will run virt-manager (Homebrew python on macOS).
Exit code is 0 even if bindings are missing — this is an evidence report, and
the caller decides what is fatal.  Expected on a full Homebrew install:
everything OK except possibly SpiceClientGtk / GtkVnc depending on build flags
(those two are optional in virt-manager and degrade gracefully).

Observed behavior changes the availability of the GUI's console widgets:
  Vte          -> in-app serial/text console tab
  GtkVnc       -> in-app VNC console tab
  SpiceClientGtk -> in-app SPICE console tab
  GtkSource    -> XML editor syntax highlighting
  Libosinfo    -> OS detection in the create-VM wizard
  LibvirtGLib  -> libvirt event loop integration
"""
import sys

checks = [
    ("Gtk", "3.0"),
    ("Gdk", "3.0"),
    ("GtkSource", "4"),
    ("Vte", "2.91"),
    ("GtkVnc", "2.0"),
    ("SpiceClientGtk", "3.0"),
    ("Libosinfo", "1.0"),
    ("LibvirtGLib", "1.0"),
]

print("python:", sys.version.replace("\n", " "))
print("executable:", sys.executable)

try:
    import gi
    print("pygobject:", gi.__version__)
except Exception as e:  # pragma: no cover
    print("pygobject: MISSING :: %s: %s" % (type(e).__name__, e))
    sys.exit(0)

import gi.repository  # noqa: E402

for ns, ver in checks:
    try:
        gi.require_version(ns, ver)
        getattr(gi.repository, ns)
        print("OK      %s %s" % (ns, ver))
    except Exception as e:
        print("MISSING %s %s :: %s: %s" % (ns, ver, type(e).__name__, e))

try:
    import libvirt
    print("OK      libvirt-python :: %s" % libvirt.getVersion())
except Exception as e:
    print("MISSING libvirt-python :: %s: %s" % (type(e).__name__, e))
