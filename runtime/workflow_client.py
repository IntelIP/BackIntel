"""Authenticated saved-workflow transport shared by optional Python agent adapters."""
import math
import re
import time

import httpx

class WorkflowClientError(Exception):
    """An explicit failure to obtain a verified workflow result."""


def saved_workflow_runner(client: httpx.Client, workflow_version: str, *, input_ref=None, wait_seconds=300):
    """Bind credentials and workflow outside model arguments; retain the full API receipt."""
    if not re.fullmatch(r'[0-9a-f]{64}', workflow_version):
        raise ValueError('Use the complete saved workflow version')
    if input_ref is not None and not re.fullmatch(r'[0-9a-f]{64}', input_ref):
        raise ValueError('Use the complete permitted collection identity')
    if (client.base_url.scheme != 'https'
            and not (client.base_url.scheme == 'http'
                     and client.base_url.host in ('127.0.0.1', 'localhost', '::1'))):
        raise ValueError('Use HTTPS, or a local loopback server for the trial')
    if client.follow_redirects:
        raise ValueError('Disable redirects for the authenticated BackIntel client')
    if not math.isfinite(wait_seconds) or not 0 <= wait_seconds <= 1800:
        raise ValueError('Wait time must be between zero and 1800 seconds')

    def request(method, path, **kwargs):
        try:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            reason = 'Access denied' if status in (401, 403) else 'Request rejected'
            raise WorkflowClientError(f'{reason} by BackIntel (HTTP {status}); no answer accepted by this tool.') from None
        except httpx.RequestError:
            raise WorkflowClientError('BackIntel connection interrupted. Retry this same tool to recover the existing run.') from None
        try:
            body = response.json()
        except ValueError:
            raise WorkflowClientError('BackIntel returned an invalid response; no answer is verified.') from None
        if (not isinstance(body, dict) or not isinstance(body.get('id'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', body['id'])
                or body.get('status') not in ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'partial')):
            raise WorkflowClientError('BackIntel returned an unsupported run response; no answer is verified.')
        return body

    def run_backintel_workflow() -> tuple[dict, dict]:
        """Run or resume the approved retail workflow. Return its checked answer and evidence.

        This tool cannot change the objective, source, permissions, or spending limits.
        A queued/running response is unfinished; retry the same tool to recover it.
        Only a succeeded response contains an accepted answer. Do not invent missing results.
        """
        body = request('POST', f'/api/v1/workflows/{workflow_version}/runs',
                       json={'input_ref': input_ref} if input_ref is not None else {})
        identity = body['id']
        deadline = time.monotonic() + wait_seconds
        # Read through the authorized result endpoint even when admission reused a finished run.
        body = request('GET', f'/api/v1/runs/{identity}')
        if body['id'] != identity:
            raise WorkflowClientError('BackIntel returned a different run; no answer is verified.')
        while body['status'] in ('queued', 'running') and time.monotonic() < deadline:
            body = request('GET', f'/api/v1/runs/{identity}')
            if body['id'] != identity:
                raise WorkflowClientError('BackIntel returned a different run; no answer is verified.')
            if body['status'] in ('queued', 'running'):
                time.sleep(min(0.5, max(0, deadline - time.monotonic())))
        content = {'run_id': identity, 'workflow_version': workflow_version, 'status': body['status']}
        if body['status'] == 'succeeded':
            result = body.get('result') or {}
            content.update({key: result[key] for key in ('summary', 'findings', 'coverage', 'evidence_id', 'usage', 'limitations')
                            if key in result})
            content['totals'] = result.get('calculation', {}).get('totals')
        else:
            content['message'] = ('The workflow is unfinished; retry the same tool to recover it.'
                                  if body['status'] in ('queued', 'running')
                                  else 'The workflow did not succeed. Inspect the retained run; no new answer is accepted.')
            if body.get('error'):
                content['reason'] = body['error']
        return content, body

    return run_backintel_workflow
