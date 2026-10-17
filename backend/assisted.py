"""Six connected extensions on existing scoped records, plans and recovery."""
import copy,json,re,uuid
from datetime import datetime,timezone
from . import repository as repo,identity,recovery
from .domain import DomainError,digest,make_plan
from .fixtures import now
from .assist_contracts import citation,fingerprint
from .knowledge_routes import catalog

KINDS={'assist','evidence-task','source-link','change-event','rereview','translation','label','label-review','handover'}


def records(db,owner,kind,case_id=None):
    values=[json.loads(row[0]) for row in db.execute('SELECT data FROM bf_records WHERE owner=? AND kind=? ORDER BY id',(owner,kind))]
    selected=[v for v in values if not case_id or v.get('case_id')==case_id]
    return sorted(selected,key=lambda v:(v.get('prepared_at') or v.get('as_of') or v.get('created_at') or v.get('started_at') or v.get('at') or '',v.get('id','')))


def save(db,owner,kind,key,value,expected=None):
    repo.put_record(db,owner,kind,key,value,expected)
    repo.audit(db,owner,identity.current_actor(),'assisted.'+kind,{},value)
    return value


def evidence_requests(db,owner,state,ranking=None):
    if ranking is None:
        _,saved=repo.get_record(db,owner,'evidence-ranking',state['id'])
        ranking=(saved or {}).get('rules') or {'policy_first':True,'deadline_first':True}
    result=make_plan(state)['result'];out=[]
    for q in result['requests']:
        item=copy.deepcopy(q);pools=set(q['pool_ids'])
        item.update(case_id=state['id'],revision=state['revision'],snapshot_hash=fingerprint(state),
            order_ids=sorted({a['order_id'] for a in state['allocations'] if a['pool_id'] in pools and a['status']=='open'}),
            due_date=q.get('earliest_order_due'),responsible_role=q.get('suggested_role'),probability=None,observed_response_seconds=None,
            closure_criteria='Relevant original source, explicit source/completeness review and current resolved planner cause. Upload alone never closes a question.',
            conditional=q.get('decision_change_units'),conditional_label='Possible proposal change only; applied holds remain. Standalone changes are not additive.')
        item['priority_reason']=['Policy/scope prerequisite' if q.get('global') else 'Receiving/source prerequisite',
            'Committed order deadline '+str(item['due_date']) if item['due_date'] else 'No committed deadline supplied',
            str(item['units'])+' distinct affected units; probability and response time unknown']
        out.append(item)
    out.sort(key=lambda q:(not(q.get('global') and ranking['policy_first']),q.get('due_date') or '9999' if ranking['deadline_first'] else '',-q['units'],q['id']))
    unique={p for q in out for p in q['pool_ids']}
    return {'requests':out,'unique_units':sum(s['units'] for s in state['stocks'] if s['id'] in unique),'ranking':ranking,
        'warning':'Individual conditional impacts overlap and must not be added. No sending or action authority.'}


def create_task(db,owner,state,cause_id,role,due_date,request_draft,idempotency_key):
    key='TASK-'+digest([state['id'],idempotency_key])[:24]
    _,prior=repo.get_record(db,owner,'evidence-task',key)
    proposed={'cause_id':cause_id,'role':role,'due_date':due_date,'request_draft':request_draft}
    if prior:
        if prior['request_fingerprint']!=digest(proposed):raise DomainError('Idempotency key belongs to another request draft')
        return prior
    q=next((q for q in evidence_requests(db,owner,state)['requests'] if q['id']==cause_id),None)
    if not q:raise DomainError('Current unresolved cause required; old requests are stale')
    if due_date:
        try:datetime.strptime(due_date,'%Y-%m-%d')
        except ValueError:raise DomainError('Use an explicit ISO due date or leave it unknown')
    task={'id':key,'case_id':state['id'],'cause_id':cause_id,'basis':q,'snapshot_hash':fingerprint(state),'case_revision':state['revision'],
          'responsible_role':role or None,'due_date':due_date or None,'draft':request_draft or q['draft'],'status':'open','responses':[],
          'request_fingerprint':digest(proposed),'created_at':now(),'actor':identity.current_actor(),'sending':'disabled; saved draft only'}
    return save(db,owner,'evidence-task',key,task,0)


