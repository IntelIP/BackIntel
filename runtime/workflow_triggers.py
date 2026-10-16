"""Bounded starts for saved workflows. Aegra remains the only timer owner."""
from datetime import timedelta
import json
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from psycopg.types.json import Jsonb

from runtime import analysis_store as db, analysis_service as service, source_workflows
from runtime.analysis_data import digest
from runtime.analysis_errors import safe_error


class TriggerInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_source: str = Field(min_length=1, max_length=160)
    timezone: str = Field(min_length=1, max_length=80)
    run_at: AwareDatetime | None = None
    expires_at: AwareDatetime
    interval_seconds: int | None = Field(default=None, strict=True, ge=60)
    max_runs: int = Field(default=2, strict=True, ge=1, le=100)
    max_spend_usd: Literal[0] = 0
    input_ref: str | None = Field(default=None, min_length=1, max_length=128)
    refresh_source: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def valid_schedule(self):
        if self.refresh_source and self.input_ref:
            raise ValueError('A source-refresh trigger reads current data; omit the retained input reference')
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError('Use a known IANA timezone, such as America/New_York') from error
        if self.run_at is not None and self.run_at >= self.expires_at:
            raise ValueError('The first scheduled run must precede expiration')
        if self.interval_seconds is not None and self.run_at is None:
            raise ValueError('An interval requires a first scheduled time')
        return self


class EventInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_id: str = Field(min_length=1, max_length=160)
    source: str = Field(min_length=1, max_length=160)
    input_ref: str | None = Field(default=None, min_length=1, max_length=128)


def _row(identity, connection, actor=None):
    row = db.query('SELECT *,clock_timestamp() AS current_time FROM backintel.analysis_workflow_triggers WHERE id=%s FOR UPDATE',
                   (identity,), one=True, connection=connection)
    if row is None:
        raise ValueError('Unknown workflow trigger')
    if actor is not None:
        goal = db.goal(row['goal_id'])
        db.authorize(actor, goal['domain'], ('manager',))
        if row['owner'] != actor['id']:
            raise PermissionError('Only the trigger owner can inspect or change it')
    row['current_time'] = connection.execute('SELECT clock_timestamp()').fetchone()[0]
    return row


def configure(version, actor, spec):
    spec = TriggerInput.model_validate(spec)
    binding = source_workflows.bind(version, spec.input_ref, actor)
    db.authorize(actor, db.goal(binding['goal_id'])['domain'], ('manager',))
    with db.connect() as connection, connection.transaction():
        now = connection.execute('SELECT clock_timestamp()').fetchone()[0]
        if spec.expires_at <= now or (spec.run_at is not None and spec.run_at <= now):
            raise ValueError('Choose future run and expiration times')
        identity = str(uuid4())
        connection.execute('''INSERT INTO backintel.analysis_workflow_triggers
            (id,goal_id,owner,workflow_version,body,state,next_due,expires_at)
            VALUES(%s,%s,%s,%s,%s,'active',%s,%s)''',
            (identity, binding['goal_id'], actor['id'], version,
             Jsonb(spec.model_dump(mode='json')), spec.run_at, spec.expires_at))
    return inspect(identity, actor)


def inspect(identity, actor):
    with db.connect() as connection, connection.transaction():
        row = _row(identity, connection, actor)
        if row['state'] == 'active' and row['expires_at'] <= row['current_time']:
            connection.execute("UPDATE backintel.analysis_workflow_triggers SET state='expired',next_due=NULL WHERE id=%s", (identity,))
            row.update(state='expired', next_due=None)
        row['attempts'] = db.query('''SELECT a.*,r.status AS run_status FROM backintel.analysis_trigger_attempts a
            LEFT JOIN backintel.analysis_runs r ON r.id=a.run_id WHERE a.trigger_id=%s ORDER BY a.sequence DESC LIMIT 100''',
            (identity,), connection=connection)
        row.pop('current_time')
        return row


def history(goal_id, actor):
    db.authorize(actor, db.goal(goal_id)['domain'], ('manager',))
    return [inspect(row['id'], actor) for row in db.query(
        'SELECT id FROM backintel.analysis_workflow_triggers WHERE goal_id=%s AND owner=%s ORDER BY created_at DESC',
        (goal_id, actor['id']))]


