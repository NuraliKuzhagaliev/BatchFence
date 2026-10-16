"""Real AMD usage metadata exposed a cross-runtime packet hash mismatch."""
import json
import subprocess
from pathlib import Path
from backend.domain import canonical, digest

ROOT = Path(__file__).resolve().parents[1]


def test_javascript_and_python_hash_actual_live_packets_identically():
    for name in ['clear-live/packet-2.json', 'unknown-involvement-packet.json']:
        p = json.loads((ROOT / 'docs/ambiguity-fix' / name).read_text(encoding='utf-8'))
        node = subprocess.run(['node', '-e', 'const fs=require("fs");const {canonical}=require("./desktop/packet.cjs");process.stdout.write(canonical(JSON.parse(fs.readFileSync(0,"utf8"))))'],
                              input=json.dumps(p['case']), capture_output=True, text=True, encoding='utf-8', cwd=ROOT, check=True)
        assert node.stdout == canonical(p['case'])


def test_json_number_thresholds_and_unicode_keys_match_javascript():
    values = {'costs': [8.33e-5, 1.2544e-6, 1e-7, 1e20, 1e21, -0.0, 0.1, 2.0],
              '\U0001f600': 'supplementary key', '\ufffd': 'BMP key'}
    node = subprocess.run(['node', '-e', 'const fs=require("fs");process.stdout.write(require("./desktop/packet.cjs").canonical(JSON.parse(fs.readFileSync(0,"utf8"))))'],
                          input=json.dumps(values), capture_output=True, text=True, encoding='utf-8', cwd=ROOT, check=True)
    assert canonical(values) == node.stdout
