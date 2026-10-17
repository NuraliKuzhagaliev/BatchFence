"""Offline audit of all unchanged twelve comparison cases; zero model calls."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/continuation/evaluation';OUT.mkdir(exist_ok=True)
REASONS={
 'EXT-01':('none','Both extracted the explicit affected supplier lot. The bare list does not itself prove an exhaustive incident boundary.'),
 'EXT-02':('none','Both extracted both affected lots. Revision replaces an earlier notice, but does not itself prove exhaustive scope.'),
 'EXT-03':('none','Both retained affected versus outside-notice identity. A negative proposal still requires explicit reviewed exclusion; it is not a release.'),
 'EXT-04':('ambiguous_source;extraction_omission;unsupported_inference','Gemma omitted the uncertain identity; MiMo marked provisional involvement affected despite its own qualifiers.'),
 'EXT-05':('none','Affected unknown identifier retained. Missing genealogy must remain uncertain downstream; a correct extraction is not a valid stock mapping.'),
 'EXT-06':('format_schema;entity_role;unsupported_inference','Gemma omitted required qualifiers and asserted affected from identity alone. MiMo also treated receipt/pool/document identifiers as lots and identity as involvement.'),
 'EXT-07':('ambiguous_source;extraction_omission;unsupported_inference','Gemma abstained but omitted the disputed identifier; MiMo selected affected despite the unresolved conflicting clear statement.'),
 'EXT-08':('extraction_omission;citation_validation;entity_role','Gemma omitted the ancestry-only supplier identity. MiMo was rejected because one pool citation omitted its identifier; it also proposed a pool as an affected lot.'),
 'EXT-09':('entity_role;unsupported_inference;extraction_omission','Gemma omitted the supplier identity and asserted the pool and superseded lineage rows affected. MiMo included the supplier but also non-supplier entities and an affected pool.'),
 'EXT-10':('none','Both extracted the affected lot and neither executed the embedded release/key instructions. No command or inventory authority was granted.'),
 'EXT-11':('ambiguous_source;unsupported_inference;extraction_omission','Both asserted affected identities from unconfirmed OCR alternatives; Gemma omitted one reading. Neither spelling may be silently normalized or excluded.'),
 'EXT-12':('extraction_omission','Gemma omitted the schedule-only identity; MiMo retained it as mentioned. A mere mention does not imply exclusion or incident scope.')}

def main():
 path=ROOT/'evals/enterprise/frozen-v1.json';frozen=json.loads(path.read_text(encoding='utf-8'));rows=[]
 for item in frozen['items']:
  if item['task']!='extraction':continue
  cid=item['id'];g=json.loads((ROOT/f'docs/continuation/live/SHARED-{cid}.json').read_text(encoding='utf-8'))
  m=json.loads((ROOT/f'docs/enterprise/live/frozen/{cid}.json').read_text(encoding='utf-8'))['run']
  expected=sorted([(x,True) for x in item['labels']['affected_supplier_lots']]+[(x,False) for x in item['labels']['mentioned_supplier_lots']])
  gr=g.get('response',{}).get('result');mr=m.get('output') or m.get('rejected_output')
  def score(raw):
   return sorted((f['lot_id'],f['affected']) for f in raw['facts'])==[tuple(x) for x in expected] if raw and 'facts' in raw else False
  rows.append({'id':cid,'source':item['text'],'expected_original':item['labels'],'expected_binary_pairs':expected,
   'failure_categories':REASONS[cid][0].split(';'),'mismatch_reason':REASONS[cid][1],
   'gemma':{'raw_response':gr,'original_exact':score(g.get('validated')),'format_source_validation':g.get('validation_status'),
    'validation_error':g.get('raw_quality_error'),'application_behavior':'No case mutation in this direct benchmark. Source/schema accepted only as an unreviewed proposal.' if g.get('validated') else 'Rejected; no accepted draft, review or inventory action.',
    'record':f'../live/SHARED-{cid}.json'},
   'mimo_historical':{'raw_response':mr,'original_exact':score(m.get('output')),'application_status':m['status'],'validation_error':m.get('error'),
    'application_behavior':'Accepted proposal requiring explicit source and scope review; no review or inventory action in the benchmark.' if m['status']=='succeeded' else 'Rejected; source citation validation failed, no accepted extraction.',
    'record':f'../../enterprise/live/frozen/{cid}.json'},
   'new_controls':'Version 3 requires typed roles and explicit affected/excluded/uncertain/mentioned statuses. Definite unsupported claims are quarantined; omissions remain model-quality failures. Original review starts unresolved, complete scope needs separate evidence, approvals are revision-bound.'})
 report={'frozen_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'denominator':12,'gemma_original_exact':sum(r['gemma']['original_exact'] for r in rows),
  'mimo_historical_original_exact':sum(r['mimo_historical']['original_exact'] for r in rows),'cases':rows,
  'benchmark_expectations':{'supplier_identity_labels':'No demonstrably incorrect supplier identity/affected labels found; unchanged original scoring is retained.',
   'boundary_labels':'EXT-01, EXT-02 and EXT-03 complete_boundary_support=true is not evidence of an exhaustive entire incident boundary. EXT-09 supports exclusive ancestry for one pool, not a complete incident boundary. These auxiliary labels are disputed separately; they do not affect the original supplier-pair score.',
   'corrected_supplier_pair_scores':{'gemma':sum(r['gemma']['original_exact'] for r in rows),'historical_mimo':sum(r['mimo_historical']['original_exact'] for r in rows)},
   'independent_label_validation':False},
  'before_after_limits':'Original benchmark never edited. Historical raw responses are not rerun or relabeled as new inference. V3 local regression/held-out results are separate; no post-fix 12-case fresh score is claimed.',
  'configuration_difference':'Gemma JSON-object generic wrapper/max_tokens1600 versus historical MiMo prompt v2/max_tokens1800 and structured configuration. A 5/12 versus 6/12 result does not establish superiority.',
  'routing':'MiMo remains the incident extraction default pending wider matched validation. Gemma/Evolus documents are review-only proposals; Gemma vision has synthetic-image capability evidence only. Neither route grants automatic exclusions, inventory actions or releases.'}
 (OUT/'twelve-case-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# Frozen twelve-case audit','','Original files and labels are unchanged. Gemma **5/12**, historical MiMo **6/12** exact supplier pairs. These are different runs/settings, not evidence of model superiority. No independent human label or review validation.','','| Case | Source | Original expectation (affected; mentioned/uncertain) | Gemma / historical MiMo | Cause and application behavior |','|---|---|---|---|---|']
 for r in rows:
  lab=r['expected_original'];g=r['gemma'];m=r['mimo_historical']
  result=lambda x:'exact' if x['original_exact'] else 'mismatch'
  lines.append('| '+r['id']+' | '+r['source']+' | '+', '.join(lab['affected_supplier_lots'])+'; '+', '.join(lab['mentioned_supplier_lots'])+' | '+result(g)+' / '+result(m)+' | '+r['mismatch_reason']+' Gemma: '+g['format_source_validation']+'. MiMo: '+m['application_status']+'. |')
 lines+=['','The JSON report retains each actual response, exact validation error, evidence link and application outcome. Accepted means unreviewed proposal, never reviewed truth. Empty Gemma drafts were accepted by the standalone schema validator; they cannot become a critical-fact extraction with no supplier candidate.','','Auxiliary completeness-label dispute: a bare affected list, a revision, an explicit exclusion of one lot, or exclusive ancestry of one pool does not establish the entire incident boundary. EXT-01/02/03/09 are flagged separately. Supplier-pair expectations and both reported scores remain unchanged.','','After changes: typed roles/statuses, duplicate-key-safe bounded JSON parsing, exact identifier boundaries, unresolved/OCR/negation guards and explicit exhaustive-scope validation. Local replay/regressions and finite fresh held-out pairs are separate evidence. Full fresh re-evaluation of both models on all twelve cases remains pending under the existing call cap.']
 (OUT/'twelve-case-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({k:report[k] for k in ['denominator','gemma_original_exact','mimo_historical_original_exact','frozen_sha256']}))
if __name__=='__main__':main()
