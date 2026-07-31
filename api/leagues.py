import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        leagues = [
            {"id": "mls", "name": "Major League Soccer", "flag": "🇺🇸"},
            {"id": "eliteserien", "name": "Eliteserien", "flag": "🇳🇴"},
            {"id": "premiership", "name": "Premiership", "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿"},
            {"id": "superliga-denmark", "name": "Superliga", "flag": "🇩🇰"}
        ]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        self.wfile.write(json.dumps(leagues).encode('utf-8'))
        return
