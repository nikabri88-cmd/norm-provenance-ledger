from common import *
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import cohen_kappa_score
from scipy.stats import mannwhitneyu, binomtest
np.random.seed(20260930); random.seed(20260930)
clean=lambda s: re.sub(r'\s*\[B\d+\]','',s or '')
# ---- semantic norm matching
texts=[clean(n['text']) for j in L for rid in common for n in L[j][rid]['ledger']['norms']]
vec=TfidfVectorizer(sublinear_tf=True,ngram_range=(1,2),min_df=1).fit(texts)
def ntext(j,rid): return {n['norm_id']:clean(n['text']) for n in L[j][rid]['ledger']['norms']}
def sem_events(rid,thr,kinds):
    """J1 events matched by a J2 event at same block, same kind, same norm type, and norm-text cosine >= thr"""
    t1,t2=ntext('j1',rid),ntext('j2',rid); nt1,nt2=ntype('j1',rid),ntype('j2',rid)
    e1=[e for e in events('j1',rid) if e['kind'] in kinds]; e2=[e for e in events('j2',rid) if e['kind'] in kinds]
    keep=[]
    for a in e1:
        cands=[b for b in e2 if b['block']==a['block'] and b['kind']==a['kind'] and nt2.get(b['norm_id'],'conduct')==nt1.get(a['norm_id'],'conduct')]
        if not cands: continue
        va=vec.transform([t1.get(a['norm_id'],'')]); best=None
        for b in cands:
            s=float((va@vec.transform([t2.get(b['norm_id'],'')]).T).toarray()[0,0])
            if best is None or s>best[0]: best=(s,b)
        if best[0]>=thr: keep.append((a,best[1]))
    return keep
res={'H1_semantic_consensus':{},'H5_semantic_consensus':{}}
for thr in [0.2,0.3,0.5]:
    comp=[];viol=[];tr={}
    for rid in common:
        for a,b in sem_events(rid,thr,{'applied','violated'}):
            if a.get('norm_type','conduct') not in ('conduct','role') or a['distance'] is None or b['distance'] is None: continue
            d=(a['distance']+b['distance'])/2
            (viol if a['kind']=='violated' else comp).append(d); tr.setdefault(rid,{'v':[],'c':[]})['v' if a['kind']=='violated' else 'c'].append(d)
    pos=sum(1 for x in tr.values() if x['v'] and x['c'] and np.median(x['v'])>np.median(x['c'])); neg=sum(1 for x in tr.values() if x['v'] and x['c'] and np.median(x['v'])<np.median(x['c']))
    res['H1_semantic_consensus'][thr]=dict(n_comp=len(comp),n_viol=len(viol),med_comp=float(np.median(comp)) if comp else None,med_viol=float(np.median(viol)) if viol else None,
        p_pooled=float(mannwhitneyu(viol,comp,alternative='greater').pvalue) if comp and viol else None,within_trace=f'{pos}/{pos+neg}',p_within=float(binomtest(pos,pos+neg,0.5,alternative='greater').pvalue) if pos+neg else None)
    # H5 semantic consensus
    rows=[]
    for rid in [r for r in common if r.startswith('A')]:
        msgs=corp[rid]['messages']; turns=[i for i,m in enumerate(msgs) if m['role']=='assistant']
        pb=sorted(a['block'] for a,b in sem_events(rid,thr,{'pressure'}))
        vb=[a['block'] for a,b in sem_events(rid,thr,{'violated'}) if a.get('norm_type','conduct') in ('conduct','role')]
        a_=A[rid]; cell=f"{a_['model'][:6]}|{a_['domain']}"
        if pb:
            ta=[i for i in turns if i>pb[0]]
            if not ta: continue
            rows.append((cell,1,sum(b>pb[0] for b in vb)/len(ta)))
        else: rows.append((cell,0,len(vb)/len(turns)))
    df=pd.DataFrame(rows,columns=['cell','p','r'])
    obs=df.r[df.p==1].mean()-df.r[df.p==0].mean(); cnt=0
    for _ in range(5000):
        pp=df.groupby('cell')['p'].transform(lambda s: np.random.permutation(s.values)); cnt+= (df.r[pp==1].mean()-df.r[pp==0].mean())>=obs-1e-12
    res['H5_semantic_consensus'][thr]=dict(n=len(df),with_pressure=int(df.p.sum()),rate_p=round(float(df.r[df.p==1].mean()),3),rate_np=round(float(df.r[df.p==0].mean()),3),p=round(cnt/5000,4))
# ---- promised reliability metrics on full common set
def blocks(j,rid,kind,excl_B_pressure=True):
    if kind=='pressure' and rid.startswith('B'): return set()
    return {e['block'] for e in L[j][rid]['ledger']['events'] if e['kind']==kind}
rel={}
for kind in ['violated','pressure']:
    y1=[];y2=[]
    for rid in common:
        b1,b2=blocks('j1',rid,kind),blocks('j2',rid,kind); n=L['j1'][rid]['n_blocks']
        y1+=[int(i in b1) for i in range(n)]; y2+=[int(i in b2) for i in range(n)]
    rel[f'block_kappa_{kind}']=round(cohen_kappa_score(y1,y2),3); rel[f'blocks_{kind}']=(sum(y1),sum(y2),sum(a&b for a,b in zip(y1,y2)))
M={j:{r['run_id']:r for r in json.load(open(f'{REPO}/results/final/metrics_all_{j}.json'))['W=6']['runs']} for j in ['j1','j2']}
pairs=[(int(M['j1'][k]['authored_external_contradicted']>0),int(M['j2'][k]['authored_external_contradicted']>0)) for k in common]
k0=cohen_kappa_score([a for a,_ in pairs],[b for _,b in pairs]); ks=[];undef=0
for _ in range(1000):
    s=[random.choice(pairs) for _ in pairs]; a=[x for x,_ in s]; b=[y for _,y in s]
    if len(set(a))<2 and len(set(b))<2: undef+=1; continue
    kk=cohen_kappa_score(a,b); 
    if kk==kk: ks.append(kk)
    else: undef+=1
ks.sort(); rel['kappa_contradicted']=dict(kappa=round(k0,3),ci95=[round(ks[int(.025*len(ks))],2),round(ks[int(.975*len(ks))-1],2)],undefined=undef)
pp=[(int(M['j1'][k]['pressure_events']>0),int(M['j2'][k]['pressure_events']>0)) for k in common if k.startswith('A')]
rel['trajectory_pressure_presence']=dict(j1=sum(a for a,_ in pp),j2=sum(b for _,b in pp),both=sum(a&b for a,b in pp),kappa=round(cohen_kappa_score([a for a,_ in pp],[b for _,b in pp]),3))
res['reliability_promised']=rel
# ---- B:run_070 check
r=[]
for j in ['j1','j2']:
    for a in L[j]['B:run_070']['ledger']['authored_rules']:
        if a['subtype']=='contradicted_external_constraint': r.append((j,a['block'],clean(a['text'])[:90]))
res['B_run_070']=r
json.dump(res,open(os.path.join(os.environ.get('NPL_OUT','reproduced'),'consensus_rel.json'),'w'),indent=1,ensure_ascii=False,default=str)
print(json.dumps(res,indent=1,ensure_ascii=False,default=str))
