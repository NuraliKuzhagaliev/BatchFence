"""Package actual captures at original speed, with burned provenance captions."""
from pathlib import Path
import json, re, subprocess, textwrap, hashlib
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
work=ROOT/'work/media-0.1.1'; out=ROOT/'submission'
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()

def duration(file):
    p=subprocess.run([ffmpeg,'-hide_banner','-i',str(file)],capture_output=True,text=True)
    m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',p.stderr)
    if not m: raise RuntimeError('Missing captured clip duration')
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def stamp(s,sep=','):
    ms=round(s*1000); h,r=divmod(ms,3600000);m,r=divmod(r,60000);s,ms=divmod(r,1000)
    return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'

def ass_stamp(s):
    cs=round(s*100);h,r=divmod(cs,360000);m,r=divmod(r,6000);s,cs=divmod(r,100)
    return f'{h}:{m:02}:{s:02}.{cs:02}'

live=json.loads((ROOT/'docs/ambiguity-fix/clear-live/browser-results.json').read_text(encoding='utf-8'))
extra=json.loads((work/'chapters.json').read_text(encoding='utf-8'))
parts=[(ROOT/'work/live-verification/ambiguity-fix-live/live-workflow.webm',live['chapters'],'FRESH LIVE AMD | Synthetic data | Agent-operated review'),
       (work/'recorded.webm',extra['recorded'],'RECORDED LIVE EVIDENCE | No new inference | Synthetic data'),
       (work/'desktop.webm',extra['desktop'],'INSTALLED WINDOWS | Historical live packet | Offline read-only')]
cues=[];total=0;metadata=[]
for file,chapters,label in parts:
    seconds=duration(file)
    for i,c in enumerate(chapters):
        start=total+(0 if i==0 else c['seconds'])
        end=total+(chapters[i+1]['seconds'] if i+1<len(chapters) else seconds)
        cues.append((start,end,label+'\n'+c['caption']))
    metadata.append({'file':str(file.relative_to(ROOT)),'seconds':seconds,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'label':label})
    total+=seconds
ass=['[Script Info]','ScriptType: v4.00+','PlayResX: 1440','PlayResY: 1140','WrapStyle: 2','',
 '[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
 'Style: Default,Segoe UI,23,&H00FFFFFF,&H00FFFFFF,&H001B180B,&H001B180B,0,0,0,0,100,100,0,0,1,0,0,2,42,42,18,1','',
 '[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
srt=[];vtt=['WEBVTT\n']
for i,(start,end,caption) in enumerate(cues):
    srt.append(f'{i+1}\n{stamp(start)} --> {stamp(end)}\n{caption}\n')
    vtt.append(f'{stamp(start,".")} --> {stamp(end,".")}\n{caption}\n')
    lines=[line for paragraph in caption.splitlines() for line in textwrap.wrap(paragraph,108)]
    rendered='\\N'.join(lines).replace('{','').replace('}','')
    ass.append(f'Dialogue: 0,{ass_stamp(start)},{ass_stamp(end)},Default,,0,0,0,,{rendered}')
(work/'captions.ass').write_text('\n'.join(ass),encoding='utf-8')
(out/'BatchFence-demo-0.1.1.srt').write_text('\n'.join(srt),encoding='utf-8')
(out/'BatchFence-demo-0.1.1.vtt').write_text('\n'.join(vtt),encoding='utf-8')
manifest=work/'concat.txt'
manifest.write_text(''.join("file '"+p.as_posix()+"'\n" for p,_,_ in parts),encoding='utf-8')
target=out/'BatchFence-demo-0.1.1.mp4'
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(manifest),
 '-vf','pad=1440:1140:0:0:color=0x0b182b,ass=work/media-0.1.1/captions.ass','-an','-c:v','libx264',
 '-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-metadata',
 'title=BatchFence 0.1.1 - actual live AMD and labeled historical evidence',str(target)],cwd=ROOT,check=True)
actual=duration(target)
assert actual<300 and abs(actual-total)<1
report={'duration_seconds':actual,'bytes':target.stat().st_size,'segments':metadata,
 'capture':'Actual browser and installed Electron pixels, original speed, no fabricated UI or model response.',
 'audio':'Silent. Burned captions plus SRT/VTT sidecars.', 'fixture_segments':0,
 'disclosures':'Synthetic data; agent-operated review; historical segments labeled; native dialog selection stubbed in recording. No independent human validation.',
 'packet_reissue':'Saved packet hashes were reissued after number serialization fix; underlying runs/reviews/receipts unchanged. See docs/ambiguity-fix/packet-reissue.json.'}
(out/'demo-video-evidence-0.1.1.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for i,t in enumerate([84.9,170,180,200]):
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(t),'-i',str(target),'-frames:v','1',str(work/f'qa-{i+1}.png')],check=True)
print(json.dumps(report,indent=2))
