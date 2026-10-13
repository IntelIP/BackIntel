"""Serve the current web app's local support check without database or provider calls."""
from __future__ import annotations

import argparse
import csv
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import mimetypes
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit

from scripts.sprint3_support_analysis import analyze, markdown

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1_048_576
MAX_TICKETS = 10_000
REQUIRED_COLUMNS = {'ticket_id', 'channel', 'resolution_time_hours'}


class SupportHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, web_dir: Path, **kwargs):
        self.web_dir = web_dir.resolve()
        super().__init__(*args, **kwargs)

    def log_message(self, *_):
        pass

    def reply(self, body: bytes, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def error(self, message, status=400):
        self.reply(json.dumps({'detail': message}).encode(), status)

    def local_request(self):
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            self.error('Open this check through its local address.', 403)
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://{host}' for host in hosts}:
            self.error('Requests from another website are not allowed.', 403)
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        path = unquote(urlsplit(self.path).path)
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/support')
            self.end_headers()
            return
        if path == '/support':
            file = self.web_dir / 'index.html'
        elif path == '/sample.csv':
            file = ROOT / 'docs/demo/Sprint3SupportTickets.csv'
        elif path.startswith('/assets/'):
            file = (self.web_dir / path.lstrip('/')).resolve()
            if not file.is_relative_to(self.web_dir / 'assets'):
                self.error('File not found.', 404)
                return
        else:
            self.error('File not found.', 404)
            return
        if not file.is_file():
            self.error('Build apps/web before opening this check.', 503)
            return
        content_type = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        self.reply(file.read_bytes(), content_type=content_type)

    def do_POST(self):
        if not self.local_request():
            return
        if urlsplit(self.path).path != '/api/support-check':
            self.error('Not found.', 404)
            return
        if self.headers.get('Transfer-Encoding'):
            self.error('Send a CSV with a known file size.')
            return
        length = self.headers.get('Content-Length', '')
        if not length.isdecimal() or not 0 < int(length) <= MAX_BYTES:
            self.error('Choose a nonempty CSV no larger than 1 MB.', 413)
            return
        if self.headers.get('Content-Type', '').split(';')[0] != 'text/csv':
            self.error('Choose a CSV file.', 415)
            return
        body = self.rfile.read(int(length))
        if len(body) != int(length):
            self.error('The complete file was not received. Choose it again.')
            return
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
                    raise ValueError('Choose a CSV with at most 10,000 tickets.')
                if None in row or any(not (row.get(key) or '').strip() for key in REQUIRED_COLUMNS):
                    raise ValueError('Every ticket needs an identity, a queue, and resolution hours.')
            if not count:
                raise ValueError('The CSV contains no tickets.')
            sample = (ROOT / 'docs/demo/Sprint3SupportTickets.csv').read_bytes()
            with TemporaryDirectory(prefix='backintel-support-') as directory:
                source = Path(directory) / 'input.csv'
                source.write_bytes(body)
                result = analyze(source, fictional=body == sample)
            result['markdown'] = markdown(result, include_file_links=False)
            self.reply(json.dumps(result, allow_nan=False).encode())
        except UnicodeError:
            self.error('Choose a CSV saved as UTF-8.')
        except (csv.Error, KeyError):
            self.error('The CSV could not be read. Check its columns and values.')
        except OverflowError:
            self.error('Resolution hours are too large to calculate safely.')
        except ValueError as error:
            self.error(str(error))


def server(port: int, web_dir: Path = ROOT / 'apps/web/dist'):
    return ThreadingHTTPServer(('127.0.0.1', port), partial(SupportHandler, web_dir=web_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=2055)
    args = parser.parse_args()
    web_dir = ROOT / 'apps/web/dist'
    if not (web_dir / 'index.html').is_file():
        parser.error('Run npm run build --prefix apps/web before starting this check.')
    with server(args.port, web_dir) as application:
        print(f'BackIntel support check: http://127.0.0.1:{application.server_port}/support', flush=True)
        try:
            application.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
