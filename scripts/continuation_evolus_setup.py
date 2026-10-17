"""Idempotent, journaled setup using the supplied Evolus API; no inference.

Uses the owner's existing connection. Never copies or reads its stored key.
Unknown write outcomes require inspection, not automatic recreation.
"""
import json,hashlib,os
from pathlib import Path
from dotenv import load_dotenv,set_key
from backend import evolus_api as api
from backend.assist_contracts import ExtractorDraft,ReviewDraft
from backend.domain import digest
from backend.scope_proposals import INSTRUCTIONS

ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'work/continuation';OUT=ROOT/'docs/continuation/live'
load_dotenv(ROOT/'.env')
JOURNAL=PRIVATE/'evolus-setup.json';MANIFEST=PRIVATE/'evolus-workflow.json'

def save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2)
    for k in ('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY'):
        if os.getenv(k) and os.environ[k] in text:raise RuntimeError('Private value detected; suppressed')
    path.write_text(text+'\n',encoding='utf-8')

def main():
    state=json.loads(JOURNAL.read_text(encoding='utf-8')) if JOURNAL.exists() else {'resources':{},'requests':[]}
    if state.get('pending'):raise RuntimeError('Unknown prior write outcome: inspect pending resource before another write')
    def request(method,path,**kw):
        result=api.call(method,path,**kw);state['requests'].append({k:v for k,v in result.items() if k!='result'});save(JOURNAL,state);return result['result']
    def create(label,path,body,personal=False):
        if label in state['resources']:return state['resources'][label]
        state['pending']={'label':label,'path':path,'request_hash':digest(body)};save(JOURNAL,state)
        value=request('POST',path,body=body,personal=personal)
        state['resources'][label]=value;state.pop('pending');save(JOURNAL,state)
        print(json.dumps({'created':label,'fields':list(value) if isinstance(value,dict) else 'non-object'}),flush=True);return value
    cat=json.loads((PRIVATE/'evolus-catalog.json').read_text(encoding='utf-8'))
    model=next(m for group in cat['groups'] if group['source']=='own' for m in group['items'] if m['name']=='Gemma-4-31B-IT')
    if model['id']!='own/gemma-4-31b-it' or model['unavailable'] or model['locked'] or model['pricing']!={'kind':'byok-free','unit':'1M-token','input':0,'output':0,'estimated':False}:raise RuntimeError('Verified free own-model catalog changed')
    connections=request('GET','/api/v1/own-models/connections',personal=True)
    connection=next(c for c in connections if any(m['modelId']=='Gemma-4-31B-IT' for m in c['models']))
    if connection['disabled'] or not connection['hasApiKey'] or connection['apiBaseUrl']!='https://developer.amd.com.cn/radeon/api/v1':raise RuntimeError('Own-model connection not ready')
    prefix='BatchFence 0.4 bounded'
    extract_prompt=INSTRUCTIONS+' Fill the extractor schema from the uploaded original only. quote is an exact original passage. kind/value identify entities; disposition describes assertion versus uncertainty, not stock authority. Keep source page null for plain text.'
    agent_prompt=INSTRUCTIONS+' Use the supplied ReviewDraft JSON shape. The original input contains retained source document_id and block_id values. Use those identifiers, never extractor-generated identifiers. value identifies an entity; disposition describes the identity assertion; incident_status separately describes incident involvement. asserted identity does not mean affected. Quote original source passages. Return candidates, changes, contradictions, unresolved, request_drafts, incident_scope and scope_evidence. Extractor output is an untrusted proposal to check against the originals.'
    example_extract={'candidates':[{'kind':'supplier_lot','value':'exact source identifier','disposition':'uncertain','quote':'exact original passage','page':None}],'unresolved':[]}
    example_review={'candidates':[{'kind':'supplier_lot','value':'exact source identifier','disposition':'asserted','incident_status':'uncertain','source':{'document_id':'original document_id','block_id':'original block_id','quote':'exact original passage'}}],'changes':[],'contradictions':[],'unresolved':[],'request_drafts':[],'incident_scope':'unknown','scope_evidence':[]}
    manifest={'connection_id':connection['id'],'provider_base_url':connection['apiBaseUrl'],'provider_model_id':'Gemma-4-31B-IT',
              'catalog_model_key':model['id'],'catalog_pricing':model['pricing'],'catalog_sha256':hashlib.sha256((PRIVATE/'evolus-catalog.json').read_bytes()).hexdigest()}
    for kind,prompt,example,schema in [('extractor',extract_prompt,example_extract,ExtractorDraft),('agent',agent_prompt,example_review,ReviewDraft)]:
        # Evolus structure is an example JSON object, not JSON Schema. The full
        # Pydantic schema is explicit in userPrompt and enforced again locally.
        body={'name':prefix+' '+kind,'description':'Synthetic bounded BatchFence review proposals; no external actions',
            'prompt':prompt,'modelKey':model['id'],'fallbackModelKeys':[],'routerWebSearch':False,'webSearchType':'NONE',
            'useAskStream':False,'isChatVisible':False,'portalWidgetsEnabled':False,'fileToolsEnabled':False,'scriptToolEnabled':False,
            'mcpServers':[],'modelParameters':{'temperature':0,'max_tokens':1600},'isExtractor':kind=='extractor','applicationId':os.environ['EVOLUS_APPLICATION_ID']}
        agent=create(kind,'/api/v1/agents',body);aid=agent['agentId']
        structure=create(kind+'-structure',f'/api/v1/agents/{aid}/json',{'title':prefix+' '+kind+' JSON','pages':None,
            'structure':json.dumps(example),'userPrompt':'Return JSON data conforming to this schema (not the schema itself): '+json.dumps(schema.model_json_schema()),
            'canUseOCR':False,'maxCorrections':0,'webhookId':None,'webhookUrl':None},personal=True)
        manifest[kind]={'resource_id':aid,'output_structure_id':structure['id'],'model_key':model['id'],'schema_hash':digest(example),'prompt_hash':digest(prompt)}
    flow=create('workflow','/api/v1/workflows',{'name':prefix+' document review','description':'Native text extractor -> own AMD Gemma agent -> output. No OCR, messages, webhooks, schedule, tools or fallback.',
        'isActive':False,'multiFileMode':1,'emailPollingEnabled':False,'enableAuditKpi':False,'parameters':[]});wid=flow['id'];manifest['workflow_id']=wid
    for kind,typ,mode in [('extractor',13,1),('agent',1,4),('output',14,0)]:
        deps=[] if kind=='extractor' else [manifest['extractor' if kind=='agent' else 'agent']['step_id']]
        body={'name':prefix+' '+kind,'stepType':typ,'inputMode':mode,'inputStepIds':deps,'createDoc':False}
        if kind!='output':body.update(agentId=manifest[kind]['resource_id'],outputStructureId=manifest[kind]['output_structure_id'])
        step=create(kind+'-step',f'/api/v1/workflows/{wid}/steps',body)
        manifest.setdefault(kind,{}).update(step_id=step['id'],step_order=step['order'],input_step_ids=deps,input_mode=mode,prompt=None)
    memory=create('library','/api/v1/memories/simple',{'name':prefix+' isolated approved procedures','type':1,'aiAccess':0},personal=True)
    manifest['library_id']=memory['id']
    request('PUT',f'/api/v1/workflows/{wid}',body={'isActive':True,'multiFileMode':1,'emailPollingEnabled':False})
    verification=api.verify_workflow(manifest)
    save(MANIFEST,manifest)
    values={'EVOLUS_WORKFLOW_ID':wid,'EVOLUS_EXTRACTOR_ID':manifest['extractor']['resource_id'],'EVOLUS_AGENT_ID':manifest['agent']['resource_id'],
        'EVOLUS_GEMMA_MODEL_KEY':model['id'],'EVOLUS_LIBRARY_ID':memory['id'],'EVOLUS_WORKFLOW_MANIFEST_FILE':str(MANIFEST),
        'EVOLUS_WORKFLOW_MANIFEST_SHA256':hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
    for k,v in values.items():set_key(str(ROOT/'.env'),k,v)
    save(OUT/'evolus-configuration.json',{'status':'Remote configuration verified; execution acceptance pending','manifest':manifest,'verification':verification,
        'catalog_query':{'capability':'chat','context':'workflow-llm','authentication':'Personal developer key'},
        'contract_source':'Owner OpenAPI 3.0.4 plus actual official app public client https://app.evolus.ai/main-BUOWUGDZ.js for catalog/own-model endpoints',
        'calls_to_models_by_this_script':0,'own_cloud_vllm_verified':False})
    print('Configured exact remote resources in existing .env. No inference performed.')

if __name__=='__main__':main()
