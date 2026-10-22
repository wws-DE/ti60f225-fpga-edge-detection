"""Independent numeric vectors plus real sensor sequencer; no hardware access."""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np
import run_checks as sim

W,R=sim.WORK,sim.REPORT
base=W.parent/'track4_v7_fullscreen_mode_001_20261021'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
auth=json.loads((R/'authorization.json').read_text(encoding='utf-8'))
assert sha(R/'approved-design-v1.md')==auth['approved_design_sha256']
changed=[]
files=[]
for folder in ('rtl','algorithm','ip','ooc'):
    files.extend(p for p in (base/folder).rglob('*') if p.is_file())
files.extend(p for p in base.iterdir() if p.is_file() and p.suffix!='.md' and p.name!='.lock')
for p in files:
    rel=p.relative_to(base)
    if sha(p)!=sha(W/rel):changed.append(rel.as_posix())
assert sorted(changed)==sorted(['rtl/ti60f225_oob_top.v','rtl/cam_i2c_ctrl/i2c/i2c_master_reg_rom.v']),changed
(R/'source-delta.json').write_text(json.dumps(dict(baseline=str(base),copied_file_count=len(files),changed=changed,unchanged_count=len(files)-len(changed)),indent=2),encoding='utf-8')
top=(W/'rtl/ti60f225_oob_top.v').read_text(encoding='utf-8')
assert re.search(r"localparam\s+\[10:0\]\s+SOBEL_EDGE_THRESHOLD\s*=\s*11'd96",top)
assert top.count('.cfg_threshold(SOBEL_EDGE_THRESHOLD)')==1
romrel='rtl/cam_i2c_ctrl/i2c/i2c_master_reg_rom.v'
old=(base/romrel).read_text(encoding='utf-8')
new=(W/romrel).read_text(encoding='utf-8')
# Restoring just the explicit edits must recover every original functional line.
restored=new.replace("// SC431HAI表2-7：0x81/0x2A约4.043倍；曝光和DCG位保持原配置。\nlocalparam [7:0] SENSOR_ANALOG_GAIN = 8'h81;\n",'').replace("ROM[8'ha1] = {16'h3E08,SENSOR_ANALOG_GAIN,1'b0};","ROM[8'ha1] = {16'h3E08,8'h80,1'b0};")
assert restored==old
ctrl=(W/'rtl/cam_i2c_ctrl/i2c/i2c_master_ctrl_top.v').read_text(encoding='utf-8')
assert re.search(r'parameter\s+DATA_LENGTH\s*=\s*164',ctrl)
sensor_sources=[W/'rtl/cam_i2c_ctrl/i2c/i2c_master_reg_set.v',W/romrel,W/'tests/tb_sensor_gain.sv']
sim.run('sensor-compile','xvlog',['--sv',*sensor_sources])
sim.snapshot('sensor_gain','tb_sensor_gain')
sensor=sim.simulate('sensor_gain','SENSOR_GAIN_PASS',['GOLD='+(W/'tests/sensor-init-golden.hex').as_posix()])

# Both gradient polarities, horizontal/vertical/diagonal, equality boundary,
# flat fields, extrema and independent lane contents. This is numeric sensitivity,
# not a claim about accuracy on real camera frames.
def vertical(delta,negative=False):
    lo,hi=16,16+delta
    if negative:lo,hi=hi,lo
    return np.array([[lo,lo,hi]]*3,dtype=np.int32)
windows=[np.full((3,3),v,dtype=np.int32) for v in (0,24,255)]
for delta in (24,25,30,64,65):
    for neg in (False,True):
        a=vertical(delta,neg);windows.extend([a,a.T])
windows.extend([np.array([[0,255,255],[0,0,255],[0,0,0]],dtype=np.int32),np.arange(9,dtype=np.int32).reshape(3,3)*25])
if len(windows)%2:windows.append(np.full((3,3),31,dtype=np.int32))
n=len(windows)//2
sim.run('sobel-threshold-compile','xvlog',['--sv',W/'algorithm/frontend/sobel_pair.sv',W/'tests/tb_sobel_threshold.sv'])
sim.snapshot('sobel_threshold','tb_sobel_threshold',{'N':n})
numeric=[]
for threshold in (96,256):
    records=[]
    for start in range(0,len(windows),2):
        pack=0;centers=gxs=gys=l1s=edges=0
        for lane,a in enumerate(windows[start:start+2]):
            gx=int(a[0,2]+2*a[1,2]+a[2,2]-a[0,0]-2*a[1,0]-a[2,0])
            gy=int(a[2,0]+2*a[2,1]+a[2,2]-a[0,0]-2*a[0,1]-a[0,2])
            magnitude=abs(gx)+abs(gy)
            pack|=sum(int(v)<<(8*i) for i,v in enumerate(a.flat))<<(72*lane)
            centers|=int(a[1,1])<<(8*lane);gxs|=(gx&2047)<<(11*lane);gys|=(gy&2047)<<(11*lane)
            l1s|=magnitude<<(11*lane);edges|=int(magnitude>threshold)<<lane
        record=((((centers<<22)|gxs)<<22|gys)<<22|l1s)<<2|edges
        records.append((pack<<84)|record)
    path=sim.SIM/f'sobel-threshold-{threshold}.hex'
    path.write_text(''.join(f'{v:057x}\n' for v in records),encoding='ascii')
    text=sim.simulate('sobel_threshold','SOBEL_THRESHOLD_PASS',['DATA='+path.as_posix(),'THRESHOLD='+str(threshold)])
    numeric.append(dict(threshold=threshold,pairs=n,vector_sha256=sha(path),completion=next(s for s in text.splitlines() if 'SOBEL_THRESHOLD_PASS' in s)))
assert 4*24==96 and not 4*24>96 and 4*25>96 and not 4*25>256
result=dict(result='PASS',sensor_completion=next(s for s in sensor.splitlines() if 'SENSOR_GAIN_PASS' in s),numeric=numeric,changed=changed,hardware_verified=False,sources={str(p):sha(p) for p in sensor_sources+[W/'algorithm/frontend/sobel_pair.sv',W/'tests/tb_sobel_threshold.sv',Path(__file__)]})
(R/'lowlight-focused-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('LOWLIGHT_FOCUSED_PASS',flush=True)
