"""Caption real read-only recordings; retain originals and model latency evidence."""
from pathlib import Path
import hashlib,json,re,subprocess
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1];W=ROOT/'work/continuation-media';OUT=ROOT/'submission/continuation';ff=imageio_ffmpeg.get_ffmpeg_exe()
def run(a):subprocess.run([ff,'-hide_banner','-loglevel','error',*a],cwd=ROOT,check=True)
def duration(p):
 t=subprocess.run([ff,'-hide_banner','-i',str(p)],capture_output=True,text=True).stderr;m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',t);assert m
 return int(m[1])*3600+int(m[2])*60+float(m[3])
segments=[('work/continuation-media/evolus.webm','Stored genuine Evolus extractor + Gemma result. Synthetic sources. Agent-operated review.'),('docs/continuation/live/ui/gemma-label-region.png','Synthetic label. Actual Gemma image response is retained. Physical-photo acceptance pending.'),('work/continuation-media/gemma.webm','Stored direct AMD Gemma workflow. Synthetic inventory. No inference during recording.')];records=[]
for i,(file,caption) in enumerate(segments):
 p=ROOT/file;still=p.suffix=='.png';seconds=6 if still else duration(p)
 ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1366\nPlayResY: 960\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow\nStyle: Default,Segoe UI,21,&H00FFFFFF,&H00182B,&H00182B,0,8,18,18,15,1,0,0\n[Events]\nFormat: Layer, Start, End, Style, Text\nDialogue: 0,0:00:00.00,0:10:00.00,Default,'+caption+'\n'
 (W/f'{i}.ass').write_text(ass,encoding='utf-8')
 vf=f'scale=1366:900:force_original_aspect_ratio=decrease,pad=1366:900:(ow-iw)/2:(oh-ih)/2:color=white,pad=1366:960:0:60:color=0x0b182b,ass=work/continuation-media/{i}.ass,fps=25,setsar=1'
 run(['-y']+(['-loop','1'] if still else [])+['-i',str(p),'-t',str(seconds),'-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(W/f'{i}.mp4')])
 records.append({'source':file,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'seconds':seconds,'caption':caption,'kind':'retained screenshot' if still else 'actual browser recording at original speed'})
(W/'concat.txt').write_text(''.join(f"file '{i}.mp4'\n" for i in range(len(segments))),encoding='utf-8');p=OUT/'BatchFence-0.4.0-rc.1-workflows.mp4'
run(['-y','-f','concat','-safe','0','-i',str(W/'concat.txt'),'-c','copy','-movflags','+faststart',str(p)])
for i in range(len(segments)):run(['-y','-ss','3','-i',str(W/f'{i}.mp4'),'-frames:v','1',str(W/f'frame-{i}.png')])
report={'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'seconds':duration(p),'segments':records,'provenance':'Separate actual Evolus and direct AMD cases, not one continuous case. Stored genuine results, synthetic sources and agent-operated review. No new inference during capture. Original speed, no audio. Caption band outside application pixels. Complete engineering walkthrough in docs/continuation/operator-walkthrough.md.'}
(OUT/'video-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
