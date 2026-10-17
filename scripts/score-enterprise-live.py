"""Offline scoring of retained responses. Never sends inference or rewrites raw data."""
import hashlib,json,statistics
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/enterprise';LIVE=OUT/'live'
frozen=(ROOT/'evals/enterprise/frozen-v1.json').read_bytes()
manifest=json.loads((ROOT/'evals/enterprise/manifest.json').read_text())
assert hashlib.sha256(frozen).hexdigest()==manifest['sha256']
items=json.loads(frozen)['items'];extraction=[];knowledge=[];runs=[]
for item in items:
    result=json.loads((LIVE/'frozen'/(item['id']+'.json')).read_text());assert result['item']==item
    run=result['run'];runs.append(run);raw=run.get('raw_output',run.get('output',run.get('rejected_output',{})))
    labels=item['labels']
    if item['task']=='extraction':
        expected=set(labels['affected_supplier_lots'])|set(labels['mentioned_supplier_lots'])
        actual={f['lot_id'] for f in raw.get('facts',[])}
        affected={f['lot_id'] for f in raw.get('facts',[]) if f['affected']}
        expected_affected=set(labels['affected_supplier_lots'])
        extraction.append({'id':item['id'],'status':run['status'],'expected_supplier_lots':sorted(expected),'proposed_entities':sorted(actual),
            'correct_supplier_entities':len(actual&expected),'proposed_entity_count':len(actual),'expected_entity_count':len(expected),
            'non_supplier_entities':sorted(actual-expected),'missing_entities':sorted(expected-actual),
            'expected_affected':sorted(expected_affected),'proposed_affected':sorted(affected),
            'true_positive_affected':len(affected&expected_affected),'false_positive_affected':sorted(affected-expected_affected),
            'false_negative_affected':sorted(expected_affected-affected),
            'exact_entity_and_disposition_match':actual==expected and affected==expected_affected,
            'raw_scope_concerns_at_run':run.get('scope_concerns',[]),'human_correction_applied':False})
    else:
        claims=raw.get('claims',[]);sources={p['document_id']+'@'+str(p['version']) for p in claims}
        passages=run['retrieval']['passages']
        exact=all(any(all(c[k]==p[k] for k in ('document_id','version','passage_id','quote')) for p in passages) for c in claims)
        abstained=raw.get('insufficient_evidence') is True and not claims
        match=(run['status']=='succeeded' and not raw.get('insufficient_evidence') and sources==set(labels['expected_sources']) and bool(claims) and exact) if labels['answerable'] else abstained
        knowledge.append({'id':item['id'],'mode':run['mode'],'status':run['status'],'expected_answerable':labels['answerable'],
            'returned_sources':sorted(sources),'retrieved_sources':sorted({p['document_id']+'@'+str(p['version']) for p in passages}),
            'claims':len(claims),'exact_quote_validation':exact,'abstained':abstained,'frozen_label_match':match,
            'semantic_review':'KNW-12 returns exact prerequisite passages but fails the expected insufficient-evidence flag. It does not authorize recovery; no case check or recovery was performed.' if item['id']=='KNW-12' else 'Operating-agent assessment against frozen synthetic labels; no independent domain reviewer.',
            'human_correction_applied':False})
