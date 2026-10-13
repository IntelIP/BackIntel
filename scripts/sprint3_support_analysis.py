"""Find support queues with the longest average resolution time from a CSV.

Supply closed tickets. This calculates observed statistics locally, without
provider calls or a prediction model.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.analysis_agent import aggregate, validate_answer
from runtime.analysis_data import digest, support


MAX_BYTES = 1_048_576
MAX_TICKETS = 10_000
REQUIRED_COLUMNS = {'ticket_id', 'channel', 'resolution_time_hours'}
FICTIONAL_SAMPLE_SHA256 = 'b19bc97f78f66e1d32ee519d0f743b783a9d7c3d16034381efda5e38471309f4'


def validate_input(body: bytes) -> None:
    if not 0 < len(body) <= MAX_BYTES:
        raise ValueError('Provide a nonempty CSV no larger than 1 MB.')
    try:
        reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig')), strict=True)
        if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError('The CSV needs ticket_id, channel, and resolution_time_hours columns.')
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError('Each CSV column must have a unique name.')
        count = 0
        for row in reader:
            count += 1
            if count > MAX_TICKETS:
                raise ValueError('Provide a CSV with at most 10,000 tickets.')
            if None in row:
                raise ValueError('Every ticket row must match the CSV column count.')
            if any(not (row.get(key) or '').strip() for key in REQUIRED_COLUMNS):
                raise ValueError('Every ticket needs an identity, a queue, and resolution hours.')
        if not count:
            raise ValueError('The CSV contains no tickets.')
    except UnicodeDecodeError as error:
        raise ValueError('Provide a UTF-8 CSV, with or without a byte-order mark.') from error
    except csv.Error as error:
        raise ValueError(f'Invalid CSV: {error}') from error


def analyze(source: Path, *, fictional: bool | None = None) -> dict:
    with source.open('rb') as stream:
        body = stream.read(MAX_BYTES + 1)
    validate_input(body)
    input_sha256 = hashlib.sha256(body).hexdigest()
    if fictional is None:
        fictional = input_sha256 == FICTIONAL_SAMPLE_SHA256
    rows = list(support([source]))
    if not rows or any(row['target'] is None or row['target'] < 0 for row in rows):
        raise ValueError('Provide closed tickets with nonnegative resolution_time_hours.')
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Ticket identities must be unique.')
    queues = {row['groups']['channel'] for row in rows}
    if not all(queues) or not 2 <= len(queues) <= 20:
        raise ValueError('Provide between two and twenty named channel queues.')
    table = aggregate(rows, group='channel', order='descending')
    selected = [row for row in table if row['mean'] == table[0]['mean']]
    proof = {
        'input_sha256': input_sha256,
        'group_by': 'channel',
        'unit': 'hours',
        'records': [{'ticket_id': row['id'], 'queue': row['groups']['channel'],
                     'resolution_hours': row['target']} for row in rows],
        'table': table,
    }
    evidence_id = digest(proof)
    evidence = {'evidence_id': evidence_id, 'tool': 'aggregate', 'kind': 'observed',
                'group_by': 'channel', 'table': table}
    findings = []
    for row in selected:
        claims = [f"{row['group']} has the highest mean.",
                  f"Group {row['group']} mean is {row['mean']:.12g}.",
                  f"{row['group']} has {row['count']} records."]
        findings.extend({'claim': claim, 'kind': 'fact', 'evidence_ids': [evidence_id]}
                        for claim in claims)
    answer = validate_answer({
        'summary': ' '.join(finding['claim'] for finding in findings),
        'findings': findings,
        'limitations': [
            'These are fictional closed tickets, not measured customer performance.' if fictional else
            'These are reviewer-supplied closed-ticket records; their accuracy is not independently verified.',
            'The review rule uses observed resolution times for this sample.',
            'Text interpretation, prediction, and the autonomous agent were not run.',
        ],
    }, [evidence], group='channel')
    return {
        'fictional': fictional,
        'question': 'Which queue needs attention?',
        'attention_rule': 'Review all channel queues with the highest average resolution time.',
        'selected_queues': [row['group'] for row in selected],
        'answer': answer,
        'evidence': {'evidence_id': evidence_id, **proof},
        'execution': 'Local support adapter, aggregate, and answer validator; no provider dispatch.',
    }


def markdown_text(value: str) -> str:
    return re.sub(r'([\\`*_{}\[\]()#+!|>])', r'\\\1', value).replace('\n', ' ')


def markdown(result: dict) -> str:
    evidence = result['evidence']
    lines = [
        '# Fresh support queue analysis', '',
        '**Fictional sample.** No customer-performance claim.' if result.get('fictional', True) else
        '**Supplied closed-ticket records.** The supplied values are not independently verified.', '',
        f"**Queue to review: {', '.join(markdown_text(queue) for queue in result['selected_queues'])}.**", '',
        'Rule: review all channel queues tied for the highest average time to resolve closed tickets.', '',
        '| Queue | Tickets | Average resolution time (hours) |',
        '| --- | --- | --- |',
    ]
    lines.extend(f"| {markdown_text(row['group'])} | {row['count']} | {row['mean']:.12g} |"
                 for row in evidence['table'])
    lines.extend(['', '## Supporting tickets', '',
                  '| Ticket | Queue | Resolution time (hours) |', '| --- | --- | --- |'])
    lines.extend(f"| {markdown_text(row['ticket_id'])} | {markdown_text(row['queue'])} | {row['resolution_hours']:.12g} |"
                 for row in evidence['records'] if row['queue'] in result['selected_queues'])
    lines.extend(['', '## Checked findings', ''])
    lines.extend(f"- {markdown_text(finding['claim'])}" for finding in result['answer']['findings'])
    lines.extend(['', '## Limits', ''])
    lines.extend(f'- {text}' for text in result['answer']['limitations'])
    lines.extend(['', 'Source: [input.csv](input.csv). Details: [report.json](report.json).'])
    lines.extend(['',
                  f"Input SHA-256: `{evidence['input_sha256']}`.",
                  f"Calculation evidence: `{evidence['evidence_id']}`.", ''])
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path,
                        help='A new folder; existing outputs are preserved.')
    parser.add_argument('--fictional', action='store_true',
                        help='Label a custom input as fictional. The included sample is recognized automatically.')
    args = parser.parse_args(argv)
    try:
        with args.input.open('rb') as stream:
            body = stream.read(MAX_BYTES + 1)
        with TemporaryDirectory(prefix='backintel-support-') as directory:
            source = Path(directory) / 'input.csv'
            source.write_bytes(body)
            result = analyze(source, fictional=True if args.fictional else None)
        result['created_at'] = datetime.now(timezone.utc).isoformat()
        report_json = json.dumps(result, indent=2, allow_nan=False) + '\n'
        report_markdown = markdown(result)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'input.csv').write_bytes(body)
        (args.output / 'report.json').write_text(report_json, encoding='utf-8')
        (args.output / 'report.md').write_text(report_markdown, encoding='utf-8')
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({'selected_queues': result['selected_queues'],
                      'report': str((args.output / 'report.md').resolve())}))


if __name__ == '__main__':
    main()
