"""Local-only Tkinter regression runner; Xvfb DISPLAY must already be available."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
paths = sorted((root / 'scripts').glob('gui_*smoke.py'))
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end = int(sys.argv[2]) if len(sys.argv) > 2 else len(paths)
chosen = paths[start:end]
env = dict(os.environ, PYTHONPATH=str(root / 'src'))

def invoke(path):
    try:
        proc = subprocess.run([sys.executable, str(path)], cwd=root, env=env,
                              capture_output=True, text=True, timeout=25)
        return path.name, proc.returncode, (proc.stdout + proc.stderr)[-1600:]
    except subprocess.TimeoutExpired:
        return path.name, 124, 'TIMEOUT (25 seconds)'

with ThreadPoolExecutor(max_workers=4) as pool:
    jobs = [pool.submit(invoke, path) for path in chosen]
    results = [f.result() for f in as_completed(jobs)]
results.sort()
for name, code, output in results:
    print(('PASS' if code == 0 else 'FAIL') + ' ' + name + ' exit=' + str(code))
    if code != 0:
        print(output)
passed = sum(code == 0 for _, code, _ in results)
print(f'GUI SLICE {start}:{end} — {passed}/{len(results)} PASS')
if passed != len(results):
    sys.exit(1)
