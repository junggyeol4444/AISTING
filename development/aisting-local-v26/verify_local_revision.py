"""Offline package inspection. No Github operations, no installation or streaming."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent

def main() -> int:
    report=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    files=report['files']
    bad=[]
    for rel, expected in sorted(files.items()):
        file=ROOT/rel
        if not file.is_file():
            bad.append(f'{rel}: missing')
        elif hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            bad.append(f'{rel}: digest mismatch')
    if bad:
        for error in bad:print('FAILED',error,file=sys.stderr)
        return 1
    for rel in files:
        if rel.endswith('.py'):
            compile((ROOT/rel).read_text('utf-8'),str(ROOT/rel),'exec')
    print(f'PASS local package integrity: {len(files)} source/docs/test/evidence files. This is NOT a real model/broadcast test.')
    return 0

if __name__=='__main__':raise SystemExit(main())
