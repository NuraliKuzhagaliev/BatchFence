"""Source/contract regressions, not model inference or human acceptance."""
import copy,json
from pathlib import Path
import pytest
from backend.fixtures import document,ROOT
from backend.scope_proposals import parse_json,validate_proposals,legacy_output
from backend.assist_contracts import validate_draft

def proposal(text,lot,status='affected',kind='supplier_lot',quote=None):
    d=document('unseen.txt',text.encode())
    e={'document_id':d['id'],'block_id':'line-1','quote':quote or text}
    return d,{'facts':[{'lot_id':lot,'kind':kind,'status':status,'evidence':[e]}],'qualifiers':[],'scope_status':'unknown','scope_evidence':[]}

@pytest.mark.parametrize('text,lot',[
    ('NX-206 may be involved; inspection is pending. The full affected boundary is unknown.','NX-206'),
    ('Receiving record REC-554 references pool POOL-21 and supplier lot NX-208. Document DOC-64 is a record identifier, not a supplier lot.','NX-208'),
    ('The first paragraph names NX-209 affected. A later unsigned note says NX-209 is clear. This contradiction remains unresolved.','NX-209'),
    ('The signed receiving reconciliation states POOL-23 contains NX-211 exclusively. It supersedes lineage rows OLD-71 and OLD-72. Supplier identity was checked by the receiver.','POOL-23'),
    ('OCR transcript: Affected lots NX-2I3 (the scanned page may read NX-213). Critical identifier not visually confirmed.','NX-2I3'),
    ('Supplier lot QZ-71 is not affected.','QZ-71')])
def test_exact_observed_unsupported_positives_are_quarantined(text,lot):
    d,p=proposal(text,lot)
    with pytest.raises(ValueError):validate_proposals(p,[d])

@pytest.mark.parametrize('status',['uncertain','mentioned'])
def test_false_legacy_never_means_excluded(status):
    d,p=proposal('Supplier lot ZZ-004 is mentioned, involvement unresolved.','ZZ-004',status)
    checked=validate_proposals(p,[d]);assert checked['facts'][0]['status']==status
    assert legacy_output(checked)['facts'][0]['affected'] is False

def test_negation_revision_and_unrelated_conflict_do_not_merge_roles():
    text=json.loads((ROOT/'evals/continuation/scope-heldout-v3.json').read_text(encoding='utf-8'))['items'][1]['source']
    d,p=proposal(text,'K9-504',quote='affected supplier lot K9-504.')
    p['facts'].append({'lot_id':'K9-503','kind':'supplier_lot','status':'explicitly_excluded','evidence':[{'document_id':d['id'],'block_id':'line-1','quote':'K9-503 is now explicitly not affected.'}]})
    p['facts'].append({'lot_id':'K9-505','kind':'supplier_lot','status':'uncertain','evidence':[{'document_id':d['id'],'block_id':'line-1','quote':'Lot K9-505 has not been investigated and may be involved.'}]})
    p['scope_status']='conflicting';assert len(validate_proposals(p,[d])['facts'])==3

@pytest.mark.parametrize('answer',['{"facts":[],"facts":[]}','{} trailing','```json\n{}\n``` trailing','[]','{"x":NaN}','~~~{}~~~',''])
def test_malformed_is_not_repaired_into_a_fact(answer):
    with pytest.raises(ValueError):parse_json(answer)

def test_missing_qualifier_is_format_failure_not_silent_empty_default():
    d,p=proposal('Affected lots: AA-77.','AA-77');p.pop('qualifiers')
    with pytest.raises(ValueError):validate_proposals(p,[d])
    assert parse_json('```json\n{"facts": []}\n```')=={'facts':[]}

def test_scope_requires_exhaustive_incident_not_exclusive_one_pool():
    d,p=proposal('Pool FG-Z exclusively contains supplier lot XB-6. Complete ancestry.','XB-6','mentioned')
    p.update(scope_status='complete',scope_evidence=p['facts'][0]['evidence'])
    with pytest.raises(ValueError,match='exhaustive'):validate_proposals(p,[d])
    d,p=proposal('Affected supplier lot R4-700. This is the complete incident boundary; no other supplier lots are affected.','R4-700',quote='Affected supplier lot R4-700.')
    p.update(scope_status='complete',scope_evidence=[{'document_id':d['id'],'block_id':'line-1','quote':'This is the complete incident boundary; no other supplier lots are affected.'}])
    assert validate_proposals(p,[d])['scope_status']=='complete'

def test_identity_assertion_has_no_affected_authority_and_prefixes_rejected():
    d,p=proposal('Receipt REC-001 references supplier lot SUP-B.','SUP-B','mentioned')
    raw={'candidates':[{'kind':'supplier_lot','value':'SUP-B','disposition':'asserted','incident_status':'mentioned','source':p['facts'][0]['evidence'][0]}]}
    assert validate_draft({'documents':[d]},raw)['candidates'][0]['incident_status']=='mentioned'
    raw['candidates'][0]['incident_status']='affected'
    with pytest.raises(ValueError):validate_draft({'documents':[d]},raw)
    d,p=proposal('Affected supplier lot AX-101.','AX-10')
    with pytest.raises(ValueError):validate_proposals(p,[d])

@pytest.mark.parametrize('item',json.loads((ROOT/'evals/continuation/scope-heldout-v3.json').read_text(encoding='utf-8'))['items'])
def test_heldout_labels_can_be_represented_without_authority(item):
    # A source-backed handcrafted proposal tests the validator, NOT model quality.
    d=document('different-filename.txt',item['source'].encode())
    facts=[]
    for lot,status in item['expected_supplier_statuses'].items():
        # Use the shortest retained sentence containing the exact identity. The
        # signed revision's earlier assertion is excluded from current proposal.
        import re
        sentences=[s for s in re.split(r'(?<=[.!?])\s+',item['source']) if lot in s]
        q=next((s for s in sentences if 'not affected' in s),sentences[0]) if status=='explicitly_excluded' else sentences[0]
        facts.append({'lot_id':lot,'kind':'supplier_lot','status':status,'evidence':[{'document_id':d['id'],'block_id':'line-1','quote':q}]})
    raw={'facts':facts,'qualifiers':[],'scope_status':item['expected_scope'],'scope_evidence':[]}
    if item['expected_scope']=='complete':raw['scope_evidence']=[{'document_id':d['id'],'block_id':'line-1','quote':item['source']}]
    assert validate_proposals(raw,[d])['scope_status']==item['expected_scope']
