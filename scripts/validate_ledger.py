"""Semantic pre-metrics gate. Citation presence/range is not proof of a contradiction."""
import re,json,argparse

def validate(run,allow_legacy=False):
    errors=[];L=run['ledger'];n=run.get('n_blocks')
    if not isinstance(n,int) or isinstance(n,bool) or n<=0:return ['n_blocks must be a positive integer']
    def block(b,label):
        if not isinstance(b,int) or isinstance(b,bool) or not 0<=b<n:errors.append(label+': block outside transcript')
    norms=L.get('norms',[]);auth=L.get('authored_rules',[])
    ni=[x['norm_id'] for x in norms];ai=[x['norm_id'] for x in auth]
    if len(ni)!=len(set(ni)) or len(ai)!=len(set(ai)):errors.append('duplicate norm IDs within a list')
    for x in norms:
        if x['source_type']=='none':
            if x['source_block']!=-1:errors.append('unsourced norm source_block must be -1')
        else:block(x['source_block'],'source')
    seen=set()
    for e in L.get('events',[]):
        block(e['block'],'event');k=(e['norm_id'],e['kind'],e['block'])
        if k in seen:errors.append('duplicate event')
        seen.add(k)
        if e['norm_id'] not in set(ni+ai):errors.append('unknown event norm_id')
        if e['kind']=='violated' and not isinstance(e.get('acknowledged'),bool):errors.append('violation needs acknowledged boolean')
        if e.get('holder') not in (None,'H','D','P','O'):errors.append('bad holder')
    for a in auth:
        block(a['block'],'authored')
        if a['subtype']=='fabricated_external_constraint' and not allow_legacy:errors.append('legacy subtype requires evidence-based recoding')
        if a['subtype']=='contradicted_external_constraint':
            ev=a.get('contradicting_evidence','');refs=re.findall(r'\[B(\d+)\]',ev)
            if not ev.strip() or not refs:errors.append('contradicted requires positive evidence and [B<n>] citations')
            for b in refs:block(int(b),'contradiction citation')
    return errors

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('path');ap.add_argument('--allow-legacy',action='store_true');a=ap.parse_args()
    data=json.load(open(a.path));runs=data if isinstance(data,list) else [data]
    bad=[{'run_id':r.get('run_id'),'errors':e} for r in runs if (e:=validate(r,a.allow_legacy))]
    print(json.dumps({'checked':len(runs),'invalid':bad},indent=2));raise SystemExit(bool(bad))
