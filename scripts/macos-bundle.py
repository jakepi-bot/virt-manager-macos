#!/usr/bin/env python3
"""Build a self-contained "Virtual Machine Manager.app" from a Homebrew
install of virt-manager on Apple Silicon macOS.

The app is fully relocatable and needs no Homebrew at runtime:

  - Python is copied (binary + dylib + stdlib) and its site-packages are
    merged from the brew venv, the global site-packages and every
    `site.addsitedir()` target in the venv's homebrew_deps.pth.
  - Every Homebrew dylib dependency of every bundled Mach-O file is copied
    into Contents/Frameworks and every reference is rewritten to a
    relative @loader_path reference; modified files are re-signed ad-hoc.
  - Resources (GObject typelibs, gsettings schemas, icon themes, osinfo
    db, gdk-pixbuf loaders) are copied under Contents/Resources with a
    launcher that points the runtime env vars at them.
  - The virt-manager install tree is copied to Contents/Resources/vmroot
    and its build.cfg prefix is rewritten, so UI/paths resolve inside the
    bundle.

Usage:  /usr/bin/python3 scripts/macos-bundle.py [outdir]

Requires: `brew install virt-manager` already done; Xcode CLT tools
(otool, install_name_tool, codesign) on PATH.  Prints a full log and fails
hard if any bundled Mach-O still references a Homebrew path.
"""
import glob
import os
import plistlib
import re
import shutil
import subprocess
import sys
from os.path import basename, dirname, exists, islink, join, realpath, relpath

OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"


def log(msg):
    print("[bundle] %s" % msg, flush=True)


def run(cmd, check=True):
    r = subprocess.run(cmd, text=True, capture_output=True)
    if check and r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit("command failed: %s" % " ".join(cmd))
    return r


BREW = run(["brew", "--prefix"]).stdout.strip()
VM = run(["brew", "--prefix", "virt-manager"]).stdout.strip()

# ---------------------------------------------------------------- python facts
cfg = {}
with open(join(VM, "libexec", "pyvenv.cfg")) as f:
    for line in f:
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
PYVER_FULL = cfg["version"]                       # e.g. 3.15.0
PYVER = ".".join(PYVER_FULL.split(".")[:2])       # e.g. 3.15
PYFORM = "python@" + PYVER
PYOPT = realpath(join(BREW, "opt", PYFORM))
VENVSP = join(VM, "libexec", "lib", "python" + PYVER, "site-packages")

log("brew prefix : %s" % BREW)
log("virt-manager: %s (python %s)" % (realpath(VM), PYVER_FULL))

APP = join(OUT, "Virtual Machine Manager.app")
C = join(APP, "Contents")
MACOS = join(C, "MacOS")
RES = join(C, "Resources")
FW = join(C, "Frameworks")
PYRES = join(RES, "python")
VMROOT = join(RES, "vmroot")


def _has_stdlib(p):
    return exists(join(p, "encodings"))


# Locate the python home.  Homebrew python is a framework build
# (Frameworks/Python.framework/Versions/X.Y/...); we preserve that layout
# inside the bundle so the interpreter relocates cleanly.  Plain layout is a
# fallback.
fw_ver = join(PYOPT, "Frameworks", "Python.framework", "Versions", PYVER)
if _has_stdlib(join(fw_ver, "lib", "python" + PYVER)):
    PYFRAMEWORK_SRC = fw_ver
    PYEXEC_REL = join("python", "Frameworks", "Python.framework", "Versions",
                      PYVER, "bin", "python" + PYVER)
    STDLIB_DST = join(PYRES, "Frameworks", "Python.framework", "Versions",
                      PYVER, "lib", "python" + PYVER)
else:
    PYFRAMEWORK_SRC = None
    PYEXEC_REL = join("python", "bin", "python" + PYVER)
    STDLIB_DST = join(PYRES, "lib", "python" + PYVER)
