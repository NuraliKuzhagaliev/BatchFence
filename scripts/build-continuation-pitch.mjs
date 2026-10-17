import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..'),tmp=path.join(root,'work/pitch-continuation040'),out=path.join(root,'submission/continuation');
const runtime='C:/Users/nural/.cache/codex-runtimes/codex-primary-runtime/dependencies',modules=runtime+'/node/node_modules';
process.env.RUNTIME_NODE_MODULES=modules;
const pkg=JSON.parse(await fs.readFile(path.join(modules,'@oai/artifact-tool/package.json'),'utf8')),entry=pkg.exports?.['.']?.import||pkg.module||pkg.main;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool',typeof entry==='string'?entry:'dist/artifact_tool.mjs')).href);
await fs.mkdir(tmp,{recursive:true});await fs.mkdir(out,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
function text(s,v,x,y,w,h,size=27,color='#516174',bold=false){const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});t.text=v;t.text.style={fontFamily:'Segoe UI',typeface:'Segoe UI',fontSize:size,color,bold};t.text.insets=0;return t;}
function slide(title,notes,dark=false){const s=p.slides.add();s.background.fill=dark?'#0b172a':'#f4f6f8';text(s,title,64,48,1152,90,42,dark?'#f5f8fc':'#142235',true);s.speakerNotes.text=notes;return s;}
async function image(s,file,position={left:570,top:160,width:646,height:440}){const b=await fs.readFile(path.join(root,file));s.images.add({blob:new Uint8Array(b),contentType:'image/png',alt:'Actual retained BatchFence screen. Synthetic records and agent-operated review.',fit:'contain',position});}
function foot(s,v){text(s,v,64,642,1152,45,20,'#8e621a');}
let s=slide('BatchFence','0.4.0-rc.1 engineering preview. Six connected extensions preserve the existing incident, review, approval and receipt architecture. No independent customer, manufacturing or language acceptance.',true);
text(s,'Evidence for the next\nquality decision',64,190,1140,170,56,'#f5f8fc');
text(s,'Source review, useful evidence requests, release prerequisites and a factual shift handover.',64,420,1080,115,30,'#b1c4db');
text(s,'Web and Windows Preview. Synthetic engineering evidence. 0.4.0-rc.1.',64,628,1152,40,21,'#dbbd79');
s=slide('Real Evolus extraction and Gemma interpretation','Sources: docs/continuation/live/evolus-product-flow.json, evolus-configuration.json, evolus-reviewed-revision-case.json and ui/capture.json. Three actual provider workflow executions. Own-model configured own/gemma-4-31b-it maps to Gemma-4-31B-IT; runtime model ID not returned by Evolus. Original final-output configuration failed. Revised notice returned an invented metadata ID and was rejected. Explicit agent correction and separate critical review produced800 and two receipts. Agent review is not independent human validation.');
text(s,'500, then 800 held',64,178,480,90,35,'#142235',true);
text(s,'The extractor and agent return source-linked proposals. Explicit review drives the deterministic scope and two receipts.',64,290,460,180);
text(s,'An invented document ID failed validation. The original error stays visible after correction.',64,505,460,105,25,'#8e621a');
await image(s,'docs/continuation/live/ui/evolus-sources.png');foot(s,'Stored genuine Evolus result. Synthetic records. Agent-operated review.');
s=slide('Ask for the missing fact','Sources: docs/continuation/live/product-flow.json, flow-model-request.json where present, tests/test_continuation.py and ui/gemma-requests.png. Existing cause planner computes distinct conditional units. Gemma drafts a request from gaps. Ambiguous response keeps800 applied. Italian complete response is original-linked and explicitly reviewed by the agent. No independent language acceptance or external message.');
text(s,'A specific next request',64,178,480,90,35,'#142235',true);
text(s,'Rank known gaps with visible rules. Keep conditional impact separate from applied restrictions.',64,290,460,150);
text(s,'Original-linked English, Russian and Italian evidence requires qualified critical review.',64,490,460,120);
await image(s,'docs/continuation/live/ui/gemma-requests.png');foot(s,'Stored direct AMD result. No inference during recording. No messages sent.');
s=slide('Inspect identity before association','Sources: docs/continuation/live/vision-capability.json, product-flow.json, IMG-01.json through IMG-05.json and windows/new-results.json. Five successful actual Gemma image responses on synthetic rendered labels. SUP-001 cannot associate with document SUP-B, HTTP422. O/0 spelling retained but model did not flag ambiguity. No physical photographs or barcode acceptance.');
text(s,'Exact spelling matters',64,178,480,90,35,'#142235',true);
text(s,'Preserve the original and crop. Review the proposed reading against the document identity before association.',64,290,460,180);
text(s,'Five synthetic image responses passed their transcription checks. Physical-photo testing is still pending.',64,500,460,115,25,'#8e621a');
await image(s,'docs/continuation/live/ui/gemma-label-region.png',{left:570,top:160,width:646,height:325});await image(s,'docs/continuation/live/ui/gemma-label-reading.png',{left:570,top:495,width:646,height:115});foot(s,'Stored genuine Gemma reading of a synthetic label. Physical-photo acceptance pending.');
s=slide('A smaller proposal needs separate recovery','Sources: docs/continuation/live/product-flow.json, decision-packet.json and ui/gemma-recovery.png. Actual direct AMD response drives reviewed scope700 while800 remain applied. Relevant source revision rejects stale recovery approval. Separate engineering-role approval and sandbox acknowledgement recover100, retain two original receipts and leave700. Source graph and handover staleness verified locally and across container restart.');
text(s,'800 applied, 700 proposed',64,170,490,100,34,'#142235',true);
text(s,'A source change blocks stale authority. Conditions, approval and acknowledgement remain distinct.',64,295,460,160);
text(s,'Separate acknowledgement recovers 100. Original receipts remain intact.',64,495,460,110);
await image(s,'docs/continuation/live/ui/gemma-recovery.png');foot(s,'Stored actual workflow. Synthetic inventory and simulated engineering roles.');
s=slide('Model quality and remaining failures','Sources: docs/continuation/evaluation/twelve-case-audit.md and README.md; live/heldout-v3-results.json. Original frozen12 remains unchanged. Gemma5/12 versus historical MiMo6/12, different wrappers/token limits. After fixes, two matched held-out cases per model: lot statuses2/2, scope1/2. Both call conflicting revision partial. No full post-fix12 rerun because48-reservation cap exhausted. No superiority claim.');
text(s,'Original frozen comparison',64,175,555,80,34,'#173655',true);
text(s,'Gemma exact: 5 of 12\nHistorical MiMo exact: 6 of 12\nOriginal labels and errors retained',64,300,550,200,29);
text(s,'Matched new cases',665,175,540,80,34,'#142235',true);
text(s,'Each model: lot statuses 2 of 2\nEach model: scope labels 1 of 2\nConflict remained uncertain.\nConsequential review stays mandatory.',665,290,545,255,28);
foot(s,'Small synthetic sample. No model superiority or productivity claim. Full original rerun pending.');
s=slide('Verified engineering preview','Sources: docs/continuation/pytest-release.xml, domain-results.json, native/native-dialog-results.json, windows/, container/ and scope-map.md.171 pytest,30 domain cases; installed shared workflows, actual owner Windows dialogs, SQLite restart and existing PostgreSQL pilot checks.48/48 model reservations exhausted. Evolus3 workflows reported0 credits. No owned AMD Cloud/vLLM verified. New cloud live configuration remains gated. Quality/language/photo/operator acceptance pending.');
text(s,'171 regression tests passed\n30 domain cases passed',64,165,560,150,34,'#173655',true);
text(s,'Web and installed Windows checks.\nOwner-operated native dialogs.\nActual Linux restart persistence.\nOffline dated handover and receipts.',64,355,540,200,27);
text(s,'Remaining acceptance',665,170,540,65,34,'#142235',true);
text(s,'Professional and language review.\nPhysical label photographs.\nThree unfamiliar operators.\nNew live budget and cloud activation.\nOwned ADC eligibility unverified.',665,270,545,250,27,'#8e621a');
text(s,'batchfence.onrender.com\ngithub.com/NuraliKuzhagaliev/BatchFence',64,600,1150,75,23,'#173655');
for(const [i,slide] of p.slides.items.entries()){const png=await p.export({slide,format:'png',scale:1});await fs.writeFile(path.join(tmp,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));}
await fs.copyFile(path.join(tmp,'slide-1.png'),path.join(out,'BatchFence-cover-0.4.0-rc.1.png'));
const candidate=path.join(tmp,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const skill='C:/Users/nural/.codex/plugins/cache/openai-primary-runtime/presentations/26.1011.51657/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const report=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:path.join(out,'BatchFence-0.4.0-rc.1-final.pptx'),pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:['Segoe UI']},verifyArtifactToolImport:true,receiptPath:path.join(tmp,'validation-release.json')});
console.log(JSON.stringify(report));