def _attempt(connection, row, occurrence, status, reason, run_id=None):
    connection.execute('''INSERT INTO backintel.analysis_trigger_attempts(trigger_id,occurrence,status,reason,run_id)
        VALUES(%s,%s,%s,%s,%s)''', (row['id'], occurrence, status, reason, run_id))
    return {'trigger_id': row['id'], 'occurrence': occurrence, 'status': status, 'reason': reason, 'run_id': run_id}


def _admit(connection, row, occurrence, source, input_ref):
    request_hash = digest({'source': source, 'input_ref': input_ref})
    receipt = db.query('SELECT * FROM backintel.analysis_trigger_receipts WHERE trigger_id=%s AND occurrence=%s',
                       (row['id'], occurrence), one=True, connection=connection)
    if receipt:
        if receipt['request_sha256'] != request_hash:
            return _attempt(connection, row, occurrence, 'denied', 'Event identity was already used with different inputs')
        return _attempt(connection, row, occurrence, 'reused', 'This occurrence already has accepted work', receipt['run_id'])
    reason = None
    if row['state'] != 'active':
        reason = 'Trigger is ' + row['state']
    elif row['expires_at'] <= row['current_time']:
        reason = 'Trigger authority expired'
        connection.execute("UPDATE backintel.analysis_workflow_triggers SET state='expired',next_due=NULL WHERE id=%s", (row['id'],))
    elif row['accepted_count'] >= row['body']['max_runs']:
        reason = 'Trigger run limit exhausted'
    elif source != row['body']['event_source']:
        reason = 'Event source is outside the configured grant'
    if reason:
        return _attempt(connection, row, occurrence, 'denied', reason)
    try:
        # Savepoint keeps denied attempts visible while rolling back failed admission.
        with connection.transaction():
            package = source_workflows.read(row['workflow_version'], {'id': row['owner']})
            if row['body'].get('refresh_source'):
                if input_ref is not None:
                    raise ValueError('A source-refresh event cannot substitute retained inputs')
                run = source_workflows.refresh(row['workflow_version'], {'id': row['owner']},
                    'trigger:' + row['id'] + ':' + occurrence, connection=connection)
            else:
                run = service.submit(row['goal_id'], {'id': row['owner']}, question=package['body']['question'],
                                     operation='workflow', workflow_version=row['workflow_version'],
                                     input_ref=input_ref, connection=connection)
    except (ValueError, PermissionError, RuntimeError, OSError) as error:
        return _attempt(connection, row, occurrence, 'denied', safe_error(error))
    connection.execute('INSERT INTO backintel.analysis_trigger_receipts VALUES(%s,%s,%s,%s)',
                       (row['id'], occurrence, request_hash, run['id']))
    connection.execute('''UPDATE backintel.analysis_workflow_triggers SET accepted_count=accepted_count+1,
        state=CASE WHEN accepted_count+1>= %s THEN 'exhausted' ELSE state END,
        next_due=CASE WHEN accepted_count+1>= %s THEN NULL ELSE next_due END WHERE id=%s''',
        (row['body']['max_runs'], row['body']['max_runs'], row['id']))
    return _attempt(connection, row, occurrence, 'accepted', 'Saved workflow admitted under current source access; no model calls', run['id'])


def event(identity, actor, payload):
    payload = EventInput.model_validate(payload)
    with db.connect() as connection, connection.transaction():
        row = _row(identity, connection, actor)
        return _admit(connection, row, 'event:' + payload.event_id, payload.source,
                      payload.input_ref or row['body']['input_ref'])


