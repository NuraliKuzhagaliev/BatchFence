const {chromium}=require('playwright'),path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{
const b=await chromium.launch({channel:'msedge',headless:true});
try{const p=await b.newPage({viewport:{width:1440,height:1200}});await p.goto('https://batchfence.onrender.com');
const open=async file=>{const chooser=p.waitForEvent('filechooser');await p.getByRole('button',{name:'Open packet',exact:true}).click();await(await chooser).setFiles(path.join(root,'docs/release-0.2.0/live',file));await p.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();await p.locator('.comparison .required strong').filter({hasText:file.startsWith('review1')?'500':'800'}).waitFor();};
await open('review1-packet.json');await p.getByRole('tab',{name:'Evidence requests',exact:false}).click();
await p.locator('.request-card').first().screenshot({path:path.join(root,'docs/release-0.2.0/live/media-question.png')});
await open('review2-packet.json');await p.getByRole('tab',{name:'Revisions',exact:true}).click();
await p.locator('.causal-comparison').screenshot({path:path.join(root,'docs/release-0.2.0/live/media-causal.png')});
console.log('Captured focused, genuine historical case views; no inference.');
}finally{await b.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1});
