"""Portable, secret-free preflight and atomic imports of approved benchmark inputs."""
from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from runtime.analysis_data import CONFIG, adapt, fingerprint, root
from runtime.real_models import CONFIG as MODEL_CONFIG, file_sha, model_root

PROJECT = Path(__file__).resolve().parents[1]
MAX_EXTRACTED_BYTES = 2 * 1024**3
REQUIRED_COLUMNS = {
    'commerce': [{'Age', 'Review Text', 'Recommended IND', 'Department Name', 'Class Name', 'Division Name'}],
    'support': [{'ticket_id', 'customer_id', 'created_at', 'resolution_time_hours', 'initial_message', 'sla_plan'}],
    'churn': [{'customerID', 'Churn', 'Contract', 'tenure', 'MonthlyCharges', 'TotalCharges'}],
    'credit': [{'SK_ID_CURR', 'TARGET', 'NAME_INCOME_TYPE'}, {'SK_ID_CURR', 'DAYS_CREDIT', 'DAYS_CREDIT_UPDATE'}],
}


def validate_files(domain, directory):
    paths = [directory / name for name in CONFIG['sources'][domain]['files']]
    summaries = []
    for index, path in enumerate(paths):
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing, empty, or linked source file: ' + path.name)
        with path.open('rb') as stream:
            prefix = stream.read(256).lstrip().lower()
        if prefix.startswith((b'version https://git-lfs.github.com/spec/', b'<!doctype html', b'<html')):
            raise ValueError('Source is a pointer or HTML response: ' + path.name)
        summary = fingerprint(path)
        if domain != 'maintenance':
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                columns = reader.fieldnames or []
                if not REQUIRED_COLUMNS[domain][index].issubset(columns):
                    raise ValueError('Required source columns are missing: ' + path.name)
                count = 0
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError('CSV row has extra or missing columns: ' + path.name)
                    count += 1
                if not count:
                    raise ValueError('Source contains no records: ' + path.name)
                summary.update(rows=count, columns=columns)
        else:
            with path.open() as stream:
                summary['rows'] = sum(bool(line.strip()) for line in stream)
        summaries.append(summary)
    snapshot, body, _ = adapt(domain, paths)
    return summaries, snapshot, body


