"""Real AMD usage metadata exposed a cross-runtime packet hash mismatch."""
import json
import subprocess
import pytest
from pathlib import Path
from backend.domain import canonical, digest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('field,value', [
    ('enterprise_packet', []), ('hold_ledger', [None]),
    ('receiving_runs', 'invalid'),
    ('quantities', {'applied_hold_units': -1, 'recovery_pending_units': 0, 'confirmed_recovery_units': 0}),
])
def test_invalid_enterprise_packet_extensions_rejected_even_with_correct_hash(field, value):
    packet = json.loads((ROOT / 'docs/verified-decision-packet.json').read_text(encoding='utf-8'))
    packet['case'][field] = value
    packet['integrity_hash'] = digest(packet['case'])
    node = subprocess.run(['node', '-e', 'const fs=require("fs");try {require("./desktop/packet.cjs").validatePacket(JSON.parse(fs.readFileSync(0,"utf8")));process.exit(2)} catch(e) {if(!e.message.includes("Invalid historical module evidence"))throw e;}'],
                          input=json.dumps(packet), capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
    assert node.returncode == 0, node.stderr


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
