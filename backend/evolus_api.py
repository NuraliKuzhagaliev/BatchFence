"""Evolus Integration API v1, from the owner's OpenAPI 3.0.4 export.

Provider execution fields are kept separate from locally derived attestations.
No callbacks, fallback models, webhooks, email or arbitrary URLs are accepted.
"""
import hashlib,json,os,re,time
import httpx
from .domain import DomainError,digest
from .fixtures import now


class UncertainExecution(DomainError):
    def __init__(self,execution_id=None):
        super().__init__('Evolus submission outcome is uncertain; reconcile any known execution ID before a new dispatch')
        self.execution_id=execution_id if isinstance(execution_id,str) and re.fullmatch(r'[a-fA-F0-9-]{36}',execution_id) else None


def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',str(value)):
        raise DomainError('Expected configured Evolus resource identifier')
    return value


def call(method,path,*,body=None,files=None,form=None,query=None,personal=False,transport=None,expect_text=False,timeout=40):
    from .evolus_adapter import https_origin,_bounded
    base=https_origin(os.environ['EVOLUS_API_BASE_URL'])
    if base!='https://api.evolus.ai':raise DomainError('Base differs from the supplied Evolus API specification')
    key_name='EVOLUS_USER_API_KEY' if personal else 'EVOLUS_API_KEY'
    if not os.getenv(key_name):raise DomainError('UNAVAILABLE: configure '+key_name+' privately')
    headers={'X-User-ApiKey' if personal else 'X-ApiKey':os.environ[key_name], 'X-Application-Id':os.environ['EVOLUS_APPLICATION_ID']}
    args={'params':query}
    if files:args.update(data=form or {},files=[('file',(f['filename'],f['raw'],f['media_type'])) for f in files])
    elif body is not None:args['json']=body
    started=time.perf_counter()
    with httpx.Client(timeout=timeout,follow_redirects=False,trust_env=False,transport=transport) as client:
        with client.stream(method,base+path,headers=headers,**args) as response:
            execution_header=response.headers.get('x-workflow-execution-id')
            try:raw=b''.join(_bounded(response.iter_bytes(),128000))
            except (httpx.TransportError,DomainError):
                if method=='POST' and path.endswith('/execute'):raise UncertainExecution(execution_header)
                raise
            if response.status_code>=400:
                # Problem bodies may contain request data; only a bounded code is retained.
                try:code=json.loads(raw).get('errorCode','')
                except (ValueError,AttributeError):code=''
                safe=code if isinstance(code,str) and re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}',code) else ''
                raise DomainError('Evolus HTTP '+str(response.status_code)+' '+safe+'; no automatic retry')
            try:result=raw.decode('utf-8') if expect_text else json.loads(raw) if raw else None
            except (ValueError,UnicodeDecodeError):
                if method=='POST' and path.endswith('/execute'):raise UncertainExecution(execution_header)
                raise DomainError('Evolus returned an invalid response; no result accepted')
    if any(os.getenv(k) and os.environ[k] in json.dumps(result) for k in ('AMD_API_KEY','GEMMA_API_KEY','EVOLUS_API_KEY','EVOLUS_USER_API_KEY')):
        raise DomainError('Private value found in provider result; output discarded')
    return {'provider':'Evolus','at':now(),'method':method,'path':path,'http_status':response.status_code,
        'elapsed_ms':round((time.perf_counter()-started)*1000),'response_hash':hashlib.sha256(raw).hexdigest(),
        'request_id':response.headers.get('x-request-id'), 'execution_header':response.headers.get('x-workflow-execution-id'),
        'result':result,'contract':'Evolus Integration API v1 / owner-supplied OpenAPI 3.0.4'}


def workflow_start(inputs,transport=None):
    wid=identifier(inputs['workflow_id'])
    try:reply=call('POST',f'/api/v1/workflows/{wid}/execute',files=inputs['file_items'],form={'input':inputs['text']},transport=transport)
    except httpx.TransportError:raise UncertainExecution()
    raw=reply.pop('result')
    try:eid=identifier(raw['executionId'])
    except (KeyError,TypeError,DomainError):raise UncertainExecution(reply.get('execution_header'))
    reply['result']={'execution_id':eid,'status':'running','provider_status':'Queued',
        'enqueued_at':raw.get('enqueuedAt'),'trace_id':raw.get('traceId'),'queue_job_id':raw.get('jobId')}
    return reply


