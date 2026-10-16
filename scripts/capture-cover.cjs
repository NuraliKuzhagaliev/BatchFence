const {chromium}=require('playwright'),path=require('node:path');
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true});const c=await b.newContext({viewport:{width:1920,height:1080}});
 const api=c.request;const base='http://127.0.0.1:8787';
 const post=async(route,data={})=>{const r=await api.post(base+route,{data});if(!r.ok())throw Error(await r.text());return r.json()};
 let s=await post('/api/cases/demo');const d=s.documents.find(d=>d.filename==='supplier_notice_v1.txt');
 s=await post('/api/cases/'+s.id+'/analyze',{document_id:d.id,mode:'fixture'});
 s=await post('/api/cases/'+s.id+'/reviews',{run_id:s.runs.at(-1).id,revision:s.revision,lot_ids:['SUP-A'],accept_scope:true,bounded_scope_reviewed:true});
 const p=await c.newPage();await p.goto(base);await p.evaluate(id=>localStorage.setItem('bf.case',id),s.id);await p.reload();
 await p.getByRole('button',{name:'Approve exact plan',exact:true}).waitFor();
 await p.evaluate(()=>scrollTo(0,0));
 await p.screenshot({path:path.resolve('submission/cover.png'),fullPage:false});
 await b.close();console.log('Actual branded cover captured at 1920x1080.');
})().catch(e=>{console.error(e);process.exit(1)});
