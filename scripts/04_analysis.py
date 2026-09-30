#!/usr/bin/env python3
"""Recompute all pre-registered analyses (reliability, H1-H5) and post-hoc checks from the published judge ledgers.
Needs the numbered corpora (scripts 00-02) for agent-turn counts. Env: NPL_BUILD (default build), NPL_OUT (default reproduced)."""
import json, random, math, re
from collections import Counter, defaultdict
from scipy.stats import mannwhitneyu, spearmanr, binomtest
from sklearn.metrics import cohen_kappa_score
random.seed(20260930)
corp={}
import pathlib, os
REPO=pathlib.Path(__file__).resolve().parent.parent; BUILD=pathlib.Path(os.environ.get('NPL_BUILD','build'))
for fn in ['reliability_30_numbered.jsonl','full_71_numbered.jsonl']:
    for l in open(BUILD/'corpus'/fn): r=json.loads(l); corp[r['id']]=r
A={('A:'+r['id']):r for r in json.load(open(REPO/'data'/'selection'/'A_index.json'))}
B={('B:'+k):v for k,v in json.load(open(REPO/'data'/'selection'/'B_mast_labels.json')).items()}
L={j:{r['run_id']:r for r in json.load(open(REPO/'results'/'final'/f'ledgers_all_{j}.json'))} for j in ['j1','j2']}
M={j:{r['run_id']:r for r in json.load(open(REPO/'results'/'final'/f'metrics_all_{j}.json'))['W=6']['runs']} for j in ['j1','j2']}
import sys; sys.path.insert(0,str(REPO/'scripts')); import ledger_metrics as LM
common=sorted(set(L['j1'])&set(L['j2']))
out={}
def classified(j,rid): return LM.classify(L[j][rid]['ledger'],6)
def ntype(j,rid): return {n['norm_id']:n.get('norm_type','conduct') for n in L[j][rid]['ledger']['norms']}
def consensus_blocks(rid,kinds):
    s1={(e['block'],e['kind'],ntype('j1',rid).get(e['norm_id'],'conduct')) for e in L['j1'][rid]['ledger']['events'] if e['kind'] in kinds}
    s2={(e['block'],e['kind'],ntype('j2',rid).get(e['norm_id'],'conduct')) for e in L['j2'][rid]['ledger']['events'] if e['kind'] in kinds}
    return s1&s2
# ---------- reliability on full set
pairs=[(M['j1'][k]['distant_rate'],M['j2'][k]['distant_rate']) for k in common if M['j1'][k]['distant_rate'] is not None and M['j2'][k]['distant_rate'] is not None]
rho=spearmanr(*zip(*pairs)).correlation
bs=[]
for _ in range(1000):
    s=[random.choice(pairs) for _ in pairs]; a,b=zip(*s)
    if len(set(a))>1 and len(set(b))>1: bs.append(spearmanr(a,b).correlation)
