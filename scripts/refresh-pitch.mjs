import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..'),tmp=path.join(root,'work/pitch-0.1.1');
const modules=process.env.BATCHFENCE_RUNTIME_NODE_MODULES||'C:/Users/nural/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const pkg=JSON.parse(await fs.readFile(path.join(modules,'@oai/artifact-tool/package.json'),'utf8'));
const entry=pkg.exports?.['.']?.import||pkg.module||pkg.main;
const {PresentationFile,FileBlob}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool',typeof entry==='string'?entry:'dist/artifact_tool.mjs')).href);
const source=path.join(root,'submission/BatchFence-pitch.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(source));
await fs.mkdir(tmp,{recursive:true});
const before=await p.inspect({select:'$.slides[*]',include:['id','index','elements.id','elements.kind','elements.text','elements.position','elements.style']});
await fs.writeFile(path.join(tmp,'before.json'),JSON.stringify(before.records,null,2));
const changes={
 'sh/65g3298r':['Synthetic walkthrough. Live AMD verification remains open.','Live AMD on synthetic data · agent-operated review'],
 'sh/x4r21kru':['The quality manager’s incident','Review model proposals before action'],
 'sh/9072xkry':['A supplier flags a cosmetic coating lot.','Every candidate starts unresolved.'],
 'sh/ozy1ofad':['The manager must reconcile stock exports, production lineage and an unresolved receiving identity before deciding what to contain.','Review affected, unresolved and excluded lots separately. Narrowing needs an exact source quote and an explicit incident boundary.'],
 'sh/a10jqpsj':['Fictional Northstar Enclosures. No safety or compliance certification.','Actual live AMD evidence. Synthetic records; review operated by Codex.'],
 'sh/0ba143al':['SUP-C adds the FG-D branch.\nThe earlier approval cannot execute.','BZ-9187 adds the FG-D branch.\nThe earlier approval cannot execute.'],
 'sh/032tgr6d':['Verification and technology','Ambiguity is contained before execution'],
 'sh/dgbulwnm':['30 / 30 domain cases','40 / 40 regression checks'],
 'sh/cf2tcr61':['18 development and 12 held out','30 frozen domain cases also passed'],
 'sh/z2tcnm5s':['Web and installed Windows flows completed sandbox transactions and packet handoff.','Unresolved scope holds all 1,200 units. A separate citation failure blocks review and execution.'],
 'sh/yhkbe1o7':['AMD live inference: blocked by missing private configuration','Model booleans remain fallible. Source review is still required.'],
 'sh/ml07i9sv':['A bounded manufacturing pilot','Local prototype; release gates remain'],
 'sh/87ipkzal':['Next gates: live AMD, distribution and independent user review.','Next gates: Docker repair, distribution and independent review.'],
};
for(const [id,[oldText,newText]] of Object.entries(changes)){
 const record=before.records.flatMap(s=>s.elements).find(e=>e.id===id);
 if(record?.text!==oldText)throw Error('Source deck text changed: '+id);
 p.resolve(id).text.replace(oldText,newText);
}
const images={
 'im/6d8jed0r':'docs/ambiguity-fix/ambiguity-review.png',
 'im/6tknud0f':'docs/ambiguity-fix/clear-live/01-reviewed-scope.png',
 'im/b2lc3q1s':'docs/ambiguity-fix/clear-live/02-reviewed-scope.png',
 'im/g7atobq5':'docs/ambiguity-fix/ambiguity-receipt.png',
 'im/8jyl8rmd':'docs/ambiguity-fix/installed-live-packet.png',
};
for(const [id,file] of Object.entries(images)){
 const im=p.resolve(id),frame=im.frame,crop=im.crop,geometry=im.geometry,borderRadius=im.borderRadius,
  rotation=im.rotation,flipHorizontal=im.flipHorizontal,flipVertical=im.flipVertical,lockAspectRatio=im.lockAspectRatio;
 im.replace({blob:new Uint8Array(await fs.readFile(path.join(root,file))),contentType:'image/png',fit:'contain',
  alt:'Actual BatchFence 0.1.1 application view of synthetic live AMD evidence; agent-operated review'});
 im.frame=frame;im.crop=crop;im.geometry=geometry;im.borderRadius=borderRadius;im.rotation=rotation;
 im.flipHorizontal=flipHorizontal;im.flipVertical=flipVertical;im.lockAspectRatio=lockAspectRatio;
}
const notes=[
 'BatchFence 0.1.1 local prototype. All data synthetic. AMD service provenance is documented in docs/live-verification/provider-documentation.md. Current requested model MiMo-V2.6-Flash, returned self-dploy/MiMo-V2.6-Flash. Explicit selection followed three Gemma failures (two typed timeouts; first cause untyped), all retained. No independent human/customer validation.',
 'Actual historical live ambiguity review screenshot. Original Gemma failure was replayed exactly; its false SUP-S proposal previously permitted an unsupported exclusion. New controls separate model output from reviewed affected/unresolved/excluded dispositions. Explicit unresolved source blocks narrowing. See docs/ambiguity-fix/before-regression.json and live-ambiguity.json. Bounded English source rules are conservative, not general semantic proof.',
 'Fresh live MiMo response drove this 500-unit plan: 400 documented and 100 uncertain. Zero lot-ID correction; agent explained why the complete supplier boundary does not resolve warehouse ancestry. No financial savings or real customer benefit is claimed. See docs/ambiguity-fix/clear-live/browser-results.json and packet-1.json.',
 'The revised live response adds BZ-9187. A new exact plan holds 800 units, preserving the uncertain 100. Two actual receipts persisted; reuse of the old approval was rejected with 409 STALE_APPROVAL. See docs/ambiguity-fix/clear-live/browser-results.json and packet-2.json.',
 '40 pytest checks, 30 frozen graph cases, 12 browser checks and seven installed desktop checks passed. Raw live quality remains imperfect: one ambiguity result required both booleans reviewed as unresolved; a different response failed citation validation and could not proceed. Three Gemma failures are retained (two typed timeouts; first cause untyped), not scored as semantic errors. Cross-runtime packet hashing was fixed for small AMD usage costs; original failed exports remain preserved. See docs/ambiguity-fix. Agent review is not independent human validation.',
 'Actual installed Windows 0.1.1 read-only packet from the live walkthrough, backend unreachable. Dialog selection supplied by the test harness for this recording; real dialogs were separately exercised at prior checkpoint ed6a2b0. Current installer is unsigned. Docker startup is blocked by AF_UNIX reparse error 1920 at sailor-ingest.sock; no blanket permissions/reset/data deletion performed. Hosted publication and event submission require authorization and eligibility review. Buyer/pilot are hypotheses, not validated customer research.'
];
for(const [i,slide] of p.slides.items.entries()){
 slide.speakerNotes.text=notes[i];
 const png=await p.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(tmp,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(tmp,'candidate.pptx'));
const after=await p.inspect({select:'$.slides[*]',include:['id','index','elements.id','elements.kind','elements.text','elements.position','elements.style']});
await fs.writeFile(path.join(tmp,'after.json'),JSON.stringify(after.records,null,2));
await fs.writeFile(path.join(tmp,'source.json'),JSON.stringify({source,sha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex'),slides:6,font:'Segoe UI',method:'Imported existing deck, replaced text/images in place, preserved frames and styles.'},null,2));
console.log('Updated six imported slides and rendered previews.');
