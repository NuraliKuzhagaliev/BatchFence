"""Staged actual container OCR check; visual confirmation is a separate invocation."""
import base64,hashlib,json,sys,time
from pathlib import Path
from datetime import datetime,timezone
import httpx
root=Path(__file__).resolve().parents[1];out=root/'docs/enterprise/ocr';out.mkdir(parents=True,exist_ok=True)
private=root/'work/pilot-eval/ocr-check.json'
credentials=json.loads((root/'work/pilot-data/backups/engineering-check-private.json').read_text())
c=httpx.Client(base_url='http://127.0.0.1:8788',timeout=120)
def call(method,path,data=None):
    r=c.request(method,path,json=data)
    if r.status_code!=200:raise RuntimeError('Local OCR check rejected: '+str(r.status_code)+' '+r.text[:800])
    return r.json()
call('POST','/api/auth/login',credentials)
if sys.argv[1]=='upload':
    s=call('POST','/api/cases/demo',{})
    raw=(root/'fixtures/enterprise/ocr/raster-only-notice.pdf').read_bytes();started=time.perf_counter()
    s=call('POST','/api/cases/'+s['id']+'/documents',{'filename':'raster-only-notice.pdf','content_base64':base64.b64encode(raw).decode(),'synthetic':True})
    doc=s['documents'][-1];assert doc['ocr']['critical_fields_confirmed'] is False
    for p in doc['ocr']['pages']:
        page=call('GET','/api/cases/'+s['id']+'/documents/'+doc['id']+'/pages/'+str(p['page']))
        png=base64.b64decode(page['data_url'].split(',')[1]);assert hashlib.sha256(png).hexdigest()==p['image_hash']
        (out/f'retained-page-{p["page"]}.png').write_bytes(png)
    result={'at':datetime.now(timezone.utc).isoformat(),'elapsed_ms':round((time.perf_counter()-started)*1000),'engine':doc['ocr']['engine'],'document':doc,
            'provenance':'Actual local Tesseract/Poppler on two synthetic raster-only pages; not AMD inference','visual_review':'pending agent page inspection; no independent human validation'}
    (out/'actual-ocr.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    private.write_text(json.dumps({'case_id':s['id'],'document_id':doc['id']}),encoding='utf-8')
    print(json.dumps({'engine':result['engine'],'elapsed_ms':result['elapsed_ms'],'pages':len(doc['ocr']['pages']),'word_boxes':len(doc['ocr']['words']),'critical_fields_confirmed':False}))
elif sys.argv[1]=='review-after-visual-inspection':
    p=json.loads(private.read_text());route='/api/cases/'+p['case_id'];s=call('GET',route);doc=next(d for d in s['documents'] if d['id']==p['document_id'])
    s=call('POST',route+'/analyze',{'document_id':doc['id'],'mode':'fixture'})
    def review_body(state):return {'run_id':state['runs'][-1]['id'],'revision':state['revision'],'lot_ids':['SUP-A'],'accept_scope':True,'bounded_scope_reviewed':True,'incident_scope_status':'resolved','resolution_quote':'Complete supplier scope: SUP-A only.','note':'Agent compared identifiers, quantities and scope to both retained synthetic page images; not independent human validation.'}
    denied=c.post(route+'/reviews',json=review_body(s));assert denied.status_code==422
    s=call('POST',route+'/ocr-review',{'document_id':doc['id'],'revision':s['revision'],'page_numbers':[1,2],'identifiers_confirmed':True,'quantities_confirmed':True,'completeness_confirmed':True,'note':review_body(s)['note']})
    s=call('POST',route+'/analyze',{'document_id':doc['id'],'mode':'fixture'})
    s=call('POST',route+'/reviews',review_body(s));assert s['plan']['result']['hold_units']==500
    result={'at':datetime.now(timezone.utc).isoformat(),'pre_visual_review_rejected':denied.status_code,'after_agent_page_review_hold_proposal':500,'applied_units':0,'original_pdf_bytes_preserved':c.get('/api/sources/'+doc['original_hash']).content==(root/'fixtures/enterprise/ocr/raster-only-notice.pdf').read_bytes(),'model':'synthetic parser; no AMD inference','reviewer':'Agent-operated visual review only','packet':call('GET',route+'/export')}
    (out/'review-behavior.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='packet'}))
else:raise ValueError('Choose upload or review-after-visual-inspection')
