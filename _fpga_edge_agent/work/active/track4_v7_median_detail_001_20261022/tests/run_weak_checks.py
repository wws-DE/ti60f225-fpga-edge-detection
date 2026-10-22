"""T1/T2/T3: v3 candidates and disabled branch against independent math/real v2."""
from pathlib import Path
import hashlib, json
import numpy as np
import run_checks as sim
from reference_v3 import window_math, windows, median_image
from quality_v3 import fixtures, noise_fixtures

W, R = sim.WORK, sim.REPORT
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = W.parent/'track4_v7_lowlight_edge_002_20261021/algorithm/frontend/sobel_pair.sv'
assert sha(baseline) == '9e239c18649cca8cfbfd188c5b708995702b53a5c690f928728c38bb12014c9b'
legacy = sim.SIM/'sobel_pair_baseline.sv'
legacy.write_text(baseline.read_text(encoding='utf-8').replace('module sobel_pair #(', 'module sobel_pair_baseline #('),encoding='utf-8')
datasets = [windows(median_image(item['gray'])).reshape(-1,3,3) for item in fixtures()]
datasets += [windows(median_image(gray)).reshape(-1,3,3) for _,_,gray in noise_fixtures()]
special = [np.full((3,3),v,dtype=np.int32) for v in (0,64,255)]
for d in (0,1,2,14,15,16,17,18,19,20,21,24,25,64,255):
    for count in (1,2,3):
        a = np.zeros((3,3),dtype=np.int32);a[:count,2]=d
        special.extend([a,255-a,a.T,(255-a).T])
    a=np.array([[0,0,d]]*3,dtype=np.int32);special.extend([a,255-a,a.T,(255-a).T])
for pos in range(9):
    a=np.zeros((3,3),dtype=np.int32);a.flat[pos]=255;special.extend([a,255-a])
special += [np.array([[0,0,0],[0,0,0],[0,0,32]],dtype=np.int32),
            np.array([[0,0,0],[0,0,0],[0,1,32]],dtype=np.int32),
            np.array([[0,255,255],[0,0,255],[0,0,0]],dtype=np.int32)]
special.extend(np.random.default_rng(431).integers(0,256,(4096,3,3),dtype=np.int32))
special=np.array(special)
assert {64,66,1530}.issubset(set(map(int,window_math(special)['l1'])))
all_windows=np.concatenate([*datasets,special])
sources=[W/'algorithm/frontend/sobel_pair.sv',legacy,W/'tests/tb_coherent_sobel.sv']
sim.run('weak-compile','xvlog',['--sv',*sources])
runs=[]
configs=[(1,16,8,64,1,True),(1,18,0,64,1,True),(0,18,0,64,1,True)]
configs += [(1,d,drop,t,1,False) for d,drop in ((16,8),(18,0)) for t in (0,7,8,2047)]
configs += [(1,18,0,64,kind,False) for kind in (0,2)]
for enabled,d,drop,t,kind,full in configs:
    values=all_windows if full else special
    if len(values)%2:values=np.concatenate([values,values[-1:]])
    n=len(values)//2
    math=window_math(values,t,d,drop,bool(enabled))
    if kind!=1:math['edge']=np.zeros_like(math['edge'])
    name=f'weak_{enabled}_{d}_{drop}_{t}_{kind}'
    p=sim.SIM/(name+'.hex')
    with p.open('w',encoding='ascii') as output:
        for i in range(0,len(values),2):
            packed=sum(int(v)<<(8*k) for k,v in enumerate(values[i:i+2].reshape(-1)))
            def field(a,bits):return sum((int(v)&((1<<bits)-1))<<(bits*j) for j,v in enumerate(a[i:i+2]))
            result=field(math['center'],8)
            for key in ('gx','gy','l1'):result=(result<<22)|field(math[key],11)
            result=(result<<2)|field(math['edge'],1)
            output.write(f'{((packed<<84)|result):057x}\n')
    sim.snapshot(name,'tb_coherent_sobel',dict(N=n,ENABLE=enabled,D=d,DROP=drop,T=t,KIND=kind))
    text=sim.simulate(name,'COHERENT_SOBEL_PASS',['DATA='+p.as_posix()])
    runs.append(dict(enabled=bool(enabled),weak_diff=d,drop=drop,threshold=t,kind=kind,pairs=n,
        vector_sha256=sha(p),completion=next(s for s in text.splitlines() if 'COHERENT_SOBEL_PASS' in s)))
result=dict(result='PASS',runs=runs,sources={str(p):sha(p) for p in sources+[Path(__file__),W/'tests/reference_v3.py',W/'tests/reference_v2.py',W/'tests/quality_v3.py']})
(R/'weak-core-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('WEAK_CORE_ALL_PASS',flush=True)