def task_response(db,owner,state,task_id,document_id,outcome,quote,reviewed,note):
    rev,task=repo.get_record(db,owner,'evidence-task',task_id)
    if not task or task['case_id']!=state['id']:raise DomainError('Request unavailable in this incident')
    doc=next((d for d in state['documents'] if d['id']==document_id),None)
    if not doc or doc.get('request_id')!=task['cause_id']:raise DomainError('Response must be uploaded against this exact request; irrelevant files cannot close it')
    basis=next(({'document_id':doc['id'],'block_id':b['id'],'quote':quote} for b in doc['blocks'] if quote and quote in b['text']),None)
    if not basis or not reviewed:raise DomainError('Explicit original-source response review required')
    signature=digest([doc['original_hash'],outcome,quote])
    if any(r['fingerprint']==signature for r in task['responses']):return task
    if outcome=='resolved':
        identity.recheck(db,'quality_reviewer')
        current=evidence_requests(db,owner,state)['requests']
        # Cause identity includes evidence. Also compare the actual pool/kind so
        # changing a citation cannot masquerade as resolving the original gap.
        if state.get('pending_revision') or any(q['id']==task['cause_id'] or (q['kind']==task['basis']['kind'] and set(q['pool_ids'])&set(task['basis']['pool_ids'])) for q in current):
            raise DomainError('Question remains unresolved in the reviewed deterministic plan; review receiving/scope before closure')
        receiving_basis=any(r.get('outcome')=='resolved' and r.get('evidence',{}).get('document_id')==document_id for r in state.get('reconciliations',[]))
        scope_basis=state.get('scope',{}).get('resolution_evidence',{}).get('document_id')==document_id if state.get('scope',{}).get('resolution_evidence') else False
        if not receiving_basis and not scope_basis:raise DomainError('Closure must cite the exact source used by the current explicit receiving/scope review; an older ambiguous response cannot borrow a later resolution')
        task['status']='closed after current source review'
    else:task['status']='open: '+outcome
    task['responses'].append({'document_id':doc['id'],'source_hash':doc['original_hash'],'citation':basis,'outcome':outcome,'at':now(),'actor':identity.current_actor(),'note':note,'fingerprint':signature})
    return save(db,owner,'evidence-task',task_id,task,rev)