def due(identity):
    with db.connect() as connection, connection.transaction():
        row = _row(identity, connection)
        if row['state'] != 'active' or row['next_due'] is None:
            return {'trigger_id': identity, 'status': 'skipped', 'reason': 'No active pending schedule'}
        if row['next_due'] > row['current_time']:
            return {'trigger_id': identity, 'status': 'waiting', 'due_at': row['next_due']}
        occurrence = 'schedule:' + row['next_due'].isoformat()
        result = _admit(connection, row, occurrence, row['body']['event_source'], row['body']['input_ref'])
        interval = row['body']['interval_seconds']
        next_due = row['next_due'] + timedelta(seconds=interval) if interval else None
        # Missed intervals coalesce into one run. Never replay a backlog of timer ticks.
        if next_due is not None and next_due <= row['current_time']:
            next_due += timedelta(seconds=interval * (int((row['current_time'] - next_due).total_seconds() // interval) + 1))
        if next_due is not None and next_due >= row['expires_at']:
            next_due = None
        connection.execute("UPDATE backintel.analysis_workflow_triggers SET next_due=CASE WHEN state='active' THEN %s::timestamptz ELSE NULL END WHERE id=%s", (next_due, identity))
        return result


def set_state(identity, actor, state):
    if state not in ('active', 'paused', 'removed'):
        raise ValueError('Trigger state must be active, paused or removed')
    with db.connect() as connection, connection.transaction():
        row = _row(identity, connection, actor)
        if row['state'] == 'removed' and state != 'removed':
            raise ValueError('A removed trigger cannot be changed')
        if state == 'active' and (row['expires_at'] <= row['current_time'] or row['accepted_count'] >= row['body']['max_runs']):
            raise ValueError('Expired or exhausted authority cannot be resumed')
        connection.execute('UPDATE backintel.analysis_workflow_triggers SET state=%s WHERE id=%s', (state, identity))
        _attempt(connection, row, 'control:' + str(uuid4()), 'skipped', 'Owner set trigger to ' + state)
    return inspect(identity, actor)


def sync_timer(identity, actor):
    """Reconcile the exact owned native cron; failures leave admissions paused."""
    with db.connect() as connection, connection.transaction():
        row = _row(identity, connection, actor)
        if row['body']['run_at'] is None:
            return
        credential = Path(os.getenv('BACKINTEL_ACCESS_CREDENTIAL_FILE', '/run/backintel-credentials/access.json'))
        token = json.loads(credential.read_text())['worker']
        purpose = 'backintel-workflow-trigger:' + identity
        with httpx.Client(base_url=os.getenv('BACKINTEL_AEGRA_URL', 'http://127.0.0.1:2026'),
                          headers={'Authorization': 'Bearer ' + token}, timeout=15) as client:
            response = client.post('/runs/crons/search', json={'assistant_id': 'workflow_triggers', 'limit': 1000})
            response.raise_for_status()
            matching = [cron for cron in response.json() if cron.get('metadata', {}).get('purpose') == purpose]
            active = row['state'] == 'active' and row['next_due'] is not None and row['expires_at'] > row['current_time']
            for cron in matching:
                response = client.delete('/runs/crons/' + cron['cron_id'])
                response.raise_for_status()
            cron_id = None
            if active:
                response = client.post('/runs/crons', json={'assistant_id': 'workflow_triggers', 'schedule': '* * * * *',
                    'input': {'trigger_id': identity}, 'metadata': {'purpose': purpose},
                    'end_time': row['expires_at'].isoformat(), 'timezone': row['body']['timezone'], 'enabled': False})
                if response.status_code == 422:
                    detail = response.json().get('detail', 'Invalid native schedule configuration')
                    if isinstance(detail, list):
                        detail = '; '.join(str(item.get('msg', 'Invalid field')) for item in detail)
                    raise ValueError('Native scheduler rejected the configuration: ' + str(detail)[:500])
                response.raise_for_status()
                cron_id = response.json()['cron_id']
                response = client.patch('/runs/crons/' + cron_id, json={'enabled': True})
                response.raise_for_status()
            connection.execute('UPDATE backintel.analysis_workflow_triggers SET cron_id=%s,timer_error=NULL WHERE id=%s', (cron_id, identity))


def timer_failed(identity, actor, error):
    with db.connect() as connection, connection.transaction():
        row = _row(identity, connection, actor)
        message = safe_error(error)
        connection.execute("""UPDATE backintel.analysis_workflow_triggers SET timer_error=%s,
            state=CASE WHEN state='active' THEN 'paused' ELSE state END WHERE id=%s""", (message, identity))
        _attempt(connection, row, 'timer:' + str(uuid4()), 'denied', 'Native schedule needs attention: ' + message)
    return inspect(identity, actor)


def dispatch(identity):
    result = due(identity)
    if result.get('run_id'):
        service.dispatch(result['run_id'])
    return result
