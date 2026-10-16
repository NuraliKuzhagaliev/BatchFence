import path from 'node:path';
import fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const root=path.resolve(import.meta.dirname,'..');
process.env.RUNTIME_NODE_MODULES=process.env.BATCHFENCE_RUNTIME_NODE_MODULES||'C:/Users/nural/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill='C:/Users/nural/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const reference=JSON.parse(await fs.readFile(path.join(root,'work/pitch-0.1.1/source.json'),'utf8'));
const result=await finalizePresentation({
 workspaceDir:root,
 candidatePath:path.join(root,'work/pitch-0.1.1/candidate.pptx'),
 finalPath:path.join(root,'submission/BatchFence-pitch-0.1.1-reviewed.pptx'),
 pythonExecutable:'C:/Users/nural/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:6,
 requiredNativeTableOwnerSlides:[],
 requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'reference',families:['Segoe UI'],referencePath:reference.source,referenceSha256:reference.sha256},
 verifyArtifactToolImport:true,
 receiptPath:path.join(root,'work/pitch-0.1.1/final-validation-reviewed.json')
});
console.log(JSON.stringify(result,null,2));
