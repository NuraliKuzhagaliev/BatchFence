from pathlib import Path
import json, subprocess, re, textwrap, hashlib
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]
work=ROOT/'work/media-0.2.0'; out=ROOT/'submission'
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(); source=work/'walkthrough.webm'
def duration(file):
    result=subprocess.run([ffmpeg,'-hide_banner','-i',str(file)],capture_output=True,text=True)
    m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',result.stderr)
    if not m: raise ValueError('Could not read captured duration')
    return int(m[1])*3600+int(m[2])*60+float(m[3])
def stamp(t):
    cs=round(t*100);h,r=divmod(cs,360000);m,r=divmod(r,6000);s,c=divmod(r,100)
    return f'{h}:{m:02}:{s:02}.{c:02}'
chapters=json.loads((work/'chapters.json').read_text());total=duration(source)
ass=['[Script Info]','ScriptType: v4.00+','PlayResX: 1440','PlayResY: 1040','WrapStyle: 2','',
'[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
'Style: Default,Segoe UI,22,&H00FFFFFF,&H00FFFFFF,&H001B180B,&H001B180B,0,0,0,0,100,100,0,0,1,0,0,2,42,42,18,1','',
'[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
for i,c in enumerate(chapters):
    end=chapters[i+1]['seconds'] if i+1<len(chapters) else total
    lines=[c['provenance']]+textwrap.wrap(c['caption'],108)
    text='\\N'.join(lines).replace('{','').replace('}','')
    ass.append(f'Dialogue: 0,{stamp(0 if i==0 else c["seconds"])},{stamp(end)},Default,,0,0,0,,{text}')
(work/'captions.ass').write_text('\n'.join(ass),encoding='utf-8')
target=out/'BatchFence-demo-0.2.0.mp4'
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(source),'-vf','pad=1440:1040:0:0:color=0x0b182b,ass=work/media-0.2.0/captions.ass','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],cwd=ROOT,check=True)
actual=duration(target);assert abs(actual-total)<1
report={'duration_seconds':actual,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'chapters':chapters,
'capture':'Actual public application; original speed; synthetic rehearsal and historical AMD replay explicitly captioned. No new model calls in recording.',
'audio':'Silent with burned captions','event_media_constraints':'Authenticated first-step form checked; later media steps require advancing the empty draft. No duration-limit claim.',
'reviewer':'Agent-operated; no independent human validation','fresh_evidence':'docs/release-0.2.0/live/ contains the underlying fresh runs, failures if any, and review receipts.'}
(out/'demo-video-evidence-0.2.0.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for i,t in enumerate([15,45,85,115,140]):
    if t<actual:subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(t),'-i',str(target),'-frames:v','1',str(work/f'qa-{i}.png')],check=True)
print(json.dumps({'duration_seconds':actual,'bytes':target.stat().st_size}))
