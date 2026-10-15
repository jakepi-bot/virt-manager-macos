# patches/

Patches applied to upstream virt-manager in the `from-source` CI job — and by
anyone running upstream master from git on macOS.

| Patch | Why |
| --- | --- |
| `0001-macos-locale-bindtextdomain-guard.patch` | Guards `locale.bindtextdomain()` in `virtinst/__init__.py`. Upstream added this call in `d13271422` ("virtinst: fix locale when running in flatpak", after v5.1.0). It assumes the platform's python provides `locale.bindtextdomain` (libintl bindings); macOS CPython builds do not, so unpatched master raises `AttributeError` at import — before any window appears. The v5.1.0 release (what Homebrew ships) is **not** affected. |

Verified by CI run on arm64 macOS — see [../VERIFICATION.md](../VERIFICATION.md).
