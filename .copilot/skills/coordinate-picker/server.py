"""Coordinate picker server — serves picker.html and saves clicked coordinates."""
import http.server
import json
import os
import sys
import webbrowser
import threading

PORT = 9876
SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.tmp', 'coord-picker')
COORDS_FILE = os.path.join(SAVE_DIR, 'picked_coords.json')
SKILL_DIR = os.path.dirname(__file__)


class PickerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SKILL_DIR, **kwargs)

    def do_POST(self):
        if self.path == '/save-coords':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            os.makedirs(SAVE_DIR, exist_ok=True)
            with open(COORDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            print(f'[picker] Saved {len(data["points"])} points to {COORDS_FILE}')
            return

        if self.path == '/screenshot-path':
            # Return path to the latest screenshot
            img_path = os.path.join(SAVE_DIR, 'screenshot.png')
            exists = os.path.exists(img_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"exists": exists, "url": "/screenshot.png" if exists else None}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/screenshot.png':
            img_path = os.path.join(SAVE_DIR, 'screenshot.png')
            if os.path.exists(img_path):
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(img_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
        super().do_GET()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def main():
    # Clear old coordinates
    if os.path.exists(COORDS_FILE):
        os.remove(COORDS_FILE)

    server = http.server.HTTPServer(('127.0.0.1', PORT), PickerHandler)
    url = f'http://127.0.0.1:{PORT}/picker.html?autoload=1'
    print(f'[picker] Server started at http://127.0.0.1:{PORT}')
    print(f'[picker] Opening {url}')
    print(f'[picker] Coordinates will be saved to: {COORDS_FILE}')
    print(f'[picker] Press Ctrl+C to stop')

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[picker] Server stopped')
        server.server_close()


if __name__ == '__main__':
    main()
