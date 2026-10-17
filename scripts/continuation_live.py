"""Finite fresh managed-AMD Gemma evaluation. Never a fixture/replay fallback.

All task inputs are synthetic, frozen before dispatch. Reviews are agent-operated.
This proves managed endpoint behavior only, not owned AMD Cloud/vLLM eligibility.
"""
import argparse,base64,hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv,set_key
from PIL import Image,ImageDraw,ImageFont,ImageFilter

ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'work/continuation';OUT=ROOT/'docs/continuation/live'
PRIVATE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
load_dotenv(ROOT/'.env')
os.environ['DATABASE_PATH']=str(PRIVATE/'live.sqlite')
os.environ['SOURCE_STORAGE_PATH']=str(PRIVATE/'sources')
os.environ['PUBLIC_DEMO']='false';os.environ['DEPLOYMENT_PROFILE']='local';os.environ['APP_ORIGIN']='http://testserver'
from backend import repository as repo,evolus_adapter as external
from backend.assist_contracts import ReviewDraft,source_context,validate_draft
from backend.label_images import LabelReading,validate_reading,decode
from backend.fixtures import document,load_demo
from backend.domain import digest

DB=PRIVATE/'live.sqlite';PROOF=PRIVATE/'gemma-allowance.json'
MODEL='Gemma-4-31B-IT';BASE='https://developer.amd.com.cn/radeon/api/v1'
LIMIT=48


def safe_save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2)
    for key in ('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY','LIVE_DEMO_TOKEN'):
        secret=os.getenv(key)
        if secret and secret in text:raise RuntimeError('Private value detected; output suppressed')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text+'\n',encoding='utf-8')


def configure():
    if os.getenv('AMD_API_BASE_URL','').rstrip('/')!=BASE:raise RuntimeError('Existing AMD endpoint differs from the verified shared manual')
    # Reuse existing authorized key mechanically, without displaying it.
    values={'GEMMA_API_BASE_URL':BASE,'GEMMA_API_KEY':os.environ['AMD_API_KEY'],'GEMMA_MODEL_ID':MODEL,
        'GEMMA_HOSTING_KIND':'managed-amd-shared','GEMMA_JSON_OBJECT':'true','GEMMA_COST_APPROVAL_FILE':str(PROOF),
        'EVOLUS_API_BASE_URL':'https://api.evolus.ai','EVOLUS_CONTRACT_FILE':str(ROOT/'docs/continuation/evolus-api-contract.json'),
        'EVOLUS_CONTRACT_SHA256':hashlib.sha256((ROOT/'docs/continuation/evolus-api-contract.json').read_bytes()).hexdigest()}
    for key,value in values.items():set_key(str(ROOT/'.env'),key,value);os.environ[key]=value
    refresh_quota('initial')
    print('Configured Gemma in the existing .env; AMD settings preserved; no inference.')


def refresh_quota(label):
    with httpx.Client(timeout=25,trust_env=False,follow_redirects=False) as client:
        response=client.get(BASE+'/usage',params={'include_recent':'false'},headers={'Authorization':'Bearer '+os.environ.get('GEMMA_API_KEY',os.environ['AMD_API_KEY'])})
        response.raise_for_status();quota=response.json()
    current=datetime.now(timezone.utc).isoformat();remaining=quota['daily_cost_remaining_usd']
    proof={'provider':'gemma','additional_cash_limit':0,'storage_network_cash_limit':0,'overages_disabled':True,
        'verified_at':current,'expires_at':quota['daily_reset_at'],'max_dispatches':LIMIT,
        'remaining_credits':remaining,'stop_margin':0.10,'max_credits_per_dispatch':0.14,
        'allowance_id':'continuation-gemma-f50349c-v1','managed_amd_shared_verified':True,
        'evidence_reference':'Authenticated AMD TokenFactory shared-model manual, 2026-10-17: free capped access; points are not charges',
        'unit':'Nonmonetary platform points; API legacy field names use USD',
        'upper_bound_basis':'At most full 262144-token context at manual 0.50/M input plus 1600 output at 3/M, rounded upward to .14. Text inputs are additionally bounded to 20 KB.',
        'hosting_kind':'managed-amd-shared; no GPU VM/storage/network resource allocated'}
    safe_save(PROOF,proof);os.environ['GEMMA_COST_APPROVAL_FILE']=str(PROOF)
    safe_save(OUT/('quota-'+label+'.json'),{'at':current,'http_status':response.status_code,
        'remaining_nonmonetary_points':remaining,'used_nonmonetary_points':quota['daily_cost_used_usd'],
        'reset_at':quota['daily_reset_at'],'today_requests':quota.get('today',{}).get('requests'),
        'today_errors':quota.get('today',{}).get('errors'),'not_monetary_charges':True})
    print(json.dumps({'quota':label,'remaining_nonmonetary_points':remaining}))
    return proof


