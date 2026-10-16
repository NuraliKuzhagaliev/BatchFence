from pathlib import Path
import json
import re
import subprocess
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
clips = ROOT / 'work/demo'
out = ROOT / 'submission'
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()


def duration(file):
    r = subprocess.run([ffmpeg, '-hide_banner', '-i', str(file)], capture_output=True, text=True)
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    if not m:
        raise RuntimeError('Could not inspect actual recorded clip duration')
    return int(m[1])*3600 + int(m[2])*60 + float(m[3])


def stamp(seconds, vtt=False):
    ms = round(seconds*1000)
    h, remainder = divmod(ms, 3600000)
    m, remainder = divmod(remainder, 60000)
    s, ms = divmod(remainder, 1000)
    return f'{h:02d}:{m:02d}:{s:02d}'+('.' if vtt else ',')+f'{ms:03d}'


web_duration = duration(clips/'web.webm')
desktop_duration = duration(clips/'desktop.webm')
chapters = json.loads((clips/'chapters.json').read_text())
cues = [(float(c['seconds']), c['caption']) for c in chapters['web']]
cues += [(web_duration+float(c['seconds']), c['caption']) for c in chapters['desktop']]
total = web_duration+desktop_duration
cues.sort()
srt = []
vtt = ['WEBVTT\n']
for i, (start, caption) in enumerate(cues):
    end = min(cues[i+1][0]-.05 if i+1<len(cues) else total, total)
    if end <= start:
        continue
    srt.append(f'{i+1}\n{stamp(start)} --> {stamp(end)}\n{caption}\n')
    vtt.append(f'{stamp(start,True)} --> {stamp(end,True)}\n{caption}\n')
(out/'BatchFence-demo.srt').write_text('\n'.join(srt), encoding='utf-8')
(out/'BatchFence-demo.vtt').write_text('\n'.join(vtt), encoding='utf-8')
manifest = clips/'concat.txt'
manifest.write_text("file '"+(clips/'web.webm').as_posix()+"'\nfile '"+(clips/'desktop.webm').as_posix()+"'\n")
command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0',
           '-i', str(manifest), '-i', str(out/'BatchFence-demo.srt'),
           '-map', '0:v:0', '-map', '1:0', '-c:v', 'libx264', '-preset', 'veryfast',
           '-crf', '20', '-pix_fmt', 'yuv420p', '-c:s', 'mov_text', '-disposition:s:0', 'default',
           '-metadata', 'title=BatchFence synthetic prototype recording', '-movflags', '+faststart',
           str(out/'BatchFence-demo.mp4')]
subprocess.run(command, check=True)
actual = duration(out/'BatchFence-demo.mp4')
report = {'duration_seconds': actual, 'byte_count': (out/'BatchFence-demo.mp4').stat().st_size,
          'web_clip_seconds': web_duration, 'installed_desktop_clip_seconds': desktop_duration,
          'audio': 'Silent recording. Embedded selectable captions and sidecar SRT/VTT.',
          'provenance': 'Actual local web workflow and actual installed offline renderer. Fixture parser. Native dialog selection supplied by test harness and disclosed in captions.',
          'live_amd': False}
assert actual < 300 and report['byte_count'] < 300000000
(out/'demo-video-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(out/'demo-decision-packet.json').write_bytes((clips/'recorded-decision.json').read_bytes())
print(json.dumps(report,indent=2))
