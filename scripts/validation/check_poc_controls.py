"""Check current offline UI, recovery and security evidence without model calls."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.validation.benchmark_campaign import file_hash, identity


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_receipt(directory, candidate, expected):
    receipt = json.loads((directory / 'receipt.json').read_text())
    require(not candidate['dirty'] and receipt.get('dirty') is False, 'Uncommitted evidence is not accepted')
    require(receipt.get('candidate_commit') == candidate['commit'] == expected, 'Evidence belongs to another commit')
    require(receipt.get('candidate_files') == candidate['files'], 'Evidence source files differ from this candidate')
    require(receipt.get('status') == 'passed' and receipt.get('mode') == 'e2e', 'Offline browser campaign did not pass')
    require(receipt.get('provider_calls') == 0 and receipt.get('new_provider_spend_usd') == 0, 'Offline cost boundary failed')
    artifacts = receipt.get('artifacts', {})
    require('browser-evidence.json' in artifacts, 'Browser evidence is missing')
    for name, digest in artifacts.items():
        path = (directory / name).resolve()
        path.relative_to(directory.resolve())
        require(path.is_file() and file_hash(path) == digest, 'Artifact missing or changed: ' + name)
    browser = json.loads((directory / 'browser-evidence.json').read_text())
    require(browser.get('status') == 'passed' and browser.get('mode') == 'fixture', 'Browser result is not a passing fixture run')
    return receipt, browser


def check_controls(mode, receipt, browser, directory):
    views = browser.get('views', [])
    expected_views = {(role, width) for role in ('manager', 'analyst', 'viewer') for width in (1440, 390)}
    require(len(views) == 6 and {(v['role'], v['width']) for v in views} == expected_views, 'Missing role or viewport')
    if mode == 'visual':
        for view in views:
            require(view.get('no_overflow') is True and view.get('keyboard_evidence') is True, 'Layout or keyboard navigation failed')
            name = f"{view['role']}-{view['width']}.png"
            require(name in browser.get('screenshots', []) and name in receipt['artifacts'], 'Screenshot missing: ' + name)
            data = (directory / name).read_bytes()
            require(data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24, 'Invalid screenshot: ' + name)
            width, height = struct.unpack('>II', data[16:24])
            require(width == view['width'] and height >= 640, 'Unexpected screenshot dimensions: ' + name)
    elif mode == 'operational':
        for name in ('hard_worker_restart', 'broker_restart'):
            result = receipt.get(name, {})
            require(result.get('status') == 'passed' and result.get('completed_events') == 1, 'Recovery did not retain one completion: ' + name)
            require(all(result.get(key) for key in ('same_run_id', 'same_job_id', 'accepted_result_sha256')), 'Recovery identity missing: ' + name)
        require(receipt['broker_restart'].get('existing_broker_untouched') is True, 'Existing broker preservation unverified')
        restore = receipt.get('database_backup_restore', {})
        require(restore.get('status') == 'passed' and restore.get('evidence_and_provider_ids_unchanged') is True, 'Backup/restore integrity unverified')
        clock = browser.get('native_clock', {})
        require(clock.get('status') == 'passed' and clock.get('cleanup') == 'removed', 'Native scheduler or cleanup failed')
        require(receipt.get('database_cleanup') == receipt.get('owned_broker_container_cleanup') == restore.get('restore_database_cleanup') == 'removed', 'Owned resource cleanup failed')
    else:
        require(all(v.get('core_denial') is True for v in views), 'Core API access boundary failed')
        denials = [s for s in browser.get('scenarios', []) if s.get('id') == 'BI-ACCESS-001']
        require(len(denials) == 6 and {(s.get('role'), s.get('width')) for s in denials} == expected_views, 'Missing access-denial scenarios')
        require(all(s.get('status') == 'passed' and s.get('write_status') == s.get('core_status') == 403 for s in denials), 'Unauthorized writes or core access were accepted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('visual', 'operational', 'security'))
    args = parser.parse_args()
    directory = Path(os.environ.get('BACKINTEL_POC_EVIDENCE', ROOT / 'artifacts/validation/PoCControls/Browser'))
    candidate = identity(ROOT)
    receipt, browser = load_receipt(directory, candidate, os.environ.get('TABELLIO_EXPECTED_COMMIT', candidate['commit']))
    check_controls(args.mode, receipt, browser, directory)
    if args.mode == 'security':
        subprocess.run([sys.executable, '-m', 'scripts.validation.check_sandbox', '--output', str(directory.parent / 'Sandbox'),
                        '--image', os.environ.get('BACKINTEL_SANDBOX_IMAGE', 'backintel-capability-demo-runtime:latest')], cwd=ROOT, check=True, timeout=120)
    print(json.dumps({'status': 'passed', 'mode': args.mode, 'candidate_commit': candidate['commit'],
                      'scope': 'offline controls; analyst responses are fixtures', 'provider_calls': 0}))


if __name__ == '__main__':
    main()
