#!/usr/bin/env python3
"""Download the public source files (tau2-bench leaderboard trajectories, MAST-Data) and verify SHA-256."""
import hashlib, json, pathlib, sys, urllib.request
DEST=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'sources_root'); DEST.mkdir(parents=True,exist_ok=True)
S=json.load(open(pathlib.Path(__file__).resolve().parent.parent/'data'/'sources.json'))
items=S['tau2']+[S['mast']]; ok=True
for it in items:
    p=DEST/it['path']; p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        print('downloading',it['url']); urllib.request.urlretrieve(it['url'],p)
    h=hashlib.sha256(p.read_bytes()).hexdigest(); good=h==it['sha256']; ok&=good
    print(('OK  ' if good else 'BAD ')+it['path'])
sys.exit(0 if ok else 1)
