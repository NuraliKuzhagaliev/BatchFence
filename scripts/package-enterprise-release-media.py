"""Package actual recordings with explicit provenance; no invented interactions or inference."""
from pathlib import Path
import hashlib,json,re,subprocess
import imageio_ffmpeg
r=Path(__file__).resolve().parents[1];w=r/'work/enterprise-release-media';w.mkdir(exist_ok=True);out=r/'submission/enterprise'
ff=imageio_ffmpeg.get_ffmpeg_exe()
def run(args):subprocess.run([ff,'-hide_banner','-loglevel','error',*args],cwd=r,check=True)
def duration(p):
 text=subprocess.run([ff,'-hide_banner','-i',str(p)],capture_output=True,text=True).stderr
 m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',text);assert m
 return int(m[1])*3600+int(m[2])*60+float(m[3])
segments=[
 ('work/enterprise-final-media/frozen.webm','Recorded fresh AMD signal response. Synthetic records. No inference during capture.'),
 ('docs/enterprise/live/ui/knowledge-quote.png','Recorded fresh AMD procedure answer. Synthetic source. Agent-operated review.'),
 ('work/enterprise-final-media/receiving-v2.webm','Recorded fresh AMD receiving result. Synthetic stock. Agent-operated review and approval.'),
 ('work/enterprise-media/connected-synthetic.webm','Synthetic workflow and historical follow-up replay. Fixtures only. Agent-operated review.')]
records=[]
for i,(file,caption) in enumerate(segments):
 p=r/file;png=p.suffix=='.png';seconds=7 if png else duration(p)
 ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1366\nPlayResY: 960\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow\nStyle: Default,Segoe UI,21,&H00FFFFFF,&H00182B,&H00182B,0,8,18,18,15,1,0,0\n[Events]\nFormat: Layer, Start, End, Style, Text\nDialogue: 0,0:00:00.00,0:10:00.00,Default,'+caption+'\n'
 (w/f'{i}.ass').write_text(ass,encoding='utf-8')
 vf=f'scale=1366:900:force_original_aspect_ratio=decrease,pad=1366:900:(ow-iw)/2:(oh-ih)/2:color=white,pad=1366:960:0:60:color=0x0b182b,ass=work/enterprise-release-media/{i}.ass,fps=25,setsar=1'
 args=['-y']+(['-loop','1'] if png else [])+['-i',str(p),'-t',str(seconds),'-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(w/f'{i}.mp4')]
 run(args);records.append({'source':file,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'seconds':seconds,'caption':caption,'kind':'retained screenshot' if png else 'actual browser recording at original speed'})
(w/'concat.txt').write_text(''.join(f"file '{i}.mp4'\n" for i in range(len(segments))),encoding='utf-8')
p=out/'BatchFence-0.3.0-verified-workflows.mp4'
run(['-y','-f','concat','-safe','0','-i',str(w/'concat.txt'),'-c','copy','-movflags','+faststart',str(p)])
for i in range(len(segments)):run(['-y','-ss','4','-i',str(w/f'{i}.mp4'),'-frames:v','1',str(w/f'frame-{i}.png')])
report={'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration_seconds':duration(p),'segments':records,'provenance':'Separate retained AMD-result cases followed by a synthetic full workflow, explicitly labeled. All data synthetic, all review agent-operated. No new AMD inference during filming. Original speed, no audio. Caption band outside application pixels. Narration is supplied for a human presenter.'}
(out/'video-evidence-0.3.0.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
