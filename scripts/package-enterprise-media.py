from pathlib import Path
import json,subprocess,re,hashlib
import imageio_ffmpeg
r=Path(__file__).resolve().parents[1];w=r/'work/enterprise-media';out=r/'submission/enterprise';out.mkdir(exist_ok=True)
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();source=w/'connected-synthetic.webm'
info=subprocess.run([ffmpeg,'-hide_banner','-i',str(source)],capture_output=True,text=True).stderr
m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',info);assert m
seconds=int(m[1])*3600+int(m[2])*60+float(m[3])
caption='ENGINEERING CANDIDATE 0.3.0-rc.1 | Synthetic records | Agent-operated review | No AMD inference in this recording'
ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1366\nPlayResY: 960\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow\nStyle: Default,Segoe UI,20,&H00FFFFFF,&H00182B,&H00182B,0,8,18,18,14,1,0,0\n[Events]\nFormat: Layer, Start, End, Style, Text\nDialogue: 0,0:00:00.00,0:10:00.00,Default,'+caption+'\n'
(w/'captions.ass').write_text(ass,encoding='utf-8')
file=out/'BatchFence-connected-synthetic-rc1.mp4'
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(source),'-vf','pad=1366:960:0:60:color=0x0b182b,ass=work/enterprise-media/captions.ass','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(file)],cwd=r,check=True)
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss','20','-i',str(file),'-frames:v','1',str(w/'review-frame.png')],check=True)
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,'duration_seconds':seconds,'provenance':'Actual running candidate captured at original speed with automated interactions and reading pauses. HTTP incident setup disclosed by browser test. All model segments use synthetic fixtures. No fresh AMD inference; no independent human review. Caption band added outside application pixels. No audio; narration supplied separately.'}
(out/'video-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
