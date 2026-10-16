"""Configured scalar conversions. Executed only inside the preparation sandbox."""
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def convert(value, operation):
    if operation == 'preserve' or value is None or value == '' or isinstance(value, str) and not value.strip():
        return value
    if operation == 'decimal':
        if isinstance(value, bool):
            raise ValueError('Boolean is not a quantity or price')
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError('Non-finite numeric value')
        return str(result)
    if operation in ('month_first', 'day_first'):
        match = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?', str(value))
        if not match:
            raise ValueError('Unsupported source date format')
        first, second, year, hour, minute, second_value = [int(item or 0) for item in match.groups()]
        month, day = (first, second) if operation == 'month_first' else (second, first)
        return datetime(year, month, day, hour, minute, second_value).isoformat()
    if operation == 'iso':
        return datetime.fromisoformat(str(value)).isoformat()
    raise ValueError('Unknown configured conversion')


def transform(snapshot):
    recipe = snapshot['recipe']
    if recipe['version'] != 1 or recipe['on_error'] not in ('stop', 'retain_unresolved'):
        raise ValueError('Unsupported preparation recipe')
    tables = {(table['schema'], table['table']): table for table in recipe['tables']}
    pages, failure_count, affected_rows = [], 0, 0
    for page in snapshot['pages']:
        table = tables[(page['schema'], page['table'])]
        if page['columns'] != [field['name'] for field in table['fields']]:
            raise ValueError('Source columns differ from the recipe')
        rows, unresolved = [], []
        for index, row in enumerate(page['rows']):
            if len(row) != len(table['fields']):
                raise ValueError('Source row width differs from the recipe')
            values, failed = [], []
            for field, value in zip(table['fields'], row):
                try:
                    values.append(convert(value, field['operation']))
                except (ValueError, InvalidOperation, TypeError, OverflowError):
                    values.append(value)
                    failed.append(field['name'])
                    failure_count += 1
            if failed:
                affected_rows += 1
                unresolved.append({'index': index, 'fields': failed})
            rows.append(values)
        pages.append({**page, 'rows': rows, 'unresolved': unresolved})
    return {'status': 'needs_repair' if failure_count and recipe['on_error'] == 'stop' else 'prepared',
            'pages': [] if failure_count and recipe['on_error'] == 'stop' else pages,
            'conversion_failures': failure_count, 'unresolved_rows': affected_rows}


if __name__ == '__main__':
    with open('/input/snapshot.json') as stream:
        result = transform(json.load(stream))
    print(json.dumps(result, separators=(',', ':'), allow_nan=False))
