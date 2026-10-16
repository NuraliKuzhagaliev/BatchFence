"""Staged live verification. Run one step, inspect raw evidence, then review explicitly.

Never prints access credentials. The reviewer is the operating agent, not an
independent human. Source inputs are frozen before their first request.
"""
from pathlib import Path
import sys, json, os, base64, time
from datetime import datetime, timezone
import httpx
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/release-0.2.0/live'
PRIVATE=ROOT/'work/upgrade-live-session.json'
OUT.mkdir(parents=True,exist_ok=True)
base=os.getenv('BATCHFENCE_BASE_URL','https://batchfence.onrender.com')
step=sys.argv[1]
private=json.loads(PRIVATE.read_text()) if PRIVATE.exists() else {}
token=dotenv_values(ROOT/'work/cloud-demo.env').get('LIVE_DEMO_TOKEN')
client=httpx.Client(base_url=base,cookies=private.get('cookies',{}),timeout=75)
def call(method,path,data=None,live=False):
    r=client.request(method,path,json=data,headers={'X-BF-Demo-Token':token} if live else {})
    if r.status_code>=400:
        (OUT/(step+'-failure.json')).write_text(json.dumps({'status':r.status_code,'response':r.json()},indent=2),encoding='utf-8')
        raise RuntimeError('Application rejected step; see sanitized failure report: '+str(r.status_code))
    return r.json()
def save(name,value):
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
def upload(text,name,request_id=None):
    args={'filename':name,'synthetic':True,'content_base64':base64.b64encode(text.encode()).decode()}
    if request_id: args['request_id']=request_id
    return call('POST',route+'/documents',args)
if step=='notice1':
    assert not private, 'Existing verification session is preserved; choose its next step'
    started=time.perf_counter();health=call('GET','/api/health');save('first-access',{'health':health,'elapsed_ms':round((time.perf_counter()-started)*1000),'at':datetime.now(timezone.utc).isoformat(),'cold_start':'Not established; this measures a real request, not an assumed sleeping instance.'})
    s=call('POST','/api/cases/demo',{})
    private['case_id']=s['id']
route='/api/cases/'+private['case_id']
try:
    s=call('GET',route)
    if step in ('notice1','notice2','reply'):
        texts={
          'notice1': 'Synthetic supplier communication, 0.2.0 verification, revision one.\nThe cosmetic coating defect is confirmed in supplier lot SUP-A.\nComplete incident boundary: SUP-A is the only affected supplier lot in this notice.\nWarehouse receiving records are separate evidence; this notice does not identify the parent of any finished pool.',
          'notice2': 'Synthetic supplier communication, 0.2.0 verification, revision two. This document supersedes revision one.\nAdditional inspection confirms the same cosmetic coating defect in SUP-C as well as SUP-A.\nComplete incident boundary: the affected supplier lots are SUP-A and SUP-C, with no additional supplier lots implicated by this notice.',
          'reply': 'Synthetic receiving clarification REC-C-2. This is a warehouse ancestry record, not a replacement incident notice.\nFG-C complete ancestry: SUP-B only. Supersedes LIN-3, LIN-4. Receipt REC-C-2 covers all 100 units; no other parent lots.\nThe identity above establishes the parent supplier lot; the current incident involvement remains governed by the separate supplier notice.'}
        text=texts[step]
        (OUT/(step+'-input.txt')).write_text(text,encoding='utf-8')
        q=next(q for q in s['plan']['result']['requests'] if q['kind']=='possible_ancestry') if step=='reply' else None
        s=upload(text,'fresh-'+step+'-communication.txt',q['id'] if q else None)
        if step=='notice2':
            stale=client.post(route+'/apply',json={**private['old_action'],'idempotency_key':'upgrade-live-stale-new-attempt'})
            save('stale-rejection',{'status':stale.status_code,'body':stale.json()});assert stale.status_code==409
        s=call('POST',route+'/analyze',{'document_id':s['documents'][-1]['id'],'mode':'live'},live=True)
        save(step+'-raw-run',s['runs'][-1]);save(step+'-before-review',call('GET',route+'/export'))
        print(json.dumps(s['runs'][-1],ensure_ascii=False,indent=2))
    elif step in ('review1','review2'):
        lots=['SUP-A'] if step=='review1' else ['SUP-A','SUP-C']
        run=s['runs'][-1];assert run['status']=='succeeded' and run['mode']=='live'
        doc=next(d for d in s['documents'] if d['id']==run['document_id'])
        basis=next(b['text'] for b in doc['blocks'] if b['text'].startswith('Complete incident boundary:'))
        # Explicit operator-selected dispositions, never derived from booleans.
        assert {f['lot_id'] for f in run['output']['facts']}<=set(lots), 'Inspect additional candidates before choosing dispositions'
        s=call('POST',route+'/reviews',{'run_id':run['id'],'revision':s['revision'],'lot_ids':lots,'accept_scope':True,
            'bounded_scope_reviewed':True,'incident_scope_status':'resolved','resolution_quote':basis,
            'note':'Agent-operated review of this fresh source: its explicit complete supplier boundary is accepted. Warehouse ambiguity remains separate; raw proposals and qualifiers are retained.'})
        assert s['plan']['result']['hold_units']==(500 if step=='review1' else 800)
        s=call('POST',route+'/approve',{'plan_id':s['plan']['id'],'digest':s['plan']['digest']})
        action={'plan_id':s['plan']['id'],'digest':s['plan']['digest'],'actions':s['plan']['actions'],'idempotency_key':'upgrade-live-'+step}
        if step=='review1':private['old_action']=action
        s=call('POST',route+'/apply',action)
        save(step+'-packet',call('GET',route+'/export'))
        if step=='review2':save('causal-comparison',call('GET',route+'/comparison'))
        print(json.dumps({'stage':step,'hold_units':s['plan']['result']['hold_units'],'orders':len(s['plan']['result']['orders']),'receipts':len(s['receipts']),'reviewer':'Agent-operated; no independent human validation'}))
    elif step=='review-reply':
        run=s['runs'][-1];assert run['status']=='succeeded' and run['mode']=='live'
        doc=s['documents'][-1]
        body={'revision':s['revision'],'document_id':doc['id'],'pool_id':'FG-C','supplier_lot_id':'SUP-B','outcome':'resolved','complete':True,
            'quote':doc['blocks'][1]['text'],'reviewed':True,'replacement_reviewed':True,
            'note':'Agent-operated explicit review: REC-C-2 covers all FG-C units and explicitly supersedes both LIN-3 and LIN-4. SUP-B identity is source-backed; prior applied holds must remain.'}
        preview=call('POST',route+'/reply-preview',body);save('reply-preview',preview)
        s=call('POST',route+'/reply-review',body)
        assert s['plan']['result']['hold_units']==700 and sum(p['units'] for p in s['stocks'] if p['status']=='held')==800
        save('final-packet',call('GET',route+'/export'))
        print(json.dumps({'hold_proposal':700,'already_held':800,'receipts':len(s['receipts']),'reviewer':'Agent-operated','automatic_release':False}))
    else: raise ValueError('Unknown staged step')
finally:
    private['cookies']=dict(client.cookies)
    PRIVATE.write_text(json.dumps(private),encoding='utf-8')
    client.close()