def reserve():
    with repo.write(lambda:repo.connect(DB)) as db:return external.reserve(db,'gemma')


def freeze_images():
    directory=ROOT/'evals/continuation/images';directory.mkdir(exist_ok=True)
    if (directory/'manifest.json').exists():return
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',46)
    cases=[('IMG-01',['SUP-001']),('IMG-02',['SUP-002']),('IMG-03',['LOT-00O7']),('IMG-04',['SUP-001','SUP-002']),('IMG-05',['SUP-001'])]
    rows=[]
    for cid,labels in cases:
        image=Image.new('RGB',(720,330),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((15,15,705,315),outline='black',width=2);draw.text((40,30),'SYNTHETIC ENGINEERING LABEL',fill='black',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25))
        for i,label in enumerate(labels):draw.text((45,95+90*i),'LOT: '+label,fill='black',font=font)
        if cid=='IMG-05':
            draw.rectangle((20,85,710,280),fill='white');image=image.filter(ImageFilter.GaussianBlur(12))
        path=directory/(cid+'.png');image.save(path)
        rows.append({'id':cid,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'synthetic':True,'physical_photo':False,'labels':labels if cid!='IMG-05' else [],'unreadable':cid=='IMG-05'})
    (directory/'IMG-06.png').write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>not a raster label</script></svg>',encoding='utf-8')
    rows.append({'id':'IMG-06','file':'IMG-06.png','sha256':hashlib.sha256((directory/'IMG-06.png').read_bytes()).hexdigest(),'synthetic':True,'expected':'Reject before inference'})
    safe_save(directory/'manifest.json',{'at':datetime.now(timezone.utc).isoformat(),'authorship':'Agent-rendered synthetic engineering fixtures, not real label photographs','items':rows})


def dispatch(cid,context,schema,image=None,validator=None):
    path=OUT/(cid+'.json')
    if path.exists():raise RuntimeError('Existing attempt retained; choose a distinct disclosed retest ID, never overwrite/retry')
    reservation=reserve();record={'id':cid,'at':datetime.now(timezone.utc).isoformat(),'input_hash':digest(context),'input':context,'reservation':reservation,'provenance':'Fresh AMD request; synthetic input; no independent human validation'}
    safe_save(path,record) # preserve reservation even if the process stops
    started=time.perf_counter()
    try:
        result=external.gemma(context,schema,image=image,vision_probe=bool(image));record['response']=result
        if validator:
            try:record['validated']=validator(result['result']);record['validation_status']='accepted unreviewed proposal'
            except Exception as error:record.update(validation_status='raw response rejected',raw_quality_error=str(error)[:800])
    except Exception as error:
        record.update(provider_failure=str(error)[:400],validation_status='no response accepted')
        if isinstance(error,external.ProviderFailure):record['failed_request_metadata']=error.evidence
    record['end_to_end_ms']=round((time.perf_counter()-started)*1000);safe_save(path,record)
    print(json.dumps({'item':cid,'status':record.get('validation_status'),'http':record.get('response',{}).get('http_status'),'elapsed_ms':record['end_to_end_ms']}),flush=True)
    # A 429 is retained; back off before a DIFFERENT item, never retry it.
    delay=30 if record.get('failed_request_metadata',{}).get('http_status')==429 else 3.1
    time.sleep(delay)
    return record


