#!/usr/bin/env python3
"""
segment_v04.py – build numbered message lists for the v0.4 pilot from judge inputs.
A (tau2): block 0 = system message with the policy text (+ tool definitions when present), then the messages as given.
B (MAST): the trajectory text is split into messages:
  MetaGPT: chunks separated by dashed lines; "FROM: X TO: Y ... CONTENT:" chunks and "NEW MESSAGES: Role: ..." chunks.
  ChatDev: log lines "[ts INFO] Sender: ..." start a message; sender "System" = harness/config dumps (source of role prompts);
           lines whose sender is missing (e.g. "**[Update Codes]**") = environment; pure infrastructure lines
           ("HTTP Request", "flask app.py did not start") are dropped and counted.
Every kept message becomes one block, numbered from 0 with a "[B<i>]" tag; for B, the tag is followed by "[<agent> -> <addressee>]".
"""
import json, re, sys, pathlib

def num(msgs):
    out=[]
    for i,m in enumerate(msgs):
        m=dict(m); who=m.get('agent'); to=m.get('addressee')
        tag=f'[B{i}]' + (f' [{who} -> {to}]' if who else '')
        m['content']=tag+' '+(m.get('content') or '')
        md=dict(m.get('metadata') or {}); md['block_index']=i; m['metadata']=md
        out.append(m)
    return out

def build_A(inp):
    d=json.load(open(inp,encoding='utf-8'))
    sys_text=d['policy'] if d.get('policy') else ''
    if d.get('tool_defs'): sys_text+='\n\n# Tool definitions\n'+json.dumps(d['tool_defs'],ensure_ascii=False)
    msgs=[{'role':'system','content':sys_text}]
    for m in d['messages']:
        mm={'role':m['role'],'content':m.get('content') or ''}
        if m.get('tool_calls'): mm['tool_calls']=m['tool_calls']
        msgs.append(mm)
    return msgs,{'dropped':0}

CHATDEV_ROLES=r'(System|Chief Executive Officer|Chief Product Officer|Chief Technology Officer|Chief Human Resource Officer|Programmer|Code Reviewer|Software Test Engineer|Counselor|Customer)'
def build_B(inp):
    t=json.load(open(inp,encoding='utf-8'))['trajectory']
    msgs=[]; dropped=0
    if 'MetaGPT Agent Communication Log' in t[:300]:
        chunks=[c.strip() for c in re.split(r'\n-{20,}\n', t) if c.strip()]
        for c in chunks:
            c=re.sub(r'^=== .*? ===\n','',c,flags=re.M).strip()
            if not c: continue
            m=re.match(r'\[[^\]]+\] FROM: (.+?) TO: (.+?)\nACTION: (.+?)\nCONTENT:\n(.*)',c,re.S)
            if m:
                who,to,act,body=m.groups(); role='user' if who.strip()=='Human' else 'assistant'
                msgs.append({'role':role,'agent':who.strip(),'addressee':to.strip(),'content':f'ACTION: {act.strip()}\n{body.strip()}'}); continue
            m=re.match(r'\[[^\]]+\] NEW MESSAGES:\n\n(.*)',c,re.S)
            if m:
                body=m.group(1).strip(); mm=re.match(r'([A-Za-z_][\w ]{0,40}?):\s*\n?(.*)',body,re.S)
                who=mm.group(1).strip() if mm else 'unknown'; text=mm.group(2) if mm else body
                msgs.append({'role':'assistant','agent':who,'addressee':'<all>','content':text.strip()}); continue
            msgs.append({'role':'user','agent':'environment','addressee':'<all>','content':c})
        return msgs,{'dropped':dropped,'format':'metagpt'}
    # ChatDev
    parts=re.split(r'(?m)^(?=\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO\] )', t)
    for p in parts:
        p=p.strip()
        if not p: continue
        m=re.match(r'\[[^\]]+ INFO\] '+CHATDEV_ROLES+r': (.*)',p,re.S)
        if m:
            who,body=m.group(1),m.group(2).strip()
            if who=='System': msgs.append({'role':'system','agent':'System','addressee':'<all>','content':body})
            else:
                to='<all>'
                mm=re.search(r'\*\*'+CHATDEV_ROLES+r'<->'+CHATDEV_ROLES+r' on',body)
                if mm: to=mm.group(2) if mm.group(1)==who else mm.group(1)
                msgs.append({'role':'assistant','agent':who,'addressee':to,'content':body})
            continue
        m=re.match(r'\[[^\]]+ INFO\] (.*)',p,re.S)
        body=m.group(1).strip() if m else p
        if re.match(r'(HTTP Request|flask app\.py did not start)',body): dropped+=1; continue
        msgs.append({'role':'user','agent':'environment','addressee':'<all>','content':body})
    return msgs,{'dropped':dropped,'format':'chatdev'}

def main(pkg_dir,out):
    pkg=pathlib.Path(pkg_dir); pilot=json.load(open(pkg/'pilot_10.json'))
    rows=[]
    for stratum,builder in (('A',build_A),('B',build_B)):
        for it in pilot[stratum]:
            msgs,info=builder(pkg/it['input_file']); msgs=num(msgs)
            rows.append({'id':f"{stratum}:{it['id']}",'metadata':{'stratum':stratum,'n_blocks':len(msgs),**info},'messages':msgs})
    with open(out,'w',encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    for r in rows: print(r['id'],r['metadata'])

if __name__=='__main__': main(sys.argv[1],sys.argv[2])
