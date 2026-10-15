# virt-manager on Apple Silicon macOS (native)

Unofficial packaging + verification work that runs **virt-manager natively on
Apple Silicon macOS** — arm64, Quartz GTK 3, no X11, no Rosetta.

Upstream virt-manager does not officially support macOS, but the app runs
natively on Apple Silicon today. This repo documents, scripts and *verifies*
that path end-to-end on real arm64 macOS GitHub Actions runners.

> **Status: v1.0.0 released** — the self-contained Mac app is published under
> [Releases](https://github.com/jakepi-bot/virt-manager-macos/releases), and CI
> on arm64 runners (macOS 15 + macOS 26) verifies all three paths: Homebrew
> packaged, upstream master from source, and the bundle launched **with
> Homebrew hidden** (no runtime dependency on it). Full evidence:
> [VERIFICATION.md](VERIFICATION.md).

## Download (prebuilt, nothing else needed)

**[Releases →](https://github.com/jakepi-bot/virt-manager-macos/releases/latest)** —
grab `virt-manager-macos-arm64.zip`: a self-contained `Virtual Machine
Manager.app` (arm64, macOS 15+), the whole GTK/Python stack inside the bundle.
Unzip, drag to /Applications, right-click → Open the first time (ad-hoc
signed, not notarized; see `README-FIRST.txt` inside the zip).

## Alternative: run it via Homebrew

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
bash scripts/install-deps-macos.sh       # installs the stack + requests, prints the interpreter
git clone https://github.com/virt-manager/virt-manager
(cd virt-manager && git apply ../patches/*.patch)
"$(brew --prefix)/bin/python3" virt-manager/virt-manager --connect test:///default
```

Note: upstream *master* currently crashes on macOS at import without the patch
in `patches/` (`locale.bindtextdomain` regression, added after v5.1.0 — see
[patches/README.md](patches/README.md)). The v5.1.0 release Homebrew ships is
not affected.

## What's in here

| Path | Purpose |
| --- | --- |
| `scripts/install-deps-macos.sh` | Homebrew deps needed to run master from a checkout; auto-selects a working python; installs `requests` |
| `scripts/check-bindings.py` | Reports which GI bindings are available (console backends, osinfo, …) |
| `scripts/smoke-test-macos.sh` | GUI launch smoke test (also used by CI): launches the app, asserts the main loop stays alive, scans log for crash signatures |
| `scripts/make-app-bundle.sh` | Builds a thin `.app` launcher for the Homebrew install |
| `scripts/macos-bundle.py` | Builds the **self-contained** `.app` (bundles Python, GTK and every dylib; no Homebrew at runtime) |
| `packaging/` | Files shipped inside the release zip (README-FIRST, NOTICE) + release notes |
| `patches/` | Patch applied to upstream master for macOS (see `patches/README.md`) |
| `.github/workflows/verify-macos.yml` | CI: `packaged` + `from-source` + self-contained-`.app` jobs on `macos-15` / `macos-26` arm64 runners, incl. REA Mach-O inspection; tag pushes publish the release |
| `Brewfile` | Same deps as `install-deps-macos.sh`, for `brew bundle` |

## Notes and known limits

- **What "native" means here:** every component is an arm64 Homebrew bottle
  (GTK 3 with its macOS Quartz backend, libvirt, libosinfo, VTE, gtk-vnc,
  spice-gtk, PyGObject). No X11, no Rosetta. The UI is GTK 3, not AppKit —
  this is as native as a real virt-manager gets on macOS.
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
- **Master-only regression:** `virtinst` added an unguarded
  `locale.bindtextdomain()` call (commit `d13271422`, after v5.1.0) that macOS
  CPython lacks; fixed by `patches/0001`.
- This repo is not affiliated with the virt-manager project. Upstream is
  GPL-2.0-or-later; the scripts here are provided as-is under the MIT license.
