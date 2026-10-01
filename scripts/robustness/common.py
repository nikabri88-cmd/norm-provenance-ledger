import json, re, random, sys
from collections import defaultdict, Counter
import os, pathlib; REPO=str(pathlib.Path(__file__).resolve().parents[2])
os.makedirs(os.environ.get('NPL_OUT','reproduced'),exist_ok=True)
sys.path.insert(0,REPO+'/scripts'); import ledger_metrics as LM
corp={}
for fn in ['reliability_30_numbered.jsonl','full_71_numbered.jsonl']:
    for l in open(os.path.join(os.environ.get('NPL_BUILD','build'),'corpus',fn)): r=json.loads(l); corp[r['id']]=r
A={('A:'+r['id']):r for r in json.load(open(REPO+'/data/selection/A_index.json'))}
B={('B:'+k):v for k,v in json.load(open(REPO+'/data/selection/B_mast_labels.json')).items()}
L={j:{r['run_id']:r for r in json.load(open(f'{REPO}/results/final/ledgers_all_{j}.json'))} for j in ['j1','j2']}
rel=json.load(open(REPO+'/data/selection/reliability_30_selection.json')); REL30={'A:'+x for x in rel['A']}|{'B:'+x for x in rel['B']}
full=json.load(open(REPO+'/data/selection/full_71_selection.json')); FULL71={'A:'+x for x in full['A']}|{'B:'+x for x in full['B']}
common=sorted(set(L['j1'])&set(L['j2']))
def corpus_of(rid):
    if rid.startswith('A'): return 'tau2'
    return B[rid]['system']
def ntype(j,rid): return {n['norm_id']:n.get('norm_type','conduct') for n in L[j][rid]['ledger']['norms']}
def events(j,rid,W=6):
    """classified events with distance, kind, block, norm_type"""
    return LM.classify(L[j][rid]['ledger'],W)
