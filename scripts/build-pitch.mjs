import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
// Use the bundled authoring runtime without installing or modifying it.
const runtimeModules=process.env.BATCHFENCE_RUNTIME_NODE_MODULES||'C:/Users/nural/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const pkg=JSON.parse(await fs.readFile(path.join(runtimeModules,'@oai/artifact-tool/package.json'),'utf8'));
const entry=pkg.exports?.['.']?.import||pkg.module||pkg.main;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtimeModules,'@oai/artifact-tool',typeof entry==='string'?entry:'dist/artifact_tool.mjs')).href);
const root=path.resolve(import.meta.dirname,'..'),tmp=path.join(root,'work/pitch'),out=path.join(root,'submission');
await fs.mkdir(tmp,{recursive:true});await fs.mkdir(out,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
function text(slide,value,x,y,w,h,size=26,color='#142235',bold=false){
 const s=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;s.text.style={fontFamily:'Segoe UI',typeface:'Segoe UI',fontSize:size,color,bold};s.text.insets=0;return s;
}
async function picture(slide,name,x,y,w,h){
 const bytes=await fs.readFile(path.join(root,'docs/screenshots',name));
 slide.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',alt:'Actual BatchFence synthetic application screenshot',fit:'contain',position:{left:x,top:y,width:w,height:h}});
}
function slide(title,notes,dark=false){
 const s=p.slides.add();s.background.fill=dark?'#0b172a':'#f4f6f8';
 text(s,title,64,52,1152,100,42,dark?'#f5f8fc':'#142235',true);
 s.speakerNotes.text=notes;
 return s;
}
let s=slide('BatchFence','Prototype for small-manufacturer quality managers. All data are synthetic. This presentation reflects a local build with live AMD and public deployment still pending.',true);
text(s,'Evidence-backed lot containment',64,172,1070,90,52,'#f5f8fc',false);
text(s,'Supplier evidence stays attached to the exact decision a reviewer approves.',64,300,830,130,31,'#a9bdd5');
text(s,'Web and Windows prototype',64,545,1000,45,23,'#d2dfed');
text(s,'Synthetic walkthrough. Live AMD verification remains open.',64,601,1120,44,20,'#d8b66c');
s=slide('The quality manager’s incident','The user and pain are a product hypothesis, not validated customer research. Source: supplied master prompt and docs/data_provenance.md.');
text(s,'A supplier flags a cosmetic coating lot.',64,180,500,120,32,'#142235',true);
text(s,'The manager must reconcile stock exports, production lineage and an unresolved receiving identity before deciding what to contain.',64,326,500,160,25,'#516174');
await picture(s,'02-critical-review-1440.png',600,164,620,465);
text(s,'Fictional Northstar Enclosures. No safety or compliance certification.',64,638,1120,35,18,'#64758a');
s=slide('The reviewed containment plan','Actual application screenshot. Fixture truth: 400 documented plus100 uncertain equals500 held units, from1200 current units at4000c each. €28,000 is carrying value outside the proposed broad hold, not savings. See docs/evaluation.md.');
text(s,'500 units require a hold',64,170,500,110,37,'#b93c4b',true);
text(s,'400 documented\n100 uncertain',64,310,480,130,31,'#142235');
text(s,'The source quote and the reason for each stock classification remain inspectable.',64,476,485,120,25,'#516174');
await picture(s,'03-exposure-1440.png',570,153,650,495);
s=slide('Changed evidence invalidates approval','Actual stale-state screenshot. Supplier correction adds SUP-C. Domain and UI tests show500 to800 held units and three tofour allocated open orders. Old approval is rejected server-side. See docs/browser-results.json and docs/desktop-results.json.');
text(s,'500 to 800 proposed units',64,175,500,110,37,'#b93c4b',true);
text(s,'SUP-C adds the FG-D branch.\nThe earlier approval cannot execute.',64,312,475,160,28,'#142235');
text(s,'Review the revised scope, then approve its new exact plan.',64,504,475,100,24,'#516174');
await picture(s,'04-stale-revision-1440.png',570,153,650,495);
s=slide('Verification and technology','Sources: docs/evaluation-results.json, docs/browser-results.json, docs/desktop-results.json, docs/amd-probe.json. All observed counts are synthetic. The AMD provider adapter exists but zero live HTTP calls have occurred. No Gemma or physical GPU claim.');
text(s,'30 / 30 domain cases',64,177,520,80,39,'#147d73',true);
text(s,'18 development and 12 held out',64,265,540,50,25,'#516174');
text(s,'Web and installed Windows flows completed sandbox transactions and packet handoff.',64,365,500,140,27,'#142235');
text(s,'AMD live inference: blocked by missing private configuration',64,557,1130,70,24,'#9c6516',true);
await picture(s,'06-receipt-1440.png',610,168,610,362);
s=slide('A bounded manufacturing pilot','Proposed business validation only. No customer interviews, revenue or validated ROI. Desktop offline screenshot is a real installed package. Native dialog result stubs verified bytes; actual OS dialog selection remains unverified. Public deployment and submission are pending user authorization.');
text(s,'Proposed buyer: a quality manager using exported production records',64,175,535,130,31,'#142235',true);
text(s,'Pilot with redacted exports.\nMeasure time to an accepted plan and unsupported exclusions.',64,350,510,150,27,'#516174');
text(s,'Next gates: live AMD, distribution and independent user review.',64,563,1110,70,24,'#9c6516');
await picture(s,'13-installed-desktop-offline.png',640,160,560,370);
for(const [i,s] of p.slides.items.entries()){
 const blob=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(tmp,'slide-'+(i+1)+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(tmp,'candidate.pptx'));
await fs.writeFile(path.join(tmp,'presentation.json'),JSON.stringify(p.toProto()));
console.log('Draft deck and six rendered slides written to '+tmp);
