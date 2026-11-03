"""Check shipped assets, embedded controllers, runtime and preserved points."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {"passed": False}
    executable = ROOT/'release'/'OliveTable'/'OliveTable.exe'
    with zipfile.ZipFile(ROOT/'release'/'OliveTable-Windows.zip') as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert not any(name.endswith('bluetooth_users.txt') for name in names)
        for name in ('index.html','olive_table_with_gesture_sidebar.html','bluetooth_ui.js',
                     'bluetooth_ui.css','hand_ui.js','hand_ui.css'):
            content = (ROOT/name).read_bytes()
            assert archive.read('OliveTable/_internal/'+name) == content, name
            assert (executable.parent/'_internal'/name).read_bytes() == content, name
        report['assets_match_source'] = True
        report['zip_excludes_user_records'] = True
    embedded = CArchiveReader(str(executable)).open_embedded_archive('PYZ.pyz')
    for name in ('hand_input', 'link_health', 'bluetooth_connection', 'bluetooth_bridge', 'integrated_menu'):
        assert embedded.extract(name) is not None, name
    report['controllers_bundled'] = True
    bridge_code = embedded.extract('bluetooth_bridge')
    bridge_class = next(code for code in bridge_code.co_consts if getattr(code, 'co_name', None) == 'BluetoothBridge')
    assert any(getattr(code, 'co_name', None) == 'continue_as_guest' for code in bridge_class.co_consts)
    report['guest_api_bundled'] = True
    result = subprocess.run([str(executable),'--check'], capture_output=True, timeout=45)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    report['packaged_camera_model_loads'] = True
    backup = ROOT/'build'/'guest-update-backup'/'bluetooth_users.txt'
    if not backup.exists():
        backup = ROOT/'build'/'gesture-update-backup'/'bluetooth_users.txt'
    points = executable.parent/'data'/'bluetooth_users.txt'
    if backup.exists():
        assert hashlib.sha256(backup.read_bytes()).digest() == hashlib.sha256(points.read_bytes()).digest()
        report['saved_points_preserved'] = True
    report['passed'] = True
    (ROOT/'build'/'gesture-package-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
