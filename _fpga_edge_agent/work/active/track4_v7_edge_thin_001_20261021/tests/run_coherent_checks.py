"""T2/T3: both candidates and disabled compatibility, real v1 core in parallel."""
from pathlib import Path
import hashlib,json
import numpy as np
import run_checks as sim
from reference_v2 import window_math,windows,median_image
from quality_candidates import fixtures,noise_fixtures

W,R=sim.WORK,sim.REPORT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
legacy_source=W.parent/'track4_v7_lowlight_edge_001_20261021/algorithm/frontend/sobel_pair.sv'
assert sha(legacy_source)=='1bf1247ef68b5573dfa3e8c64191d090507b1c0ed10589ef24157e9366a740dd'
legacy=sim.SIM/'sobel_pair_baseline.sv'
legacy.write_text(legacy_source.read_text(encoding='utf-8').replace('module sobel_pair (','module sobel_pair_baseline ('),encoding='utf-8')
datasets=[]
for item in fixtures():datasets.append(windows(median_image(item['gray'])).reshape(-1,3,3))
for amp,seed,gray in noise_fixtures():datasets.append(windows(median_image(gray)).reshape(-1,3,3))
special=[np.full((3,3),v,dtype=np.int32) for v in (0,64,255)]
for delta in (15,16,17,19,20,21,24,25,64,255):
    a=np.array([[0,0,delta]]*3,dtype=np.int32)
    special.extend([a,255-a,a.T,(255-a).T])
for pos in range(9):
    a=np.zeros((3,3),dtype=np.int32);a.flat[pos]=255;special.extend([a,255-a])
special.extend([np.array([[0,0,0],[0,0,0],[0,0,32]],dtype=np.int32),
    np.array([[0,0,0],[0,0,0],[0,1,32]],dtype=np.int32),
    np.array([[0,255,255],[0,0,255],[0,0,0]],dtype=np.int32)])
special.extend(np.random.default_rng(431).integers(0,256,(1024,3,3),dtype=np.int32))
datasets.append(np.array(special))
all_windows=np.concatenate(datasets)
if len(all_windows)%2:all_windows=np.concatenate([all_windows,all_windows[-1:]])
N=len(all_windows)//2
assert {64,66,1530}.issubset(set(map(int,window_math(np.array(special))['l1'])))
sources=[W/'algorithm/frontend/sobel_pair.sv',legacy,W/'tests/tb_coherent_sobel.sv']
sim.run('coherent-compile','xvlog',['--sv',*sources])
results=[]
for enabled,d,threshold in ((1,16,64),(1,20,64),(0,16,96)):
    print('GENERATE',enabled,d,threshold,N,flush=True)
    m=window_math(all_windows,threshold,d,bool(enabled))
    p=sim.SIM/f'coherent-{enabled}-{d}-{threshold}.hex'
    with p.open('w',encoding='ascii') as stream:
        for i in range(0,len(all_windows),2):
            packed=sum(int(v)<<(8*k) for k,v in enumerate(all_windows[i:i+2].reshape(-1)))
            def field(values,bits):return sum((int(v)&((1<<bits)-1))<<(bits*j) for j,v in enumerate(values[i:i+2]))
            result=field(m['center'],8)
            for key in ('gx','gy','l1'):result=(result<<22)|field(m[key],11)
            result=(result<<2)|field(m['edge'],1)
            stream.write(f'{((packed<<84)|result):057x}\n')
    name=f'coherent_{enabled}_{d}_{threshold}'
    sim.snapshot(name,'tb_coherent_sobel',dict(N=N,ENABLE=enabled,D=d,T=threshold))
    text=sim.simulate(name,'COHERENT_SOBEL_PASS',['DATA='+p.as_posix()])
    results.append(dict(enabled=bool(enabled),D=d,threshold=threshold,pairs=N,vector_sha256=sha(p),completion=next(s for s in text.splitlines() if 'COHERENT_SOBEL_PASS' in s)))
(R/'coherent-core-result.json').write_text(json.dumps(dict(result='PASS',runs=results,sources={str(p):sha(p) for p in sources+[Path(__file__),W/'tests/reference_v2.py']}),indent=2),encoding='utf-8')
print('COHERENT_CORE_ALL_PASS',flush=True)
