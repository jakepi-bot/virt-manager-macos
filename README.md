# virt-manager on Apple Silicon macOS (native)

Unofficial packaging + verification work that runs **virt-manager natively on
Apple Silicon macOS** — arm64, Quartz GTK 3, no X11, no Rosetta.

Upstream virt-manager does not officially support macOS, but the app runs
natively on Apple Silicon today. This repo documents, scripts and *verifies*
that path end-to-end on real arm64 macOS GitHub Actions runners.

> **Status: see [VERIFICATION.md](VERIFICATION.md)** for the CI evidence
> (macOS 15 Sequoia + macOS 26 Tahoe, arm64).

## Quick start (Homebrew, recommended)

```sh
brew install virt-manager
virt-manager --connect qemu+ssh://you@your-hypervisor/system
```

Homebrew ships a maintained [virt-manager formula](https://formulae.brew.sh/formula/virt-manager)
(5.1.0 with backported upstream patches, arm64 bottles for the whole GTK stack).

Optional — wrap it in a proper app bundle (Launchpad/Spotlight-friendly):

```sh
bash scripts/make-app-bundle.sh          # creates ~/Applications/Virtual Machine Manager.app
```

## From source (upstream master)

```sh
bash scripts/install-deps-macos.sh
git clone https://github.com/virt-manager/virt-manager
"$(brew --prefix)/bin/python3" virt-manager/virt-manager --connect test:///default
```

## What's in here

| Path | Purpose |
| --- | --- |
| `scripts/install-deps-macos.sh` | Homebrew deps needed to run master from a checkout |
| `scripts/check-bindings.py` | Reports which GI bindings are available (console backends, osinfo, …) |
| `scripts/smoke-test-macos.sh` | GUI launch smoke test (also used by CI): launches the app, asserts the main loop stays alive, scans log for crash signatures |
| `scripts/make-app-bundle.sh` | Builds a thin `.app` launcher for the Homebrew install |
| `.github/workflows/verify-macos.yml` | CI: `packaged` + `from-source` jobs on `macos-15` / `macos-26` arm64 runners |
| `Brewfile` | Same deps as `install-deps-macos.sh`, for `brew bundle` |

## Notes and known limits

- **What "native" means here:** every component is an arm64 Homebrew bottle
  (GTK 3 with its macOS Quartz backend, libvirt, libosinfo, VTE, gtk-vnc,
  spice-gtk, PyGObject). No X11, no Rosetta.
- **Manage remote Linux hosts.** macOS has no KVM; the primary use is remote
  administration of Linux boxes via `qemu+ssh://…`. Local VMs are possible via
  libvirt + QEMU's `hvf` accelerator (see <https://libvirt.org/macos.html>),
  but that's outside this repo's scope.
- **libguestfs VM inspection** is unavailable on macOS (the feature degrades).
- **System tray icon** is unavailable (requires Ayatana AppIndicator; degrades).
- **Historical macOS crash (virt-manager ≤ 4.x / issue #620):** fixed upstream
  by defaulting to `--no-fork` (commit `408a39a77`, included in v5.1.0). The
  `.app` launcher additionally sets `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`
  for the remaining fork sites (SSH console tunnels).
- This repo is not affiliated with the virt-manager project. Upstream is
  GPL-2.0-or-later; the scripts here are provided as-is under the MIT license.
