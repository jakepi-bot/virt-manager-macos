# Verification log

All results below come from GitHub Actions runs of
[`.github/workflows/verify-macos.yml`](.github/workflows/verify-macos.yml) on
GitHub-hosted **arm64 (Apple Silicon)** macOS runners. Evidence artifacts
(logs, binding matrices, REA reports) are attached to each run.

## Latest full run — 2026-10-15

**Run [#38763193718](https://github.com/jakepi-bot/virt-manager-macos/actions/runs/38763193718): 4/4 jobs green.**

| Job | OS | Result |
| --- | --- | --- |
| packaged (Homebrew) | macos-15 (Sequoia) | ✅ success |
| packaged (Homebrew) | macos-26 (Tahoe) | ✅ success |
| from-source master `bac5379` + `patches/0001` | macos-15 | ✅ success |
| from-source master `bac5379` + `patches/0001` | macos-26 | ✅ success |

### What that proves (evidence lines from the run's artifacts)

**Packaged (Homebrew) job** — `brew install virt-manager` (5.1.0, arm64 bottles throughout):

- `virt-manager --version` → `5.1.0`; `virt-install --version` → `5.1.0`
- GI binding matrix (formula venv python, Python 3.14.7) — **every binding OK**:

      OK Gtk 3.0 · Gdk 3.0 · GtkSource 4 · Vte 2.91 · GtkVnc 2.0 ·
      SpiceClientGtk 3.0 · Libosinfo 1.0 · LibvirtGLib 1.0 · libvirt-python 12.7.0

  → in-app serial console (VTE), VNC and SPICE consoles, XML-editor syntax
  highlighting and OS detection are all available on macOS.
- `virt-install --connect test:///default … --print-xml` → valid domain XML (virtinst works).
- GUI smoke 1 (manager window): `GTK version: 3.24.52`,
  `conn=test:///default changed to state=Active`, `Showing manager`,
  process alive at 20 s, no crash signatures.
- GUI smoke 2 (domain editor window): `Showing VM details: <vmmDomain name=test …>`, alive at 15 s.
- `.app` bundle: `scripts/make-app-bundle.sh` produced
  `Virtual Machine Manager.app` (executable launcher + `Info.plist` verified; icon via `sips`/`iconutil`).
- **REA** (`npx rea-agents@6.4.0 inspect-macho`, executed on the arm64 runner):
  - `libgtk-3.0.dylib` → `subject.architecture: arm64`, `format: mach-o`,
    37 load commands, 23 dylib dependencies (incl. the Quartz/AppKit/CoreGraphics stack)
  - `libvte-2.91.0.dylib` → arm64 Mach-O report
  - `libvirtmod_lxc.cpython-314-darwin.so` → arm64 Mach-O report
  - (REA refuses Mach-O analysis off-macOS: "Native macOS utilities require macOS" — hence it runs here.)

**From-source job** — upstream master `bac5379` (2026-09-04) + `patches/0001`:

- `scripts/install-deps-macos.sh` installed the full Homebrew component set,
  auto-selected a python with working `gi` + `Gtk 3.0` + `libvirt` (3.14.7),
  and installed `requests`.
- Binding matrix: all 9 bindings OK (same list as above).
- GUI smoke: `GTK version: 3.24.52`, `conn=test:///default changed to state=Active`,
  `Showing manager`, `SMOKE_RESULT: rc=0` — **upstream master runs natively on
  macOS Apple Silicon with `patches/0001` applied.**
- 0 crash signatures (`Traceback` / `Abort trap` / ObjC fork-safety abort)
  across **all 6** smoke logs of the run (both jobs × both OSes).

## Iteration history (what CI caught on the way)

| Run | Finding |
| --- | --- |
| [#38761347110](https://github.com/jakepi-bot/virt-manager-macos/actions/runs/38761347110) | packaged ✅; from-source failed on a stale Homebrew index (python pin + `HOMEBREW_NO_AUTO_UPDATE`) |
| [#38761930377](https://github.com/jakepi-bot/virt-manager-macos/actions/runs/38761930377) | packaged ✅ both OSes; from-source exposed the real master regression: `AttributeError: module 'locale' has no attribute 'bindtextdomain'` — upstream commit `d13271422` (after v5.1.0) |
| [#38762754031](https://github.com/jakepi-bot/virt-manager-macos/actions/runs/38762754031) | `patches/0001` applied; next blocker: `ModuleNotFoundError: No module named 'requests'` (virtinst imports it at load; the brew formula ships it in its venv) |
| [#38763193718](https://github.com/jakepi-bot/virt-manager-macos/actions/runs/38763193718) | **all green** |

## Known limitations (not covered by CI)

- `libguestfs` VM inspection unavailable on macOS (graceful: `python guestfs is not installed`).
- System tray icon unavailable (Ayatana AppIndicator absent; graceful: `Showing systray: False`).
- macOS has no KVM; the supported usage is remote administration of Linux hosts
  (`qemu+ssh://…`). Local VMs via libvirt + QEMU `hvf` exist but are untested here.
- The `.app` bundle is generated and structurally verified in CI; its
  double-click launch (`open`) and Gatekeeper behavior were not exercised in CI.
- "Native" means: arm64 everywhere, Quartz GTK, no X11, no Rosetta — the UI is
  GTK 3, not AppKit. There is no AppKit-native virt-manager; this is the
  closest a real virt-manager gets on macOS.
- The from-source route tracks upstream master at `UPSTREAM_SHA` (set in the
  workflow); master can regress again — rerun the workflow to check.
