"""Exact approved Blob sets and a narrowly authorized fictional Rag phase."""
import os,json,hashlib
from . import identity,repository as repo,evolus_adapter as guard,evolus_api as api,evolus_rag as rag,assisted as a
from .domain import DomainError,digest
from .knowledge_routes import catalog
from .public_demo import inference_access
from .fixtures import now


def scope_for(owner,product,process,documents,kind):
    base=api.library_scope(owner,product,process,documents)
    return digest({'scope':base,'route':'agent-rag-v1'}) if kind=='Rag' else base


def index(data,request):
    from .app import connect
    owner=request.state.owner
    with inference_access('live',request.headers.get('x-bf-demo-token','')):
        with repo.write(connect) as db:
            identity.recheck(db,'administrator')
            if not data.reviewed:raise DomainError('Explicit isolated source, revision and library review required')
            docs=catalog(db,owner);approved=api.applicable_documents(docs,data.product,data.process,data.synthetic)
            if not approved or len(approved)>12:raise DomainError('Index1–12 exact approved versions, resolving overlapping revisions first')
            if data.library_type=='Rag':
                proof=guard.allowance('evolus')
                if not proof.get('embedding_indexing_authorized') or not data.synthetic or any(not d['synthetic'] for d in approved):raise DomainError('This Rag phase accepts only explicitly approved fictional sources under verified event funding')
                allowed=set(proof.get('rag_source_hashes',[]))
                if not 1<=len(approved)<=proof.get('rag_max_documents',1) or any(d['source_hash'] not in allowed for d in approved):raise DomainError('Rag source set is outside the exact fictional hashes authorized for this phase; no upload occurred')
            if data.library_type=='Blob' and not data.library_id:raise DomainError('Select a dedicated empty Blob library')
            scope=scope_for(owner,data.product,data.process,approved,data.library_type);snapshot=digest(docs)
            _,prior=repo.get_record(db,owner,'knowledge-binding',scope)
            if prior:
                if not data.reconcile_agent_id or data.library_type!='Rag':return prior
                if data.library_id and data.library_id!=prior['library_id']:raise DomainError('Reconciliation cannot substitute the bound source library')
                if prior['catalog_digest']!=snapshot or not prior.get('documents') or len(prior['documents'])!=len(approved):raise DomainError('Partial source upload requires explicit investigation; no automatic re-ingestion')
                passages=[{'document_id':d['id'],'version':d['version'],'quote':p['text']} for d in approved for p in d['passages']]
                api.library_passages(prior,passages)
                value=rag.reconcile_binding(prior,data.reconcile_agent_id)
                value.update(status='indexed verified scope',at=now(),error=None,reconciled=True)
                return a.save(db,owner,'knowledge-binding',scope,value)
            for who,encoded in db.execute("SELECT owner,data FROM bf_records WHERE kind='knowledge-binding'"):
                if data.library_id and json.loads(encoded)['library_id']==data.library_id:raise DomainError('Library already reserved for another exact source set')
            guard.contract();guard.reserve(db,'evolus',metadata=True)
            value={'library_id':data.library_id,'library_type':data.library_type,'scope':scope,'product':data.product,'process':data.process,'status':'reserved / indexing incomplete',
                'catalog_digest':snapshot,'documents':[],'at':now(),'actor':identity.current_actor(),'note':data.note,'provenance':[]}
            a.save(db,owner,'knowledge-binding',scope,value,0)
        try:
            if not value['library_id']:
                result=api.call('POST','/api/v1/memories/simple',personal=True,body={'name':'BatchFence fictional scope '+scope[:12],'type':0,'aiAccess':0})
                value['library_id']=result['result']['id']
                with repo.write(connect) as db:a.save(db,owner,'knowledge-binding',scope,value)
            lid=api.identifier(value['library_id']);inspection=api.inspect_library(lid)
            if inspection['result']!=[]:raise DomainError('Dedicated empty library required; no existing broad content may be adopted')
            memory=api.call('GET',f'/api/v1/memories/{lid}')['result']
            if memory.get('applicationId')!=os.environ['EVOLUS_APPLICATION_ID'] or memory.get('type')!=(0 if data.library_type=='Rag' else 1) or memory.get('aiAccess')!=0:raise DomainError('Exact application-owned read-only library type required')
            for document in approved:
                with repo.write(connect) as db:
                    identity.recheck(db,'administrator')
                    if digest(catalog(db,owner))!=snapshot:raise DomainError('Catalog changed during indexing; partial library stays unavailable')
                    guard.reserve(db,'evolus',metadata=True)
                if data.library_type=='Rag':
                    before=rag.balance()
                    with repo.write(connect) as db:guard.reserve(db,'evolus')
                    text='Document ID: '+document['id']+'\nRevision: '+str(document['version'])+'\nSource hash: '+document['source_hash']+'\n\n'+'\n\n'.join('Passage ID: '+p['id']+'\nPage: '+str(p['page'])+'\n'+p['text'] for p in document['passages'])
                else:text='\n\n'.join(p['text'] for p in document['passages'])
                content=text.encode('utf-8');language='ru' if any('\u0400'<=c<='\u04ff' for c in text) else 'en'
                reply=api.call('POST',f'/api/v1/memories/{lid}/documents',files=[{'filename':document['source_hash']+'.txt','raw':content,'media_type':'text/plain'}],query={'language':language,'backgroundIngestion':'false','augmentation':'false','rephrasings':0,'implicitQuestions':0})
                remote=reply['result']
                if remote.get('memoryId')!=lid or not remote.get('id'):raise DomainError('Unexpected indexing destination')
                value['documents'].append({'document_id':document['id'],'version':document['version'],'source_hash':document['source_hash'],'remote_document_id':remote['id'],'ingestion_status':remote.get('ingestionStatus'),'uploaded_content_hash':hashlib.sha256(content).hexdigest(),'source_basis':'Approved retained passages; Rag adds explicit document/version/passage headers'})
                value['provenance'].append({k:v for k,v in reply.items() if k!='result'})
                if data.library_type=='Rag':
                    after=rag.balance(enforce=False);value.setdefault('credit_observations',[]).append({'before':before,'after':after,'delta_account_wide':before['spendable_platform_credits']-after['spendable_platform_credits'],'tariff':'Metadata403; authorized small event-credit probe, actual balance monitored'})
                    if after['spendable_platform_credits']<guard.allowance('evolus')['stop_margin']:raise DomainError('Demo reserve reached; stop expansion')
                if remote.get('ingestionStatus')!=2:raise DomainError('Indexing incomplete; preserve remote document ID and reconcile. No automatic re-ingestion or model use.')
                with repo.write(connect) as db:a.save(db,owner,'knowledge-binding',scope,value)
            if data.library_type=='Rag':
                def retain(made):
                    value.update(agent_id=made['agent_id'],agent_prompt_hash=made['prompt_hash'],configured_model_key=made['configured_model_key'],citation_protocol=made['citation_protocol'])
                    with repo.write(connect) as db:a.save(db,owner,'knowledge-binding',scope,value)
                made=rag.create_agent(lid,retain=retain);rag.verify(value)
            with repo.write(connect) as db:
                identity.recheck(db,'administrator')
                if digest(catalog(db,owner))!=snapshot:raise DomainError('Approved revisions changed; binding remains unavailable')
                value.update(status='indexed verified scope',at=now());return a.save(db,owner,'knowledge-binding',scope,value)
        except Exception as exc:
            value.update(status='indexing unavailable / explicit reconciliation required',error=str(exc) if isinstance(exc,DomainError) else 'Provider/indexing transport failed; no automatic re-ingestion')
            with repo.write(connect) as db:a.save(db,owner,'knowledge-binding',scope,value)
            raise