def verify_workflow(manifest,before_call=lambda:None,transport=None):
    """Reject remote configuration drift before dispatch, including tools/costs."""
    evidence=[];wid=identifier(manifest['workflow_id'])
    def read(path,personal=False):
        before_call();reply=call('GET',path,personal=personal,transport=transport)
        evidence.append({k:v for k,v in reply.items() if k!='result'});return reply['result']
    flow=read(f'/api/v1/workflows/{wid}')
    connections=read('/api/v1/own-models/connections',personal=True)
    connection=next((c for c in connections if c.get('id')==manifest['connection_id']),None)
    if not connection or connection.get('disabled') or connection.get('apiBaseUrl')!=manifest['provider_base_url'] or not connection.get('hasApiKey'):
        raise DomainError('Verified own-model connection is missing, disabled or changed')
    if not any(m.get('modelId')==manifest['provider_model_id'] for m in connection.get('models',[])):
        raise DomainError('Verified Gemma model is no longer in the own-model connection')
    if flow.get('applicationId')!=os.environ['EVOLUS_APPLICATION_ID'] or not flow.get('isActive') or flow.get('multiFileMode')!=1:
        raise DomainError('Configured workflow ownership, active state or combined-file mode changed')
    if flow.get('emailPollingEnabled') or flow.get('scheduleCron'):raise DomainError('External/scheduled delivery must remain disabled')
    steps=flow.get('steps') or [];expected={manifest[k]['step_id'] for k in ('extractor','agent','output')}
    reader=manifest.get('document_reader')
    if reader:expected.add(reader['step_id'])
    if len(steps)!=len(expected) or {s['id'] for s in steps}!=expected:raise DomainError('Workflow must contain only the exact verified document, extractor, interpretation and terminal output steps')
    if reader:
        from .evolus_adapter import allowance
        proof=allowance('evolus')
        if not proof.get('phase_id') or proof.get('ocr_credits_per_page')!=reader['credits_per_page']:raise DomainError('Current funded document-reading tariff required')
        step=next(s for s in steps if s['id']==reader['step_id'])
        if step.get('stepType')!=0 or step.get('order')!=reader['step_order'] or step.get('inputStepIds') or step.get('inputMode')!=1 or step.get('ocrModelKey')!=reader['model_key'] or step.get('agentId') or step.get('prompt') or json.loads(step.get('stepConfigJson') or '{}')!=reader['config']:
            raise DomainError('Document-reading model, source or strict completeness configuration changed')
    for kind,step_type in [('extractor',13),('agent',1),('output',14)]:
        expected_step=manifest[kind];step=next(s for s in steps if s['id']==expected_step['step_id'])
        if step.get('order')!=expected_step['step_order']:raise DomainError('Workflow step order changed; execution output mapping is no longer verified')
        if step.get('stepType')!=step_type or step.get('inputStepIds',[])!=(expected_step.get('input_step_ids') or []):raise DomainError('Workflow dependency graph changed')
        if step.get('inputMode')!=expected_step['input_mode'] or step.get('prompt')!=expected_step.get('prompt'):
            raise DomainError('Workflow original-source input or step instructions changed')
        if step.get('stepConfigJson'):raise DomainError('Unexpected workflow block configuration; external or platform tools are not permitted')
        if kind=='output':continue
        aid=identifier(expected_step['resource_id']);oid=identifier(expected_step['output_structure_id'])
        if step.get('agentId')!=aid or step.get('outputStructureId')!=oid:raise DomainError('Workflow agent/output structure changed')
        agent=read(f'/api/v1/agents/{aid}')
        if digest(agent.get('prompt'))!=expected_step['prompt_hash'] or bool(agent.get('isExtractor'))!=(kind=='extractor') or agent.get('routerWebSearch') or agent.get('webSearchType')!='NONE':
            raise DomainError('Own-model instructions, extractor role or web-search configuration changed')
        if agent.get('modelKey')!=expected_step['model_key'] or agent.get('fallbackModelKeys') or agent.get('fileToolsEnabled') or agent.get('scriptToolEnabled') or agent.get('mcpServers') or agent.get('subAgents') or agent.get('functions') or agent.get('webApis') or agent.get('skills'):
            raise DomainError('Own Gemma model configuration changed or external tools/fallbacks were enabled')
        params=agent.get('modelParameters') or {}
        if not 0<int(params.get('max_tokens',0))<=1600 or params.get('temperature')!=0:raise DomainError('Model token/temperature budget changed')
        structure=read(f'/api/v1/agents/{aid}/json/{oid}',personal=True)
        schema=structure.get('structure')
        if isinstance(schema,str):schema=json.loads(schema)
        if digest(schema)!=expected_step['schema_hash'] or digest(structure.get('userPrompt'))!=expected_step['structure_prompt_hash'] or structure.get('checkScript') or structure.get('maxCorrections')!=0 or structure.get('canUseOCR') or structure.get('webhookId') or structure.get('webhookUrl'):
            raise DomainError('Extractor/output contract changed or automatic correction, OCR or webhook delivery was enabled')
    return {'checked_at':now(),'configuration_hash':digest(manifest),'requests':evidence,
        'model_identity_basis':'Verified own-model configuration; WorkflowExecution does not return runtime model ID',
        'provider_internal_retries':'BatchFence makes one dispatch. Structured correction budget is zero; undocumented provider infrastructure retries are not claimed absent.'}


