"""Explicitly dispatched, bounded reference-connector outbox. Pending means held."""
import copy
import os
import time
import uuid
from urllib.parse import urlsplit
import httpx
from . import repository as repo,recovery,identity
from .domain import DomainError,digest
from .fixtures import now


def enqueue(db,owner,key,expected,idempotency_key):
    recovery.require_role(db,'release_approver')
    operation_id=digest({'owner':owner,'key':idempotency_key})
    _,prior=repo.get_record(db,owner,'outbox',operation_id)
    fingerprint=digest({'recovery_id':key,'digest':expected})
    if prior:
        if prior['fingerprint']!=fingerprint:raise DomainError('Outbox idempotency conflict')
        return prior
    rev,proposal=repo.get_record(db,owner,'recovery',key)
    if not proposal or proposal['status']!='approved' or proposal['digest']!=expected:raise DomainError('Current unconsumed approved recovery required')
    recovery.check_current(db,owner,proposal)
    if not recovery.authority_current(db,proposal['approval']['actor'],'release_approver'):raise DomainError('Approver authority revoked')
    payload={'operation_id':operation_id,'scope_hash':digest(owner),'actions':proposal['snapshot']['actions']}
    item={'id':operation_id,'recovery_id':key,'status':'pending_ack','attempts':0,'payload':payload,'payload_digest':digest(payload),
          'idempotency_key':idempotency_key,'fingerprint':fingerprint,'created_at':now(),'automatic_retry':False,
          'boundary':'Local reference connector sandbox. Pending or failed acknowledgement keeps every local restriction active.'}
    proposal['status']='pending_ack'
    repo.put_record(db,owner,'recovery',key,proposal,rev)
    repo.put_record(db,owner,'outbox',operation_id,item,0)
    repo.audit(db,owner,identity.current_actor(),'connector.enqueued',{},item,operation_id=idempotency_key)
    return item


def send(payload):
    address=os.getenv('REFERENCE_CONNECTOR_URL','')
    token=os.getenv('REFERENCE_CONNECTOR_TOKEN','')
    url=urlsplit(address)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or not url.port or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
        raise DomainError('Only an explicitly configured loopback local reference connector is supported')
    if len(token)<32:raise DomainError('Private reference connector token missing')
    with httpx.Client(timeout=8,follow_redirects=False,trust_env=False) as client:
        response=client.post(address.rstrip('/')+'/inventory/restrictions',headers={'Authorization':'Bearer '+token},json=payload)
    if response.status_code!=200 or len(response.content)>16000:raise DomainError('Reference connector failed to acknowledge the exact request')
    ack=response.json()
    if ack.get('operation_id')!=payload['operation_id'] or ack.get('request_digest')!=digest(payload) or ack.get('execution')!='LOCAL SANDBOX REFERENCE':
        raise DomainError('Reference acknowledgement does not match the exact operation')
    return ack


def dispatch(factory,owner,key):
    with repo.write(factory) as db:
        recovery.require_role(db,'release_approver')
        rev,item=repo.get_record(db,owner,'outbox',key)
        if not item:raise DomainError('Outbox operation unavailable')
        if item['status']=='acknowledged':return item
        if item['status']=='dispatching' and item['lease_until']>time.time():raise DomainError('Reference attempt already running')
        if item['attempts']>=3:raise DomainError('Three-attempt limit reached; owner reconciliation is required')
        _,proposal=repo.get_record(db,owner,'recovery',item['recovery_id'])
        recovery.check_current(db,owner,proposal)
        if not recovery.authority_current(db,proposal['approval']['actor'],'release_approver'):raise DomainError('Release approval revoked')
        attempt=uuid.uuid4().hex
        item.update(status='dispatching',attempts=item['attempts']+1,attempt_id=attempt,lease_until=time.time()+20,last_attempt_at=now())
        repo.put_record(db,owner,'outbox',key,item,rev)
    try:
        ack=send(item['payload']);error=None
    except Exception:
        ack=None;error='Reference timeout, transport or acknowledgement validation failure. Restrictions remain active. Retry explicitly using the same operation.'
    with repo.write(factory) as db:
        recovery.require_role(db,'release_approver')
        rev,current=repo.get_record(db,owner,'outbox',key)
        if current.get('attempt_id')!=attempt:return current
        current.setdefault('attempt_history',[]).append({'at':now(),'attempt':current['attempts'],'acknowledgement':ack,'error':error})
        proposal_rev,proposal=repo.get_record(db,owner,'recovery',item['recovery_id'])
        if ack:
            try:
                state=recovery.check_current(db,owner,proposal)
                if not recovery.authority_current(db,proposal['approval']['actor'],'release_approver'):raise DomainError('Approver authority changed')
            except DomainError:
                current.update(status='reconciliation_required',error='Acknowledgement arrived after local evidence/holds/authority changed. No local recovery applied; owner reconciliation required.')
                proposal['status']='failed_ack';repo.put_record(db,owner,'recovery',proposal['id'],proposal,proposal_rev)
            else:
                receipt=recovery.commit_removal(db,owner,proposal_rev,proposal,state,item['idempotency_key'],item['fingerprint'],ack)
                current.update(status='acknowledged',receipt=receipt)
        else:
            current.update(status='failed_ack',error=error)
            proposal['status']='failed_ack';repo.put_record(db,owner,'recovery',proposal['id'],proposal,proposal_rev)
        repo.put_record(db,owner,'outbox',key,current,rev)
        repo.audit(db,owner,identity.current_actor(),'connector.attempt_completed',item,current,operation_id=item['idempotency_key'])
        return current
