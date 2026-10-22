"""Approved v3 fixed fixtures, geometry, separation, inclusion and noise gates."""
from pathlib import Path
import hashlib, json
import numpy as np
from quality_candidates import fixtures as old_fixtures, noise_fixtures, geometry_quality
from reference_v3 import CANDIDATES, image_math, windows
from reference_v2 import image_math as baseline_math

W = Path(__file__).resolve().parents[1]
R = W.parents[2] / 'reports/TRACK4-V7-LOWLIGHT-EDGE-003'
LIMITS = {8: 0, 16: 58, 24: 3304}

def fixtures():
    # Preserve v2 geometry, masks and metric; vary only the approved contrasts.
    originals = [item for item in old_fixtures() if item['delta'] == 64]
    for delta in (14, 15, 16, 17, 18, 19, 20, 24, 25, 64):
        for original in originals:
            yield {**original, 'name': f"{original['kind']}-d{delta}", 'delta': delta,
                   'gray': 32 + (original['gray'] > 32).astype(np.int32)*delta}

def main():
    metrics = {}
    for name, (d, drop) in CANDIDATES.items():
        data = dict(shapes=[], noise=[], noise_totals=[], failures=[], target_delta=d)
        for item in fixtures():
            old = baseline_math(item['gray'], 64, 20)['edge']
            new = image_math(item['gray'], 64, d, drop)['edge']
            assert not (old & ~new).any(), 'v2 edge inclusion'
            old_geom, new_geom = geometry_quality(item, old), geometry_quality(item, new)
            row = dict(name=item['name'], kind=item['kind'], delta=item['delta'],
                       old_geometry=old_geom, new_geometry=new_geom,
                       old_off_band=int((old & ~item['truth'] & item['interior']).sum()),
                       new_off_band=int((new & ~item['truth'] & item['interior']).sum()))
            data['shapes'].append(row)
            if item['delta'] == d and item['kind'] in ('vertical', 'horizontal', 'rectangle'):
                if new_geom['covered'] <= old_geom['covered']:
                    data['failures'].append(item['name']+': weak geometry did not improve')
            if item['delta'] == 64 and (new_geom['covered'] != new_geom['points'] or
                    new_geom['complete_connected_contours'] != new_geom['expected_contours']):
                data['failures'].append(item['name']+': strong geometry missing/disconnected')
            if row['new_off_band'] > row['old_off_band']:
                data['failures'].append(item['name']+': off-band edges increased')
        for amp, seed, gray in noise_fixtures():
            old = baseline_math(gray, 64, 20)['edge'][2:-2, 2:-2]
            new = image_math(gray, 64, d, drop)['edge'][2:-2, 2:-2]
            assert not (old & ~new).any()
            data['noise'].append(dict(amplitude=amp, seed=seed, pixels=int(new.size),
                                     old_false_edges=int(old.sum()), new_false_edges=int(new.sum())))
        for amp in LIMITS:
            rows = [r for r in data['noise'] if r['amplitude'] == amp]
            total = dict(amplitude=amp, old_false_edges=sum(r['old_false_edges'] for r in rows),
                         new_false_edges=sum(r['new_false_edges'] for r in rows),
                         pixels=sum(r['pixels'] for r in rows), limit=LIMITS[amp])
            assert total['pixels'] == 93744
            assert total['old_false_edges'] == {8:0,16:49,24:2754}[amp]
            if total['new_false_edges'] > LIMITS[amp]:
                data['failures'].append(f'noise amplitude {amp}: exceeds fixed limit')
            data['noise_totals'].append(total)
        y, x = np.indices((48, 64))
        stripes = 32 + (((x >= 20) & (x <= 22) | (x >= 26) & (x <= 28)) & (y >= 8) & (y <= 39))*d
        edge = image_math(stripes, 64, d, drop)['edge'][24]
        positions = np.flatnonzero(edge).tolist()
        # Four non-touching boundary bands, with line centres and gap clear.
        separated = all(edge[left:right+1].any() for left,right in ((19,20),(22,23),(25,26),(28,29))) and not edge[[21,24,27]].any()
        data['parallel_stripes'] = dict(edge_x_at_y24=positions, separated=bool(separated), target_delta=d)
        if not separated: data['failures'].append('parallel thin contours merged/missing')
        impulse = np.full((48,64),64,dtype=np.int32);impulse[20,20]=255;impulse[30,40]=0
        data['salt_pepper_edges'] = int(image_math(impulse,64,d,drop)['edge'].sum())
        if data['salt_pepper_edges']: data['failures'].append('salt/pepper survived')
        data['extra_weak_geometry_coverage'] = sum(row['new_geometry']['covered']-row['old_geometry']['covered']
            for row in data['shapes'] if row['delta'] in (16,18,19))
        data['noise_sum'] = sum(row['new_false_edges'] for row in data['noise_totals'])
        data['eligible'] = not data['failures']
        metrics[name] = data
    eligible = [name for name in metrics if metrics[name]['eligible']]
    chosen = min(eligible,key=lambda name:(-metrics[name]['extra_weak_geometry_coverage'],metrics[name]['noise_sum'],name!='B')) if eligible else None
    result = dict(result='SYNTHETIC_GATE_PASS' if chosen else 'SYNTHETIC_GATE_FAIL',selected_candidate=chosen,
                  candidates=metrics,synthetic_only=True,real_camera_accuracy_measured=False,
                  source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      [Path(__file__),W/'tests/reference_v3.py',W/'tests/reference_v2.py',W/'tests/quality_candidates.py']})
    (R/'candidate-quality.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(result=result['result'],selected_candidate=chosen,candidates={name:{k:v for k,v in m.items() if k not in ('shapes','noise')} for name,m in metrics.items()}),indent=2),flush=True)
    if not chosen:raise SystemExit(2)
    return result

if __name__ == '__main__':main()