def conditions(db,owner,state,proposal_id=None):
    """Explain the actual recovery gates; this view creates no second authority."""
    _,policy=repo.get_record(db,owner,'recovery-policy','current');docs=catalog(db,owner)
    proposals=records(db,owner,'recovery',state['id']);proposal=next((p for p in proposals if p['id']==proposal_id),None) if proposal_id else (proposals[-1] if proposals else None)
    proofs=records(db,owner,'recovery-evidence',state['id']);items=[]
    def add(key,status,why,evidence=None):items.append({'id':key,'status':status,'reason':why,'evidence':evidence,'policy_clause':(policy or {}).get('id','Unreviewed whole-pool policy'),'verifier':(policy or {}).get('approved_by'),'verified_at':(policy or {}).get('at'),'version':(policy or {}).get('revision')})
    add('policy','satisfied' if policy and policy['catalog_digest']==digest(docs) else 'unknown','Current explicitly reviewed applicable whole-pool policy required',policy)
    add('incident_scope','satisfied' if not state.get('pending_revision') and state['scope'].get('incident_scope_status')=='resolved' else 'unknown','Current source-backed incident scope; receiving evidence alone cannot resolve scope',state['scope'])
    add('ancestry','satisfied' if proposal else 'unknown','Complete reviewed ancestry for each selected recovery pool is checked by recovery.snapshot; no proposal-wide percentage',proposal and proposal.get('snapshot',{}).get('evidence'))
    add('identity_and_inspection','satisfied' if proposal and proofs else 'unknown','Verified source authenticity and passed whole-pool inspection for every selected pool',proofs)
    current=False;failure='Prepare an exact recovery to evaluate all evidence and versions'
    if proposal:
        if proposal['status']=='executed':
            current=True;failure='Historical exact recovery receipt; no new authority'
        else:
            try:recovery.check_current(db,owner,proposal);current=True;failure='Snapshot, procedure, source, inventory and reviewer authority match'
            except DomainError as e:failure=str(e)
    add('current_snapshot','satisfied' if current else 'unknown',failure)
    for item in items:
        if item['id'] in ('ancestry','identity_and_inspection') and proposal and not current:item['status']='unknown'
    approval_recorded=bool(proposal and proposal.get('approval'))
    approved=bool(approval_recorded and recovery.authority_current(db,proposal['approval']['actor'],'release_approver'))
    add('independent_approval','satisfied' if approved else 'unsatisfied','Separate currently authorized identity must approve the exact recovery digest',proposal and proposal.get('approval'))
    executed=bool(proposal and proposal['status']=='executed')
    add('acknowledgement','satisfied' if executed else 'unsatisfied','Execution acknowledgement or sandbox receipt required; readiness is not execution',proposal and proposal.get('receipt'))
    _,inventory=repo.get_record(db,owner,'inventory','shared')
    others=[h for h in (inventory or {}).get('holds',[]) if h['status']=='active' and h['pool_id'] in proposal.get('pool_ids',[]) and h['id'] not in proposal.get('hold_ids',[])] if proposal else []
    add('other_holds','unsatisfied' if others else 'satisfied' if proposal else 'unknown','Other active reasons still block availability even after this reason is removed',others)
    stage='execution acknowledged' if executed else 'execution pending' if approved and current else 'approval received / stale or authority revoked' if approval_recorded else 'eligible to request approval' if current else 'review prerequisites'
    for item in items:
        if item['id']=='policy':continue
        evidence=item.get('evidence')
        item['verifier']=evidence.get('actor') if isinstance(evidence,dict) else None
        item['verified_at']=evidence.get('at') if isinstance(evidence,dict) else None
        item['verification_note']='See each source/inspection record for its actual verifier; policy approval is not evidence verification'
    return {'case_id':state['id'],'proposal_id':proposal and proposal['id'],'stage':stage,'conditions':items,'quantities':state.get('quantities',{}),
        'proposed_hold_units':state.get('plan',{}).get('result',{}).get('hold_units') if state.get('plan') else None,'score':None,'authority':'Informational explanation of existing recovery engine; no approval or execution endpoint here'}


