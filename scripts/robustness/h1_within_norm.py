from common import *
import numpy as np
from scipy.stats import binomtest
res={}
for j in ['j1','j2']:
    pos=neg=0; n_norms=0
    for rid in L[j]:
        by=defaultdict(lambda:{'v':[],'c':[]})
        for e in events(j,rid):
            if e['distance'] is None or e.get('norm_type','conduct') not in ('conduct','role'): continue
            if e['class']=='violation': by[e['norm_id']]['v'].append(e['distance'])
            elif e['class'] in ('near','distant') and e['kind']=='applied': by[e['norm_id']]['c'].append(e['distance'])
        for nid,x in by.items():
            if x['v'] and x['c']:
                n_norms+=1; d=np.median(x['v'])-np.median(x['c'])
                pos+= d>0; neg+= d<0
    res[j]=dict(norms_with_both=n_norms,viol_farther=int(pos),viol_closer=int(neg),p=round(float(binomtest(int(pos),int(pos+neg),0.5,alternative='greater').pvalue),5))
json.dump(res,open(os.path.join(os.environ.get('NPL_OUT','reproduced'),'h1_within_norm.json'),'w'),indent=1); print(res)
