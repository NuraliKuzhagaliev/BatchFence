// Actual stored results of the four fresh calls; no inference during capture.
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:8795',out=path.join(root,'docs/enterprise/live/ui');
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const privateState=JSON.parse(await fs.readFile(path.join(root,'work/enterprise-live/private.json'),'utf8'));
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1366,height:900},recordVideo:{dir:path.join(root,'work/enterprise-live/media'),size:{width:1366,height:900}}});
 const login=await context.request.post(base+'/api/auth/login',{data:{username:'fresh-reviewer',password:privateState.password,org:'liveeval',site:'synthetic'}});assert.equal(login.status(),200);
 const page=await context.newPage(),errors=[],writes=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);});
 await page.goto(base);await page.evaluate(id=>localStorage.setItem('bf.case',id),privateState.case_id);await page.reload();
 const shot=async name=>{await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});await page.waitForTimeout(3500);};
 await page.getByRole('button',{name:'Overview',exact:true}).click();await page.getByRole('heading',{name:'One evidence chain. Four connected decisions.',exact:true}).waitFor();await shot('overview');
 await page.getByRole('button',{name:'Knowledge',exact:true}).click();await page.getByRole('heading',{name:'Source-backed proposals',exact:true}).waitFor();
 const proposal=page.locator('.module-card').filter({has:page.getByRole('heading',{name:'Source-backed proposals',exact:true})});
 await proposal.locator('blockquote').screenshot({path:path.join(out,'knowledge-quote.png')});await shot('knowledge');
 await page.getByText('Retrieval, actual response and validation',{exact:true}).click();await shot('knowledge-provenance');
 await page.getByRole('button',{name:'Incidents',exact:true}).click();await page.getByRole('tab',{name:'Recovery',exact:true}).click();await page.getByRole('heading',{name:'Recovery proposal',exact:true}).waitFor();await shot('recovery');
 await page.getByRole('button',{name:'Signals',exact:true}).click();await page.getByRole('img',{name:'Nonconforming-unit proportions against varying three-sigma control limits'}).waitFor();await shot('signals');
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
 const report={at:new Date().toISOString(),base,version:(await(await context.request.get(base+'/api/health')).json()).version,
  case_id:privateState.case_id,provenance:'Actual application read-only display of persisted results from four fresh AMD calls. Sources are synthetic and every review is agent-operated. No new inference or inventory action during this recording. Typed errors and signal semantic error are retained in adjacent evidence.',writes,errors};
 await fs.writeFile(path.join(out,'capture.json'),JSON.stringify(report,null,2));const video=page.video();await context.close();await video.saveAs(path.join(root,'work/enterprise-live/media/recorded-fresh-results.webm'));await browser.close();console.log(JSON.stringify(report));
})().catch(e=>{console.error(e.message);process.exit(1)});
