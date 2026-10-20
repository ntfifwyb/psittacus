"""Build dist/psittacus-<version>-windows.ankiaddon: the add-on plus its engines' packages.

uv run --no-project scripts/build.py

The packages are resolved for Anki's bundled Python (3.13, 64-bit Windows), so this runs
from WSL or Linux too. Model files aren't included; the add-on downloads them on first use.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "addon"
PLATFORM = "x86_64-pc-windows-msvc"
# Command-line wrappers and test suites that some packages install next to their code.
PRUNE = {"bin", "__pycache__", "tests", "test"}


def main() -> None:
    version = json.loads((ADDON / "manifest.json").read_text())["human_version"]
    vendor = ROOT / "build" / "vendor"
    shutil.rmtree(vendor, ignore_errors=True)
    subprocess.run(
        ["uv", "pip", "install", "--quiet", "--target", str(vendor)]
        + ["--python-platform", PLATFORM, "--python-version", "3.13", "--no-compile"]
        + ["-r", str(ROOT / "requirements-addon.lock")],
        check=True,
    )
    for path in list(vendor.iterdir()):
        if path.name in PRUNE:
            shutil.rmtree(path)

    out = ROOT / "dist" / f"psittacus-{version}-windows.ankiaddon"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ADDON.rglob("*")):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and "user_files" not in path.parts
            ):
                z.write(path, path.relative_to(ADDON))
        for path in sorted(vendor.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                z.write(path, Path("vendor") / path.relative_to(vendor))
        z.writestr("user_files/README.txt", "Downloaded models and cached clips live here.\n")
    print(f"{out.relative_to(ROOT)}: {out.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
