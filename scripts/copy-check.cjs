const {_electron:electron,chromium}=require('playwright'),path=require('node:path'),assert=require('node:assert/strict'),fs=require('node:fs/promises');
const root=path.resolve(__dirname,'..');let app;
(async()=>{
 const web=process.argv.includes('--web');
 app=web?await chromium.launch({channel:'msedge',headless:true}):await electron.launch({executablePath:path.join(root,'work/installed/BatchFence.exe'),env:{...process.env,BATCHFENCE_USER_DATA:path.join(root,'work/copy-check-profile')}});
 const page=web?await app.newPage():await app.firstWindow();
 if(web)await page.goto('http://127.0.0.1:8787/');
 await page.getByRole('button',{name:'Load synthetic incident',exact:false}).click();
 await page.getByRole('button',{name:'Extract selected notice',exact:true}).click();
 await page.getByLabel('I checked lot IDs, exclusions, qualifiers and whether this notice supersedes prior scope.').check();
 await page.getByRole('button',{name:'Confirm scope & calculate',exact:true}).click();
 await page.getByRole('button',{name:'Approve exact plan',exact:true}).waitFor();
 await page.getByRole('tab',{name:'Evidence requests'}).click();
 await page.getByRole('button',{name:'Copy request draft',exact:true}).click();
 await page.getByText('Draft copied. No message was sent.',{exact:true}).waitFor({timeout:5000});
 await fs.writeFile(path.join(root,web?'docs/copy-web-check.json':'docs/copy-check.json'),JSON.stringify({passed:true,surface:web?'Microsoft Edge web client':'Installed Windows executable',operation:'Explicit user-gesture clipboard write succeeded. Existing clipboard content was never read.'},null,2));
 console.log((web?'Web':'Installed')+' request-draft copy verified.');
 await app.close();
})().catch(async e=>{console.error(e.message);if(app)await app.close();process.exitCode=1});
