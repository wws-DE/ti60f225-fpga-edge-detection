"""Independent scalar confirmation of fixed median v1, including failing inputs."""
from pathlib import Path
import hashlib, json
import numpy as np
from reference_median_detail import CANDIDATES, detail_windows, scalar_window, median_detail, image_math
from reference_thin_v11 import image_math as baseline
from reference_v2 import windows, median_image
from quality_candidates import noise_fixtures

W=Path(__file__).resolve().parents[1]
R=W.parents[2]/'reports/TRACK4-V7-MEDIAN-DETAIL-001'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    counts={}
    for name,(d,s) in CANDIDATES.items():
        rng=np.random.default_rng(20261022)
        groups=[rng.integers(0,256,(12000,3,3),dtype=np.int32)]
        # All ternary windows exercise order statistics and close/far values.
        digit=np.arange(3**9,dtype=np.int32)
        ternary=np.empty((len(digit),9),dtype=np.int32)
        for k in range(9):ternary[:,k]=(digit//3**k)%3
        groups.append(np.array([24,24+d,255],dtype=np.int32)[ternary].reshape(-1,3,3))
        targeted=[]
        for tangent in ((1,7),(0,8),(3,5),(2,6)):
            for c in (0,1,16,18,32,127,224,254,255):
                for polarity in (-1,1):
                    for dd in (d-1,d,d+1):
                        bg=c+polarity*dd
                        if not 0<=bg<=255:continue
                        for diff in (0,s-1,s,s+1):
                            for sign in (-1,1):
                                fg=c+sign*diff
                                if not 0<=fg<=255:continue
                                v=np.full(9,bg,dtype=np.int32);v[4]=c;v[list(tangent)]=fg
                                targeted.append(v.copy())
                                for index in range(9):
                                    changed=v.copy();changed[index]=255-changed[index];targeted.append(changed)
                        for span in (2*s-1,2*s,2*s+1):
                            for index in range(9):
                                if index in (4,*tangent):continue
                                v=np.full(9,bg,dtype=np.int32);v[4]=c;v[list(tangent)]=c
                                other=bg+polarity*span
                                if 0<=other<=255:v[index]=other;targeted.append(v.copy())
        groups.append(np.asarray(targeted).reshape(-1,3,3))
        batch=np.concatenate(groups)
        vector,keep=detail_windows(batch,d,s)
        for i,p in enumerate(batch):
            value,flag=scalar_window(p,2,2,8,5,d,s)
            assert value==vector[i] and flag==keep[i],(name,i,p.tolist(),value,int(vector[i]),flag,bool(keep[i]))
        image_checks=0
        y,x=np.indices((40,64))
        images=[rng.integers(0,256,(40,64),dtype=np.int32),24+((x==32)|(y==20))*32,
                224-((x-y==8)|(x+y==54))*20,np.full((40,64),24,dtype=np.int32)]
        for gray in images:
            for me,de in ((True,True),(True,False),(False,True)):
                out,flags=median_detail(gray,d,s,me,de)
                ww=windows(gray)
                for yy,xx in np.ndindex(gray.shape):
                    value,flag=scalar_window(ww[yy,xx],xx,yy,64,40,d,s,me,de)
                    assert value==out[yy,xx] and flag==flags[yy,xx],(name,xx,yy,me,de)
                    image_checks+=1
        counts[name]=dict(arbitrary_windows=len(batch),image_pixels_with_control_and_boundary=image_checks,
                          protected_windows=int(keep.sum()))
    quality=json.loads((R/'candidate-quality.json').read_text(encoding='utf-8'))
    assert quality['result']=='SYNTHETIC_GATE_FAIL' and quality['selected_candidate'] is None
    saved=[]
    # Preserve the exact correlated-noise failures that gate off RTL generation.
    for name in CANDIDATES:
        for amp,seed,gray in noise_fixtures():
            for axis in (0,1):
                p=np.pad(gray,1,mode='edge')
                smooth=((p[:-2,1:-1]+2*gray+p[2:,1:-1]) if axis==0 else
                        (p[1:-1,:-2]+2*gray+p[1:-1,2:]))//4
                old=baseline(smooth,1);new=image_math(smooth,name);roi=(slice(2,-2),slice(2,-2))
                row=next(q for q in quality['candidates'][name]['correlated_noise']
                         if q['amplitude']==amp and q['seed']==seed and q['axis']==axis)
                assert int(old['edge'][roi].sum())==row['old_edges'] and int(new['edge'][roi].sum())==row['new_edges']
                if row['new_edges']<=row['old_edges']:continue
                vv,kk=median_detail(smooth,*CANDIDATES[name]);ww=windows(smooth)
                for yy,xx in np.argwhere(kk):
                    value,flag=scalar_window(ww[yy,xx],int(xx),int(yy),256,128,*CANDIDATES[name])
                    assert flag and value==vv[yy,xx]
                target=R/f'{name}-correlated-amp{amp}-seed{seed}-axis{axis}.npz'
                np.savez_compressed(target,source_gray=gray,gray=smooth,old_median=old['median'],new_median=new['median'],
                                    detail_keep=new['detail_keep'],old_seed=old['seed'],new_seed=new['seed'],
                                    old_edge=old['edge'],new_edge=new['edge'])
                saved.append(dict(path=str(target),sha256=sha(target),**row,candidate=name))
    record=dict(result='SCALAR_VECTOR_AGREE_FAILURE_CONFIRMED',cases=counts,correlated_failure_inputs=saved,
                source_sha256={str(p):sha(p) for p in (Path(__file__),W/'tests/reference_median_detail.py')},
                quality_sha256=sha(R/'candidate-quality.json'),rtl_checked=False,hardware_checked=False)
    (R/'reference-verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(dict(result=record['result'],cases=counts,correlated_failures=len(saved)),indent=2))


if __name__=='__main__':main()