def extract_sources(archive, directory, wanted, seen=None, depth=0, total=None):
    seen = seen if seen is not None else set()
    total = total if total is not None else [0]
    if depth > 2:
        raise ValueError('Source archive nesting limit exceeded')
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            name = PurePosixPath(member.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in member.filename or ':' in member.filename:
                raise ValueError('Source archive contains an unsafe path')
            if stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1:
                raise ValueError('Linked or encrypted archive entries are unsupported')
            if member.is_dir():
                continue
            selected = name.name in wanted
            nested = name.suffix.lower() == '.zip'
            if not selected and not nested:
                continue
            total[0] += member.file_size
            if total[0] > MAX_EXTRACTED_BYTES:
                raise ValueError('Source archive exceeds the extraction budget')
            if selected:
                if name.name in seen:
                    raise ValueError('Source archive contains duplicate expected filenames')
                seen.add(name.name)
                with zipped.open(member) as source, (directory / name.name).open('xb') as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
            else:
                with tempfile.TemporaryFile() as inner:
                    with zipped.open(member) as source:
                        shutil.copyfileobj(source, inner, length=1024 * 1024)
                    inner.seek(0)
                    extract_sources(inner, directory, wanted, seen, depth + 1, total)
    return seen


def import_data(domain, source, provenance=None):
    """Validate the entire input before publishing a dataset directory; no rule acceptance."""
    source = Path(source)
    base = root()
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = base / domain.title()
    if destination.is_symlink():
        raise ValueError('Dataset destination must not be a symbolic link')
    with tempfile.TemporaryDirectory(prefix='.import-', dir=base) as temporary:
        staging = Path(temporary) / domain.title()
        staging.mkdir(mode=0o700)
        wanted = set(CONFIG['sources'][domain]['files'])
        if source.is_dir():
            for name in wanted:
                candidate = source / name
                if candidate.is_symlink() or not candidate.is_file():
                    raise ValueError('Expected local source file is missing or linked: ' + name)
                shutil.copyfile(candidate, staging / name)
        elif source.is_file() and zipfile.is_zipfile(source):
            found = extract_sources(source, staging, wanted)
            if wanted != found:
                raise ValueError('Expected source files are missing: ' + ', '.join(sorted(wanted - found)))
        elif source.is_file() and not source.is_symlink() and len(wanted) == 1:
            shutil.copyfile(source, staging / next(iter(wanted)))
        else:
            raise ValueError('Supply a complete source directory, ZIP archive, or single expected CSV')
        files, snapshot, body = validate_files(domain, staging)
        receipt = {'schema': 'backintel-source-import/v1', 'domain': domain,
                   'kaggle': CONFIG['sources'][domain]['kaggle'],
                   'attribution': CONFIG['sources'][domain]['name'],
                   'declared_source_license': CONFIG['sources'][domain]['license'],
                   'terms_acknowledged': True, 'authorization_basis': 'operator-authorized benchmark/testing use',
                   'competition_rules_accepted_by_tool': False,
                   'provenance': provenance or {'kind': 'operator-supplied files', 'original_byte_identity': 'unverified'},
                   'files': files, 'snapshot_id': snapshot, 'adapter_receipt': body}
        (staging / 'source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        if destination.exists():
            existing, _, _ = validate_files(domain, destination)
            if existing != files:
                raise ValueError('Existing dataset differs; preserve it and choose a new BACKINTEL_DATASET_DIR')
            return receipt
        staging.rename(destination)
    return receipt


def published(domain):
    from scripts.analysis_demo import download
    sources = json.loads((PROJECT / 'config/analysis-published-sources.json').read_text())
    if domain not in sources:
        raise ValueError('No verified complete published copy is configured for this domain; import local files')
    spec = sources[domain]
    with tempfile.TemporaryDirectory(prefix='backintel-published-') as temporary:
        directory = Path(temporary)
        for item in spec['files']:
            path = directory / item['file']
            download(item['url'], path)
            if fingerprint(path) != {key: item[key] for key in ('file', 'bytes', 'sha256')}:
                raise ValueError('Published source does not match the frozen file identity')
        files, _, _ = validate_files(domain, directory)
        if any(file['rows'] != item['rows'] for file, item in zip(files, spec['files'])):
            raise ValueError('Published source record count differs from its frozen identity')
        receipt = import_data(domain, directory, {key: value for key, value in spec.items() if key != 'files'})
        return receipt


def download_weights(kind):
    from scripts.analysis_demo import download, weights
    if kind == 'decide':
        model_root()  # Require the explicit model directory for portable acquisition.
        weights()
        return {'kind': kind, 'status': 'downloaded', 'revision': CONFIG['decide']['revision'], 'execution_verified': False}
    spec = json.loads(MODEL_CONFIG.read_text())['tabiclv2']
    pinned = spec['checkpoints'][kind]
    url = f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{pinned['file']}?download=true"
    with tempfile.TemporaryDirectory(prefix='backintel-checkpoint-') as temporary:
        path = Path(temporary) / pinned['file']
        download(url, path)
        return import_weights(kind, path)


def import_weights(kind, source):
    source = Path(source)
    base = model_root()
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if kind != 'decide':
        spec = json.loads(MODEL_CONFIG.read_text())['tabiclv2']['checkpoints'][kind]
        if source.is_symlink() or not source.is_file() or source.stat().st_size != spec['bytes'] or file_sha(source) != spec['sha256']:
            raise ValueError('TabICLv2 checkpoint does not match the approved size and SHA-256')
        directory = base / 'Weights'
        directory.mkdir(exist_ok=True)
        if directory.is_symlink():
            raise ValueError('Weights destination must not be linked')
        target = directory / spec['file']
        if target.exists():
            if target.is_symlink() or file_sha(target) != spec['sha256']:
                raise ValueError('Existing checkpoint differs; choose a new model directory')
        else:
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                try:
                    with source.open('rb') as stream:
                        shutil.copyfileobj(stream, temporary, length=1024 * 1024)
                    temporary.flush()
                    if file_sha(temporary_path) != spec['sha256']:
                        raise ValueError('Checkpoint changed during import')
                    temporary_path.replace(target)
                finally:
                    temporary_path.unlink(missing_ok=True)
        return {'kind': kind, 'status': 'verified', **spec}
    receipt = json.loads((source / 'backintel-weights.json').read_text())
    if any(receipt.get(key) != CONFIG['decide'][key] for key in ('repository', 'revision')) or not receipt.get('files'):
        raise ValueError('Decide receipt is missing or has an unapproved revision')
    declared = set()
    for item in receipt['files']:
        name = PurePosixPath(item['file'])
        path = source / str(name)
        if name.is_absolute() or '..' in name.parts or '\\' in str(name) or str(name) in declared or not path.resolve().is_relative_to(source.resolve()) or path.is_symlink():
            raise ValueError('Decide receipt contains an unsafe or duplicate path')
        declared.add(str(name))
        if fingerprint(path) != {key: item[key] for key in ('file', 'bytes', 'sha256')}:
            # Existing receipts use basenames in their fingerprint even for nested files.
            if path.stat().st_size != item['bytes'] or file_sha(path) != item['sha256']:
                raise ValueError('Decide weight identity mismatch')
    if 'config.json' not in declared or not any(name.endswith('.safetensors') for name in declared):
        raise ValueError('Decide receipt is not a complete model package')
    destination = base / 'Decide'
    if destination.exists():
        raise ValueError('Preserve existing Decide weights and choose a new model directory')
    with tempfile.TemporaryDirectory(prefix='.weights-', dir=base) as temporary:
        staging = Path(temporary) / 'Decide'
        staging.mkdir()
        for item in receipt['files']:
            target = staging / item['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / item['file'], target)
            if file_sha(target) != item['sha256']:
                raise ValueError('Decide weight changed during import')
        (staging / 'backintel-weights.json').write_text(json.dumps(receipt, indent=2) + '\n')
        staging.rename(destination)
    return {'kind': kind, 'status': 'receipt-verified', 'revision': receipt['revision'],
            'limitation': 'Hashes verify the supplied receipt; publisher provenance relies on the original pinned acquisition.'}


def preflight(probe=False):
    report = {'schema': 'backintel-setup-preflight/v1', 'provider_calls': 0, 'provider_usd': 0,
              'budget_usd': CONFIG['budget']['suite_usd'], 'datasets': {}, 'weights': {}, 'libraries': {},
              'analyst': {'variable': 'OPENROUTER_API_KEY', 'environment_binding_present': bool(os.getenv('OPENROUTER_API_KEY'))},
              'configuration_request': json.loads((PROJECT / 'config/analysis-cloud-access.json').read_text())}
    for domain in CONFIG['sources']:
        try:
            files, snapshot, body = validate_files(domain, root() / domain.title())
            report['datasets'][domain] = {'status': 'ready', 'files': files, 'snapshot_id': snapshot, 'adapted_rows': body['rows']}
        except (OSError, ValueError, KeyError) as error:
            report['datasets'][domain] = {'status': 'missing-or-invalid', 'reason': type(error).__name__}
    for package in ('catboost', 'scikit-learn', 'numpy', 'joblib', 'tabicl', 'torch', 'gliner2'):
        try:
            report['libraries'][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report['libraries'][package] = None
    if os.getenv('BACKINTEL_MODEL_DIR'):
        from runtime.real_models import checkpoint
        for kind in ('classification', 'regression'):
            try:
                _, spec = checkpoint(kind)
                report['weights'][kind] = {'status': 'ready', **spec}
            except (OSError, ValueError, RuntimeError) as error:
                report['weights'][kind] = {'status': 'missing-or-invalid', 'reason': type(error).__name__}
        report['weights']['decide'] = {'receipt_present': (model_root() / 'Decide/backintel-weights.json').is_file(), 'status': 'execution-unverified'}
    else:
        report['weights']['status'] = 'BACKINTEL_MODEL_DIR-unset'
    if probe:
        report['network'] = {}
        for host in ('raw.githubusercontent.com', 'www.kaggle.com', 'huggingface.co', 'openrouter.ai'):
            result = subprocess.run(['curl', '--silent', '--show-error', '--head', '--output', os.devnull,
                                     '--write-out', '%{http_code}', '--connect-timeout', '5', '--max-time', '10',
                                     'https://' + host], capture_output=True, text=True, timeout=12)
            report['network'][host] = {'reachable': result.returncode == 0,
                                      'http_status': result.stdout[-3:] if result.stdout[-3:].isdigit() else None,
                                      'proxy_policy_denied': 'CONNECT tunnel failed, response 403' in result.stderr,
                                      'curl_exit': result.returncode}
    # A binding or an HTTP response does not prove provider authentication/model availability.
    report['full_live_campaign_ready'] = False
    report['remaining_validation'] = 'Provider authentication, approved model catalog, full local-model execution, and live campaign acceptance remain required.'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('preflight'); p.add_argument('--probe', action='store_true'); p.add_argument('--output')
    p = sub.add_parser('import-data'); p.add_argument('--domain', choices=CONFIG['sources'], required=True); p.add_argument('--input', required=True); p.add_argument('--source-url')
    p = sub.add_parser('published'); p.add_argument('--domain', choices=CONFIG['sources'], required=True)
    p = sub.add_parser('import-weights'); p.add_argument('--kind', choices=('classification', 'regression', 'decide'), required=True); p.add_argument('--input', required=True)
    p = sub.add_parser('download-weights'); p.add_argument('--kind', choices=('classification', 'regression', 'decide'), required=True)
    args = parser.parse_args()
    if args.command == 'preflight':
        result = preflight(args.probe)
        if args.output:
            path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2) + '\n')
    elif args.command == 'import-data':
        provenance = {'kind': 'operator-supplied files', 'original_byte_identity': 'unverified'}
        if args.source_url:
            provenance['source_url'] = args.source_url
        result = import_data(args.domain, args.input, provenance)
    elif args.command == 'published':
        result = published(args.domain)
    elif args.command == 'download-weights':
        result = download_weights(args.kind)
    else:
        result = import_weights(args.kind, args.input)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
