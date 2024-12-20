import os
import json
import logging
from itertools import groupby
from http.server import BaseHTTPRequestHandler, HTTPServer
from .status import _get_metadata_list
from .tunnel import TunnelManager

logger = logging.getLogger(__name__)

def do_dashboard(config):
    class CustomHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                with open(os.path.join(os.path.dirname(__file__), 'dashboard.html'), 'rb') as f:
                    content = f.read()
                self.wfile.write(content)
            elif self.path == '/favicon.png':
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                with open(os.path.join(os.path.dirname(__file__), 'blake-verdoorn-cssvEZacHvQ-unsplash-resized.png'), 'rb') as f:
                    content = f.read()
                self.wfile.write(content)
            elif self.path == '/data.json':
                self.send_response(200)
                self.send_header('Content-type', 'text/json')
                self.end_headers()
                metadata_list = _get_metadata_list(config['commit'])

                grouped_tunnels = {
                    name: list(tunnels)
                    for name, tunnels in groupby(tunnel_manager.tunnels, key=lambda t: t.name)
                }
                start_list = [
                    {
                        'name': name,
                        'zone': tunnels[0].zone,
                        'tunnels': [
                            { 'local_port': t.local_port, 'remote_port': t.remote_port }
                            for t in tunnels
                        ],
                    }
                    for name, tunnels in grouped_tunnels.items()
                ]

                data = {
                    'config': config,
                    'metadata_list': metadata_list,
                    'start_list': start_list,
                }
                self.wfile.write(json.dumps(data, indent=4, sort_keys=True).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")


    tunnel_manager = TunnelManager(config['dashboard']['tunnel'])

    host = "0.0.0.0"
    port = 8000
    server = HTTPServer((host, port), CustomHandler)
    logger.info(f"Serving on http://{host}:{port}")
    server.serve_forever()