def sample():
    freeze_images();frozen=json.loads((ROOT/'evals/continuation/frozen-v1.json').read_text(encoding='utf-8'))
    expected='b3ea8615041b885fc54eefa36ab36e10b5ddffd36fbf8f2a7503842322472549'
    if hashlib.sha256((ROOT/'evals/continuation/frozen-v1.json').read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen sample changed')
    refresh_quota('before-sample');done=0
    for item in frozen['items']:
        cid=item['id']
        if item['kind'] not in ('scope','en','ru','it','label'):continue
        if cid=='IMG-06':
            try:decode((ROOT/'evals/continuation/images/IMG-06.png').read_bytes(),[])
            except Exception as e:safe_save(OUT/'IMG-06-local.json',{'id':cid,'inference_calls':0,'rejected_before_provider':True,'error':str(e)})
            continue
        if (OUT/(cid+'.json')).exists():continue # resume remaining items, never retry old attempt
        if done and done%3==0:refresh_quota('sample-'+str(done))
        if item['kind']=='label':
            raw=(ROOT/f'evals/continuation/images/{cid}.png').read_bytes();_,derived=decode(raw,[])
            image='data:image/png;base64,'+base64.b64encode(derived).decode()
            dispatch(cid,{'task':'Read visible LOT IDs only, preserving exact spelling and leading zeros. Report O/0,B/8,S/5 ambiguities. Multiple labels stay separate. Unreadable images require abstention. No authenticity, quality or action authority.','image_hash':hashlib.sha256(raw).hexdigest(),'image_kind':'Synthetic rendered label, not physical photo'},LabelReading.model_json_schema(),image,validate_reading)
        else:
            state=load_demo();doc=document('fresh-evidence.txt',item['input'].encode('utf-8'),synthetic=True);doc['revision']=state['revision'];state['documents']=[doc]
            context=source_context(state,[doc['id']]);context['task']='Identify typed source candidates, assertions versus uncertainty and contradictions. Do not classify receipt IDs as supplier lots. Preserve modality and uncertainty in all supported languages.'
            dispatch(cid,context,ReviewDraft.model_json_schema(),validator=lambda raw:validate_draft(state,raw))
        done+=1
    refresh_quota('after-sample')


def shared():
    from backend.provider import Extraction,SYSTEM,validate_output
    frozen=json.loads((ROOT/'evals/enterprise/frozen-v1.json').read_text(encoding='utf-8'))
    items=[i for i in frozen['items'] if i['task']=='extraction'];refresh_quota('before-shared');summary=[]
    for i,item in enumerate(items):
        cid='SHARED-'+item['id']
        if not (OUT/(cid+'.json')).exists():
            if i and i%3==0:refresh_quota('shared-'+str(i))
            doc=document('unseen-shared-source.txt',item['text'].encode(),synthetic=True)
            dispatch(cid,{'task':SYSTEM,'documents':[doc]},Extraction.model_json_schema(),validator=lambda raw:validate_output(raw,[doc]))
        result=json.loads((OUT/(cid+'.json')).read_text(encoding='utf-8'))
        expected={(v,True) for v in item['labels']['affected_supplier_lots']}|{(v,False) for v in item['labels']['mentioned_supplier_lots']}
        new=result.get('validated');actual={(f['lot_id'],f['affected']) for f in new['facts']} if new else None
        historical=json.loads((ROOT/f'docs/enterprise/live/frozen/{item["id"]}.json').read_text(encoding='utf-8'))
        old=historical['run'].get('output');old_actual={(f['lot_id'],f['affected']) for f in old['facts']} if old else None
        summary.append({'id':item['id'],'expected':sorted(expected),'gemma_actual':sorted(actual) if actual is not None else None,
            'gemma_raw_exact':actual==expected,'historical_mimo_raw_exact':old_actual==expected,'gemma_record':cid+'.json'})
    safe_save(OUT/'shared-comparison.json',{'items':summary,'denominator':len(items),'gemma_exact':sum(i['gemma_raw_exact'] for i in summary),
        'historical_mimo_exact':sum(i['historical_mimo_raw_exact'] for i in summary),'new_mimo_calls':0,
        'limits':'Same frozen text, schema and source-validation rules. Historical MiMo versus fresh Gemma; generic system wrapper and output budget differ (1600 versus 1800). Agent-authored synthetic labels; not a controlled model-only or human benchmark.'})
    refresh_quota('after-shared')


def explicit_retests():
    # One explicitly requested diagnostic rerun per initial 429, with its own
    # permanent ID. Original failures and the first-attempt denominator remain.
    refresh_quota('before-explicit-retests')
    for cid in ('LANG-01','IMG-04'):
        original=json.loads((OUT/(cid+'.json')).read_text(encoding='utf-8'))
        if original.get('provider_failure')!='Gemma endpoint HTTP 429; no retry':raise RuntimeError('Only the disclosed 429 items are eligible for this explicit diagnostic')
        if (OUT/(cid+'-retest-1.json')).exists():raise RuntimeError('Explicit retest already attempted; no further retry')
        if cid.startswith('IMG'):
            raw=(ROOT/f'evals/continuation/images/{cid}.png').read_bytes();_,derived=decode(raw,[])
            dispatch(cid+'-retest-1',original['input'],LabelReading.model_json_schema(),'data:image/png;base64,'+base64.b64encode(derived).decode(),validate_reading)
        else:
            sources=original['input']['sources'];state={'documents':[{'id':s['document_id'],'revision':s['revision'],'original_hash':s['source_hash'],'blocks':[{'id':p['block_id'],'text':p['text'],'page':p.get('page')} for p in s['passages']]} for s in sources]}
            dispatch(cid+'-retest-1',original['input'],ReviewDraft.model_json_schema(),validator=lambda raw:validate_draft(state,raw))
    refresh_quota('after-explicit-retests')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['configure','freeze-images','sample','shared','explicit-retests']);args=parser.parse_args()
    {'configure':configure,'freeze-images':freeze_images,'sample':sample,'shared':shared,'explicit-retests':explicit_retests}[args.mode]()
