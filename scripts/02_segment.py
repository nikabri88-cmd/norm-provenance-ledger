#!/usr/bin/env python3
"""Segment and number the judge inputs into the three corpora used in the study, and verify their SHA-256
against the values frozen in the pre-registration (preregistration/hashes.txt)."""
import hashlib, json, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).parent)); import segment_lib as seg
BUILD=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'build'); OUT=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'build/corpus'); OUT.mkdir(parents=True,exist_ok=True)
SEL=pathlib.Path(__file__).resolve().parent.parent/'data'/'selection'
def rows_for(A,B):
    rows=[]
    for rid in A:
        m,info=seg.build_A(BUILD/'judge_inputs_A'/f'{rid}.json'); m=seg.num(m); rows.append({'id':f'A:{rid}','metadata':{'stratum':'A','n_blocks':len(m),**info},'messages':m})
    for rid in B:
        m,info=seg.build_B(BUILD/'judge_inputs_B'/f'{rid}.json'); m=seg.num(m); rows.append({'id':f'B:{rid}','metadata':{'stratum':'B','n_blocks':len(m),**info},'messages':m})
    return rows
expected={'pilot_10_numbered.jsonl':'17c8dbb634e1b524fa08940a3f0bfa825f5575b3cb8ece4e6c1eee4737695f72',
          'reliability_30_numbered.jsonl':'ef9f33c1f8a2ceaa521b03b09d61681ee0095cadc2991bec59c522f12c180f3e',
          'full_71_numbered.jsonl':'060042041e6af26c46575a15a78ed9874ceb629332963c50391893b00db02cec'}
p=json.load(open(SEL/'pilot_10.json')); r=json.load(open(SEL/'reliability_30_selection.json')); f=json.load(open(SEL/'full_71_selection.json'))
sets={'pilot_10_numbered.jsonl':([x['id'] for x in p['A']],[x['id'] for x in p['B']]),'reliability_30_numbered.jsonl':(r['A'],r['B']),'full_71_numbered.jsonl':(f['A'],f['B'])}
ok=True
for fn,(A,B) in sets.items():
    with open(OUT/fn,'w',encoding='utf-8') as fh:
        for row in rows_for(A,B): fh.write(json.dumps(row,ensure_ascii=False)+'\n')
    h=hashlib.sha256((OUT/fn).read_bytes()).hexdigest(); match=h==expected[fn]; ok&=match
    print(fn, h[:16], 'matches pre-registration' if match else 'MISMATCH')
sys.exit(0 if ok else 1)
