"""Inspect the failed, already approved fixtures; no new algorithm/candidate."""
from pathlib import Path
import hashlib,json
import numpy as np
from quality_v3 import fixtures
from reference_v3 import image_math,windows

W=Path(__file__).resolve().parents[1];R=W.parents[2]/'reports/TRACK4-V7-LOWLIGHT-EDGE-004'
rows=[]
for item in fixtures():
    if item['delta'] not in (18,19) or item['kind'] not in ('diagonal','curve'):continue
    m=image_math(item['gray'],64,18,0)
    roi=item['interior']&item['truth'];missing=roi&(m['l1']>64)&~m['edge']
    candidates=np.argwhere(missing)
    example=None
    if len(candidates):
        y,x=map(int,candidates[len(candidates)//2]);a=windows(m['median'])[y,x]
        dx=a[:,2]-a[:,0];dy=a[2,:]-a[0,:]
        example=dict(x=x,y=y,median_window=a.tolist(),gx=int(m['gx'][y,x]),gy=int(m['gy'][y,x]),l1=int(m['l1'][y,x]),
            row_differences=dx.tolist(),column_differences=dy.tolist(),v3_seed=bool(m['edge'][y,x]),
            interpretation='L1 passed64 but per-row/column coherence gate rejected; postprocessing cannot create a seed where the whole diagonal lacks seeds')
    rows.append(dict(name=item['name'],threshold_only_in_band=int(((m['l1']>64)&roi).sum()),
        v3_seed_in_band=int((m['edge']&roi).sum()),rejected_despite_l1=int(missing.sum()),example=example))
result=dict(scope='Only original approved delta18/19 diagonal/curve fixtures and unchanged v3 reference',rows=rows,
    candidate_quality_sha256=hashlib.sha256((R/'candidate-quality.json').read_bytes()).hexdigest(),
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    real_camera_cause_proven=False,algorithm_parameters_changed=False)
(R/'failure-diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
