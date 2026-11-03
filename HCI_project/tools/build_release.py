"""Build a portable Windows app and ZIP while preserving existing user records."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit("Build the Windows release on Windows.")
    staging = (ROOT / "build" / "package").resolve()
    staging.relative_to(ROOT.resolve())
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
        "--noupx", "--name", "OliveTable",
        "--distpath", str(staging), "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        "--collect-submodules", "bleak.backends.winrt",
        "--collect-submodules", "winrt", "--copy-metadata", "bleak",
        "--hidden-import", "webview.platforms.edgechromium",
        "--hidden-import", "webview.platforms.winforms",
        "--collect-data", "webview", "--copy-metadata", "pywebview",
        "--collect-all", "pythonnet", "--collect-data", "clr_loader",
        "--collect-data", "mediapipe", "--collect-binaries", "mediapipe",
        "--add-data", f"{ROOT / 'index.html'}:.",
        "--add-data", f"{ROOT / 'olive_table_with_gesture_sidebar.html'}:.",
        "--add-data", f"{ROOT / 'bluetooth_ui.js'}:.", "--add-data", f"{ROOT / 'bluetooth_ui.css'}:.",
        "--add-data", f"{ROOT / 'hand_ui.js'}:.", "--add-data", f"{ROOT / 'hand_ui.css'}:.",
        "--add-data", f"{ROOT / 'assets'}:assets",
        str(ROOT / "run_menu.py"),
    ], cwd=ROOT, check=True)

    destination = ROOT / "release" / "OliveTable"
    # Copy only the generated runtime, retaining any existing points dataset.
    shutil.copytree(staging / "OliveTable", destination, dirs_exist_ok=True)
    for name in ("START_HERE.txt", "BLUETOOTH_SETUP.md"):
        shutil.copy2(ROOT / name, destination / name)
    data = destination / "data"
    data.mkdir(exist_ok=True)
    (data / "KEEP_YOUR_POINTS.txt").write_text(
        "Your bluetooth_users.txt dataset is created here after the first successful connection.\n"
        "Keep it when updating the app to preserve users and points.\n", encoding="utf-8",
    )
    archive = ROOT / "release" / "OliveTable-Windows.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        # Archive only freshly built runtime files, never the user's release
        # folder (which can contain points, browser state, or other local data).
        for path in sorted((staging / "OliveTable").rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(staging / "OliveTable")
            package.write(path, Path("OliveTable") / relative)
        for name in ("START_HERE.txt", "BLUETOOTH_SETUP.md"):
            package.write(ROOT / name, Path("OliveTable") / name)
        package.write(data / "KEEP_YOUR_POINTS.txt", "OliveTable/data/KEEP_YOUR_POINTS.txt")
    print(json.dumps({"application": str(destination / "OliveTable.exe"),
                      "archive": str(archive), "archive_bytes": archive.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
