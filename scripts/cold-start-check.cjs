// One bounded free-host idle observation; no keepalive or inference traffic.
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='https://batchfence.onrender.com',out=path.join(root,'releases');
(async()=>{
 const idleMs=Number(process.env.BATCHFENCE_IDLE_MS||960000),expected=process.env.BATCHFENCE_EXPECTED_COMMIT;
 assert(expected,'Set the actual expected published commit');
 const report={expected_commit:expected,version:'0.2.0',idle_started_at:new Date().toISOString(),idle_ms:idleMs,network_during_idle:'No requests from this verification process. Other visitors cannot be controlled.',live_inference_calls:0};
 console.log(JSON.stringify({status:'Waiting without web requests',idle_minutes:idleMs/60000}));
 for(let remaining=idleMs;remaining>0;remaining-=60000) await new Promise(r=>setTimeout(r,Math.min(60000,remaining)));
 const b=await chromium.launch({channel:'msedge',headless:true});
 try{
  const c=await b.newContext({viewport:{width:1440,height:900}}),p=await c.newPage();const start=performance.now();
  report.first_request_at=new Date().toISOString();
  await p.goto(base,{waitUntil:'domcontentloaded',timeout:180000});
  report.initial_dom_ms=Math.round(performance.now()-start);report.initial_title=await p.title();report.initial_text=(await p.locator('body').innerText()).slice(0,1200);
  await p.screenshot({path:path.join(out,'cold-initial-0.2.0.png')});
  report.render_wake_page_observed=/waking|spinning|starting your service|service is starting|onrender.*loading/i.test(report.initial_text);
  await p.getByRole('button',{name:'Open example incident',exact:true}).waitFor({timeout:180000});
  report.application_ready_ms=Math.round(performance.now()-start);
  const h=await c.request.get(base+'/api/health');assert.equal(h.status(),200);report.health=await h.json();assert.equal(report.health.commit,expected);assert.equal(report.health.version,'0.2.0');
  report.assets=[];
  for(const url of await p.locator('script[src],link[rel=stylesheet]').evaluateAll(es=>es.map(e=>e.src||e.href))){
   const r=await c.request.get(url);assert.equal(r.status(),200);const remote=crypto.createHash('sha256').update(await r.body()).digest('hex');const local=crypto.createHash('sha256').update(await fs.readFile(path.join(root,'dist',new URL(url).pathname))).digest('hex');assert.equal(remote,local);report.assets.push({path:new URL(url).pathname,sha256:remote,matches_tested_local_build:true});
  }
  await p.getByRole('button',{name:'Open example incident',exact:true}).click();await p.getByRole('region',{name:'Genealogy not yet evaluated'}).waitFor();
  const challenges=await c.request.post(base+'/api/challenges',{data:{}});assert.equal(challenges.status(),200);const checks=(await challenges.json()).checks;assert.equal(checks.length,6);assert(checks.every(x=>x.passed));report.policy_challenges=checks;
  await p.screenshot({path:path.join(out,'final-public-0.2.0.png')});
  report.passed=true;report.completed_at=new Date().toISOString();report.cold_start_interpretation=report.render_wake_page_observed?'Render wake page observed before application became usable.':'No wake page observed. This is an access check after controlled agent idle, not proof that the service slept; other traffic can keep it awake.';
 }catch(e){report.passed=false;report.error=e.message;process.exitCode=1;}finally{await b.close();await fs.mkdir(out,{recursive:true});await fs.writeFile(path.join(out,'final-verification-0.2.0.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
})().catch(e=>{console.error(e.message);process.exitCode=1});