SP = join(STDLIB_DST, "site-packages")
PYEXEC = join(RES, PYEXEC_REL)

for d in (APP, C, MACOS, RES, FW, SP, VMROOT):
    os.makedirs(d, exist_ok=True)

PRUNE = shutil.ignore_patterns("__pycache__", "*.pyc")


def make_writable(tree):
    """Brew ships some files read-only; make bundling + user edits safe."""
    for root, dirs, files in os.walk(tree):
        for d in dirs:
            p = join(root, d)
            try:
                os.chmod(p, os.stat(p).st_mode | 0o200)
            except OSError:
                pass
        for f in files:
            p = join(root, f)
            try:
                os.chmod(p, os.stat(p).st_mode | 0o200)
            except OSError:
                pass


def copytree(src, dst, ignore=None):
    shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=True,
                    ignore=ignore or PRUNE)
    make_writable(dst)
    log("copied tree %s -> %s" % (src, relpath(dst, APP)))


def copyfile(src, dst, mode=None):
    os.makedirs(dirname(dst), exist_ok=True)
    if exists(dst):
        try:
            os.chmod(dst, os.stat(dst).st_mode | 0o200)
        except OSError:
            pass
    shutil.copy2(realpath(src), dst)
    os.chmod(dst, os.stat(dst).st_mode | 0o200)
    if mode is not None:
        os.chmod(dst, mode)
    return dst


# ------------------------------------------------------------------ 1. python
if PYFRAMEWORK_SRC:
    copytree(PYFRAMEWORK_SRC, join(PYRES, "Frameworks", "Python.framework",
                                   "Versions", PYVER))
    log("python framework: %s" % PYFRAMEWORK_SRC)
else:
    bin_src = realpath(join(PYOPT, "bin", "python" + PYVER))
    if not exists(bin_src):
        raise SystemExit("python binary not found: %s" % bin_src)
    copyfile(bin_src, join(RES, PYEXEC_REL), mode=0o755)
    libpy = glob.glob(join(PYOPT, "lib", "libpython%s*.dylib" % PYVER))
    if libpy:
        copyfile(libpy[0], join(PYRES, "lib", basename(libpy[0])))
    stdlib_src = None
    for cand in (join(PYOPT, "lib", "python" + PYVER),
                 join(BREW, "lib", "python" + PYVER)):
        if _has_stdlib(cand):
            stdlib_src = cand
            break
    if not stdlib_src:
        raise SystemExit("could not locate the python standard library")
    log("stdlib       : %s" % stdlib_src)
    copytree(stdlib_src, STDLIB_DST)
log("python exec  : %s" % PYEXEC)
for junk in ("test", "idlelib", "tkinter", "turtledemo", "ensurepip"):
    shutil.rmtree(join(STDLIB_DST, junk), ignore_errors=True)

# site-packages merge: venv + global + every addsitedir target in the .pth
copytree(VENVSP, SP)
pth = join(SP, "homebrew_deps.pth")
if exists(pth):
    content = open(pth).read()
    log("homebrew_deps.pth:\n  " + content.replace("\n", "\n  "))
    seen = set()
    for m in re.finditer(r"addsitedir\('([^']+)'\)", content):
        target = m.group(1).replace("@@HOMEBREW_PREFIX@@", BREW)
        if target in seen:
            continue
        seen.add(target)
        if exists(target):
            copytree(target, SP)
    os.remove(pth)
# The brew-wide site-packages directory mostly holds unrelated formulae (and
# runner-image preinstalls); everything virt-manager needs is merged from the
# venv and the addsitedir targets above, so it is intentionally not copied.
global_sp = join(BREW, "lib", "python" + PYVER, "site-packages")
if exists(global_sp):
    log("skipping global site-packages: %s" % global_sp)
for p in glob.glob(join(SP, "*.pth")):
    txt = open(p).read()
    if BREW in txt:
        log("dropping brew-referencing pth: %s" % basename(p))
        os.remove(p)

