"""Bind unchanged modes and identical full-resolution input to v2 evidence."""
from pathlib import Path
import hashlib, json
from itertools import zip_longest

W=Path(__file__).resolve().parents[1];A=W.parents[2]
R=A/'reports/TRACK4-V7-LOWLIGHT-EDGE-003'
B=W.parent/'track4_v7_lowlight_edge_002_20261021'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((R/'sim-full-result.json').read_text(encoding='utf-8'))['result']=='PASS'
new_input=W/'sim_fullscreen/full-input.hex';old_input=B/'sim_fullscreen/full-input.hex'
assert sha(new_input)==sha(old_input)
count=1920*1080*3//2
old_gold=B/'sim_fullscreen/full-gold.hex';new_gold=W/'sim_fullscreen/full-gold.hex'
with old_gold.open('rb') as old,new_gold.open('rb') as new:
    for i in range(count):
        x,y=old.readline(),new.readline()
        assert x and x==y,('mode 0/1/2 differs',i)
sources={}
for rel in ('rtl/ti60f225_oob_top.v','rtl/v7_fullscreen_mode_control.sv',
            'algorithm/frontend/rgb_to_y_pair.sv','algorithm/frontend/median9_pair.sv',
            'rtl/cam_i2c_ctrl/i2c/i2c_master_reg_rom.v'):
    assert sha(W/rel)==sha(B/rel),rel
    sources[rel]=sha(W/rel)
result=dict(result='PASS',method='Identical RGB input; first three expected frames byte-equal to v2; new RTL checked against these vectors',
            pixels=1920*1080*3,input_sha256=sha(new_input),old_gold_sha256=sha(old_gold),new_gold_sha256=sha(new_gold),
            unchanged_source_sha256=sources,script_sha256=sha(Path(__file__)),
            v2_edge_inclusion='Per-image reference assertion before vector generation, plus real v2 core comparison in T1/T2/T3',
            hardware_acceptance=False)
(R/'v2-mode-012-equivalence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('V2_MODE_012_EQUIVALENCE_PASS',result['pixels'])
