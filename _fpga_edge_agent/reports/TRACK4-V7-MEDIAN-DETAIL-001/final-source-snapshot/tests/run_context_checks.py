"""Approved v4 T2/T3: independent numeric vectors, real RAM window and stalls."""
from pathlib import Path
import hashlib,json
import numpy as np
import run_checks as sim
from reference_v4 import packed_fields,context_image,filter_windows
from reference_v2 import window_math

W,R=sim.WORK,sim.REPORT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[sim.MODEL,*sorted((W/'algorithm/edge').glob('*.sv')),W/'tests/tb_context_chain.sv',W/'tests/tb_context_filter.sv']
sim.run('context-compile','xvlog',['--sv',*sources])
results=[]

# Direct spatial windows exhaust all seed-neighbor masks, direction and weak bit.
records=[]
for direction in range(4):
    for weak in (0,1):
        for own in (0,1):
            for mask in range(256):
                pair=np.zeros((2,3,3),dtype=np.uint16)
                for lane in range(2):
                    pair[lane]=np.arange(9,dtype=np.uint16).reshape(3,3)+lane*17
                    for bit,cell in enumerate((0,1,2,3,5,6,7,8)):
                        pair[lane].flat[cell]|=(direction<<8)|(((mask>>bit)&1)<<11)
                    pair[lane,1,1]|=(direction<<8)|(weak<<10)|(own<<11)
                records.append((pair,2,2))
for center_dir in range(4):
    for d1 in range(4):
        for d2 in range(4):
            for x,y in ((0,0),(38,0),(0,11),(38,11),(0,5),(38,5),(8,0),(8,11),(8,5)):
                pair=np.full((2,3,3),2048|1024,dtype=np.uint16)
                for lane in range(2):
                    pair[lane,1,1]=(center_dir<<8)|1024|lane
                    pair[lane,0,:]|=d1<<8;pair[lane,2,:]|=d2<<8
                    pair[lane,1,0]|=d1<<8;pair[lane,1,2]|=d2<<8
                records.append((pair,x,y))
rng=np.random.default_rng(431)
for _ in range(2048):
    a=rng.integers(0,4096,(2,3,3),dtype=np.uint16)
    records.append((a,int(rng.integers(0,20))*2,int(rng.integers(0,12))))
p=sim.SIM/'context-filter.hex'
with p.open('w',encoding='ascii') as output:
    for pair,x,y in records:
        numeric=filter_windows(pair,x,y,40,12)
        centers=numeric[0][0]|(numeric[1][0]<<8);edges=numeric[0][1]|(numeric[1][1]<<1)
        packed=sum(int(v)<<(16*i) for i,v in enumerate(pair.reshape(-1)))
        output.write(f'{(packed<<40)|(x<<29)|(y<<18)|(centers<<2)|edges:082x}\n')
sim.snapshot('context_filter','tb_context_filter',dict(N=len(records)))
text=sim.simulate('context_filter','CONTEXT_FILTER_PASS',['DATA='+p.as_posix()])
results.append(dict(test='direct spatial filter',vectors=len(records),vector_sha256=sha(p),completion=next(s for s in text.splitlines() if 'CONTEXT_FILTER_PASS' in s)))

configs=[(40,12,d,64) for d in (32,16)]
configs += [(8,5,d,t) for d in (32,16) for t in (0,7,16,32,2047)]
for width,height,drop,t in configs:
    n=width*height
    pixels=rng.integers(0,256,(n,3,3),dtype=np.int32)
    m=window_math(pixels,t,20,True)
    # Explicit zero, sign, ratio, abs-extreme and TL comparison boundaries.
    special=[(0,0),(32,0),(34,0),(48,0),(50,0),(16,8),(16,10),(8,16),(10,16),
             (1020,0),(-1020,0),(0,1020),(0,-1020),(765,765),(-765,-765),(-16,8),(16,-8)]
    for i,(gx,gy) in enumerate(special):m['gx'][i]=gx;m['gy'][i]=gy;m['l1'][i]=abs(gx)+abs(gy)
    seed=rng.integers(0,2,n,dtype=np.uint16).astype(bool)
    packed=packed_fields(m['center'],m['gx'],m['gy'],m['l1'],seed,t,drop).reshape(height,width)
    edge=context_image(packed)['edge'].reshape(-1)
    paths=[sim.SIM/f'context-{width}-{height}-{drop}-{t}-{kind}.hex' for kind in ('input','gold')]
    def field(values,i,bits):return sum((int(v)&((1<<bits)-1))<<(bits*j) for j,v in enumerate(values[i:i+2]))
    with paths[0].open('w',encoding='ascii') as src,paths[1].open('w',encoding='ascii') as gold:
        flat=packed.reshape(-1)
        for i in range(0,n,2):
            v=field(m['center'],i,8)
            for key in ('gx','gy','l1'):v=(v<<22)|field(m[key],i,11)
            v=(v<<2)|field(seed,i,1)
            src.write(f'{v:021x}\n')
            expected=(field(flat,i,16)<<18)|(field(m['center'],i,8)<<2)|field(edge,i,1)
            gold.write(f'{expected:013x}\n')
    name=f'context_{width}_{height}_{drop}_{t}'
    sim.snapshot(name,'tb_context_chain',dict(W=width,H=height,DROP=drop,T=t))
    text=sim.simulate(name,'CONTEXT_CHAIN_PASS',['INPUT='+paths[0].as_posix(),'GOLD='+paths[1].as_posix()])
    results.append(dict(test='pack/window/filter',W=width,H=height,drop=drop,threshold=t,frames=5,interrupts=3,
        vector_sha256={p.name:sha(p) for p in paths},completion=next(s for s in text.splitlines() if 'CONTEXT_CHAIN_PASS' in s)))
result=dict(result='PASS',runs=results,sources={str(p):sha(p) for p in sources+[Path(__file__),W/'tests/reference_v4.py',W/'tests/reference_v2.py',W/'tests/reference_v3.py']})
(R/'context-core-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('CONTEXT_CORE_ALL_PASS',flush=True)
