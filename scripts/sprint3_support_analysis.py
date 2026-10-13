"""Answer the bounded Sprint 3 queue question using local analysis functions.

Inputs are synthetic closed support tickets in the existing support CSV format.
This runs observed statistics, not the paid agent or a prediction model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path

from runtime.analysis_agent import aggregate, validate_answer
from runtime.analysis_data import digest, support


def analyze(source: Path, *, fictional: bool = True) -> dict:
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
        'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
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


def markdown(result: dict, *, include_file_links: bool = True) -> str:
    evidence = result['evidence']
    lines = [
        '# Fresh support queue analysis', '',
        '**Fictional sample.** No customer-performance claim.' if result.get('fictional', True) else
        '**Uploaded closed-ticket records.** The supplied values are not independently verified.', '',
        f"**Queue to review: {', '.join(markdown_text(queue) for queue in result['selected_queues'])}.**", '',
        'Rule: review the channel queue with the highest average time to resolve closed tickets.', '',
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
    if include_file_links:
        lines.extend(['', 'Source: [input.csv](input.csv). Details: [report.json](report.json).'])
    lines.extend(['',
                  f"Input SHA-256: `{evidence['input_sha256']}`.",
                  f"Calculation evidence: `{evidence['evidence_id']}`.", ''])
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path,
                        help='A new folder; existing outputs are preserved.')
    args = parser.parse_args()
    try:
        body = args.input.read_bytes()
        args.output.mkdir(parents=True, exist_ok=False)
        source = args.output / 'input.csv'
        source.write_bytes(body)
        result = analyze(source)
        result['created_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        (args.output / 'report.md').write_text(markdown(result))
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({'selected_queues': result['selected_queues'],
                      'report': str((args.output / 'report.md').resolve())}))


if __name__ == '__main__':
    main()
