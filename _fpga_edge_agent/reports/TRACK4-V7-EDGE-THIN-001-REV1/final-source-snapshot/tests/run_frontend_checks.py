"""Full frontend T5 including default-disabled and external-owner legacy checks."""
from pathlib import Path
import hashlib,json
import numpy as np
import run_checks as sim
from reference_v41 import image_math
from reference_v3 import image_math as old_math

W,R=sim.WORK,sim.REPORT
sim.SIM=W/'sim_frontend';sim.SIM.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
B=W.parent/'track4_v7_lowlight_edge_003_20261021'
baseline=[]
for rel,old,new in [('algorithm/frontend/sobel_pair.sv','module sobel_pair #(','module sobel_pair_baseline #('),
                    ('algorithm/frontend/frontend_frame_pair.sv','module frontend_frame_pair #(','module frontend_frame_pair_baseline #(')]:
    src=B/rel;s=src.read_text(encoding='utf-8');assert old in s
    s=s.replace(old,new)
    if 'frontend_frame' in rel:s=s.replace('sobel_pair #(','sobel_pair_baseline #(')
    target=sim.SIM/Path(rel).name;target.write_text(s,encoding='utf-8');baseline.append(target)
sources=[sim.MODEL,*sorted((W/'algorithm/frontend').glob('*.sv')),*sorted((W/'algorithm/edge').glob('*.sv')),
         *baseline,W/'tests/tb_frontend_context.sv']
sim.run('frontend-compile','xvlog',['--sv',*sources])
y,x=np.indices((5,8),dtype=np.uint32)
r=(x*17+y*31)%256;g=(x*41+y*7)%256;b=(x*3+y*61)%256
rgb=(r<<16)|(g<<8)|b;gray=((77*r+150*g+29*b+128)>>8).astype(np.int32)
old=old_math(gray,64,18,0);new=image_math(gray,64,18)
def write(path,array,bits,width):
    with path.open('w',encoding='ascii') as stream:
        for a,b in np.asarray(array).reshape(-1,2):stream.write(f'{(int(a)|(int(b)<<bits)):0{width}x}\n')
inp=sim.SIM/'input.hex';write(inp,rgb,24,12)
runs=[]
for enabled,compare,owner in ((1,0,0),(0,1,0),(0,1,1)):
    golden0=old['median'].astype(np.uint32)<<1
    m=new if enabled else old
    golden1=(m['median'].astype(np.uint32)<<1)|m['edge'].astype(np.uint32)
    # TB expects {center_pair16, edge_pair2}, not interleaved per-pixel bits.
    paths=[]
    for name,mapping in [('gold0',golden0),('gold1',golden1)]:
        path=sim.SIM/f'{name}-{enabled}-{owner}.hex';paths.append(path)
        with path.open('w',encoding='ascii') as f:
            for a,b in mapping.reshape(-1,2):
                a,b=int(a),int(b);center=(a>>1)|((b>>1)<<8);edge=(a&1)|((b&1)<<1)
                f.write(f'{((center<<2)|edge):05x}\n')
    name=f'frontend_{enabled}_{owner}'
    sim.snapshot(name,'tb_frontend_context',dict(CONTEXT=enabled,DIAG=18,COMPARE=compare,OWNER=owner))
    text=sim.simulate(name,'FRONTEND_CONTEXT_PASS',['INPUT='+inp.as_posix(),'GOLD0='+paths[0].as_posix(),'GOLD1='+paths[1].as_posix()])
    runs.append(dict(context_enabled=bool(enabled),compare_real_v3=bool(compare),external_owner=bool(owner),
        completion=next(s for s in text.splitlines() if 'FRONTEND_CONTEXT_PASS' in s),
        vector_sha256={p.name:sha(p) for p in [inp,*paths]}))
result=dict(result='PASS',runs=runs,sources={str(p):sha(p) for p in sources+[Path(__file__),W/'tests/reference_v41.py',W/'tests/reference_v3.py',W/'tests/reference_v4.py']},
    actual_v3_baseline_sources={str(B/rel):sha(B/rel) for rel in ('algorithm/frontend/sobel_pair.sv','algorithm/frontend/frontend_frame_pair.sv')})
(R/'frontend-context-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('FRONTEND_ALL_PASS',flush=True)
