#!/usr/bin/env python3
"""v0.4 pilot launcher. Pinned SDK 0.1.87. dry-run is offline; launch uploads exactly the 10 numbered pilot runs
(5 tau2 + 5 MAST) into a new collection, creates the v0.4 rubric, and evaluates at most 10 runs. Raw export keeps the
server response intact. Names are neutral (pilot_01..pilot_10); metadata is not shown to the judge."""
import argparse,json,os,pathlib
from docent.sdk import Docent
from docent.data_models import AgentRun,Transcript
from docent.data_models.chat import SystemMessage,UserMessage,AssistantMessage,ToolMessage,ToolCall
from docent.judges.types import Rubric
from docent._llm_util.providers.preference_types import ModelOption
HERE=pathlib.Path(__file__).resolve().parent; ROOT=pathlib.Path(os.environ.get('NPL_BUILD','build')).resolve(); RUBRIC=HERE.parent/'rubric'
PROTOCOL='0.4.4'
CL={'system':SystemMessage,'user':UserMessage,'assistant':AssistantMessage,'tool':ToolMessage}

def convert(r,name):
    msgs=[]; pending=[]
    for i,m in enumerate(r['messages']):
        assert m['metadata']['block_index']==i
        md={'block_index':i}
        if m.get('agent'): md['agent']=m['agent']; md['addressee']=m.get('addressee')
        kw={'content':m.get('content') or '','metadata':md}
        if m['role']=='assistant' and m.get('tool_calls'):
            calls=[]
            for t in m['tool_calls']:
                f=t.get('function') or {'name':t.get('name'),'arguments':t.get('arguments')}
                a=f.get('arguments'); a=json.loads(a) if isinstance(a,str) else (a or {})
                calls.append(ToolCall(id=t['id'],function=f['name'],arguments=a,type='function')); pending.append(t['id'])
            kw['tool_calls']=calls
        if m['role']=='tool':
            kw['tool_call_id']=m.get('tool_call_id') or (pending.pop(0) if pending else None)
        msgs.append(CL[m['role']](**kw))
    meta={**r['metadata'],'source_run_id':r['id'],'protocol_version':PROTOCOL}
    return AgentRun(name=name,metadata=meta,transcripts=[Transcript(messages=msgs)])

CORPORA={'pilot':('pilot_10_numbered.jsonl',10,'pilot'),'rel30':('reliability_30_numbered.jsonl',30,'rel'),'full71':('full_71_numbered.jsonl',71,'full')}
def load_pilot(corpus='pilot'):
    fn,n,prefix=CORPORA[corpus]
    rows=[json.loads(s) for s in (ROOT/'corpus'/fn).read_text().splitlines()]
    if len(rows)!=n: raise ValueError(f'expected {n} runs in {fn}')
    return rows,[convert(r,f'{prefix}_{i:02d}') for i,r in enumerate(rows,1)]

def rubric(spec):
    kw={}
    if spec:
        p=spec.split(':'); kw['judge_model']=ModelOption(provider=p[0],model_name=p[1],reasoning_effort=p[2] if len(p)==3 else None)
    return Rubric(rubric_text=(RUBRIC/'rubric_text_v0.4.1.md').read_text(),output_schema=json.loads((RUBRIC/'output_schema_v0.4.json').read_text()),output_format='json',**kw)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['dry-run','launch','raw-export']);ap.add_argument('--judge');ap.add_argument('--label',default='v0.4.1');ap.add_argument('--state',default=None);ap.add_argument('--corpus',choices=['pilot','rel30','full71'],default='pilot');a=ap.parse_args()
    statepath=pathlib.Path(a.state or ROOT/f'docent_pilot_state_{a.label}.json')
    rows,runs=load_pilot(a.corpus);rub=rubric(a.judge);N=len(runs)
    if a.command=='dry-run':
        print(json.dumps({'runs':len(runs),'blocks':sum(len(r['messages']) for r in rows),'rubric_constructed':True,'names':[x.name for x in runs]}));return
    key=os.environ.get('DOCENT_API_KEY')
    if not key:raise SystemExit('DOCENT_API_KEY is not configured; no network writes performed.')
    c=Docent(api_key=key)
    if a.command=='launch':
        if not a.judge:raise SystemExit('--judge must be explicitly chosen')
        if statepath.exists():raise SystemExit('State exists; will not launch twice.')
        cid=c.create_collection(name=f'Norm Provenance Ledger {a.label} – {a.corpus} {N} (tau2 + MAST)',metadata={'protocol':a.label,'corpus':a.corpus,'size':N})
        state={'collection_id':cid,'stage':'created','neutral_names':{x.name:r['id'] for x,r in zip(runs,rows)},'judge':a.judge}
        save=lambda:statepath.write_text(json.dumps(state,indent=2)); save()
        res=c.add_agent_runs(cid,runs,wait=True)
        if res.get('status')!='success' or res.get('total_runs_added')!=N:raise RuntimeError(f'unexpected ingestion result: {res}')
        state['stage']='ingested';save()
        rid=c.create_rubric(cid,rub);state['rubric_id']=rid;state['stage']='rubric_created';save()
        jid=c.start_rubric_eval_job(cid,rid,max_agent_runs=N,n_rollouts_per_input=1,include_metadata=False)
        state.update(stage='evaluation_started',job_id=jid);save();print(json.dumps(state));return
    state=json.loads(statepath.read_text())
    raw=c.get_rubric_run_state(state['collection_id'],state['rubric_id'],include_failures=True)
    (ROOT/f'raw_run_state_{a.label}.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2)); print('saved raw state')

if __name__=='__main__':main()