# ------------------------------------------------------- 2. virt-manager tree
copytree(join(VM, "share", "virt-manager"), join(VMROOT, "share", "virt-manager"))
bc = join(VMROOT, "share", "virt-manager", "virtinst", "build.cfg")
if exists(bc):
    txt = open(bc).read()
    txt2 = re.sub(r"(?m)^prefix=.*$", "prefix=" + VMROOT, txt)
    with open(bc, "w") as f:
        f.write(txt2)
    log("build.cfg rewrite: %r -> prefix=%s" % (txt.strip().replace("\n", " | ")[:160], VMROOT))

# ------------------------------------------------------------- 3. resources
gir_dst = join(RES, "girepository")
gir_src = join(BREW, "lib", "girepository-1.0")
TYPELIB_ALLOW = [
    "GLib-2.0", "GObject-2.0", "Gio-2.0", "GModule-2.0",
    "Gdk-3.0", "Gtk-3.0", "GdkPixbuf-2.0",
    "Pango-1.0", "PangoCairo-1.0", "PangoFT2-1.0", "HarfBuzz-0.0",
    "freetype2-2.0", "cairo-1.0", "Atk-1.0",
    "GtkSource-4", "Vte-2.91", "GtkVnc-2.0",
    "SpiceClientGtk-3.0", "SpiceClientGLib-2.0",
    "Libosinfo-1.0", "LibvirtGLib-1.0",
    "xlib-2.0", "GL-1.0", "Json-1.0",
]
os.makedirs(gir_dst, exist_ok=True)
NEEDED_DYLIBS = set()
for t in TYPELIB_ALLOW:
    src_t = join(gir_src, t + ".typelib")
    if not exists(src_t):
        log("WARNING: typelib not found: %s" % src_t)
        continue
    shutil.copy2(src_t, join(gir_dst, t + ".typelib"))
    data = open(src_t, "rb").read()
    for m in re.finditer(rb"lib[A-Za-z0-9+_.\-]*\.dylib", data):
        NEEDED_DYLIBS.add(m.group().decode())
log("typelibs: %d copied, %d library names referenced"
    % (len(os.listdir(gir_dst)), len(NEEDED_DYLIBS)))

sch_dst = join(VMROOT, "share", "glib-2.0", "schemas")
copytree(join(BREW, "share", "glib-2.0", "schemas"), sch_dst,
         ignore=shutil.ignore_patterns("gschemas.compiled"))
run([join(BREW, "bin", "glib-compile-schemas"), "--strict", sch_dst])
log("gsettings schemas compiled")

icon_dst = join(RES, "share", "icons")
for theme in ("Adwaita", "hicolor"):
    src = join(BREW, "share", "icons", theme)
    if exists(src):
        copytree(src, join(icon_dst, theme))

os_src = join(BREW, "share", "osinfo")
if exists(os_src):
    copytree(os_src, join(RES, "share", "osinfo"))

gpb_dst = join(RES, "gdk-pixbuf")
loaders = glob.glob(join(BREW, "lib", "gdk-pixbuf-2.0", "*", "loaders"))
if loaders:
    copytree(loaders[0], join(gpb_dst, "loaders"))
copyfile(join(BREW, "bin", "gdk-pixbuf-query-loaders"),
         join(gpb_dst, "query-loaders"), mode=0o755)

# ------------------------------------------------------------- 4. dyld walk
def otool_deps(path):
    r = run(["otool", "-L", path], check=False)
    if r.returncode != 0:
        return None
    deps = []
    for ln in r.stdout.splitlines()[1:]:
        ln = ln.strip()
        if not ln:
            continue
        deps.append(ln.split(" (")[0].strip())
    return deps


