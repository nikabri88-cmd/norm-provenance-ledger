from common import *
from scipy.stats import mannwhitneyu, binomtest
import numpy as np, pandas as pd, statsmodels.formula.api as smf
out={}
def collect(j, rids, kinds_comp=('applied','stated_by_agent')):
    rows=[]
    for rid in rids:
        n=L[j][rid]['n_blocks']
        for e in events(j,rid):
            if e['distance'] is None or e.get('norm_type','conduct') not in ('conduct','role'): continue
            if e['class']=='violation': y=1
            elif e['class'] in ('near','distant') and e['kind'] in kinds_comp: y=0
            else: continue
            rows.append(dict(rid=rid,corpus=corpus_of(rid),y=y,dist=e['distance'],dnorm=e['distance']/n,pos=e['block']/n,n=n))
    return pd.DataFrame(rows)
def pooled(df):
    v=df[df.y==1].dist; c=df[df.y==0].dist
    if len(v)==0 or len(c)==0: return None
    return dict(n_comp=len(c),n_viol=len(v),med_comp=float(np.median(c)),med_viol=float(np.median(v)),p=float(mannwhitneyu(v,c,alternative='greater').pvalue))
def within(df,col='dist'):
    pos=neg=0
    for rid,g in df.groupby('rid'):
        v=g[g.y==1][col]; c=g[g.y==0][col]
        if len(v) and len(c):
            d=np.median(v)-np.median(c)
            pos+= d>0; neg+= d<0
    return dict(viol_farther=int(pos),viol_closer=int(neg),p=float(binomtest(int(pos),int(pos+neg),0.5,alternative='greater').pvalue) if pos+neg else None)
def logit(df):
    # violation ~ normalized distance + relative position, cluster-robust by trace
    d=df.copy(); d['dz']=(d.dnorm-d.dnorm.mean())/d.dnorm.std(); d['pz']=(d.pos-d.pos.mean())/d.pos.std()
    try:
        m=smf.logit('y ~ dz + pz',d).fit(disp=0,cov_type='cluster',cov_kwds={'groups':pd.factorize(d.rid)[0]})
        return {k:dict(coef=round(float(m.params[k]),3),p=float(m.pvalues[k])) for k in ['dz','pz']}
    except Exception as ex: return str(ex)[:120]
for j in ['j1','j2']:
    res={}
    for label,kinds in [('applied+stated (as pre-registered)',('applied','stated_by_agent')),('applied only',('applied',))]:
        df=collect(j,sorted(L[j]),kinds)
        res[label]={'pooled':pooled(df),'within_trace':within(df),'within_trace_normalized':within(df,'dnorm'),'logit_dist_and_position':logit(df),
                    'by_corpus':{c:{'pooled':pooled(g),'within':within(g)} for c,g in df.groupby('corpus')}}
    df71=collect(j,sorted(r for r in L[j] if r in FULL71),('applied',))
    res['applied only, untouched 71']={'pooled':pooled(df71),'within_trace':within(df71)}
    out[j]=res
json.dump(out,open(os.path.join(os.environ.get('NPL_OUT','reproduced'),'h1_robust.json'),'w'),indent=1,default=str)
for j in out:
    print('=====',j)
    for k,v in out[j].items():
        print(' --',k); 
        for kk,vv in v.items(): print('    ',kk,':',json.dumps(vv,default=str)[:300])
