"""Nine-stage wrapper protocol and scalar-value verification."""
from pathlib import Path
import hashlib,json
import numpy as np
import run_checks as sim
from reference_median_detail import scalar_window

W=Path(__file__).resolve().parents[1];R=W.parents[2]/'reports/TRACK4-V7-MEDIAN-DETAIL-001'
S=W/'sim_median_detail';S.mkdir(exist_ok=True);sim.SIM=S;sim.REPORT=R
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def vectors(width,height,n=12000):
    rng=np.random.default_rng(431);input_path=S/f'{width}-{height}-input.hex';gold_path=S/f'{width}-{height}-gold.hex'
    with input_path.open('w',encoding='ascii') as f,gold_path.open('w',encoding='ascii') as g:
        for i in range(n):
            p=rng.integers(0,256,(3,3),dtype=np.int32)
            if i%3!=0:
                c=int(rng.integers(32,224));bg=c+(-1 if i%2 else 1)*int(rng.integers(16,32));p[:]=bg;p[1,1]=c
                dy,dx=((1,0),(1,1),(0,1),(1,-1))[i%4];p[1-dy,1-dx]=c;p[1+dy,1+dx]=c
            x=int(rng.integers(0,width//2))*2;y=int(rng.integers(0,height));flags=int(rng.integers(0,8));enabled=i%11!=0
            ordinary=[];new=[]
            pair=np.stack([p,np.roll(p,i%3,axis=0)])
            for lane in range(2):
                ordinary.append(scalar_window(pair[lane],x+lane,y,width,height,16,4,True,False)[0])
                new.append(scalar_window(pair[lane],x+lane,y,width,height,16,4,True,enabled)[0])
            packed=sum(int(v)<<(8*k) for k,v in enumerate(pair.reshape(-1)))
            packed|=x<<144|y<<155|flags<<166|int(enabled)<<169
            f.write(f'{packed:043x}\n');gold=sum(v<<(8*k) for k,v in enumerate(ordinary))+sum(v<<(16+8*k) for k,v in enumerate(new));g.write(f'{gold:08x}\n')
    return input_path,gold_path


def main():
    sources=[W/'algorithm/frontend/median9_pair.sv',W/'algorithm/frontend/median9_detail_pair.sv',W/'tests/tb_median_detail.sv']
    sim.run('median-detail-compile','xvlog',['--sv',*sources]);runs=[]
    for width,height in ((6,5),(40,12),(1920,1080)):
        p,g=vectors(width,height);name=f'median_{width}_{height}'
        sim.snapshot(name,'tb_median_detail',dict(W=width,H=height,N=12000))
        out=sim.simulate(name,'MEDIAN_DETAIL_PASS',['INPUT='+p.as_posix(),'GOLD='+g.as_posix()])
        runs.append(dict(W=width,H=height,vectors=12000,vector_sha256={p.name:sha(p),g.name:sha(g)},completion=next(x for x in out.splitlines() if 'MEDIAN_DETAIL_PASS' in x)))
    sources += [Path(__file__),W/'tests/reference_median_detail.py']
    record=dict(result='PASS',runs=runs,sources={str(p):sha(p) for p in sources})
    (R/'median-core-result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print('MEDIAN_CORE_ALL_PASS')


if __name__=='__main__':main()
