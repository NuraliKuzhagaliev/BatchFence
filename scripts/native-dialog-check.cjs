// Real Windows dialogs. No showOpenDialog/showSaveDialog replacements.
const { _electron: electron } = require('playwright');
const fs=require('node:fs/promises'),path=require('node:path');
const root=path.resolve(__dirname,'..'),version=require('../package.json').version,out=process.env.BATCHFENCE_NATIVE_REPORT_DIR||path.join(root,'docs/continuation/native'),packetFile=path.join(root,'work','native-dialog-packet-'+version+'.json');
(async()=>{
  await fs.mkdir(out,{recursive:true});
  const app=await electron.launch({executablePath:process.env.BATCHFENCE_TEST_EXE || path.join(root,'work','installed-'+version,'BatchFence Preview.exe'),env:{...process.env,
    BATCHFENCE_USER_DATA:path.join(root,'work/native-dialog-profile')}});
  const page=await app.firstWindow();
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.restore();w.show();w.focus();});
  const resume=process.env.BATCHFENCE_NATIVE_RESUME_CASE;
  if(!resume){await page.getByRole('button',{name:'Open example incident',exact:false}).click();
  await page.getByRole('button',{name:'Add evidence',exact:true}).waitFor();
  await page.getByRole('button',{name:'Add evidence',exact:true}).click();
  console.log('Real Import evidence dialog requested; waiting for OS selection. No inference will run.');}
  try {
    if(!resume){
    await page.getByRole('heading',{name:'supplier_notice_v2.txt',exact:true}).first().waitFor({timeout:600000});
    await page.screenshot({path:path.join(out,'native-import.png'),fullPage:true});
    console.log('Native evidence selection succeeded.');
    await page.getByRole('tab',{name:'Sources & intake',exact:true}).click();
    await page.getByRole('button',{name:'Choose label photo',exact:true}).click();
    console.log('Real label-photo chooser requested. Choose evals/continuation/images/IMG-01.png (synthetic UI test only).');
    await page.getByRole('button',{name:'Import original & derived region',exact:true}).waitFor({state:'visible',timeout:600000});
    await page.getByRole('button',{name:'Import original & derived region',exact:true}).click();
    await page.getByRole('button',{name:'Inspect retained image region',exact:true}).waitFor({timeout:20000});
    await page.screenshot({path:path.join(out,'native-label-import.png'),fullPage:true});
    }else{
      await page.getByRole('button',{name:'Add evidence',exact:true}).waitFor();
      if(await page.evaluate(()=>localStorage.getItem('bf.case'))!==resume)throw Error('Native resume case differs; no new source selection');
      await page.getByRole('tab',{name:'Sources & intake',exact:true}).click();
      const savedLabel=await page.evaluate(async id=>(await window.batchfence.request('GET','/api/cases/'+id+'/assisted')).label,resume);
      if(!savedLabel.some(l=>l.filename==='IMG-01.png'))throw Error('Original native label selection did not persist');
      await page.getByRole('button',{name:'Inspect retained image region',exact:true}).waitFor();
      await page.screenshot({path:path.join(out,'native-label-import-resumed.png'),fullPage:true});
      console.log('Resumed retained native source/image after original UI heading wait failed; no dialog replacements or inference.');
    }
    await page.getByRole('button',{name:'Export packet',exact:true}).click();
    console.log('Real Save decision packet dialog requested. Save as '+packetFile);
    await page.getByText('Decision packet saved with source extracts, review history and receipts.',{exact:true}).waitFor({timeout:600000});
    const saved=JSON.parse(await fs.readFile(packetFile,'utf8'));
    if(!saved.case.documents.some(d=>d.filename==='supplier_notice_v2.txt')) throw Error('Saved packet missing imported evidence');
    await page.getByRole('button',{name:'Open packet',exact:true}).click();
    console.log('Real Open offline decision packet dialog requested. Reopen the same file.');
    await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor({timeout:600000});
    await page.screenshot({path:path.join(out,'native-reopened.png'),fullPage:true});
    const result={at:new Date().toISOString(),status:'passed',dialog_stubs:false,checks:['actual OS evidence selection','actual OS synthetic-image selection','actual OS save','actual OS reopen','read-only historical packet'],source:'fixtures/demo/supplier_notice_v2.txt',saved_packet:path.relative(root,packetFile),version,operator:process.env.BATCHFENCE_NATIVE_OPERATOR||'Owner-operated selections; helper never chooses native files',resumed_after_retained_image:!!resume,physical_photo_validation:false,inference_calls:0};
    await fs.writeFile(path.join(out,'native-dialog-results.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } catch(e) {
    await page.screenshot({path:path.join(out,'native-failure.png'),fullPage:true}).catch(()=>{});
    await fs.writeFile(path.join(out,'native-dialog-results.json'),JSON.stringify({at:new Date().toISOString(),status:'blocked',dialog_stubs:false,error:e.message,inference_calls:0},null,2));
    console.error(e.message);process.exitCode=1;
  } finally {await app.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