def normalize_execution(raw,manifest):
    """stepStates does not return model identity. Never manufacture that field."""
    if raw.get('workflowId')!=manifest['workflow_id']:raise DomainError('Execution belongs to another configured workflow')
    states=raw.get('stepStates') or {};outputs=raw.get('stepOutputs') or {};steps=[]
    for kind in ('extractor','agent'):
        expected=manifest[kind];sid=expected['step_id']
        # Actual executions key these dictionaries by saved numeric step order.
        execution_key=str(expected['step_order']) if 'step_order' in expected else sid
        state=states.get(execution_key)
        if not state or execution_key not in outputs or state.get('durationMs') is None or state.get('status') not in (None,'done'):continue
        steps.append({'kind':kind,'id':expected['resource_id'],'step_id':sid,'state':state,
            'configured_model_key':expected['model_key'],'model_identity_basis':'Configuration, not a returned runtime model ID',
            'output_hash':digest(outputs.get(execution_key)),'output':outputs.get(execution_key),'execution_step_key':execution_key})
    provider_status=raw.get('status','');status={'Completed':'completed','Succeeded':'completed','Failed':'failed','Cancelled':'failed'}.get(provider_status,'running')
    draft=None
    if status=='completed':
        from .scope_proposals import parse_json
        try:draft=parse_json(raw.get('output'))
        except ValueError:draft={'unparsed_response':raw.get('output'),'raw_extraction_error':'Completed workflow output is not one JSON review draft; no facts accepted'}
    reader=manifest.get('document_reader');reading=None
    if reader:
        k=str(reader['step_order']);text=outputs.get(k)
        reading={'step_id':reader['step_id'],'configured_ocr_model':reader['model_key'],'state':states.get(k),'output_hash':digest(text),'text':text,
            'operation':'Evolus document reading; prefer native PDF text, OCR for scans','page_mapping':'Not returned as retained local block IDs; exact original/source validation and visual OCR review remain required'}
        if status=='completed' and (not text or not states.get(k) or states[k].get('status') not in (None,'done')):
            status='failed';draft=None
    return {'execution_id':raw['id'],'status':status,'provider_status':provider_status,'steps':steps,'draft':draft,'document_reading':reading,
        'interpretation_contract':manifest.get('interpretation_contract'),
        'consumption':raw.get('consumption'),'requested_at':raw.get('requestedAt'),'completed_at':raw.get('completedAt'),
        'trace_id':raw.get('traceId'),'error_present':bool(raw.get('error')),
        'runtime_model_identity':'Not returned by this API; independent AMD request evidence is required for runtime identity verification'}


