import { useEffect, useRef, useState } from 'react';
import type { Case, Evidence, Hypothesis, Question, Simulation, Upload } from './types';
import { request, copyDraft, fileUpload, native } from './platform';
import { Graph } from './Graph';
import {TypedReceiving} from './RecoveryPanel';
import completeReply from '../fixtures/resolution/receiving-complete.txt?raw';
import inconclusiveReply from '../fixtures/resolution/receiving-inconclusive.txt?raw';

const euro = (c:number) => new Intl.NumberFormat('en-IE',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(c/100);
export function Elapsed({label}:{label:string}) {
  const [seconds,setSeconds]=useState(0);
  useEffect(()=>{const start=performance.now(); setSeconds(0); const timer=setInterval(()=>setSeconds(Math.floor((performance.now()-start)/1000)),1000); return()=>clearInterval(timer);},[label]);
  return <span role="status">{label} · {seconds}s elapsed</span>;
}
function Impact({value}:{value:Simulation}) {
  return <section className="impact-result" aria-label="Simulation results">
    <span className="pill uncertainty">Simulation · no execution authority</span>
    <h3>{value.before.hold_units} → {value.after.hold_units} proposed units</h3>
    <p>{value.changed_units} unique units change classification · {euro(value.changed_value_cents)} inventory carrying value</p>
    <p>Changed pools: {value.changed_pool_ids.join(', ') || 'None'}. New order reviews: {value.new_order_reviews.join(', ') || 'None'}. Removed from proposal: {value.removed_order_reviews.join(', ') || 'None'}.</p>
    <p><strong>{value.applied_hold_units} units already held remain held.</strong> {value.warning}</p>
    <details><summary>{value.remaining_blockers.length} remaining questions</summary>{value.remaining_blockers.map(q=><p key={q.id}>{q.missing}: {q.pool_ids.join(', ')}</p>)}</details>
  </section>;
}
const hypothesisLabel=(h:Hypothesis)=>h.kind==='inconclusive'?'Answer remains inconclusive':h.kind==='boundary'?'Explicit complete incident boundary':`${h.pool_id}: ${h.supplier_lot_id} ${h.complete?'only, complete replacement':'confirmed; other paths retained'}`;
type ReplyPreview={impact:Simulation; old_relationships:unknown[]; proposed_relationships:unknown[]; conflicts:string[]};
export function EvidencePlanner({state,readOnly,mode,onUpdate,onEvidence}:{state:Case;readOnly:boolean;mode:string;onUpdate:(s:Case)=>void;onEvidence:(e:Evidence)=>void}) {
  const [busy,setBusy]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [scenario,setScenario]=useState<Simulation|null>(null),[basket,setBasket]=useState<Hypothesis[]>([]);
  const [question,setQuestion]=useState<Question|null>(null),[replyId,setReplyId]=useState('');
  const [pool,setPool]=useState(''),[supplier,setSupplier]=useState(''),[outcome,setOutcome]=useState('inconclusive');
  const [complete,setComplete]=useState(false),[quote,setQuote]=useState(''),[note,setNote]=useState('');
  const [reviewed,setReviewed]=useState(false),[replacement,setReplacement]=useState(false),[preview,setPreview]=useState<ReplyPreview|null>(null);
  const [boundary,setBoundary]=useState<Record<string,string>>({});
  const input=useRef<HTMLInputElement>(null);
  const result=state.plan?.result, route='/api/cases/'+state.id;
  const reply=state.documents.find(d=>d.id===replyId) || [...state.documents].reverse().find(d=>d.request_id && d.revision===state.revision);
  const replyRun=[...state.runs].reverse().find(r=>r.document_id===reply?.id);
  useEffect(()=>{setPreview(null);},[pool,supplier,outcome,complete,quote,state.revision]);
  async function act(label:string,fn:()=>Promise<void>){setBusy(label);setError('');setMessage('');try{await fn();}catch(e){setError(e instanceof Error?e.message:'Operation failed');}finally{setBusy('');}}
  async function simulate(h:Hypothesis[]){await act('Calculating simulation',async()=>setScenario(await request<Simulation>('POST',route+'/simulate',{revision:state.revision,hypotheses:h})));}
  async function attach(file:Upload,q:Question){const s=await request<Case>('POST',route+'/documents',{...file,request_id:q.id});onUpdate(s);setReplyId(s.documents.at(-1)!.id);setPool(q.pool_ids[0]);setSupplier('');setQuote('');setNote('');setReviewed(false);setReplacement(false);setPreview(null);setScenario(null);setOutcome('inconclusive');setComplete(false);}
  const body={revision:state.revision,document_id:reply?.id,pool_id:pool,supplier_lot_id:supplier,outcome,complete,quote,note,reviewed,replacement_reviewed:replacement};
  return <section className="queue planner">
    <div className="queue-summary"><p><strong>{result?.request_unique_units || 0} units · {euro(result?.request_unique_cents || 0)}</strong><br/>Unique inventory touched by open questions. Shared causes overlap; impacts cannot be added.</p></div>
    {busy && <Elapsed label={busy}/>} {error && <p className="inline-error" role="alert">{error}</p>} {message && <p role="status">{message}</p>}
    {scenario && <><Impact value={scenario}/><button className="button small" onClick={()=>setScenario(null)}>Close simulation</button></>}
    {basket.length>0 && <div className="scenario-basket"><strong>Joint scenario · {basket.length} assumptions</strong>{basket.map((h,i)=><p key={i}>{hypothesisLabel(h)}</p>)}<button className="button" disabled={readOnly||!!busy} onClick={()=>void simulate(basket)}>Recompute joint scenario</button><button className="text-button" onClick={()=>setBasket([])}>Clear assumptions</button></div>}
    {result?.requests.map((q,i)=><article className="request-card" key={q.id}>
      <b className="request-rank">{String(i+1).padStart(2,'0')}</b><div>
        <h3>{q.missing}</h3><span className="pill uncertainty">{q.units} unique units · {q.pool_ids.join(', ')}</span>
        <p>{q.reason}</p><p className="caption">Suggested owner: {q.suggested_role || 'Quality reviewer'} · {q.sort_reason || 'Historical request order'}</p>
        {(q.evidence||[]).map((e,n)=><button key={n} className="source-quote" onClick={()=>onEvidence(e)}>{e.quote}<small>{e.document_id} / {e.block_id}</small></button>)}
        <p>{q.review_existing_first?'Review the existing source first.':'Missing evidence or clarification is required.'} {q.impact_note}</p>
        <details><summary>Request draft · {euro(q.value_cents)} carrying value</summary><textarea readOnly aria-label={'Draft for '+q.id} value={q.draft}/><button className="button small" onClick={()=>void act('Copying draft',async()=>{await copyDraft(q.draft);setMessage('Draft copied. No message was sent.');})}>Copy request draft</button></details>
        {(q.hypotheses||[]).map((h,n)=><div className="hypothesis" key={n}><span>{hypothesisLabel(h)}</span><button className="button small" disabled={readOnly||!!busy} onClick={()=>void simulate([h])}>Simulate</button><button className="text-button" disabled={readOnly||basket.length>=6} onClick={()=>setBasket([...basket,h])}>Add to joint scenario</button></div>)}
        {q.global && <details><summary>Supply a hypothetical complete boundary</summary><p>Conditional only. Select known incident lots explicitly. This cannot resolve the real notice.</p>{[...new Set(state.edges.map(e=>e.source))].map(lot=><label className="boundary-choice" key={lot}>{lot}<select aria-label={'Hypothetical involvement of '+lot} value={boundary[lot]||''} onChange={e=>setBoundary({...boundary,[lot]:e.target.value})}><option value="">Not supplied</option><option value="affected">Affected</option><option value="unresolved">Unresolved involvement</option></select></label>)}<button className="button" disabled={readOnly||!!busy||!Object.values(boundary).some(Boolean)} onClick={()=>void simulate([{kind:'boundary',lot_ids:Object.keys(boundary).filter(k=>boundary[k]==='affected'),uncertain_lot_ids:Object.keys(boundary).filter(k=>boundary[k]==='unresolved')}])}>Simulate supplied boundary</button></details>}
        {!q.global && <button className="button" disabled={readOnly||!!busy||state.pending_revision} onClick={()=>{setQuestion(q);if(native)void act('Opening reply file',async()=>{const files=await native!.chooseFiles();if(files[0])await attach(files[0],q);});else input.current?.click();}}>Attach reply to this question</button>}
        {state.synthetic && q.kind==='possible_ancestry' && q.pool_ids.includes('FG-C') && <div className="sample-replies"><span>Synthetic receiving exercise</span>{[['Complete',completeReply],['Inconclusive',inconclusiveReply]].map(([label,text])=><button key={label} className="text-button" disabled={readOnly||!!busy||state.pending_revision} onClick={()=>void act('Attaching synthetic reply',()=>attach({filename:'receiving-'+label.toLowerCase()+'.txt',synthetic:true,content_base64:btoa(text)},q))}>{label} example reply</button>)}</div>}
      </div>
    </article>)}
    {!result?.requests.length && <p>No open evidence questions in this reviewed proposal.</p>}
    <TypedReceiving state={state} readOnly={readOnly} mode={mode} update={onUpdate}/>
    {reply && state.pending_revision && <details className="reply-review"><summary>Legacy bounded-syntax receiving review</summary>
      <h3>Review linked reply</h3><p>{reply.filename} · source revision {reply.revision} · {reply.synthetic?'Synthetic source':'Uploaded source'}</p>
      {reply.blocks.map(b=><blockquote key={b.id}>{b.text}</blockquote>)}
      <button className="button" disabled={readOnly||!!busy||reply.revision!==state.revision} onClick={()=>void act(mode==='live'?'Waiting for AMD reply interpretation':'Reading synthetic reply',async()=>{const s=await request<Case>('POST',route+'/analyze',{document_id:reply.id,mode});onUpdate(s);if(s.runs.at(-1)?.status!=='succeeded')throw Error(s.runs.at(-1)?.error||'Interpretation failed');})}>Interpret reply · {mode==='live'?'Live AMD':'Synthetic'}</button>
      {replyRun && <div className="raw-reply"><p>Raw {replyRun.mode} extraction: {replyRun.status}. Candidates are proposals, not confirmed ancestry.</p>{replyRun.output?.facts.map((f,i)=><p key={i}>{f.lot_id} · model affected={String(f.affected)} · {f.evidence.map(e=>e.quote).join(' / ')}</p>)}{replyRun.output?.qualifiers.map((q,i)=><p key={i}>{q}</p>)}</div>}
      <label className="field-label">Reply pool<select aria-label="Reply pool" value={pool} onChange={e=>setPool(e.target.value)}><option value="">Select pool</option>{reply.request_snapshot?.pool_ids.map(p=><option key={p}>{p}</option>)}</select></label>
      <label className="field-label">Reply outcome<select aria-label="Reply outcome" value={outcome} onChange={e=>setOutcome(e.target.value)}><option value="inconclusive">Inconclusive · retain uncertainty</option><option value="conflicting">Conflicting · retain uncertainty</option><option value="resolved">Source-backed identity</option></select></label>
      {outcome==='resolved' && <><label className="field-label">Reviewed supplier identity<select aria-label="Reviewed supplier identity" value={supplier} onChange={e=>setSupplier(e.target.value)}><option value="">Select candidate</option>{[...new Set(state.edges.filter(e=>e.target===pool).map(e=>e.source))].map(l=><option key={l}>{l}</option>)}</select></label><label className="checkbox"><input type="checkbox" checked={complete} onChange={e=>setComplete(e.target.checked)}/>This is a complete replacement of every parent record</label><p className="caption">Complete-record syntax: “POOL complete ancestry: LOT only. Supersedes ROW-1, ROW-2.” Partial: “POOL confirmed parent: LOT.” Other wording requires a clarified record; mentions alone cannot narrow ancestry.</p></>}
      <label className="field-label">Exact reply passage<textarea aria-label="Exact reply passage" value={quote} onChange={e=>setQuote(e.target.value)}/></label>
      <label className="field-label">Reply review explanation<textarea aria-label="Reply review explanation" value={note} onChange={e=>setNote(e.target.value)}/></label>
      <button className="button" disabled={readOnly||!!busy} onClick={()=>void act('Checking reply proposal',async()=>setPreview(await request<ReplyPreview>('POST',route+'/reply-preview',body)))}>Preview reconciliation</button>
      {preview && <><Impact value={preview.impact}/><details><summary>Old and proposed records · conflicts</summary><pre>{JSON.stringify({old:preview.old_relationships,proposed:preview.proposed_relationships,conflicts:preview.conflicts},null,2)}</pre></details></>}
      <label className="checkbox"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>I reviewed the exact reply and record identity</label>
      {complete && outcome==='resolved' && <label className="checkbox"><input type="checkbox" checked={replacement} onChange={e=>setReplacement(e.target.checked)}/>I reviewed every superseded parent and the complete replacement</label>}
      <button className="button primary" disabled={readOnly||!!busy||!preview||!reviewed||note.length<20||(complete&&outcome==='resolved'&&!replacement)} onClick={()=>void act('Recording explicit reply review',async()=>{onUpdate(await request<Case>('POST',route+'/reply-review',body));setReplyId('');setPreview(null);setScenario(null);setMessage('New proposal calculated. Existing holds remain; prior approval cannot transfer.');})}>Confirm reply & recalculate</button>
    </details>}
    <input ref={input} hidden type="file" accept=".txt,.pdf" onChange={e=>{const f=e.target.files?.[0];if(f&&question)void act('Attaching reply',async()=>attach(await fileUpload(f),question));e.target.value='';}}/>
  </section>;
}

type Comparison={before_units:number;after_units:number;new_order_reviews:string[];prior_order_reviews:string[];pools:{pool_id:string;group:string;before:string;after:string;units:number;value_cents:number;path:string[];order_ids:string[];evidence:Evidence[];lineage_edges:unknown[]}[];notice:string;scope_changes:unknown[];source_changes:unknown;claims_before:unknown;claims_after:unknown};
export function RevisionComparison({state,readOnly,onEvidence}:{state:Case;readOnly:boolean;onEvidence:(e:Evidence)=>void}) {
  const [diff,setDiff]=useState<Comparison|null>(null),[error,setError]=useState(''),[before,setBefore]=useState(false),[selected,setSelected]=useState('');
  const old=state.plans.at(-1), current=state.plan, shown=before?old:current;
  useEffect(()=>{setDiff(null);setBefore(false);if(readOnly||!old||!current)return;let active=true;request<Comparison>('GET','/api/cases/'+state.id+'/comparison').then(d=>{if(active)setDiff(d);},e=>{if(active)setError(String(e));});return()=>{active=false;};},[state.id,state.revision,current?.digest,old?.digest,readOnly]);
  if(!old||!current)return <p>Review a second evidence revision to compare decisions.</p>;
  return <section className="causal-comparison"><h3>Why the proposal changed</h3>{error&&<p role="alert">{error}</p>}
    <p>{old.result.hold_units} → {current.result.hold_units} units. Historical approval cannot transfer or be restored.</p>
    <div className="comparison-toggle"><button className={'button '+(before?'primary':'')} onClick={()=>setBefore(true)}>Before · historical</button><button className={'button '+(!before?'primary':'')} onClick={()=>setBefore(false)}>After · current proposal</button></div>
    {shown?.inputs && <Graph data={{...state,edges:shown.inputs.lineage,stocks:shown.inputs.stocks,scope:shown.inputs.reviewed_scope,pending_revision:false}} result={shown.result} selected={selected} onSelect={setSelected}/>}
    {diff ? <><p>New order reviews: <strong>{diff.new_order_reviews.join(', ')||'None'}</strong>. Previously affected: {diff.prior_order_reviews.join(', ')}.</p>{diff.pools.map(p=><article className={'causal-pool '+(p.group==='newly_included'?'changed-path':'')} key={p.pool_id}><strong>{p.pool_id} · {p.units} units · {euro(p.value_cents)}</strong><p>{p.before} → {p.after} · {p.group.replaceAll('_',' ')}</p><p>{p.path.join(' → ')||'Unresolved ancestry'} → {p.order_ids.join(', ')||'No open allocation'}</p>{p.evidence.map((e,i)=><button key={i} className="source-quote" onClick={()=>{setSelected(p.pool_id);onEvidence(e);}}>{e.quote}</button>)}<details><summary>All ancestor links (including merged paths)</summary><pre>{JSON.stringify(p.lineage_edges,null,2)}</pre></details></article>)}<details><summary>Source claims, versions and reviewed assumptions</summary><pre>{JSON.stringify({sources:diff.source_changes,claims_before:diff.claims_before,claims_after:diff.claims_after,scope:diff.scope_changes},null,2)}</pre></details><p className="caption">{diff.notice}</p></>:<p className="caption">{readOnly?'Offline comparison shows saved snapshots; server causal analysis requires an owned online case.':'Loading causal comparison…'}</p>}
  </section>;
}

export function VerificationPanel({state,replay,readOnly}:{state:Case;replay:boolean;readOnly:boolean}) {
  const [checks,setChecks]=useState<{name:string;passed:boolean;actual:unknown}[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  return <section className="verification-panel"><h3>Evidence and verification</h3><p>Raw interpretation, review decisions and deterministic results are separate. These records do not establish general model accuracy or independent human validation.</p>
    {state.runs.map(r=><article key={r.id} className="verification-run"><strong>{replay?(r.mode==='live'?'Historical AMD Replay':'Historical Synthetic'):r.mode==='live'?'Fresh Live AMD':'Synthetic'} · {r.status}</strong><dl><dt>Provider / model</dt><dd>{r.provider||'not available'} / {r.model_id||'not available'}</dd><dt>Timestamp / clock</dt><dd>{r.timestamp||'not available'} / {r.clock_source||'not available (historical run)'}</dd><dt>Latency / request</dt><dd>{r.elapsed_ms??'not available'} ms / {r.request_id||'not available'}</dd><dt>HTTP / validation</dt><dd>{r.http_status??'not available'} / {r.status==='succeeded'?'Schema and exact citations accepted; semantic truth still requires review':r.error||'not completed'}</dd><dt>Prompt / schema / source</dt><dd>{r.prompt_version||'not available'} / {r.schema_version??'not available'} / {r.document_id||'not available'}</dd></dl><details><summary>Input hash, tokens and raw output</summary><pre>{JSON.stringify({input_hash:r.input_hash||'not available',usage:r.usage||'not available',output:r.output},null,2)}</pre></details></article>)}
    <details><summary>Reviewed decisions and corrections · {state.reviews.length}</summary><pre>{JSON.stringify(state.reviews,null,2)}</pre></details>
    <p>Deterministic proposal: {state.plan?.result.hold_units??'not calculated'} units · {state.plan?.status||'not reviewed'}. Receipts: {state.receipts.length}. Model identity alone does not verify hardware provenance.</p>
    <h3>Run isolated synthetic challenges</h3><p>Uses fresh in-memory records and the actual policy/validation functions. Your incident is unchanged. These are synthetic checks, not model accuracy tests.</p>
    <button className="button" disabled={readOnly||busy} onClick={async()=>{setBusy(true);setError('');try{const r=await request<{checks:typeof checks}>('POST','/api/challenges',{});setChecks(r.checks);}catch(e){setError(String(e));}finally{setBusy(false);}}}>Run boundary challenges</button>
    {error&&<p role="alert">{error}</p>}{checks.map(c=><article key={c.name} className="challenge-result"><strong>{c.passed?'Passed':'FAILED'} · {c.name}</strong><pre>{JSON.stringify(c.actual,null,2)}</pre></article>)}
  </section>;
}