def references(state,modules=None):
    refs=[]
    def add(kind,key,doc_id,detail):
        doc=next((d for d in state['documents'] if d['id']==doc_id),None)
        if doc:refs.append({'case_id':state['id'],'target_kind':kind,'target_id':key,'source_kind':'document','source_id':doc['id'],'version':doc['revision'],'source_hash':doc['original_hash'],'detail':detail})
    for i,e in enumerate(state['edges']):add('lineage',e.get('row_id',str(i)),e.get('evidence',{}).get('document_id'),'reviewed ancestry relationship')
    for p in state.get('plans',[])+([state['plan']] if state.get('plan') else []):
        for row in p.get('result',{}).get('rows',[]):
            for e in row.get('evidence',[]):add('plan',p['id'],e.get('document_id'),'plan source; applied receipts remain immutable')
    add('reviewed_scope',state['id'],state['scope'].get('source_document_id'),'reviewed incident boundary')
    for kind,values in (modules or {}).items():
        if kind not in ('answer','action','recovery','recovery-evidence','evidence-task','handover','assist','translation','label-review'):continue
        if not isinstance(values,list):continue
        for value in values:
            if not isinstance(value,dict):continue
            def visit(node):
                if isinstance(node,list):
                    for child in node:visit(child)
                elif isinstance(node,dict):
                    doc_id=node.get('document_id')
                    if isinstance(doc_id,str):
                        if any(d['id']==doc_id for d in state['documents']):add(kind,value.get('id','record'),doc_id,'typed module citation')
                        elif node.get('version') and isinstance(node.get('passage_id'),str):
                            refs.append({'case_id':state['id'],'target_kind':kind,'target_id':value.get('id','record'),'source_kind':'procedure','source_id':doc_id,'version':node['version'],'source_hash':node.get('source_hash',digest(node)),'detail':'typed approved-passage citation'})
                    for ref in node.get('procedure_refs',[]):
                        if isinstance(ref,str) and '@' in ref:
                            sid,version=ref.rsplit('@',1)
                            refs.append({'case_id':state['id'],'target_kind':kind,'target_id':value.get('id','record'),'source_kind':'procedure','source_id':sid,'version':version,'source_hash':digest(node),'detail':'explicit policy procedure revision'})
                    for child in node.values():
                        if isinstance(child,(dict,list)):visit(child)
            visit(value)
    return list({digest(r):r for r in refs}.values())


def register_change(db,owner,source_kind,source_id,old_version,new_version,classification,effective_at,old_quote,new_quote,note,event_key):
    identity.recheck(db,'quality_reviewer')
    key='CHANGE-'+digest([owner,event_key])[:24];_,prior=repo.get_record(db,owner,'change-event',key)
    payload={'source_kind':source_kind,'source_id':source_id,'old_version':old_version,'new_version':new_version,'classification':classification,'effective_at':effective_at,'old_quote':old_quote,'new_quote':new_quote}
    if prior:
        if prior['event_fingerprint']!=digest(payload):raise DomainError('Change-event idempotency key reused with different content')
        return prior
    effective=datetime.fromisoformat(effective_at.replace('Z','+00:00'))
    if not effective.tzinfo:raise DomainError('Timezone-aware effective time required')
    if source_kind=='procedure':
        docs=[d for d in catalog(db,owner) if d['id']==source_id];old=next((d for d in docs if str(d['version'])==old_version),None);new=next((d for d in docs if str(d['version'])==new_version),None)
        if not old or not new or old_quote not in '\n'.join(p['text'] for p in old['passages']) or new_quote not in '\n'.join(p['text'] for p in new['passages']):raise DomainError('Exact owned old/new approved-procedure passages required')
    shared_old_hash=None
    if source_kind=='document':
        all_states=[json.loads(r[0]) for r in db.execute('SELECT state FROM cases WHERE owner=?',(owner,))]
        first=next((d for s in all_states for d in s['documents'] if (d['id']==source_id or d['original_hash']==source_id) and str(d['revision'])==old_version),None)
        if not first:raise DomainError('Owned immutable old document version required')
        shared_old_hash=first['original_hash']
    impacted=[]
    from .enterprise_routes import snapshot
    for case_id,raw in db.execute('SELECT id,state FROM cases WHERE owner=?',(owner,)):
        state=json.loads(raw)
        if source_kind=='document':
            old=next((d for d in state['documents'] if d['original_hash']==shared_old_hash and str(d['revision'])==old_version),None)
            if not old:continue
            # Document versions use retained source hashes, not filenames. The new
            # source is another owned immutable document selected by ID.
            new=next((d for s in all_states for d in s['documents'] if d['id']==new_version),None)
            if not new or not any(old_quote in b['text'] for b in old['blocks']) or not any(new_quote in b['text'] for b in new['blocks']):raise DomainError('Exact retained old/new source passages required')
        links=references(state,snapshot(db,owner,case_id))
        relevant=any(l['source_kind']==source_kind and l['source_id']==source_id and str(l['version'])==old_version for l in links)
        if source_kind=='document':relevant=relevant or bool(old)
        if not relevant:continue
        task_id='REREVIEW-'+digest([key,case_id])[:24]
        current=effective<=datetime.now(timezone.utc)
        task={'id':task_id,'case_id':case_id,'change_id':key,'status':'scheduled future-effective review' if not current else 'wording-only assessment' if classification=='wording_only' else 'review required',
              'owner_role':'Quality reviewer','reason':classification,'old_quote':old_quote,'new_quote':new_quote,'references':links,
              'historical_receipts_preserved':[r['transaction_id'] for r in state['receipts']],'at':now(),'effective_at':effective_at}
        save(db,owner,'rereview',task_id,task,0);impacted.append(task)
        if current and classification!='wording_only':
            from .app import invalidate
            state['revision']+=1;invalidate(state,'Registered source/procedure change requires assessment; applied restrictions and receipts remain')
            db.execute('UPDATE cases SET state=? WHERE owner=? AND id=?',(json.dumps(state),owner,case_id))
    event={'id':key,**payload,'at':now(),'actor':identity.current_actor(),'note':note,'event_fingerprint':digest(payload),'impacted_cases':[t['case_id'] for t in impacted],
           'boundary':'Future-effective changes do not apply retroactively. Completed receipts are immutable; assessments do not create physical holds.'}
    return save(db,owner,'change-event',key,event,0)


