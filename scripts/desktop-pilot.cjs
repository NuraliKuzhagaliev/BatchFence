// Installed explicitly configured loopback pilot check. Never prints private credentials or session capabilities.
const {_electron:electron}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=process.env.BATCHFENCE_DESKTOP_REPORT_DIR||path.join(root,'docs/enterprise/desktop');let app;
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const credentials=JSON.parse(await fs.readFile(path.join(root,'work/pilot-data/backups/engineering-check-private.json'),'utf8'));
 const env={...process.env,BATCHFENCE_USER_DATA:path.join(root,'work/desktop-pilot-candidate'),BATCHFENCE_BACKEND_ORIGIN:process.env.BATCHFENCE_PILOT_ORIGIN||'http://127.0.0.1:8788'};
 app=await electron.launch({executablePath:process.env.BATCHFENCE_TEST_EXE||path.join(root,'work/installed-'+require('../package.json').version+'/BatchFence.exe'),env});
 const page=await app.firstWindow(),errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));
 await page.getByRole('heading',{name:'Sign in to your quality workspace',exact:true}).waitFor();
 for(const [label,key] of [['Username','username'],['Password','password'],['Organization','org'],['Site','site']])await page.getByLabel(label,{exact:true}).fill(credentials[key]);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('heading',{name:'Sign in to your quality workspace',exact:true}).waitFor({state:'hidden'});
 const call=(method,route,body)=>page.evaluate(p=>window.batchfence.request(p.method,p.route,p.body),{method,route,body});
 const me=await call('GET','/api/auth/me');assert.equal(me.actor.username,credentials.username);checks.push('Explicit '+env.BATCHFENCE_BACKEND_ORIGIN+' pilot origin: named engineering sign-in through installed restricted transport');
 const health=await call('GET','/api/health');assert.equal(health.version,require('../package.json').version);
 for(const route of ['/api/signals','/api/knowledge','/api/actions','/api/jobs'])await call('GET',route);
 checks.push('All module read routes and jobs available to named scoped identity');
 await page.screenshot({path:path.join(out,'default-pilot.png'),fullPage:true});
 await assert.rejects(call('GET','/api/sources/../../../private'));
 checks.push('Native transport rejects non-enumerated source/traversal target');
 await call('POST','/api/auth/logout',{});await assert.rejects(call('GET','/api/cases'));
 checks.push('Pilot logout removes current session authority');assert.deepEqual(errors,[]);
 const release=await app.evaluate(({app})=>({version:app.getVersion(),packaged:app.isPackaged,exe:app.getPath('exe')}));
 await fs.writeFile(path.join(out,'default-pilot.json'),JSON.stringify({at:new Date().toISOString(),release,backend_origin:env.BATCHFENCE_BACKEND_ORIGIN,checks,errors,review:'Agent-operated test identity, not independent human validation'},null,2));await app.close();console.log(JSON.stringify({checks,errors}));
})().catch(async()=>{await app?.close();console.error('Default pilot acceptance failed. Inspect the private local test environment; credentials were not logged.');process.exitCode=1});