bs.sort(); out['reliability']={'n_common':len(common),'spearman_distant_rate':round(rho,3),'n':len(pairs),'ci95':[round(bs[25],2),round(bs[974],2)]}
c1=[int(M['j1'][k]['authored_external_contradicted']>0) for k in common]; c2=[int(M['j2'][k]['authored_external_contradicted']>0) for k in common]
out['reliability']['contradicted_presence']={'j1':sum(c1),'j2':sum(c2),'agree':sum(a==b for a,b in zip(c1,c2)),'kappa':None if len(set(c1+c2))<2 else round(cohen_kappa_score(c1,c2),3)}
a1=[len(L['j1'][k]['ledger']['authored_rules']) for k in common]; a2=[len(L['j2'][k]['ledger']['authored_rules']) for k in common]
out['reliability']['authored_counts']={'j1':sum(a1),'j2':sum(a2),'spearman':round(spearmanr(a1,a2).correlation,3)}
# ---------- H1
def h1(j,consensus=False):
    comp=[];viol=[]
    for rid in (common if consensus else L[j]):
        nt=ntype(j,rid); cb=consensus_blocks(rid,{'applied','stated_by_agent','violated'}) if consensus else None
        for e in classified(j,rid):
            if e['class'] in ('near','distant','violation') and e['distance'] is not None and e.get('norm_type','conduct') in ('conduct','role'):
                if consensus and (e['block'],e['kind'],e.get('norm_type','conduct')) not in cb: continue
                (viol if e['class']=='violation' else comp).append(e['distance'])
    if not viol or not comp: return {'n_comp':len(comp),'n_viol':len(viol),'p':None}
    u=mannwhitneyu(viol,comp,alternative='greater')
    med=lambda x: sorted(x)[len(x)//2]
    return {'n_comp':len(comp),'n_viol':len(viol),'median_dist_comp':med(comp),'median_dist_viol':med(viol),'U':float(u.statistic),'p_one_sided':float(u.pvalue)}
out['H1']={'j1':h1('j1'),'j2':h1('j2'),'consensus':h1('j1',True)}
# ---------- H2 (A): contradicted presence vs reward, task-cluster permutation within model x domain
def h2(j,key='contradicted',rids=None):
    rows=[]
    for rid in (rids or [k for k in L[j] if k.startswith('A')]):
        m=M[j][rid]; x=m['authored_external_contradicted'] if key=='contradicted' else m['authored_external_contradicted']+m['authored_external_unsupported']
        a=A[rid]; rows.append((a['model'],a['domain'],a['task_id'],a['reward'],int(x>0)))
    def stat(rs):
        cells=defaultdict(list)
        for mo,do,t,rw,y in rs: cells[(mo,do)].append((t,rw,y))
        num=den=0
        for c,v in cells.items():
            r0=[y for _,rw,y in v if rw==0]; r1=[y for _,rw,y in v if rw==1]
            if not r0 or not r1: continue
            w=len({t for t,_,_ in v}); num+=w*(sum(r0)/len(r0)-sum(r1)/len(r1)); den+=w
        return num/den if den else float('nan')
    obs=stat(rows); cnt=0; B_=10000
    cells=defaultdict(lambda: defaultdict(list))
    for mo,do,t,rw,y in rows: cells[(mo,do)][t].append((rw,y))
    for _ in range(B_):
        perm=[]
        for c,tasks in cells.items():
            # permute reward bundles among tasks with equal trajectory counts; y stays with its task
            bysize=defaultdict(list)
            for t,v in tasks.items(): bysize[len(v)].append(t)
            for sz,ts in bysize.items():
                bundles=[[rw for rw,_ in tasks[t]] for t in ts]; random.shuffle(bundles)
                for t,bund in zip(ts,bundles):
                    for (rw,y),nrw in zip(tasks[t],bund): perm.append((c[0],c[1],t,nrw,y))
        if stat(perm)>=obs-1e-12: cnt+=1
    pos=sum(y for *_,y in rows)
    return {'n':len(rows),'positives':pos,'diff_reward0_minus_reward1':None if obs!=obs else round(obs,3),'p_perm_one_sided':None if obs!=obs else round(cnt/B_,4)}
out['H2']={'j1':h2('j1'),'j2':h2('j2'),'j1_sensitivity_union':h2('j1','union'),'j2_sensitivity_union':h2('j2','union')}
# ---------- H5 (A): violations per agent turn after first pressure vs no-pressure trajectories
def h5(j):
    rows=[];nozero=0
    for rid in [k for k in L[j] if k.startswith('A')]:
        msgs=corp[rid]['messages']; ev=classified(j,rid)
        press=[e['block'] for e in ev if e['class']=='pressure']
        viol=[e['block'] for e in ev if e['class']=='violation' and e.get('norm_type') in ('conduct','role')]
        turns=[i for i,m in enumerate(msgs) if m['role']=='assistant']
        if press:
            fp=min(press); t_after=[i for i in turns if i>fp]
            if not t_after: nozero+=1; continue
            rate=sum(1 for b in viol if b>fp)/len(t_after); p=1
        else:
            rate=len(viol)/len(turns) if turns else 0; p=0
        a=A[rid]; rows.append(((a['model'],a['domain']),p,rate))
    def stat(rs):
        p1=[r for _,p,r in rs if p==1]; p0=[r for _,p,r in rs if p==0]
        return (sum(p1)/len(p1)-sum(p0)/len(p0)) if p1 and p0 else float('nan')
    obs=stat(rows); cnt=0
    cells=defaultdict(list)
    for c,p,r in rows: cells[c].append((p,r))
    for _ in range(10000):
        perm=[]
        for c,v in cells.items():
            ps=[p for p,_ in v]; random.shuffle(ps); perm+=[(c,p,r) for p,(_,r) in zip(ps,v)]
        if stat(perm)>=obs-1e-12: cnt+=1
    n1=sum(1 for _,p,_ in rows if p==1)
    return {'n':len(rows),'with_pressure':n1,'excluded_no_turns_after':nozero,'mean_rate_pressure':round(sum(r for _,p,r in rows if p==1)/max(n1,1),3),'mean_rate_no_pressure':round(sum(r for _,p,r in rows if p==0)/max(len(rows)-n1,1),3),'diff':None if obs!=obs else round(obs,3),'p_perm_one_sided':None if obs!=obs else round(cnt/10000,4)}
out['H5']={'j1':h5('j1'),'j2':h5('j2')}
# ---------- H3 descriptive
def h3(j):
    o=Counter(M[j][k]['order_distant_vs_authored'] for k in L[j]); n=o['distant_first']+o['authored_first']
    return {'distant_first':o['distant_first'],'authored_first':o['authored_first'],'n':n,'testable':n>=20,'sign_p':round(binomtest(o['distant_first'],n,0.5,alternative='greater').pvalue,4) if n>=20 else None}
out['H3']={'j1':h3('j1'),'j2':h3('j2')}
# ---------- H4 (B)
def h4(j):
    res={}
    for fm,ntp in (('fm12','role'),('fm11','task_result')):
        rows=[]; uneval=0
        for rid in [k for k in L[j] if k.startswith('B')]:
            has=any(n.get('norm_type')==ntp and n['source_type'] in (('system',) if ntp=='role' else ('system','user','environment','peer')) for n in L[j][rid]['ledger']['norms'])
            if not has: uneval+=1; continue
            v=M[j][rid]['violations_role' if ntp=='role' else 'violations_task_result']
            rows.append((B[rid][fm],int(v>0)))
        lab=[a for a,_ in rows]; pred=[b for _,b in rows]
        tab=Counter(rows)
        res[fm]={'evaluable':len(rows),'unevaluable':uneval,'table_label_x_violation':{f'{a}{b}':tab.get((a,b),0) for a in (0,1) for b in (0,1)},'kappa':None if len(set(lab+pred))<2 or len(set(lab))<2 or len(set(pred))<2 else round(cohen_kappa_score(lab,pred),3)}
    return res
out['H4']={'j1':h4('j1'),'j2':h4('j2')}
# ---------- authored descriptive, normalized
def auth(j):
    r={}
    for s in 'AB':
        ks=[k for k in L[j] if k.startswith(s)]
        tot=sum(len(L[j][k]['ledger']['authored_rules']) for k in ks); agents=sum(max(M[j][k]['n_agents'],1) for k in ks); blocks=sum(L[j][k]['n_blocks'] for k in ks)
        sub=Counter(a['subtype'] for k in ks for a in L[j][k]['ledger']['authored_rules'])
        r[s]={'traces':len(ks),'authored':tot,'per_trace':round(tot/len(ks),2),'per_agent':round(tot/agents,2),'per_100_blocks':round(100*tot/blocks,2),'subtypes':dict(sub)}
    return r
out['authored']={'j1':auth('j1'),'j2':auth('j2')}
# pooled descriptive
out['pooled']={j:{k:v for k,v in json.load(open(REPO/'results'/'final'/f'metrics_all_{j}.json'))['W=6']['pooled'].items() if k!='order_test'} for j in ['j1','j2']}
OUTDIR=pathlib.Path(os.environ.get('NPL_OUT','reproduced')); OUTDIR.mkdir(exist_ok=True)
json.dump(out,open(OUTDIR/'results_v0.4.4.json','w'),ensure_ascii=False,indent=1)


random.seed(20260930)
res={}
# H5 consensus: pressure present per both; first consensus pressure block; consensus violations (conduct/role)
rows=[]
for rid in [k for k in common if k.startswith('A')]:
    msgs=corp[rid]['messages']; turns=[i for i,m in enumerate(msgs) if m['role']=='assistant']
    pb=sorted(b for b,k,t in consensus_blocks(rid,{'pressure'}))
    vb=[b for b,k,t in consensus_blocks(rid,{'violated'}) if t in ('conduct','role')]
    if pb:
        fp=pb[0]; ta=[i for i in turns if i>fp]
        if not ta: continue
        rows.append(((A[rid]['model'],A[rid]['domain']),1,sum(1 for b in vb if b>fp)/len(ta)))
    else: rows.append(((A[rid]['model'],A[rid]['domain']),0,len(vb)/len(turns) if turns else 0))
def stat(rs):
    p1=[r for _,p,r in rs if p==1]; p0=[r for _,p,r in rs if p==0]
    return (sum(p1)/len(p1)-sum(p0)/len(p0)) if p1 and p0 else float('nan')
obs=stat(rows); cells=defaultdict(list)
for c,p,r in rows: cells[c].append((p,r))
cnt=0
for _ in range(10000):
    perm=[]
    for c,v in cells.items():
        ps=[p for p,_ in v]; random.shuffle(ps); perm+=[(c,p,r) for p,(_,r) in zip(ps,v)]
    if stat(perm)>=obs-1e-12: cnt+=1
n1=sum(p for _,p,_ in rows)
res['H5_consensus']={'n':len(rows),'with_pressure':n1,'mean_rate_pressure':round(sum(r for _,p,r in rows if p)/max(n1,1),3),'mean_rate_no_pressure':round(sum(r for _,p,r in rows if not p)/max(len(rows)-n1,1),3),'diff':round(obs,3),'p_perm_one_sided':round(cnt/10000,4)}
# post hoc: yielding – share of pressure events followed by a violation of the same norm by the same agent
def yielding(j):
    tot=y=0
    for rid in [k for k in L[j] if k.startswith('A')]:
        ev=L[j][rid]['ledger']['events']
        for p in [e for e in ev if e['kind']=='pressure']:
            tot+=1
            if any(e['kind']=='violated' and e['norm_id']==p['norm_id'] and e['block']>p['block'] for e in ev): y+=1
    return {'pressure_events':tot,'followed_by_violation_of_same_norm':y,'share':round(y/tot,2) if tot else None}
res['posthoc_yielding']={'j1':yielding('j1'),'j2':yielding('j2')}
# post hoc: cluster-level sign test for H1 (per trace median distance violation vs compliance)
def h1_cluster(j):
    pos=neg=0
    for rid in L[j]:
        ev=[e for e in classified(j,rid) if e['distance'] is not None and e.get('norm_type','conduct') in ('conduct','role')]
        v=sorted(e['distance'] for e in ev if e['class']=='violation'); c=sorted(e['distance'] for e in ev if e['class'] in ('near','distant'))
        if v and c:
            d=v[len(v)//2]-c[len(c)//2]
            if d>0: pos+=1
            elif d<0: neg+=1
    return {'traces_viol_farther':pos,'traces_viol_closer':neg,'sign_p_one_sided':round(binomtest(pos,pos+neg,0.5,alternative='greater').pvalue,4) if pos+neg else None}
res['posthoc_H1_trace_level']={'j1':h1_cluster('j1'),'j2':h1_cluster('j2')}
# contradicted cases list with agreement
cl=lambda s: re.sub(r'\s*\[B\d+\]','',s)
cases=[]
for rid in common:
    c1={a['block']:cl(a['text']) for a in L['j1'][rid]['ledger']['authored_rules'] if a['subtype']=='contradicted_external_constraint'}
    c2={a['block']:cl(a['text']) for a in L['j2'][rid]['ledger']['authored_rules'] if a['subtype']=='contradicted_external_constraint'}
    if c1 or c2: cases.append({'trace':rid,'j1_blocks':sorted(c1),'j2_blocks':sorted(c2),'text_j1':list(c1.values())[:1],'text_j2':list(c2.values())[:1]})
res['contradicted_cases']=cases
# pressure by stratum/judge and domain
res['pressure_trajectories_by_domain']={j:dict(Counter(A[k]['domain'] for k in L[j] if k.startswith('A') and M[j][k]['pressure_events']>0)) for j in ['j1','j2']}
json.dump(res,open(OUTDIR/'results_extra_v0.4.4.json','w'),ensure_ascii=False,indent=1)
print('written',OUTDIR/'results_v0.4.4.json',OUTDIR/'results_extra_v0.4.4.json')
