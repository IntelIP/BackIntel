"""Local demonstration targets and a durable inbox; never exposes real business policy."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sqlite3
import uuid


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def serve(targets, database, port=0, drop_first_ack=False):
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, payload TEXT NOT NULL, receipt TEXT NOT NULL)')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value):
            encoded = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if self.path == '/targets':
                self.reply(200, json.loads(targets.read_text()))
            elif self.path.startswith('/deliveries/'):
                with sqlite3.connect(database) as connection:
                    row = connection.execute('SELECT receipt FROM deliveries WHERE id=?', (self.path.split('/')[-1],)).fetchone()
                self.reply(200 if row else 404, json.loads(row[0]) if row else {'error': 'Unknown receipt'})
            else:
                self.reply(404, {'error': 'Unknown path'})

        def do_POST(self):
            if self.path != '/deliveries':
                self.reply(404, {'error': 'No business-record write endpoint exists'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 262144:
                    raise ValueError('Invalid payload size')
                value = json.loads(self.rfile.read(length))
                if (set(value) != {'delivery_id', 'result_id', 'result_sha256', 'finding'}
                        or value['result_sha256'] != digest(value['finding'])
                        or value['finding']['id'] != value['result_id']
                        or value['finding']['status'] != 'accepted' or value['finding']['demonstration'] is not True):
                    raise ValueError('Only accepted demonstration findings are supported')
                fingerprint = digest(value)
                with sqlite3.connect(database) as connection:
                    connection.execute('BEGIN IMMEDIATE')
                    prior = connection.execute('SELECT sha256,receipt FROM deliveries WHERE id=?', (value['delivery_id'],)).fetchone()
                    if prior:
                        if prior[0] != fingerprint:
                            self.reply(409, {'error': 'Delivery identity conflicts with its retained finding'})
                            return
                        receipt = json.loads(prior[1])
                    else:
                        receipt = {key: value[key] for key in ('delivery_id', 'result_id', 'result_sha256')}
                        receipt.update(status='accepted', receipt_id=str(uuid.uuid4()), accepted_at=datetime.now(timezone.utc).isoformat())
                        connection.execute('INSERT INTO deliveries VALUES(?,?,?,?)',
                            (value['delivery_id'], fingerprint, json.dumps(value), json.dumps(receipt)))
                if drop_first_ack and prior is None:
                    self.reply(503, {'error': 'Simulated lost acknowledgement after durable acceptance'})
                else:
                    self.reply(200, receipt)
            except (ValueError, KeyError, TypeError):
                self.reply(400, {'error': 'Invalid demonstration finding'})

    server = HTTPServer(('127.0.0.1', port), Handler)
    print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port)}), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--drop-first-ack', action='store_true')
    args = parser.parse_args()
    serve(args.targets, args.database, args.port, args.drop_first_ack)
