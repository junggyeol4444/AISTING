"""Manually run all bundled Tk GUI smokes with isolated disposable user dirs.

Requires an existing GUI display (on Linux: run with xvfb-run -a). No install,
external API, OBS, real broadcast or account interaction is performed here.
The individual smoke scripts are responsible for mocking sensitive services.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / 'scripts').glob('gui_*smoke.py'))


def main() -> int:
    passed, failed = 0, []
    for index, script in enumerate(SCRIPTS, 1):
        with tempfile.TemporaryDirectory(prefix='aisting_gui_isolated_') as directory:
            env = os.environ.copy()
            env.update({
                'HOME': directory,
                'USERPROFILE': directory,
                'LOCALAPPDATA': directory,
                'PYTHONPATH': str(ROOT / 'src'),
                'PYTHONWARNINGS': 'always::ResourceWarning',
                'PYTHONUTF8': '1',
                'TERM': 'xterm',
            })
            started = time.monotonic()
            try:
                result = subprocess.run(
                    [sys.executable, str(script)], cwd=ROOT, env=env,
                    capture_output=True, text=True, errors='replace', timeout=45,
                )
                elapsed = time.monotonic() - started
                warning_count = (result.stdout + result.stderr).count('ResourceWarning')
                if result.returncode == 0 and warning_count == 0:
                    passed += 1
                    print(f'PASS {index:03d}/{len(SCRIPTS):03d} {script.name} ({elapsed:.2f}s)', flush=True)
                else:
                    failed.append(script.name)
                    print(f'FAIL {index:03d}/{len(SCRIPTS):03d} {script.name} rc={result.returncode} '
                          f'warning={warning_count} ({elapsed:.2f}s)\n{result.stdout}\n{result.stderr}', flush=True)
            except subprocess.TimeoutExpired as exc:
                failed.append(script.name)
                print(f'TIMEOUT {index:03d}/{len(SCRIPTS):03d} {script.name} ({exc.timeout}s)', flush=True)
    print(f'SUMMARY: {passed}/{len(SCRIPTS)} PASS, {len(failed)} FAIL; failures={failed}', flush=True)
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
