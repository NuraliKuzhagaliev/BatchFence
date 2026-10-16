// Actual application views of preserved live evidence; no new inference calls.
const path=require('node:path'),fs=require('node:fs/promises');
const root=path.resolve(__dirname,'..'),out=path.join(root,'work/media-0.1.1');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.join(root,'.cache/playwright');
const {chromium,_electron:electron}=require('playwright');
async function main(){
 await fs.mkdir(out,{recursive:true});
 const chapters={recorded:[],desktop:[]};
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:out,size:{width:1440,height:1000},fps:15}});
 const cookies=JSON.parse(await fs.readFile(path.join(root,'work/ambiguity-live-session.json'),'utf8'));
 await context.addCookies(Object.entries(cookies).map(([name,value])=>({name,value,url:'http://127.0.0.1:8787'})));
 const page=await context.newPage(),start=Date.now();
 const report=JSON.parse(await fs.readFile(path.join(root,'docs/ambiguity-fix/live-ambiguity.json'),'utf8'));
 const hold=async(seconds,caption)=>{chapters.recorded.push({seconds:(Date.now()-start)/1000,caption});await page.waitForTimeout(seconds*1000)};
 await page.goto('http://127.0.0.1:8787/');
 await page.evaluate(id=>localStorage.setItem('bf.case',id),report.cases[0].case_id);await page.reload();
 await page.locator('.comparison .required strong').filter({hasText:'1,200'}).waitFor();
 await page.getByRole('button',{name:'Review candidate facts',exact:false}).click();
 await page.getByText('This notice explicitly leaves scope unresolved.',{exact:false}).waitFor();
 await page.screenshot({path:path.join(root,'docs/ambiguity-fix/ambiguity-review.png'),fullPage:true});
 await hold(7,'Recorded live evidence: MiMo proposed true/false for two unresolved lots. The source guard blocks narrowing; all candidates start unresolved. No new inference in this segment.');
 await page.getByRole('tab',{name:'Receipt',exact:true}).click();
 // Closing the review form via the selected source exposes the saved receipt tab.
 await page.locator('.source-item').filter({hasText:'supplier-message.txt'}).click();
 await page.getByRole('tab',{name:'Receipt',exact:true}).click();
 await page.getByRole('heading',{name:'Holds applied. Evidence preserved.',exact:true}).waitFor();
 await page.screenshot({path:path.join(root,'docs/ambiguity-fix/ambiguity-receipt.png'),fullPage:true});
 await hold(6,'Recorded live result after agent review: 1,200 units held, zero exclusions. The original model error remains in the audit history.');
 await page.evaluate(id=>localStorage.setItem('bf.case',id),report.cases[1].case_id);await page.reload();
 await page.getByText('Lot identifier absent from cited quote',{exact:false}).waitFor();
 await page.screenshot({path:path.join(root,'docs/ambiguity-fix/rejected-citation.png'),fullPage:true});
 await hold(6,'Recorded failed live extraction: citation validation rejected the response. Review, plan creation and execution are blocked. No corrected model result is claimed.');
 const video=page.video();await context.close();await video.saveAs(path.join(out,'recorded.webm'));await browser.close();
 const app=await electron.launch({executablePath:path.join(root,'work/installed-0.1.1/BatchFence.exe'),
  env:{...process.env,PATH:'C:\\Windows\\System32',BATCHFENCE_BACKEND_ORIGIN:'http://127.0.0.1:9',BATCHFENCE_USER_DATA:path.join(root,'work/media-desktop-0.1.1')},
  recordVideo:{dir:out,size:{width:1440,height:1000},fps:15}});
 const desktop=await app.firstWindow(),desktopStart=Date.now();
 await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setContentSize(1440,1000));
 await desktop.getByText('Backend offline',{exact:true}).waitFor();
 await app.evaluate(({dialog},file)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[file]})},path.join(root,'docs/ambiguity-fix/clear-live/packet-2.json'));
 await desktop.getByRole('button',{name:'Open packet',exact:true}).click();
 await desktop.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
 chapters.desktop.push({seconds:(Date.now()-desktopStart)/1000,caption:'Installed Windows 0.1.1, backend unreachable: historical live-AMD packet opens read-only. Dialog selection is supplied by the test harness; real file reading and validation run.'});
 await desktop.waitForTimeout(6000);
 await desktop.getByRole('tab',{name:'Receipt',exact:true}).click();
 await desktop.locator('.receipt-card').last().scrollIntoViewIfNeeded();
 await desktop.screenshot({path:path.join(root,'docs/ambiguity-fix/installed-live-packet.png'),fullPage:true});
 chapters.desktop.push({seconds:(Date.now()-desktopStart)/1000,caption:'Historical live receipt: 800 units held after revision. Offline approval and execution are disabled. Synthetic evidence; no independent human validation.'});
 await desktop.waitForTimeout(6000);
 const desktopVideo=desktop.video();await app.close();await desktopVideo.saveAs(path.join(out,'desktop.webm'));
 await fs.writeFile(path.join(out,'chapters.json'),JSON.stringify(chapters,null,2));
 console.log('Recorded actual historical live-evidence views and installed offline packet; zero inference calls.');
}
main().catch(e=>{console.error(e.message);process.exit(1)});
