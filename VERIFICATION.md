# Verification log

Evidence from CI: `.github/workflows/verify-macos.yml` (GitHub Actions, arm64
Apple Silicon runners). Each artifact listed is attached to the corresponding
workflow run (Actions → run → Artifacts).

| Job | OS (arm64) | Result | Run |
| --- | --- | --- | --- |
| packaged (Homebrew) | macos-15 (Sequoia) | _pending_ | |
| packaged (Homebrew) | macos-26 (Tahoe) | _pending_ | |
| from-source master `bac5379` | macos-15 (Sequoia) | _pending_ | |
| from-source master `bac5379` | macos-26 (Tahoe) | _pending_ | |

Per-run artifacts:

- `binding-matrix.txt` — which GI bindings are actually available (Gtk, GtkSource,
  Vte, GtkVnc, SpiceClientGtk, Libosinfo, LibvirtGLib, libvirt-python)
- `smoke.log` — `--debug` output of the GUI launch smoke test
- `guest.xml` — `virt-install` test-driver smoke output (packaged job)
- `rea-*.txt` — REA CLI `inspect-macho` output for native stack components
  (libgtk-3, libvte, libvirtmod)