LANGUAGES={'en':'English','ru':'Russian','it':'Italian'}
ID_PATTERN=re.compile(r'\b(?:SUP|FG|LOT|REC|LIN|DOC|PROC|NX|RM)[- ][A-Za-zА-Яа-я0-9-]+\b|\b\d+(?:[.,]\d+)?\b')


def translation_flags(original,translated):
    protected=ID_PATTERN.findall(original);missing=[v for v in protected if v not in translated]
    flags=['Original identifier/number not preserved: '+v for v in missing]
    if re.search(r'\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b|\b\d+[,.]\d+\b',original):flags.append('Date/decimal interpretation requires explicit original-value review; no implicit conversion')
    source_uncertain=bool(re.search(r'\b(?:may|might|possibly|could|non|not|не|может|возможно|potrebbe|forse)\b',original,re.I))
    target_certain=bool(re.search(r'\b(?:unaffected|safe|complete|is affected|unlimited|release)\b',translated,re.I))
    if source_uncertain and target_certain:flags.append('Negation/modality or completeness may have changed; original-language verification required')
    return flags


def make_translation(db,owner,state,document_id,language,segments,provenance,key):
    if language not in LANGUAGES:raise DomainError('Supported initial evidence languages are English, Russian and Italian; unsupported language requires qualified assistance')
    doc=next((d for d in state['documents'] if d['id']==document_id),None)
    if not doc:raise DomainError('Original source unavailable')
    declared=doc.get('evidence_language','en')
    if declared in ('ru','it','unsupported') and language!=declared:raise DomainError('Derived translation must preserve the original declared language; unsupported evidence requires qualified support')
    if len(segments)>80:raise DomainError('Translation segment limit is 80')
    linked=[];flags=[]
    for segment in segments:
        ref=citation(state,segment['source']);text=segment['translation']
        if not text or len(text)>2500:raise DomainError('Bounded nonempty translation required')
        if ref['document_id']!=document_id:raise DomainError('Translation cannot quote another source')
        linked.append({'source':ref,'translation':text,'protected_original_values':ID_PATTERN.findall(ref['quote'])})
        flags+=translation_flags(ref['quote'],text)
    result={'id':'TR-'+digest([state['id'],key])[:24],'case_id':state['id'],'document_id':document_id,'original_hash':doc['original_hash'],
        'source_language':language,'target_language':'en','segments':linked,'flags':sorted(set(flags)),'status':'unreviewed derived translation',
        'provenance':provenance,'at':now(),'case_revision':state['revision'],'review':None,'authority':'Original source only; translation is not a verbatim original quotation or inventory fact'}
    _,prior=repo.get_record(db,owner,'translation',result['id'])
    if prior:
        if prior['segments']!=linked:raise DomainError('Translation idempotency key used for different content')
        return prior
    if language!='en':
        # Metadata makes the qualification gate apply to the existing incident
        # and receiving review paths too, not merely this derived-artifact view.
        doc['evidence_language']=language
        doc['language_review_required']=True
        doc['language_review']=None
        if state.get('plan') and not state.get('pending_revision'):
            from .app import invalidate
            invalidate(state,'Original-language qualification is required before consequential use of this source')
    return save(db,owner,'translation',result['id'],result,0)


