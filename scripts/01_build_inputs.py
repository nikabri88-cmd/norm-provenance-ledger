#!/usr/bin/env python3
"""Rebuild judge inputs A (tau2) and B (MAST) exactly as in the study, from the downloaded public sources.
Selection logic is copied from the corpus audit (build_package.py) and select_B.py; only file I/O is simplified."""
import hashlib, json, pathlib, random, sys
ROOT=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); OUT=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'build').resolve()
SEED=20260930
sha=lambda b: hashlib.sha256(b).hexdigest()
def dump(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
# ---- A: tau2
selected=[]
for p in sorted((ROOT/'sources'/'submissions').glob('*/trajectories/*_default_*')):
    x=json.loads(p.read_text()); info=x['info']; env=info['environment_info']
    tasks={t['id']:t for t in x['tasks']}; model=info['agent_info']['llm']; domain=env['domain_name']
    for reward in [0,1]:
        pool=sorted([s for s in x['simulations'] if s.get('reward_info',{}).get('reward')==reward],key=lambda s:s['id'])
        rng=random.Random(f'{SEED}|A|{model}|{domain}|{reward}')
        for s in rng.sample(pool,5): selected.append(dict(model=model,domain=domain,reward=reward,simulation=s,info=info))
random.Random(f'{SEED}|A|neutral-order').shuffle(selected)
for i,r in enumerate(selected):
    clean={'policy':r['info']['environment_info']['policy'],'tool_defs':r['info']['environment_info']['tool_defs'],'messages':[{k:m[k] for k in ['role','content','tool_calls','tool_call_id','name'] if k in m} for m in r['simulation']['messages']]}
    dump(OUT/'judge_inputs_A'/f'run_{i+1:03d}.json',clean)
# ---- B: MAST
rows=json.loads((ROOT/'mast_full.json').read_text())
idx=json.loads((ROOT/'B_index.json').read_text())   # published selection (row_index, id)
for r in idx:
    rec=rows[r['row_index']]
    assert sha(rec['trace']['trajectory'].encode())==r['body_sha256'], r['id']
    dump(OUT/'judge_inputs_B'/f"{r['id']}.json",{'id':r['id'],'trajectory':rec['trace']['trajectory']})
print('built', len(selected), 'A inputs and', len(idx), 'B inputs into', OUT)
