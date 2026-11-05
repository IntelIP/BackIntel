"""Retain bounded document originals and ground field explanations in exact passages."""

from contextlib import nullcontext
import hashlib
from html.parser import HTMLParser
import re
import textwrap
import time
from urllib.parse import urlsplit
from psycopg.types.json import Jsonb
from runtime import analysis_store as db
from runtime.analysis_data import digest
from runtime.evidence import Evidence

MAX_BYTES = 2_000_000
MAX_TEXT = 128_000
MAX_ATTACHED = 4
FORMATS = ('text/plain', 'text/html')


class DocumentText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.ignored += 1
        elif not self.ignored and tag in ('p', 'div', 'li', 'tr', 'br', 'h1', 'h2', 'h3', 'section'):
            self.parts.append('\n')
        elif not self.ignored and tag in ('td', 'th'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.ignored = max(0, self.ignored - 1)
        elif not self.ignored and tag in ('p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'section'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def extract(payload, media_type):
    if media_type not in FORMATS:
        raise ValueError('Supported documents are UTF-8 plain text and HTML; PDF and scanned text are not supported')
    if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_BYTES:
        raise ValueError('A document must contain at most 2 MB of original bytes')
    try:
        original = payload.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError('The original document must be valid UTF-8 text') from None
    if '\x00' in original:
        raise ValueError('Binary document content is not supported')
    if media_type == 'text/html':
        parser = DocumentText()
        parser.feed(original)
        parser.close()
        original = ''.join(parser.parts)
    lines = [re.sub(r'\s+', ' ', line).strip() for line in original.splitlines()]
    text = '\n'.join(line for line in lines if line)
    if not text or len(text) > MAX_TEXT:
        raise ValueError('The document has no readable text or exceeds the 128,000-character text limit')
    passages = []
    for line in text.splitlines():
        for part in textwrap.wrap(line, width=1600, break_long_words=False, break_on_hyphens=False):
            if len(part) > 1600 or len(passages) >= 1024:
                raise ValueError('The document exceeds the supported passage size or count; no partial document was admitted')
            passages.append({'id': digest([len(passages), part]), 'text': part, 'ordinal': len(passages) + 1})
    return {'text': text, 'text_sha256': digest(text), 'passages': passages, 'extraction': 'utf8-text-v1'}


def admit(goal_id, actor, *, title, source_url, media_type, payload):
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
        raise ValueError('A document title must contain 1–200 characters')
    if source_url is not None:
        if not isinstance(source_url, str) or len(source_url) > 2000:
            raise ValueError('The source URL must be a bounded HTTP or HTTPS reference')
        parsed = urlsplit(source_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('The source URL must be HTTP or HTTPS without embedded credentials')
    extracted = extract(payload, media_type)
    body = {**extracted, 'title': title.strip(), 'source_url': source_url, 'media_type': media_type,
            'bytes': len(payload), 'payload_sha256': hashlib.sha256(payload).hexdigest()}
    identity = digest([goal_id, body])
    with db.connect() as connection, connection.transaction():
        connection.execute('SELECT id FROM backintel.analysis_goals WHERE id=%s FOR UPDATE', (goal_id,))
        db.authorize_goal(actor, goal_id, ('manager',), permission='manage', connection=connection)
        existing = db.query('SELECT id FROM backintel.analysis_documents WHERE id=%s', (identity,), one=True, connection=connection)
        count = db.query('SELECT count(*) AS n FROM backintel.analysis_documents WHERE goal_id=%s', (goal_id,), one=True, connection=connection)['n']
        if not existing and count >= 40:
            raise ValueError('This objective has reached its 40 retained document versions limit')
        connection.execute('INSERT INTO backintel.analysis_documents(id,goal_id,payload,body) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                           (identity, goal_id, payload, Jsonb(body)))
        evidence = Evidence(connection, 'analysis-goal-' + goal_id)
        if not evidence.find('source_document', identity):
            evidence.put('source_document', identity, {'id': identity, **body}, int(time.time()))
    return {'id': identity, **body}


def read(identity, actor, *, connection=None):
    with (nullcontext(connection) if connection is not None else db.connect()) as control, control.transaction():
        row = db.query('SELECT * FROM backintel.analysis_documents WHERE id=%s', (identity,), one=True, connection=control)
        if row is None:
            raise ValueError('Unknown retained document')
        db.authorize_goal(actor, row['goal_id'], connection=control)
        row['payload'] = bytes(row['payload'])
        body = row['body']
        if (hashlib.sha256(row['payload']).hexdigest() != body['payload_sha256']
                or digest([row['goal_id'], body]) != identity or digest(body['text']) != body['text_sha256']):
            raise ValueError('The retained document failed its integrity check')
        return row


def validate_references(goal_id, identities, actor, *, connection=None):
    if (not isinstance(identities, list) or len(identities) > MAX_ATTACHED
            or any(not isinstance(identity, str) for identity in identities) or len(set(identities)) != len(identities)):
        raise ValueError('Attach at most four distinct retained documents')
    for identity in identities:
        if not isinstance(identity, str) or read(identity, actor, connection=connection)['goal_id'] != goal_id:
            raise PermissionError('A document must belong to this permitted objective')
    return identities


def listing(goal, actor):
    result = []
    for identity in goal['body'].get('document_refs', []):
        row = read(identity, actor)
        result.append({'id': identity, **{key: row['body'][key] for key in ('title', 'source_url', 'media_type', 'bytes', 'payload_sha256')}})
    return result


def context(goal, profile, actor):
    names = {field['name'] for table in profile['tables'] for field in table['fields']}
    candidates = []
    for identity in goal['body'].get('document_refs', []):
        row = read(identity, actor)
        if row['goal_id'] != goal['id']:
            raise PermissionError('Document context belongs to another objective')
        for passage in row['body']['passages']:
            matches = [name for name in names if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', passage['text'], re.IGNORECASE)]
            if matches:
                candidates.append({'document_id': identity, 'passage_id': passage['id'], 'text': passage['text'],
                                   'title': row['body']['title'], 'source_url': row['body']['source_url'], 'fields': sorted(matches)})
    return sorted(candidates, key=lambda p: (-len(p['fields']), p['document_id'], p['passage_id']))[:16]


def validate_citations(proposal, passages, *, required=False):
    allowed = {(p['document_id'], p['passage_id']): p for p in passages}
    linked = []
    for table in proposal['tables']:
        for field in table['fields']:
            for citation in field.get('citations', []):
                passage = allowed.get((citation['document_id'], citation['passage_id']))
                quote = citation['quote']
                if (not passage or not quote.strip() or quote not in passage['text']
                        or not re.search(r'(?<!\w)' + re.escape(field['name']) + r'(?!\w)', quote, re.IGNORECASE)):
                    raise ValueError('A document citation must quote a supplied passage exactly and name the linked field')
                linked.append({**citation, 'schema': table['schema_name'], 'table': table['table_name'], 'field': field['name'],
                               'title': passage['title'], 'source_url': passage['source_url']})
    if required and not linked and not proposal['unresolved']:
        raise ValueError('Attached documents need cited field evidence or an explicit unresolved interpretation')
    return linked


def accepted_evidence(goal, interpretation, actor):
    if sorted(interpretation.get('document_refs', [])) != sorted(goal['body'].get('document_refs', [])):
        raise ValueError('The interpretation belongs to different attached documents; interpret the current objective again')
    if not goal['body'].get('document_refs'):
        return validate_citations(interpretation['interpretation'], [])
    passages = context(goal, interpretation['profile'], actor)
    return validate_citations(interpretation['interpretation'], passages, required=bool(goal['body'].get('document_refs')))