original=[json.loads((LIVE/'fresh'/name).read_text()) for name in ('partial-raw.json','complete-raw.json','knowledge-raw.json','signal-raw.json')]
retests=[json.loads((LIVE/'fresh/receiving-v2'/name).read_text()) for name in ('partial-raw.json','complete-raw.json')]
signal_runs=[json.loads((LIVE/'frozen'/name).read_text()) for name in ('signal-v2.json','signal-v3.json')]
all_live={r.get('request_id') or r['id']:r for r in original+retests+runs+signal_runs if r['mode']=='live'}
http=[r for r in all_live.values() if r.get('http_status')==200]
def ratio(n,d):return {'numerator':n,'denominator':d,'ratio':round(n/d,4) if d else None}
last=json.loads((LIVE/'frozen/quota-after-v3.json').read_text())
quality={'at':datetime.now(timezone.utc).isoformat(),'frozen_hash':manifest['sha256'],'full_denominator':24,'frozen_items_exercised':24,
    'frozen_model_requests':sum(r['mode']=='live' for r in runs),'frozen_retrieval_only_abstentions':sum(r['mode']!='live' for r in runs),
    'total_fresh_request_attempts':len(all_live),'http_200_responses':len(http),'timeouts':sum(r.get('error_kind')=='ReadTimeout' for r in all_live.values()),
    'retries':0,'automatic_repairs':0,'fixture_substitutions':0,'requested_models':sorted({r['requested_model_id'] for r in all_live.values()}),
    'actual_models':sorted({r['model_id'] for r in http}),
    'latency_ms':{'measured_attempts':len(all_live),'median':statistics.median(r['elapsed_ms'] for r in all_live.values()),'min':min(r['elapsed_ms'] for r in all_live.values()),'max':max(r['elapsed_ms'] for r in all_live.values())},
    'provenance':'Frozen agent-authored synthetic labels, one model, one pass. KNW-01 reuses the original fresh integrated request. No independent human validation; after-review results never replace raw scores.',
    'extraction':{'source_schema_accepted':ratio(sum(x['status']=='succeeded' for x in extraction),12),
        'supplier_entity_precision':ratio(sum(x['correct_supplier_entities'] for x in extraction),sum(x['proposed_entity_count'] for x in extraction)),
        'supplier_entity_recall':ratio(sum(x['correct_supplier_entities'] for x in extraction),sum(x['expected_entity_count'] for x in extraction)),
        'affected_precision':ratio(sum(x['true_positive_affected'] for x in extraction),sum(len(x['proposed_affected']) for x in extraction)),
        'affected_recall':ratio(sum(x['true_positive_affected'] for x in extraction),sum(len(x['expected_affected']) for x in extraction)),
        'exact_item_matches':ratio(sum(x['exact_entity_and_disposition_match'] for x in extraction),12),
        'scope_boundary_accuracy':'Not measurable: legacy extraction schema has no completeness prediction. Frozen complete_boundary_support mixes ancestry/notice support and is not relabeled after outcomes. Reviewer completeness and unknown-entity controls remain separate.',
        'raw_scope_errors':[x['id'] for x in extraction if x['false_positive_affected'] or x['false_negative_affected']],
        'minimum_label_corrections':sum(len(x['non_supplier_entities'])+len(set(x['false_positive_affected'])&set(x['expected_supplier_lots']))+len(x['false_negative_affected']) for x in extraction),
        'correction_measurement':'Minimum entity/disposition edits inferred from labels, not observed human effort or elapsed productivity.', 'items':extraction},
    'knowledge':{'pipeline_label_matches':ratio(sum(x['frozen_label_match'] for x in knowledge),12),
        'model_label_matches':ratio(sum(x['frozen_label_match'] for x in knowledge if x['mode']=='live'),sum(x['mode']=='live' for x in knowledge)),
        'answerable_expected_source_matches':ratio(sum(x['frozen_label_match'] for x in knowledge if x['expected_answerable']),4),
        'unanswerable_abstentions':ratio(sum(x['abstained'] for x in knowledge if not x['expected_answerable']),8),
        'exact_passage_claims':ratio(sum(x['claims'] for x in knowledge if x['exact_quote_validation']),sum(x['claims'] for x in knowledge)),
        'source_entailment':'Four answerable outputs select directly relevant frozen procedure passages (P1, P2, PROC-101/P1, P3), inspected by the agent. KNW-12 is an abstention error even though its quotes are exact and conservative.', 'items':knowledge},
    'receiving':{'original_source_valid':ratio(0,2),'after_context_fix_source_valid':ratio(2,2),'retest_boundary':'Same two inputs after source-only context fix, not new holdout items.',
        'reviewed_workflow':'Partial reply retained 800 held. Accepted complete AMD draft, explicit source/replacement review, 700 proposed while 800 applied, separate named engineering approval and exact 100-unit sandbox recovery. Original two receipts unchanged.',
        'evidence':'live/fresh/receiving-v2/workflow-summary.json'},
    'signals':{'original':'Schema accepted; baseline-ID semantic error. Non-signal investigation rejected 422.',
        'context_v2':'ReadTimeout at 45964ms; no output or fallback.',
        'context_v3_status':signal_runs[-1]['status'],'context_v3_semantic_review':'Agent inspected all five comments against retained numeric context: SHIFT-001..005 counts 59/500,72/800,43/500,81/800,46/500; rates 0.118,0.09,0.086,0.10125,0.092; rounded upper limits 0.03538 or 0.03168; baseline BASE-001..020,230/13000;20 omitted follow-ups disclosed. No unsupported causal/action statement identified. One successful retest, not independent validation.',
        'evidence':'live/frozen/signal-v3.json'},
    'application_authority':{'frozen_cases_reviewed':0,'frozen_approvals':0,'frozen_inventory_actions':0,
        'recorded_replay_checks':'Exact EXT-04/07/11 copied booleans reject 422; explicit unresolved review retains 1200/0 outside. Original receiving failures reject narrative narrowing. Old review-policy approvals reject 409. Actual core/typed workflows tested separately.',
        'limitation':'No enumeration of every possible semantic error. Bounded English rules do not authenticate sources or replace responsible review.'},
    'allowance':{'confirmed_additional_monetary_charge_usd':0,'basis':'Authenticated event manual for exact endpoint/model; accounting points are nonmonetary.',
        'maximum_total_authorized':30,'maximum_additional_authorized':24,'actual_additional_attempts':len(all_live)-6,'last_quota':last,
        'reported_points_for_http_200':sum(r.get('usage',{}).get('cost',0) for r in http),'timeout_accounting':'Provider may account a timed-out request later; no response-based usage is available for it.'},
    'limitations':['Small synthetic single-model exercise; no industrial accuracy, human timing, safety-critical or productivity claim.','Frozen extraction tests use new supplier IDs outside the prepared genealogy, so they do not prove narrow scope for real inventory.','No additional live request is needed merely to improve these scores. Retained errors are release limitations.']}
(OUT/'model-evaluation.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
print(json.dumps({k:quality[k] for k in ('frozen_items_exercised','frozen_model_requests','frozen_retrieval_only_abstentions','total_fresh_request_attempts','http_200_responses','timeouts')}))
