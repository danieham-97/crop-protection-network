"""Exercise CI browser setup and failure propagation without network or Docker."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('bash'), 'Browser CI runner requires Bash')
class BrowserRunnerTests(unittest.TestCase):
    def exercise(self, *, pull_failures=0, npm_exit=0, browser_exit=0):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            app = root / 'app with spaces'
            app.mkdir()
            script = app / 'run_browser_tests.sh'
            shutil.copyfile(ROOT / script.name, script)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            log = root / 'commands.jsonl'
            mock = '''import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
with open(os.environ['MOCK_LOG'], 'a') as out:
    out.write(json.dumps([name, *sys.argv[1:]]) + '\\n')
if name == 'npm': sys.exit(int(os.environ['MOCK_NPM_EXIT']))
if name == 'docker' and sys.argv[1] == 'pull':
    path = pathlib.Path(os.environ['MOCK_PULL_COUNT'])
    count = int(path.read_text()) + 1 if path.exists() else 1
    path.write_text(str(count))
    sys.exit(1 if count <= int(os.environ['MOCK_PULL_FAILURES']) else 0)
if name == 'docker' and sys.argv[1] == 'run':
    sys.exit(int(os.environ['MOCK_BROWSER_EXIT']))
'''
            for name in ('npm', 'docker', 'sleep'):
                path = bin_dir / name
                path.write_text('#!' + sys.executable + '\n' + mock)
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(bin_dir)+os.pathsep+os.environ['PATH'],
                       MOCK_LOG=str(log), MOCK_PULL_COUNT=str(root/'pulls'),
                       MOCK_PULL_FAILURES=str(pull_failures), MOCK_NPM_EXIT=str(npm_exit),
                       MOCK_BROWSER_EXIT=str(browser_exit))
            result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            return result, calls

    def test_transient_pull_failure_recovers_and_runs_matching_browser(self):
        result, calls = self.exercise(pull_failures=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        pulls = [c for c in calls if c[:2] == ['docker', 'pull']]
        runs = [c for c in calls if c[:2] == ['docker', 'run']]
        self.assertEqual(len(pulls), 2)
        self.assertEqual(len(runs), 1)
        version = calls[0][-1].split('@')[1]
        self.assertEqual(pulls[0][-1], f'mcr.microsoft.com/playwright:v{version}-noble')
        self.assertIn(pulls[0][-1], runs[0])
        self.assertEqual(runs[0][-2:], ['node', 'tests/ui_test.cjs'])
        self.assertIn('--user', runs[0])
        self.assertTrue(any('app with spaces:/work' in arg for arg in runs[0]))

    def test_exhausted_pulls_fail_without_running_tests(self):
        result, calls = self.exercise(pull_failures=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(c[:2] == ['docker', 'pull'] for c in calls), 3)
        self.assertFalse(any(c[:2] == ['docker', 'run'] for c in calls))

    def test_browser_failure_is_not_retried_or_hidden(self):
        result, calls = self.exercise(browser_exit=7)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(sum(c[:2] == ['docker', 'run'] for c in calls), 1)

    def test_package_failure_stops_browser_setup(self):
        result, calls = self.exercise(npm_exit=9)
        self.assertEqual(result.returncode, 9)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