def workflow_status(inputs,manifest,transport=None):
    wid=identifier(inputs['workflow_id']);eid=identifier(inputs['execution_id'])
    reply=call('GET',f'/api/v1/workflows/{wid}/executions/{eid}',transport=transport)
    if reply['result']['id']!=eid:raise DomainError('Unexpected external execution identifier')
    reply['result']=normalize_execution(reply['result'],manifest)
    return reply


def applicable_documents(documents,product,process,synthetic):
    from datetime import datetime,timezone
    current=datetime.now(timezone.utc)
    allowed=[d for d in documents if d['status']=='approved' and product in d['products'] and process in d['processes']
        and (synthetic or not d['synthetic']) and datetime.fromisoformat(d['valid_from'].replace('Z','+00:00'))<=current
        and (not d['valid_to'] or current<datetime.fromisoformat(d['valid_to'].replace('Z','+00:00')))]
    if len({d['id'] for d in allowed})!=len(allowed):raise DomainError('Overlapping approved revisions require owner resolution before indexing')
    return allowed


def library_scope(owner,product,process,documents):
    return digest({'owner':owner,'product':product,'process':process,'source_set':[(d['id'],d['version'],d['source_hash']) for d in sorted(documents,key=lambda x:x['id'])]})


def inspect_library(library_id,transport=None):
    return call('GET',f'/api/v1/memories/{identifier(library_id)}/documents',transport=transport)


def library_passages(binding,allowed_passages,transport=None,before_call=lambda:None):
    """Check exact remote membership BEFORE reading chunks. No broad agent RAG.

    Backend ranks only authorized passages; the library substantively retains
    and returns source chunks. Unknown/extra remote documents disable the path.
    """
    library_id=binding['library_id'];before_call();listed=inspect_library(library_id,transport)
    ids={d['id'] for d in listed['result']};expected={d['remote_document_id'] for d in binding['documents']}
    if ids!=expected:raise DomainError('Dedicated library membership drifted; retrieval disabled before reading content')
    if binding.get('library_type')=='Rag' and any(d.get('ingestionStatus')!=2 for d in listed['result']):raise DomainError('Rag indexing is not complete; no model may read the library')
    passages=[];provenance=[{k:v for k,v in listed.items() if k!='result'}]
    for document in binding['documents']:
        relevant=[p for p in allowed_passages if p['document_id']==document['document_id'] and p['version']==document['version']]
        if not relevant:continue
        before_call()
        if binding.get('library_type')=='Blob':
            reply=call('GET',f'/api/v1/memories/{identifier(library_id)}/documents/{identifier(document["remote_document_id"])}/download',transport=transport,expect_text=True)
            text=reply['result']
            if hashlib.sha256(text.encode('utf-8')).hexdigest()!=document['uploaded_content_hash']:raise DomainError('Retained library source changed; retrieval disabled')
        else:
            reply=call('GET',f'/api/v1/memories/{identifier(library_id)}/documents/{identifier(document["remote_document_id"])}/chunks',transport=transport)
            text='\n'.join(c.get('body') or '' for c in reply['result'])
        # Retained exact passages must survive indexing. No fabricated source offsets.
        for p in relevant:
            if p['quote'] not in text:raise DomainError('Library lacks the exact approved original passage; retrieval abstains')
            mapped={**p,'provider_document_id':document['remote_document_id'],'local_quote_mapping':'Exact approved passage in retained library content; provider span unavailable'}
            if binding.get('library_type')=='Rag':
                matched=[c for c in reply['result'] if c.get('id') and p['quote'] in (c.get('body') or '')]
                if not matched:raise DomainError('Complete approved passage is not present in an identified indexed chunk; no source citation accepted')
                mapped['provider_chunk_proof']={'remote_document_id':document['remote_document_id'],'source_hash':document['source_hash'],
                    'chunks':[{'id':c['id'],'body_hash':hashlib.sha256(c['body'].encode('utf-8')).hexdigest()} for c in matched]}
            passages.append(mapped)
        provenance.append({k:v for k,v in reply.items() if k!='result'})
    return passages,provenance