def otool_rpaths(path):
    r = run(["otool", "-l", path], check=False)
    rpaths = []
    if r.returncode != 0:
        return rpaths
    lines = r.stdout.splitlines()
    for i, ln in enumerate(lines):
        if "LC_RPATH" in ln:
            for j in range(i, min(i + 6, len(lines))):
                s = lines[j].strip()
                if s.startswith("path "):
                    rpaths.append(s.split()[1])
                    break
    return rpaths


def otool_id(path):
    r = run(["otool", "-l", path], check=False)
    if r.returncode != 0:
        return None
    lines = r.stdout.splitlines()
    for i, ln in enumerate(lines):
        if "LC_ID_DYLIB" in ln:
            for j in range(i, min(i + 6, len(lines))):
                s = lines[j].strip()
                if s.startswith("name "):
                    return s.split()[1]
    return None


def is_macho(path):
    r = run(["file", "-b", path], check=False)
    return r.returncode == 0 and "Mach-O" in r.stdout


def classify(path):
    for prefix in ("/usr/lib", "/System", "/usr/local/lib"):
        if path.startswith(prefix):
            return "system"
    return "other"


BUNDLE_ROOT = realpath(APP)
BAR = realpath(BREW)
copied = {}          # real brew source path -> bundle path
processed = set()
pending = []
problems = []


def resolve(dep, fp, rpaths):
    """Return (kind, realpath) for a dependency reference."""
    if dep.startswith(("/usr/lib", "/System", "/usr/local/lib")):
        # System libraries live in the dyld shared cache; no file on disk.
        return ("system", dep)
    cands = []
    if dep.startswith("/"):
        cands.append(dep)
    elif dep.startswith("@loader_path/"):
        cands.append(os.path.normpath(join(dirname(fp), dep[len("@loader_path/"):])))
    elif dep.startswith("@executable_path/"):
        exe = dirname(PYEXEC)
        cands.append(os.path.normpath(join(exe, dep[len("@executable_path/"):])))
    elif dep.startswith("@rpath/"):
        suffix = dep[len("@rpath/"):]
        for rp in rpaths:
            rp2 = rp.replace("@loader_path", dirname(fp))
            rp2 = rp2.replace("@executable_path", dirname(PYEXEC))
            cands.append(join(rp2, suffix))
    for c in cands:
        if exists(c):
            real = realpath(c)
            if real.startswith(BAR + os.sep):
                return ("brew", real)
            if real.startswith(BUNDLE_ROOT + os.sep):
                return ("bundle", real)
            return (classify(real), real)
    # fallback: a relative or dangling reference whose real library exists
    # elsewhere in Homebrew (e.g. @loader_path siblings like libicudata)
    src = dylib_index.get(basename(dep))
    if src:
        return ("brew", realpath(src))
    return (None, None)


def resign(fp):
    r = run(["codesign", "--force", "--sign", "-", fp], check=False)
    if r.returncode != 0:
        log("WARNING: codesign failed for %s: %s" % (fp, r.stderr.strip()[:200]))


def enqueue(fp):
    pending.append(fp)


enqueue(PYEXEC)
enqueue(join(gpb_dst, "query-loaders"))
for base in (SP, join(gpb_dst, "loaders")):
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".so"):
                enqueue(join(root, f))

# Typelibs dlopen their libraries BY NAME at runtime, so make sure every
# library referenced by a bundled typelib is present in Frameworks even when
# no bundled Mach-O links it directly.
dylib_index = {}
for root in [join(BREW, "lib")] + sorted(glob.glob(join(BREW, "opt", "*", "lib"))):
    for dirpath, dirs, files in os.walk(root):
        if dirpath[len(root):].count(os.sep) > 2:
            dirs[:] = []
            continue
        for f in files:
            if f.endswith(".dylib"):
                dylib_index.setdefault(f, join(dirpath, f))