def review_translation(db,owner,state,key,can_verify_original,qualified_reference,critical_fields_confirmed,note):
    identity.recheck(db,'quality_reviewer');rev,tr=repo.get_record(db,owner,'translation',key)
    if not tr or tr['case_id']!=state['id']:raise DomainError('Translation unavailable')
    doc=next((d for d in state['documents'] if d['id']==tr['document_id']),None)
    if not doc or doc['original_hash']!=tr['original_hash'] or state['revision']!=tr['case_revision']:raise DomainError('Translation review is stale')
    if not can_verify_original or len(qualified_reference.strip())<8 or not critical_fields_confirmed:raise DomainError('Consequential translated fields require a reviewer who can verify the original and an explicit qualification/reference')
    if tr['flags']:raise DomainError('Translation flags remain unresolved; create a corrected derived version before approval')
    tr.update(status='reviewed translation / original remains authoritative',review={'actor':identity.current_actor(),'at':now(),'qualification_reference':qualified_reference,'note':note,'critical_fields_confirmed':True})
    doc['language_review']={'translation_id':key,'original_hash':doc['original_hash'],'at':now(),'actor':identity.current_actor(),'qualification_reference':qualified_reference}
    return save(db,owner,'translation',key,tr,rev)


def handover_snapshot(db,owner,state,previous_id=None):
    previous=None
    if previous_id:
        _,previous=repo.get_record(db,owner,'handover',previous_id)
        if not previous or previous['case_id']!=state['id']:raise DomainError('Previous handover unavailable in this case')
    plan=state.get('plan');proposal_current=bool(plan and not state.get('pending_revision') and plan.get('revision')==state['revision'] and plan.get('status')!='stale')
    quantities={'proposed_hold_units':plan['result']['hold_units'] if proposal_current else None,
                'applied_hold_units':state.get('quantities',{}).get('applied_hold_units',sum(s['units'] for s in state['stocks'] if s['status']=='held')),
                'pending_recovery_units':state.get('quantities',{}).get('recovery_pending_units',0),'confirmed_recovery_units':state.get('quantities',{}).get('confirmed_recovery_units',0)}
    tasks=records(db,owner,'evidence-task',state['id']);rereviews=records(db,owner,'rereview',state['id'])
    events=[{'id':'event-'+str(i),'at':e['at'],'type':e['type'],'message':e['message']} for i,e in enumerate(state['history']) if not previous or e['at']>previous['as_of']]
    facts=[{'id':'quantity-'+k,'text':k.replace('_',' ')+': '+(str(v) if v is not None else 'unknown / not calculated'),'value':v} for k,v in quantities.items()]
    if plan and not proposal_current:facts.append({'id':'prior-proposal','text':'Historical proposal: '+str(plan['result']['hold_units'])+' units; stale after changed evidence, not current authority.'})
    facts += [{'id':t['id'],'text':('Evidence request: '+t['draft']+' Owner: '+str(t['responsible_role'] or 'not assigned')+' Due: '+str(t['due_date'] or 'not set'))[:1600]} for t in tasks if not t['status'].startswith('closed')]
    facts += [{'id':'gap-'+q['id'],'text':q['missing']+'. '+q['reason']} for q in evidence_requests(db,owner,state)['requests']]
    facts += [{'id':t['id'],'text':'Re-review: '+t['reason']+'. '+t['status']} for t in rereviews]
    facts += [{'id':e['id'],'text':e['message'][:1600]} for e in events[-10:]]
    readiness=conditions(db,owner,state) if state.get('workspace_attached') else {'stage':'Review current scope before planning recovery'}
    facts.insert(4,{'id':'next-action','text':'Next permitted action: '+readiness['stage']})
    if previous and not events:facts.insert(5,{'id':'shift-changes','text':'No new incident audit events since '+previous['as_of']+'. Check current outstanding tasks before continuing.'})
    return {'case_id':state['id'],'case_revision':state['revision'],'inventory_version':state['inventory_version'],'quantities':quantities,'facts':facts,
            'events':events,'task_owners_missing':[t['id'] for t in tasks if not t['responsible_role']],'previous_id':previous_id,
            'fingerprint':fingerprint(state,catalog(db,owner)),'records_hash':material_records_hash(db,owner,state['id']),
            'required_fact_ids':[f['id'] for f in facts[:5]],'as_of':now()}


