"""Run local tests and build the preview, from any working directory."""
import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-node', action='store_true', help='Fail instead of skipping JavaScript checks when Node.js is absent')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        print('Tests require Python 3.11 or newer.', file=sys.stderr)
        return 1
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo('America/Chicago')
        except ZoneInfoNotFoundError:
            print('Timezone data is missing. Run: python -m pip install tzdata', file=sys.stderr)
            return 1
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, 'build_preview.py'], cwd=ROOT, check=True)
        node = shutil.which('node')
        if not node:
            print('SKIPPED: JavaScript checks require Node.js 22 or newer. Python tests and preview build passed.')
            return 1 if args.require_node else 0
        major = int(subprocess.check_output([node, '--version'], text=True).strip().lstrip('v').split('.')[0])
        if major < 22:
            print('JavaScript checks require Node.js 22 or newer.', file=sys.stderr)
            return 1
        subprocess.run([node, 'tests/logic_test.cjs'], cwd=ROOT, check=True)
        subprocess.run([node, 'tests/live_catalog_test.cjs'], cwd=ROOT, check=True)
        print('PASS: Python tests, preview build, and JavaScript logic checks. No source refresh was performed.')
        return 0
    except subprocess.CalledProcessError as exc:
        print(f'Test or build failed (exit {exc.returncode}). See the output above.', file=sys.stderr)
        return exc.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())

