// Real Windows dialogs. No showOpenDialog/showSaveDialog replacements.
const { _electron: electron } = require('playwright');
const fs=require('node:fs/promises'),path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{
  const app=await electron.launch({executablePath:path.join(root,'work/installed/BatchFence.exe'),env:{...process.env,
    BATCHFENCE_USER_DATA:path.join(root,'work/native-dialog-profile')}});
  const page=await app.firstWindow();
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.restore();w.show();w.focus();});
  await page.getByRole('button',{name:'Load synthetic incident',exact:false}).click();
  await page.getByRole('button',{name:'Add evidence',exact:true}).waitFor();
  await page.getByRole('button',{name:'Add evidence',exact:true}).click();
  console.log('Real Import evidence dialog requested; waiting for OS selection. No inference will run.');
  try {
    await page.getByRole('heading',{name:'supplier_notice_v2.txt',exact:true}).first().waitFor({timeout:180000});
    await page.screenshot({path:path.join(root,'docs/live-verification/native-import.png'),fullPage:true});
    console.log('Native evidence selection succeeded.');
    await page.getByRole('button',{name:'Export packet',exact:true}).click();
    console.log('Real Save decision packet dialog requested. Save as D:\\projects\\BatchFence\\work\\native-dialog-packet.json');
    await page.getByText('Decision packet saved with source extracts, review history and receipts.',{exact:true}).waitFor({timeout:180000});
    const saved=JSON.parse(await fs.readFile(path.join(root,'work/native-dialog-packet.json'),'utf8'));
    if(!saved.case.documents.some(d=>d.filename==='supplier_notice_v2.txt')) throw Error('Saved packet missing imported evidence');
    await page.getByRole('button',{name:'Open packet',exact:true}).click();
    console.log('Real Open offline decision packet dialog requested. Reopen the same file.');
    await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor({timeout:180000});
    await page.screenshot({path:path.join(root,'docs/live-verification/native-reopened.png'),fullPage:true});
    const result={at:new Date().toISOString(),status:'passed',dialog_stubs:false,checks:['actual OS evidence selection','actual OS save','actual OS reopen','read-only historical packet'],source:'fixtures/demo/supplier_notice_v2.txt',saved_packet:'work/native-dialog-packet.json',inference_calls:0};
    await fs.writeFile(path.join(root,'docs/live-verification/native-dialog-results.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } catch(e) {
    await fs.writeFile(path.join(root,'docs/live-verification/native-dialog-results.json'),JSON.stringify({at:new Date().toISOString(),status:'blocked',dialog_stubs:false,error:e.message,inference_calls:0},null,2));
    console.error(e.message);process.exitCode=1;
  } finally {await app.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