def validate_handover(snapshot,raw):
    """Narrative may select exact facts; novel numbers/statuses cannot sneak in."""
    allowed={f['id']:f['text'] for f in snapshot['facts']}
    if not isinstance(raw,dict) or set(raw)!={'statements'} or not isinstance(raw['statements'],list) or len(raw['statements'])>24:raise DomainError('Invalid handover narrative schema')
    for statement in raw['statements']:
        if set(statement)!={'fact_id','text'} or statement['fact_id'] not in allowed or statement['text']!=allowed[statement['fact_id']]:
            raise DomainError('Handover invented or changed a number/status/source fact')
    if not set(snapshot.get('required_fact_ids',[]))<={s['fact_id'] for s in raw['statements']}:raise DomainError('Handover omitted required proposed/applied/recovery quantities or next permitted action')
    return raw['statements']


def create_handover(db,owner,state,key,previous_id=None,narrative=None,provenance=None):
    hid='HANDOVER-'+digest([state['id'],key])[:24];_,prior=repo.get_record(db,owner,'handover',hid)
    if prior:
        if prior['previous_id']!=previous_id:raise DomainError('Handover idempotency key reused')
        return prior
    snap=handover_snapshot(db,owner,state,previous_id)
    fallback=None
    try:statements=validate_handover(snap,narrative) if narrative is not None else snap['facts'][:24]
    except DomainError as exc:statements=snap['facts'][:24];fallback=str(exc)
    brief={'id':hid,'case_id':state['id'],'previous_id':previous_id,'as_of':snap['as_of'],'snapshot':snap,'statements':statements,
           'provenance':provenance or {'provider':'Deterministic snapshot summary / no model call'},'fallback':fallback,
           'author':identity.current_actor(),'review':None,'authority':'Read/acknowledge/export only; this brief never approves or executes recovery'}
    return save(db,owner,'handover',hid,brief,0)


def brief_current(db,owner,state,brief):
    snap=brief['snapshot']
    return snap['fingerprint']==fingerprint(state,catalog(db,owner)) and snap['records_hash']==material_records_hash(db,owner,state['id'])


def material_records_hash(db,owner,case_id):
    return digest({kind:records(db,owner,kind,case_id) for kind in ('evidence-task','rereview','translation','label','label-review','recovery','action','answer')})


def blocking_reviews(db,owner,case_id):
    return [r for r in records(db,owner,'rereview',case_id)
        if r['reason']!='wording_only' and not r.get('review') and datetime.fromisoformat(r['effective_at'].replace('Z','+00:00'))<=datetime.now(timezone.utc)]
