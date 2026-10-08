"""Require the local operator credential before accepting capability API work."""
import hmac
import os

from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def authenticate(headers: dict):
    token = os.environ.get('BACKINTEL_CAPABILITY_TOKEN', '')
    header = headers.get('authorization', '')
    if not token or not hmac.compare_digest(header.encode(), ('Bearer ' + token).encode()):
        raise Auth.exceptions.HTTPException(status_code=401, detail='Valid capability operator credential required')
    return {'identity': 'capability-operator', 'is_authenticated': True}
