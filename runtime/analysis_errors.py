"""Redact configured credentials before errors enter API replies or evidence."""
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def safe_error(error):
    literals = {os.getenv('OPENROUTER_API_KEY', '')}
    for variable, default in (
        ('BACKINTEL_ANALYST_CREDENTIAL_FILE', '/run/backintel-credentials/analyst.json'),
        ('BACKINTEL_ACCESS_CREDENTIAL_FILE', '/run/backintel-credentials/access.json'),
    ):
        try:
            values = json.loads(Path(os.getenv(variable, default)).read_text())
            if isinstance(values, dict):
                literals.update(value for value in values.values() if isinstance(value, str))
        except (OSError, ValueError):
            pass
    for variable in ('DATABASE_URL', 'BACKINTEL_APP_DATABASE_URL', 'BACKINTEL_TEST_DATABASE_URL'):
        try:
            password = urlsplit(os.getenv(variable, '')).password
            if password:
                literals.update((password, unquote(password)))
        except ValueError:
            pass
    message = str(error)
    for value in sorted((value for value in literals if value), key=len, reverse=True):
        message = message.replace(value, '[redacted]')
    message = re.sub(r'(?i)\bBearer\s+[^\s,;\"\'<>]+', 'Bearer [redacted]', message)
    return message[:2000]
