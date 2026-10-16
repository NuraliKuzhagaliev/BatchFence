const {_electron:electron}=require('playwright'),path=require('node:path'),fs=require('node:fs/promises'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
(async()=>{
 const checks=[];
 for(const factor of [1,1.25]){
  const app=await electron.launch({executablePath:process.env.BATCHFENCE_TEST_EXE || path.join(root,'work/installed-0.2.0/BatchFence.exe'),args:['--force-device-scale-factor='+factor],env:{...process.env,BATCHFENCE_BACKEND_ORIGIN:'http://127.0.0.1:9',BATCHFENCE_USER_DATA:path.join(root,'work/scale-profile-'+factor)}});
  try{
   const page=await app.firstWindow();await page.getByText('Backend offline',{exact:true}).waitFor();
   await app.evaluate(({dialog},file)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[file]})},path.join(root,'docs/verified-decision-packet.json'));
   await page.getByRole('button',{name:'Open packet',exact:true}).click();
   await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
   const metrics=await page.evaluate(()=>({innerWidth,innerHeight,dpr:devicePixelRatio,scrollWidth:document.documentElement.scrollWidth}));
   assert(metrics.scrollWidth<=metrics.innerWidth);assert(Math.abs(metrics.dpr-factor)<.01);
   await page.screenshot({path:path.join(process.env.BATCHFENCE_DESKTOP_REPORT_DIR || path.join(root,'docs/release-0.2.0'),'desktop-scale-'+factor+'.png'),fullPage:true});
   checks.push({factor,metrics,method:'Chromium device-scale override in the real installed executable. OS display settings unchanged.'});
  }finally{await app.close()}
 }
 await fs.writeFile(path.join(process.env.BATCHFENCE_DESKTOP_REPORT_DIR || path.join(root,'docs/release-0.2.0'),'desktop-scale-results.json'),JSON.stringify({checks},null,2));
 console.log(JSON.stringify(checks,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
