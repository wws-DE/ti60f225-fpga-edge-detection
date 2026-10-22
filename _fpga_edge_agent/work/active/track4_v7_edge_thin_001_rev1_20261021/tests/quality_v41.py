"""Approved v4 fixed A/B quality gate; do not relax after seeing results."""
from pathlib import Path
import hashlib,json
import numpy as np
from quality_v3 import fixtures
from quality_candidates import noise_fixtures,geometry_quality
from reference_v41 import CANDIDATES,image_math
from reference_v4 import context_image

W=Path(__file__).resolve().parents[1];R=W.parents[2]/'reports/TRACK4-V7-LOWLIGHT-EDGE-004-REV1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    core=json.loads((R/'diagonal-core-result.json').read_text(encoding='utf-8'))
    assert core['result']=='PASS'
    assert all(sha(Path(p))==h for p,h in core['sources'].items())
    candidates={}
    for name,drop in CANDIDATES.items():
        data=dict(diagonal_min_diff=drop,shapes=[],noise=[],noise_totals=[],failures=[],improved_weak_shapes=[])
        for item in fixtures():
            if item['delta'] not in (17,18,19,20,24,25,64):continue
            m=image_math(item['gray'],64,drop);old,new=m['v3_edge'],m['edge']
            a,b=geometry_quality(item,old),geometry_quality(item,new)
            row=dict(name=item['name'],kind=item['kind'],delta=item['delta'],old_geometry=a,new_geometry=b,
                added=int(m['added'].sum()),removed=int(m['removed'].sum()),
                old_off_band=int((old&~item['truth']&item['interior']).sum()),
                new_off_band=int((new&~item['truth']&item['interior']).sum()))
            data['shapes'].append(row)
            if item['delta']==64 and (b['covered']!=b['points'] or b['complete_connected_contours']!=b['expected_contours']):
                data['failures'].append(item['name']+': strong geometry lost or fragmented')
            if item['kind'] in ('horizontal','vertical','rectangle') and b['covered']<a['covered']:
                data['failures'].append(item['name']+': weak orthogonal geometry coverage fell')
            if item['delta'] in (18,19) and item['kind'] in ('diagonal','curve') and (
                    b['covered']>a['covered'] or b['complete_connected_contours']>a['complete_connected_contours']):
                data['improved_weak_shapes'].append(item['name'])
            if row['new_off_band']>row['old_off_band']:
                data['failures'].append(item['name']+': off-band response increased')
        if not data['improved_weak_shapes']:
            data['failures'].append('No required delta18/19 diagonal/curve geometry improvement')
        for amp,seed,gray in noise_fixtures():
            m=image_math(gray,64,drop);roi=(slice(2,-2),slice(2,-2))
            data['noise'].append(dict(amplitude=amp,seed=seed,pixels=int(m['edge'][roi].size),
                old_false_edges=int(m['v3_edge'][roi].sum()),new_false_edges=int(m['edge'][roi].sum()),
                added=int(m['added'][roi].sum()),removed=int(m['removed'][roi].sum())))
        for amp in (8,16,24):
            rows=[row for row in data['noise'] if row['amplitude']==amp]
            total=dict(amplitude=amp,pixels=sum(row['pixels'] for row in rows),
                old_false_edges=sum(row['old_false_edges'] for row in rows),new_false_edges=sum(row['new_false_edges'] for row in rows),
                added=sum(row['added'] for row in rows),removed=sum(row['removed'] for row in rows))
            assert total['pixels']==93744 and total['old_false_edges']=={8:0,16:56,24:2885}[amp]
            assert total['new_false_edges']==total['old_false_edges']+total['added']-total['removed']
            if total['new_false_edges']>total['old_false_edges']:
                data['failures'].append(f'noise amplitude {amp}: false edges increased')
            data['noise_totals'].append(total)
        if not any(row['new_false_edges']<row['old_false_edges'] for row in data['noise_totals'] if row['amplitude']!=8):
            data['failures'].append('No required strict noise reduction')
        y,x=np.indices((48,64));stripes=[]
        for delta in (18,64):
            gray=32+(((x>=20)&(x<=22)|(x>=26)&(x<=28))&(y>=8)&(y<=39))*delta
            e=image_math(gray,64,drop)['edge'][24]
            separated=all(e[left:right+1].any() for left,right in ((19,20),(22,23),(25,26),(28,29))) and not e[[21,24,27]].any()
            stripes.append(dict(delta=delta,edge_x_at_y24=np.flatnonzero(e).tolist(),separated=bool(separated)))
            if not separated:data['failures'].append(f'parallel stripes delta{delta}: merged/missing')
        data['parallel_stripes']=stripes
        impulse=np.full((48,64),64,dtype=np.int32);impulse[20,20]=255;impulse[30,40]=0
        data['salt_pepper_edges']=int(image_math(impulse,64,drop)['edge'].sum())
        if data['salt_pepper_edges']:data['failures'].append('salt/pepper edges survived')
        # These are explicit post-Sobel seed semantics, not claims about a camera dot.
        one=np.zeros((7,8),dtype=np.uint16);one[3,3]=2048|1024
        two=one.copy();two[3,4]=2048|1024
        assert context_image(one)['edge'].sum()==0 and context_image(two)['edge'].sum()==2
        data['post_seed_small_features']=dict(isolated_single_removed=True,adjacent_two_preserved=True,scope='post-Sobel seed map')
        data['weak_geometry_gain']=sum(row['new_geometry']['covered']-row['old_geometry']['covered']+
            row['new_geometry']['complete_connected_contours']-row['old_geometry']['complete_connected_contours']
            for row in data['shapes'] if row['delta'] in (18,19))
        data['noise_sum']=sum(row['new_false_edges'] for row in data['noise_totals'])
        data['eligible']=not data['failures'];candidates[name]=data
    eligible=[k for k in candidates if candidates[k]['eligible']]
    selected=min(eligible,key=lambda k:(-candidates[k]['weak_geometry_gain'],candidates[k]['noise_sum'],k!='B')) if eligible else None
    result=dict(result='SYNTHETIC_GATE_PASS' if selected else 'SYNTHETIC_GATE_FAIL',selected_candidate=selected,candidates=candidates,
        synthetic_only=True,real_camera_accuracy_measured=False,approved_gates_unchanged=True,
        source_sha256={str(p):sha(p) for p in [Path(__file__),W/'tests/reference_v41.py',W/'tests/reference_v4.py',W/'tests/reference_v3.py',W/'tests/reference_v2.py',W/'tests/quality_v3.py',W/'tests/quality_candidates.py']},
        context_core_result_sha256=sha(R/'diagonal-core-result.json'))
    (R/'candidate-quality.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(result=result['result'],selected_candidate=selected,candidates={k:{key:d[key] for key in ('eligible','improved_weak_shapes','weak_geometry_gain','noise_totals','failures')} for k,d in candidates.items()}),indent=2),flush=True)
    if not selected:raise SystemExit(2)
    return result

if __name__=='__main__':main()
