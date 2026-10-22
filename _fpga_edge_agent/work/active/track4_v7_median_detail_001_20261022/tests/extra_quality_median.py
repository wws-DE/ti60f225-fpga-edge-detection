"""Complete approved remaining geometry checks for A; no noise exception here."""
from pathlib import Path
import json, hashlib
import numpy as np
from reference_median_detail import image_math
from reference_thin_v11 import image_math as old_math
from reference_v2 import windows
from quality_candidates import geometry_quality

W=Path(__file__).resolve().parents[1];R=W.parents[2]/'reports/TRACK4-V7-MEDIAN-DETAIL-001'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
y,x=np.indices((48,64));inside=(x>=4)&(x<60)&(y>=4)&(y<44)


def main():
    results=[];failures=[]
    # Positions/widths, bends, branches and short strokes; bright/dark are symmetric.
    for shift in (0,1):
        xx=x-shift
        for width in (1,2):
            line=(xx>=30)&(xx<30+width)&(y>=10)&(y<=38)
            bar=(y>=24)&(y<24+width)&(xx>=16)&(xx<=49)
            masks=dict(line=line,negative_diagonal=(xx-y>=8)&(xx-y<8+width)&(y>=10)&(y<=38),
                corner=line|((y>=36)&(y<36+width)&(xx>=30)&(xx<=48)),cross=line|bar,
                t=line|((y>=10)&(y<10+width)&(xx>=16)&(xx<=48)),
                y=line|(abs(abs(xx-30)-(24-y))<width)&(y>=10)&(y<=24),
                text=line|((y>=10)&(y<10+width)|(y>=22)&(y<22+width)|(y>=36)&(y<36+width))&(xx>=30)&(xx<=44),
                short=(xx>=30)&(xx<30+width)&(y>=20)&(y<=24))
            for kind,mask in masks.items():
                neighborhood=windows(mask.astype(np.int32),2)
                truth=neighborhood.max(axis=(-2,-1))!=neighborhood.min(axis=(-2,-1))
                item=dict(kind=kind,gray=32+mask*64,truth=truth,interior=inside)
                for delta in (18,20,32,64):
                    for polarity in (-1,1):
                        for amplitude in (0,2,4):
                            noise=np.random.default_rng(431).integers(-amplitude,amplitude+1,mask.shape)
                            gray=96+polarity*delta*mask+noise
                            old=old_math(gray,1);new=image_math(gray,'A')
                            a,b=geometry_quality(item,old['edge']),geometry_quality(item,new['edge'])
                            off=~truth&inside
                            row=dict(kind=kind,shift=shift,width=width,delta=delta,polarity=polarity,noise=amplitude,
                                old_covered=a['covered'],new_covered=b['covered'],old_contours=a['complete_connected_contours'],
                                new_contours=b['complete_connected_contours'],old_off=int((old['edge']&off).sum()),new_off=int((new['edge']&off).sum()))
                            results.append(row)
                            if row['new_covered']<row['old_covered'] or row['new_contours']<row['old_contours'] or row['new_off']>row['old_off']:
                                failures.append(row)
    separation=[]
    for delta in (18,64):
        gray=32+(((x>=20)&(x<=22)|(x>=26)&(x<=28))&(y>=8)&(y<=39))*delta
        line=image_math(gray,'A')['edge'][24]
        separated=all(line[l:r+1].any() for l,r in ((19,20),(22,23),(25,26),(28,29))) and not line[[21,24,27]].any()
        separation.append(dict(delta=delta,positions=np.flatnonzero(line).tolist(),separated=bool(separated)))
        if not separated:failures.append({'separation_delta':delta})
    result=dict(result='PASS' if not failures else 'FAIL',candidate='A',cases=len(results),results=results,
        parallel_stripes=separation,failures=failures,source_sha256={str(p):sha(p) for p in (Path(__file__),W/'tests/reference_median_detail.py')})
    (R/'extra-quality.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','source_sha256')},indent=2))
    if failures:raise SystemExit(2)


if __name__=='__main__':main()