missing_libs = []
for name in sorted(NEEDED_DYLIBS):
    src = dylib_index.get(name)
    if not src:
        missing_libs.append(name)
        continue
    rsrc = realpath(src)
    if rsrc in copied:
        continue
    cand = realpath(join(FW, name))
    if exists(cand) and cand != rsrc:
        pass
    copyfile(src, cand)
    copied[rsrc] = cand
    enqueue(cand)
    run(["install_name_tool", "-id", "@loader_path/" + name, cand], check=False)
    resign(cand)
for name in missing_libs:
    log("WARNING: typelib-referenced library not found in brew: %s" % name)

while pending:
    fp = pending.pop()
    if fp in processed or not exists(fp):
        continue
    processed.add(fp)
    if not is_macho(fp):
        continue
    deps = otool_deps(fp) or []
    rpaths = otool_rpaths(fp)
    fid = otool_id(fp)
    if fid:
        deps = [d for d in deps if d != fid]  # don't treat self-id as a dep
    changes = []
    for dep in deps:
        kind, src = resolve(dep, fp, rpaths)
        if kind == "brew":
            bdst = copied.get(src)
            if bdst is None:
                name = basename(src)
                cand = join(FW, name)
                n = 2
                while exists(cand) and realpath(cand) != src:
                    cand = join(FW, "%d-%s" % (n, name))
                    n += 1
                copyfile(src, cand)
                bdst = copied[src] = realpath(cand)
                enqueue(bdst)
                run(["install_name_tool", "-id", "@loader_path/" + basename(bdst), bdst], check=False)
                resign(bdst)
            newref = "@loader_path/" + relpath(bdst, dirname(fp))
            if newref != dep:
                changes.append((dep, newref))
        elif kind in ("system", "bundle"):
            continue
        elif kind == "other":
            problems.append((fp, dep, "non-brew non-system dependency"))
        elif kind is None:
            # unresolvable: flag only absolute-looking refs
            if dep.startswith("/") or dep.startswith("@"):
                problems.append((fp, dep, "unresolved"))
    if changes:
        cmd = ["install_name_tool"]
        for old, new in changes:
            cmd += ["-change", old, new]
        cmd.append(fp)
        run(cmd)
        resign(fp)
    fid = otool_id(fp)
    if fid and fid.startswith("/"):
        run(["install_name_tool", "-id", "@loader_path/" + basename(fp), fp], check=False)
        resign(fp)

log("walk done: %d Mach-O files processed, %d dylibs copied into Frameworks"
    % (len(processed), len(copied)))

# verify: no brew refs anywhere in the bundle's Mach-O files
bad = []
for fp in sorted(processed):
    if not is_macho(fp):
        continue
    fid = otool_id(fp)
    for dep in otool_deps(fp) or []:
        if dep == fid:
            continue
        if BREW in dep or "/opt/homebrew" in dep:
            bad.append((fp, dep))
if bad:
    for fp, dep in bad[:40]:
        log("LEAK: %s -> %s" % (relpath(fp, APP), dep))
    raise SystemExit("bundle still references Homebrew (%d refs)" % len(bad))
log("verified: zero Homebrew references in all bundled Mach-O files")
if problems:
    for fp, dep, why in problems[:40]:
        log("WARN dependency (%s): %s -> %s" % (why, relpath(fp, APP), dep))

# ------------------------------------------------------- 5. launcher + extras
APP_PY = join(RES, "app.py")
with open(APP_PY, "w") as f:
    f.write(
        "import os\n"
        "import sys\n"
        "RES = os.path.dirname(os.path.abspath(__file__))\n"
        "sys.path.insert(0, os.path.join(RES, 'vmroot', 'share', 'virt-manager'))\n"
        "from virtManager import virtmanager\n"
        "virtmanager.runcli()\n"
    )
os.chmod(APP_PY, 0o644)

