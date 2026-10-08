"""Validate the shipped recording in a fresh extraction with no site packages."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def check_extracted(root):
    sys.path.insert(0, str(root))
    from scripts.package_business_demo import server, verify
    initial = verify(root)
    api = server(root, 0)
    worker = threading.Thread(target=api.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{api.server_port}'
    try:
        with urlopen(base, timeout=10) as response:
            assert response.status == 200 and b'<html' in response.read().lower()
        with urlopen(base + '/api/workspace', timeout=10) as response:
            packet = json.load(response)
        assert packet['demo']['status'] == 'completed'
        case = packet['cases'][0]
        body = {'expected_revision': (case.get('review') or {}).get('revision', 0),
                'expected_source_sha256': case['evidence']['sha256'], 'decision': 'follow_up',
                'reason': 'Fresh extracted-package validation'}
        request = Request(base + f"/api/cases/{case['id']}/decision", data=json.dumps(body).encode(),
                          method='PUT', headers={'Content-Type': 'application/json', 'Origin': base})
        with urlopen(request, timeout=10) as response:
            saved = json.load(response)
        assert saved['review']['revision'] == body['expected_revision'] + 1
        with urlopen(base + '/api/workspace', timeout=10) as response:
            reloaded = json.load(response)
        assert next(row for row in reloaded['cases'] if row['id'] == case['id'])['review'] == saved['review']
        assert verify(root) == initial
        return {'status': 'passed', 'files': len(initial['files']), 'new_provider_calls': 0}
    finally:
        api.shutdown()
        api.server_close()
        worker.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', type=Path)
    parser.add_argument('--write-receipt', action='store_true')
    args = parser.parse_args()
    if args.package_root:
        print(json.dumps(check_extracted(args.package_root)))
        return
    directory = ROOT / 'docs/demo/Packages'
    package = json.loads((directory / 'PackageReceipt.json').read_text())
    archive = directory / package['archive']
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == package['archive_sha256'], 'Archive differs from its package receipt'
    with tempfile.TemporaryDirectory(prefix='BackIntelRecordedCheck') as temporary:
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                (Path(temporary) / name).resolve().relative_to(Path(temporary).resolve())
            zipped.extractall(temporary)
        root = Path(temporary) / 'BackIntelDemo'
        check = subprocess.run([sys.executable, '-B', '-S', 'RunDemo.py', '--check'], cwd=root,
                               check=True, capture_output=True, text=True, timeout=20)
        initial = json.loads(check.stdout)
        playback = subprocess.run([sys.executable, '-B', '-S', str(Path(__file__).resolve()), '--package-root', str(root)],
                                  cwd=root, check=True, capture_output=True, text=True, timeout=30)
        after = json.loads(playback.stdout)
    receipt = {'status': 'passed', 'archive_sha256': digest, 'mode': 'recorded_synthetic_run',
               'exact_commit_product_readiness': 'blocked', 'fresh_extracted_package': True,
               'site_packages_disabled': True, 'new_provider_calls': 0,
               'checks': ['all archived file hashes', 'stdlib-only CLI installation check', 'built frontend served',
                          'completed Support packet', 'review saved and reloaded only in extracted copy',
                          'immutable packaged files unchanged after review'],
               'initial_check': initial, 'after_review_check': after}
    destination = directory / 'PackageValidation.json'
    if args.write_receipt:
        destination.write_text(json.dumps(receipt, indent=2) + '\n')
    else:
        assert json.loads(destination.read_text()) == receipt, 'Regenerate validation against the shipped archive'
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
