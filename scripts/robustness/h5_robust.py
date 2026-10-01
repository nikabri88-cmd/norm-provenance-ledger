from common import *
import numpy as np, pandas as pd, statsmodels.formula.api as smf, statsmodels.api as sm
random.seed(20260930)
def rows(j, rids):
    out=[]
    for rid in rids:
        if not rid.startswith('A'): continue
        msgs=corp[rid]['messages']; ev=events(j,rid); turns=[i for i,m in enumerate(msgs) if m['role']=='assistant']
        press=[e['block'] for e in ev if e['class']=='pressure']
        viol=[e['block'] for e in ev if e['class']=='violation' and e.get('norm_type') in ('conduct','role')]
        a=A[rid]
        if press:
            fp=min(press); ta=[i for i in turns if i>fp]
            if not ta: continue
            out.append(dict(rid=rid,task=a['task_id'],cell=f"{a['model'][:6]}|{a['domain']}",model=a['model'][:6],domain=a['domain'],p=1,v=sum(b>fp for b in viol),t=len(ta),n_turns=len(turns)))
        else:
            out.append(dict(rid=rid,task=a['task_id'],cell=f"{a['model'][:6]}|{a['domain']}",model=a['model'][:6],domain=a['domain'],p=0,v=len(viol),t=len(turns),n_turns=len(turns)))
    return pd.DataFrame(out)
def perm(df,B=10000):
    r=df.v/df.t; obs=r[df.p==1].mean()-r[df.p==0].mean(); cnt=0
    for _ in range(B):
        pp=df.groupby('cell')['p'].transform(lambda s: np.random.permutation(s.values))
        d=r[pp==1].mean()-r[pp==0].mean()
        cnt+= d>=obs-1e-12
    return dict(n=len(df),with_pressure=int(df.p.sum()),rate_p=round(float(r[df.p==1].mean()),3),rate_np=round(float(r[df.p==0].mean()),3),p=round(cnt/B,4))
def poisson(df):
    d=df.copy(); d['logt']=np.log(d.t); d['logn']=np.log(d.n_turns)
    try:
        m=smf.glm('v ~ p + model + domain + logn',d,family=sm.families.Poisson(),offset=d.logt).fit(cov_type='cluster',cov_kwds={'groups':pd.factorize(d.task+d.domain)[0]})
        return dict(rate_ratio=round(float(np.exp(m.params['p'])),2),ci=[round(float(np.exp(x)),2) for x in m.conf_int().loc['p']],p=round(float(m.pvalues['p']),4))
    except Exception as ex: return str(ex)[:150]
np.random.seed(20260930)
res={}
for j in ['j1','j2']:
    df=rows(j,sorted(L[j])); df71=rows(j,sorted(r for r in L[j] if r in FULL71))
    # task-matched: tasks having both a pressure and a no-pressure trajectory (same model x domain cell)
    tm=df.groupby(['cell','task']).p.agg(['min','max']); tasks=[k for k,v in tm.iterrows() if v['min']==0 and v['max']==1]
    res[j]={'all':perm(df),'poisson_adjusted':poisson(df),'untouched71':perm(df71),'untouched71_poisson':poisson(df71),'task_matched_pairs_available':len(tasks)}
json.dump(res,open(os.path.join(os.environ.get('NPL_OUT','reproduced'),'h5_robust.json'),'w'),indent=1)
for j,v in res.items(): print(j,json.dumps(v))