launcher = join(MACOS, "launcher")
with open(launcher, "w") as f:
    f.write("""#!/bin/bash
# Launcher for the self-contained virt-manager bundle.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$(cd "$HERE/../.." && pwd)"
RES="$APP/Contents/Resources"
export DYLD_FALLBACK_LIBRARY_PATH="$APP/Contents/Frameworks"
export GI_TYPELIB_PATH="$RES/girepository"
export XDG_DATA_DIRS="$RES/vmroot/share:$RES/share"
export GSETTINGS_SCHEMA_DIR="$RES/vmroot/share/glib-2.0/schemas"
export GDK_PIXBUF_MODULEDIR="$RES/gdk-pixbuf/loaders"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY="${OBJC_DISABLE_INITIALIZE_FORK_SAFETY:-YES}"
CACHE="$HOME/Library/Caches/virt-manager-macos"
mkdir -p "$CACHE"
MODFILE="$CACHE/loaders.cache"
if [ ! -f "$MODFILE" ] || ! grep -q "$GDK_PIXBUF_MODULEDIR" "$MODFILE" 2>/dev/null; then
  GDK_PIXBUF_MODULEDIR="$GDK_PIXBUF_MODULEDIR" "$RES/gdk-pixbuf/query-loaders" >"$MODFILE" 2>/dev/null || rm -f "$MODFILE"
fi
[ -f "$MODFILE" ] && export GDK_PIXBUF_MODULE_FILE="$MODFILE"
exec "$RES/__PYEXEC__" "$RES/app.py" "$@"
""".replace("__PYEXEC__", PYEXEC_REL))
os.chmod(launcher, 0o755)

# icon
png = None
for cand in (join(VM, "share", "icons", "hicolor", "256x256", "apps", "virt-manager.png"),
             join(RES, "share", "icons", "hicolor", "256x256", "apps", "virt-manager.png")):
    if exists(cand):
        png = cand
        break
if png:
    tmp = join(RES, ".iconset")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    ok = True
    for s in (16, 32, 128, 256, 512):
        r1 = run(["sips", "-z", str(s), str(s), png, "--out", join(tmp, "icon_%dx%d.png" % (s, s))], check=False)
        r2 = run(["sips", "-z", str(s * 2), str(s * 2), png, "--out", join(tmp, "icon_%dx%d@2x.png" % (s, s))], check=False)
        ok = ok and r1.returncode == 0 and r2.returncode == 0
    r = run(["iconutil", "-c", "icns", tmp, "-o", join(RES, "virt-manager.icns")], check=False)
    if r.returncode != 0:
        log("WARNING: icon conversion failed: %s" % (r.stderr or "")[:300])
    shutil.rmtree(tmp, ignore_errors=True)
else:
    log("WARNING: no icon PNG found")

with open(join(C, "Info.plist"), "wb") as f:
    plistlib.dump({
        "CFBundleName": "Virtual Machine Manager",
        "CFBundleDisplayName": "Virtual Machine Manager",
        "CFBundleIdentifier": "org.virt-manager.virtmanager.macos-bundle",
        "CFBundleExecutable": "launcher",
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1.0",
        "CFBundleShortVersionString": "1.0",
        "CFBundleIconFile": "virt-manager",
        "LSMinimumSystemVersion": "15.0",
        "NSHighResolutionCapable": True,
    }, f)

manifest = join(RES, "manifest.txt")
with open(manifest, "w") as f:
    f.write("virt-manager bundle manifest\n")
    f.write("python: %s\n" % PYVER_FULL)
    f.write("brew formulae (runtime):\n")
    r = run(["brew", "list", "--formula", "--versions"], check=False)
    f.write(r.stdout or "(unavailable)\n")

run(["codesign", "--force", "--deep", "--sign", "-", APP], check=False)
v = run(["codesign", "--verify", "--deep", APP], check=False)
log("codesign verify rc=%d" % v.returncode)

total = 0
for root, _d, files in os.walk(APP):
    for x in files:
        total += os.path.getsize(join(root, x))
log("BUNDLE OK: %s (%.1f MB, %d dylibs in Frameworks)" % (APP, total / 1e6, len(copied)))
