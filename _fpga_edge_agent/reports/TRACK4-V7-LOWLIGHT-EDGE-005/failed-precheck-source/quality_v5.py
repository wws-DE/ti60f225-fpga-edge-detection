"""Frozen approved v5 A/B quality gates; run before spending RTL/build time."""
from pathlib import Path
import hashlib
import json
import numpy as np
from quality_v3 import fixtures
from quality_candidates import noise_fixtures, geometry_quality
from reference_v41 import image_math as baseline_math
from reference_v5 import CANDIDATES, image_math, blur_image

W = Path(__file__).resolve().parents[1]
R = W.parents[2] / 'reports/TRACK4-V7-LOWLIGHT-EDGE-005'
BASELINE_LIMITS = {8: 0, 16: 50, 24: 2843}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def comparison(item, actual_gray, drop):
    old = baseline_math(actual_gray, 64, 18)['edge']
    new = image_math(actual_gray, 64, drop)['edge']
    a, b = geometry_quality(item, old), geometry_quality(item, new)
    off = ~item['truth'] & item['interior']
    return dict(name=item['name'], kind=item['kind'], delta=item['delta'],
                old_geometry=a, new_geometry=b, old_off_band=int((old & off).sum()),
                new_off_band=int((new & off).sum()),
                gain=b['covered'] - a['covered'] + b['complete_connected_contours'] - a['complete_connected_contours'])


