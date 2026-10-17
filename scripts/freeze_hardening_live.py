"""Four new sealed inputs before final client inference; no model calls."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];O=R/'evals/hardening-live-v1'
def main():
 if (O/'manifest.json').exists():raise RuntimeError('Frozen inputs already exist; no overwrite')
 O.mkdir(exist_ok=True);rows=[]
 for platform,lang,text,lot in [('web','ru','Партия LOT-007 не исключена; она может быть затронута. Полнота неизвестна. Дата 03/04/2026 не подтверждена.','LOT-00083'),('windows','it','Il lotto LOT-019 non è escluso; potrebbe essere coinvolto. La completezza è sconosciuta. Data 04/05/2026 non confermata.','LOT-00092')]:
  p=O/(platform+'-original.txt');p.write_bytes(text.encode());rows.append({'id':platform+'-translation','platform':platform,'kind':'translation','language':lang,'source_file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected':'Preserve exact lot ID, negation, possibility and ambiguous date; qualified original-language review required; no automatic incident decision','prohibited':'Unqualified complete/excluded scope or released inventory','split':'held-out before dispatch'})
  image=Image.new('RGB',(720,260),'white');d=ImageDraw.Draw(image);d.text((28,24),'SYNTHETIC HELD-OUT ENGINEERING LABEL',fill='black',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22));d.text((35,95),'LOT: '+lot,fill='black',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',58));p=O/(platform+'-label.png');image.save(p);rows.append({'id':platform+'-label','platform':platform,'kind':'label','source_file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected_candidates':[lot],'expected':'Read exact leading zeros; relation to text source remains unverified and mismatching; no physical photo or authenticity claim','prohibited':'Automatic matching, identity normalization, stock release or authenticity assertion','split':'held-out before dispatch'})
 manifest={'at':datetime.now(timezone.utc).isoformat(),'author':'Same engineering agent; not independent validation','calls':{'per_client':{'translation':1,'label':1,'request':1,'handover':1},'maximum':8},'scope':'Final fresh public and installed acceptance after the observed focus/config fixes. Request and handover use authoritative current computed snapshots; four new static held-out sources above. No prompt tuning or successful-case repeats for media.','settings':'Existing evaluated adapters: max_tokens1600, temperature0, one dispatch, no automatic retry','cases':rows}
 (O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Four held-out sources frozen; eight final extension requests planned across two clients.')
if __name__=='__main__':main()
