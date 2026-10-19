"""Open the seed-treatment database locally. No collection or external writes."""
import argparse
import functools
import http.server
import pathlib
import sys
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        print('Use Python 3.11 or newer.', file=sys.stderr)
        return 1
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535')
    handler = functools.partial(Handler, directory=str(ROOT / 'static'))
    try:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    except OSError as exc:
        print(f'Could not start on port {args.port}: {exc}. Try --port 8081.', file=sys.stderr)
        return 1
    url = f'http://127.0.0.1:{args.port}'
    print(f'Open {url}\nPress Ctrl+C to stop. Source updates are not running.', flush=True)
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