def main():
    candidates = {}
    originals = [item for item in fixtures() if item['delta'] == 64]
    for candidate, drop in CANDIDATES.items():
        result = dict(drop=drop, low_threshold=64-drop, old_shapes=[], weak_shapes=[],
                      blurred_shapes=[], noise=[], correlated_noise=[], noisy_weak=[],
                      failures=[], parallel_stripes=[])
        fail = result['failures'].append
        for item in fixtures():
            row = comparison(item, item['gray'], drop)
            result['old_shapes'].append(row)
            a, b = row['old_geometry'], row['new_geometry']
            if b['covered'] < a['covered'] or b['complete_connected_contours'] < a['complete_connected_contours']:
                fail(item['name'] + ': existing geometric coverage/connectivity regressed')
            if item['delta'] == 64 and (b['covered'] != b['points'] or b['complete_connected_contours'] != b['expected_contours']):
                fail(item['name'] + ': high contrast geometry lost or fragmented')
            if row['new_off_band'] > row['old_off_band']:
                fail(item['name'] + ': off-band responses increased')
        for background in (16, 32, 64):
            for delta in (8, 10, 12, 16):
                for original in originals:
                    mask = original['gray'] > 32
                    # Geometric truth stays tied to the unblurred shape, never brightness >32.
                    item = {**original, 'name': f"{original['kind']}-bg{background}-d{delta}",
                            'delta': delta, 'gray': 32 + mask.astype(np.int32)*delta}
                    gray = background + mask.astype(np.int32)*delta
                    row = comparison(item, gray, drop)
                    result['weak_shapes'].append(row)
                    if row['new_off_band'] > row['old_off_band']:
                        fail(item['name'] + ': new weak off-band responses increased')
                    for weights in ((1, 2, 1), (1, 4, 6, 4, 1)):
                        blurred = comparison(item, blur_image(gray, weights), drop)
                        blurred['kernel'] = list(weights)
                        result['blurred_shapes'].append(blurred)
                        if blurred['new_off_band'] > blurred['old_off_band']:
                            fail(item['name'] + f': blur{len(weights)} off-band responses increased')
        for kind in ('horizontal', 'vertical'):
            if not any(row['delta'] == 12 and row['kind'] == kind and row['gain'] > 0 for row in result['weak_shapes']):
                fail('delta12 ' + kind + ': required weak geometry improvement absent')
        if not any(row['delta'] == 12 and row['kind'] in ('diagonal', 'curve') and row['gain'] > 0 for row in result['weak_shapes']):
            fail('delta12 diagonal/curve: required weak geometry improvement absent')
        if not any(row['gain'] > 0 for row in result['blurred_shapes']):
            fail('No required blurred weak geometry improvement')
        for amplitude, seed, gray in noise_fixtures():
            roi = (slice(2, -2), slice(2, -2))
            old = baseline_math(gray, 64, 18)['edge'][roi]
            new = image_math(gray, 64, drop)['edge'][roi]
            result['noise'].append(dict(amplitude=amplitude, seed=seed, pixels=int(old.size),
                                        old_false_edges=int(old.sum()), new_false_edges=int(new.sum())))
            for axis in (0, 1):
                p = np.pad(gray, 1, mode='edge')
                smoothed = ((p[:-2, 1:-1]+2*gray+p[2:, 1:-1]) if axis == 0
                            else (p[1:-1, :-2]+2*gray+p[1:-1, 2:])) // 4
                a = baseline_math(smoothed, 64, 18)['edge'][roi]
                b = image_math(smoothed, 64, drop)['edge'][roi]
                row = dict(amplitude=amplitude, seed=seed, axis=axis, pixels=int(a.size),
                           old_false_edges=int(a.sum()), new_false_edges=int(b.sum()))
                result['correlated_noise'].append(row)
        result['noise_totals'] = []
        for amp, limit in BASELINE_LIMITS.items():
            rows = [row for row in result['noise'] if row['amplitude'] == amp]
            a, b = sum(row['old_false_edges'] for row in rows), sum(row['new_false_edges'] for row in rows)
            assert sum(row['pixels'] for row in rows) == 93744 and a == limit
            result['noise_totals'].append(dict(amplitude=amp, old_false_edges=a, new_false_edges=b, limit=limit, pixels=93744))
            if b > limit:
                fail(f'noise amplitude {amp}: {b} > approved v4.1 cap {limit}')
            for axis in (0, 1):
                rows = [row for row in result['correlated_noise'] if row['amplitude'] == amp and row['axis'] == axis]
                a, b = sum(row['old_false_edges'] for row in rows), sum(row['new_false_edges'] for row in rows)
                if b > a:
                    fail(f'correlated noise amplitude {amp} axis {axis}: {b} > v4.1 {a}')
        for original in originals:
            item = {**original, 'name': original['kind']+'-d12-noise4', 'delta': 12,
                    'gray': 32 + (original['gray'] > 32).astype(np.int32)*12}
            rng = np.random.default_rng(431)
            gray = item['gray'] + rng.integers(-4, 5, item['gray'].shape)
            row = comparison(item, gray, drop)
            result['noisy_weak'].append(row)
            if row['new_off_band'] > row['old_off_band']:
                fail(item['name'] + ': noisy weak background responses increased')
        if not any(row['gain'] > 0 for row in result['noisy_weak']):
            fail('No required noisy weak geometry improvement')
        y, x = np.indices((48, 64))
        for delta in (18, 64):
            gray = 32 + (((x >= 20) & (x <= 22) | (x >= 26) & (x <= 28)) & (y >= 8) & (y <= 39))*delta
            line = image_math(gray, 64, drop)['edge'][24]
            separated = all(line[left:right+1].any() for left, right in ((19, 20), (22, 23), (25, 26), (28, 29))) and not line[[21, 24, 27]].any()
            result['parallel_stripes'].append(dict(delta=delta, edge_positions=np.flatnonzero(line).tolist(), separated=bool(separated)))
            if not separated:
                fail(f'parallel stripes delta{delta}: missing/merged boundaries')
        impulse = np.full((48, 64), 64, dtype=np.int32)
        impulse[20, 20], impulse[30, 40] = 255, 0
        result['salt_pepper_edges'] = int(image_math(impulse, 64, drop)['edge'].sum())
        if result['salt_pepper_edges']:
            fail('salt/pepper survived')
        result['weak_geometry_gain'] = sum(row['gain'] for row in result['weak_shapes'])
        result['noise_sum'] = sum(row['new_false_edges'] for row in result['noise'] + result['correlated_noise'])
        result['eligible'] = not result['failures']
        candidates[candidate] = result
    eligible = [key for key, result in candidates.items() if result['eligible']]
    chosen = min(eligible, key=lambda k: (-candidates[k]['weak_geometry_gain'], candidates[k]['noise_sum'], k != 'B')) if eligible else None
    files = [Path(__file__), W/'tests/reference_v5.py', W/'tests/reference_v41.py', W/'tests/reference_v4.py',
             W/'tests/reference_v3.py', W/'tests/reference_v2.py', W/'tests/quality_v3.py', W/'tests/quality_candidates.py']
    report = dict(result='SYNTHETIC_GATE_PASS' if chosen else 'SYNTHETIC_GATE_FAIL', selected_candidate=chosen,
                  phase='mathematical feasibility before RTL', candidates=candidates, approved_gates_unchanged=True,
                  rtl_checked=False, hardware_checked=False, synthetic_only=True,
                  source_sha256={str(p): sha(p) for p in files})
    (R/'candidate-quality.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(result=report['result'], selected_candidate=chosen, candidates={key: {
        k: result[k] for k in ('low_threshold', 'eligible', 'weak_geometry_gain', 'noise_totals', 'failures')
    } for key, result in candidates.items()}), indent=2), flush=True)
    if not chosen:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
