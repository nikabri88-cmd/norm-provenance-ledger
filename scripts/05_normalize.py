#!/usr/bin/env python3
"""Rebuild the judge ledgers and metrics from the raw Docent exports + id maps (results/final/raw), and check
that they equal the published ledgers in results/final. Env: NPL_BUILD (numbered corpora), NPL_OUT."""
import json, os, pathlib, re, subprocess, sys
REPO=pathlib.Path(__file__).resolve().parent.parent; RAW=REPO/'results'/'final'/'raw'; BUILD=pathlib.Path(os.environ.get('NPL_BUILD','build'))
OUT=pathlib.Path(os.environ.get('NPL_OUT','reproduced')); OUT.mkdir(exist_ok=True)
corp={}
for fn in ['reliability_30_numbered.jsonl','full_71_numbered.jsonl']:
    for l in open(BUILD/'corpus'/fn): r=json.loads(l); corp[r['id']]=r
def flat(v):
    if isinstance(v,dict) and 'text' in v: return re.sub(r'\[T0B(\d+)(?::<RANGE>.*?</RANGE>)?\]', r'[B\1]', v['text'], flags=re.S)
    return v
ok=True
for j in ['j1','j2']:
    runs=[]
    for part in ['rel30','full71']:
        d=json.load(open(RAW/f'raw_{part}_{j}.json')); mp=json.load(open(RAW/f'id_map_{part}_{j}.json'))
        for res in d['results']:
            if not res['results'] or res['results'][0].get('output') is None: continue
            pid=mp[res['agent_run_id']]; o=res['results'][0]['output']
            L={'norms':[{**x,'text':flat(x['text'])} for x in o.get('norms',[])],'events':[{**e,'evidence':flat(e.get('evidence',''))} for e in o.get('events',[])],
               'authored_rules':[{**a,'text':flat(a['text']),'contradicting_evidence':flat(a.get('contradicting_evidence',''))} for a in o.get('authored_rules',[])],'notes':flat(o.get('notes',''))}
            runs.append({'run_id':pid,'stratum':pid[0],'n_blocks':len(corp[pid]['messages']),'ledger':L})
    runs.sort(key=lambda r:r['run_id']); p=OUT/f'ledgers_all_{j}.json'; json.dump(runs,open(p,'w'),ensure_ascii=False,indent=1)
    same=json.load(open(p))==json.load(open(REPO/'results'/'final'/f'ledgers_all_{j}.json')); ok&=same
    print(j,len(runs),'ledgers;','identical to published' if same else 'DIFFERENT from published')
    subprocess.run([sys.executable,str(REPO/'scripts'/'ledger_metrics.py'),str(p),'--sensitivity'],stdout=open(OUT/f'metrics_all_{j}.json','w'),check=True)
sys.exit(0 if ok else 1)
