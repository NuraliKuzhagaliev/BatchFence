"""Mapped CSV proposals. Parsing never grants incident or inventory authority."""
import copy
import csv
import hashlib
import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .domain import DomainError, validate_dataset, digest
from .fixtures import document, now

FIELDS={
 'inventory':['row_id','pool_id','units','unit_cents','status','ancestry_complete','site','product_family'],
 'lineage':['row_id','source','target','kind'],
 'allocations':['row_id','order_id','pool_id','units','due_date','status'],
 'inspections':['observation_id','event_time','site','product','process','method','regime','inspected','nonconforming','defect','pool_ids','metric'],
}


def integer(value):
    if not str(value).isdigit(): raise ValueError('Expected a nonnegative whole number')
    n=int(value)
    if n>9_000_000_000: raise ValueError('Value exceeds supported bound')
    return n


def timestamp(value,tz):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo(tz))
    return dt.astimezone(timezone.utc).isoformat()


def inspection(row,source,tz):
    if row['metric']!='nonconforming_units': raise ValueError('Use nonconforming units, not total defect counts')
    n=integer(row['inspected']); bad=integer(row['nonconforming'])
    if not n or bad>n: raise ValueError('Inspected quantity must be positive; nonconforming cannot exceed inspected')
    if any(not str(row[k]).strip() for k in FIELDS['inspections'] if k!='pool_ids'): raise ValueError('Required inspection field is empty')
    return {**row,'inspected':n,'nonconforming':bad,'event_time':timestamp(row['event_time'],tz),
            'pool_ids':[x.strip() for x in row['pool_ids'].split(';') if x.strip()], 'source':source}


def preview(state,raw,filename,kind,mapping,metadata):
    if kind not in FIELDS: raise DomainError('Unsupported import kind')
    if metadata.get('unit')!='piece': raise DomainError('Only discrete piece quantities are supported; no implicit unit conversion')
    if not metadata.get('source_revision'): raise DomainError('A source revision is required')
    try: ZoneInfo(metadata['timezone'])
    except (KeyError,ZoneInfoNotFoundError): raise DomainError('Choose an explicit IANA timezone')
    try: observed_at=timestamp(metadata['observed_at'],metadata['timezone'])
    except (KeyError,ValueError): raise DomainError('Source observation time is required')
    doc=document(filename,raw,synthetic=metadata.get('synthetic',False))
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),strict=True))
    if not rows or len(rows)>500: raise DomainError('Imports support 1–500 rows')
    if any(None in r or any(v is None for v in r.values()) for r in rows): raise DomainError('CSV has missing/extra columns')
    headers=list(rows[0]); errors=[]; parsed=[]
    missing=[f for f in FIELDS[kind] if mapping.get(f) not in headers]
    if missing: return {'headers':headers,'required_fields':FIELDS[kind],'errors':[{'row':0,'message':'Map fields: '+', '.join(missing)}],'rows':[], 'document':doc}
    ids=set()
    for i,row in enumerate(rows):
        source={'document_id':doc['id'],'block_id':doc['blocks'][i+1]['id'],'quote':doc['blocks'][i+1]['text']}
        try:
            r={field:row[mapping[field]].strip() for field in FIELDS[kind]}
            key=r.get('row_id') or r.get('observation_id')
            if not key or key in ids: raise ValueError('Missing or duplicate stable row identifier')
            ids.add(key)
            if kind=='inventory':
                if r['ancestry_complete'] not in ('true','false'): raise ValueError('Completeness must be explicitly true or false')
                parsed.append({'id':r['pool_id'],'row_id':r['row_id'],'units':integer(r['units']),'unit_cents':integer(r['unit_cents']),
                    'complete':r['ancestry_complete']=='true','status':r['status'],'site':r['site'],'product_family':r['product_family'],
                    'source':source,'snapshot_version':metadata['source_revision']})
            elif kind=='lineage': parsed.append({**r,'evidence':source})
            elif kind=='allocations': parsed.append({**r,'units':integer(r['units']),'revision':metadata['source_revision'],'source':source})
            else: parsed.append(inspection(r,source,metadata['timezone']))
        except (ValueError,KeyError) as exc: errors.append({'row':i+2,'message':str(exc)})
    proposal=copy.deepcopy(state)
    target={'inventory':'stocks','lineage':'edges','allocations':'allocations'}.get(kind)
    if target and not errors:
        proposal[target]=parsed
        try:
            validate_dataset(proposal['stocks'],proposal['edges'],proposal['allocations'])
            known={e['source'] for e in state['edges']}|{e['target'] for e in state['edges']}|{s['id'] for s in state['stocks']}
            if kind=='lineage' and any(e['source'] not in known or e['target'] not in known for e in parsed):
                raise DomainError('Unknown lineage entities require separately reviewed registration; no genealogy is inferred')
            held={s['id']:s['units'] for s in state['stocks'] if s['status']=='held'}
            for pool,units in held.items():
                if not any(s['id']==pool and s['units']==units for s in proposal['stocks']):
                    raise DomainError('Held stock cannot disappear or change quantity through import')
        except DomainError as exc: errors.append({'row':0,'message':str(exc)})
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(observed_at)).total_seconds()/86400
    warnings=[]
    if age>30: warnings.append('Source is older than the configured 30-day freshness policy; confirm current records before decisions.')
    if age<0: errors.append({'row':0,'message':'Source observation time is in the future'})
    if kind=='inspections':
        known={s['id'] for s in state['stocks']}|{e['source'] for e in state['edges']}
        unknown=sorted({pool for row in parsed for pool in row['pool_ids'] if pool not in known})
        if unknown: warnings.append('Unmapped inspection identifiers remain unresolved: '+', '.join(unknown))
    return {'headers':headers,'required_fields':FIELDS[kind],'errors':errors,'warnings':warnings,'rows':parsed,'document':doc,
            'kind':kind,'mapping':mapping,'metadata':metadata,'case_id':state['id'],'case_revision':state['revision'],
            'input_digest':digest({'revision':state['revision'],'inventory':state['inventory_version'],'stocks':state['stocks'],'edges':state['edges']}),
            'review_required':True,'observed_at':observed_at,'original_hash':hashlib.sha256(raw).hexdigest()}


def validate_commit(state,proposal,reviewed,note,freshness_ack):
    if proposal.get('errors'): raise DomainError('Correct all import errors and preview again')
    if not reviewed or len(note.strip())<20: raise DomainError('Explicit mapping, units and source review with an explanation is required')
    if proposal.get('warnings') and not freshness_ack: raise DomainError('Review freshness and unmapped-identifier warnings explicitly')
    expected=digest({'revision':state['revision'],'inventory':state['inventory_version'],'stocks':state['stocks'],'edges':state['edges']})
    if proposal.get('case_id')!=state['id'] or expected!=proposal.get('input_digest'): raise DomainError('Import preview is stale; preview current records again')
