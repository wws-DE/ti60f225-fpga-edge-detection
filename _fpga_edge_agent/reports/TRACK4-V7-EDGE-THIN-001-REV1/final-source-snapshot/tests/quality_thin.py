"""Approved thinning v1 A/B quality gates; preserve existing geometric coverage."""
from pathlib import Path
import hashlib
import json
import numpy as np
from quality_v3 import fixtures
from quality_candidates import noise_fixtures, geometry_quality, components
from reference_thin import CANDIDATES, image_math
from reference_v3 import windows

W = Path(__file__).resolve().parents[1]
R = W.parents[2] / 'reports/TRACK4-V7-EDGE-THIN-001'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def extra_fixtures():
    y, x = np.indices((48, 64))
    masks = dict(negative_diagonal=x-y >= 8, staircase=x >= 16+3*(y//4),
                 t_junction=((abs(x-32) <= 1) & (y >= 12) & (y <= 38)) |
                            ((abs(y-12) <= 1) & (x >= 16) & (x <= 48)),
                 y_junction=((abs(x-31) <= 1) & (y >= 24) & (y <= 40)) |
                            ((abs(abs(x-31)-(24-y)) <= 1) & (y >= 10) & (y <= 24)),
                 cross=((abs(x-31) <= 1) & (y >= 10) & (y <= 38)) |
                       ((abs(y-24) <= 1) & (x >= 14) & (x <= 49)),
                 corner=((x >= 16) & (x <= 18) & (y >= 12) & (y <= 36)) |
                        ((y >= 34) & (y <= 36) & (x >= 16) & (x <= 48)))
    for delta in (18, 64):
        for name, mask in masks.items():
            neighbors = windows(mask.astype(np.int32), 2)
            truth = neighbors.max(axis=(-2, -1)) != neighbors.min(axis=(-2, -1))
            interior = (x >= 2) & (x < 62) & (y >= 2) & (y < 46)
            yield dict(name=f'{name}-d{delta}', kind=name, delta=delta, gray=32+mask*delta,
                       truth=truth, interior=interior)


def compare_shape(item, mode, require_component_preservation=False):
    model = image_math(item['gray'], mode)
    old, new = model['v41_edge'], model['edge']
    assert not (new & ~old).any()
    a, b = geometry_quality(item, old), geometry_quality(item, new)
    off = ~item['truth'] & item['interior']
    fragmented = []
    if require_component_preservation:
        for index, old_part in enumerate(components(old & item['interior'])):
            parts = components(new & old_part)
            if len(parts) != 1:
                fragmented.append(dict(old_component=index, old_pixels=int(old_part.sum()), new_parts=len(parts)))
    return dict(name=item['name'], kind=item['kind'], delta=item['delta'], old_geometry=a, new_geometry=b,
                old_count=int((old & item['interior']).sum()), new_count=int((new & item['interior']).sum()),
                old_off_band=int((old & off).sum()), new_off_band=int((new & off).sum()), fragmented=fragmented)


def main():
    candidates = {}
    for name, mode in CANDIDATES.items():
        result = dict(mode=mode, old_shapes=[], extra_shapes=[], noise=[], correlated_noise=[],
                      steps=[], parallel_stripes=[], failures=[])
        fail = result['failures'].append
        for item in fixtures():
            row = compare_shape(item, mode)
            result['old_shapes'].append(row)
            a, b = row['old_geometry'], row['new_geometry']
            if b['covered'] < a['covered'] or b['complete_connected_contours'] < a['complete_connected_contours']:
                fail(item['name']+': geometry/complete contour regressed')
            if item['delta'] == 64 and (b['covered'] != b['points'] or b['complete_connected_contours'] != b['expected_contours']):
                fail(item['name']+': high contrast geometry incomplete')
        for item in extra_fixtures():
            row = compare_shape(item, mode, True)
            result['extra_shapes'].append(row)
            a, b = row['old_geometry'], row['new_geometry']
            if b['covered'] < a['covered'] or b['complete_connected_contours'] < a['complete_connected_contours'] or row['fragmented']:
                fail(item['name']+': geometry/connected part regressed')
        for delta in (18, 64):
            for axis in (0, 1):
                for reverse in (False, True):
                    y, x = np.indices((48, 64))
                    mask = y >= 24 if axis == 0 else x >= 32
                    gray = 32+np.logical_xor(mask, reverse)*delta
                    model = image_math(gray, mode)
                    old_line = model['v41_edge'][:, 24] if axis == 0 else model['v41_edge'][24]
                    new_line = model['edge'][:, 24] if axis == 0 else model['edge'][24]
                    expected = 23 if axis == 0 else 31
                    row = dict(delta=delta, axis=axis, reversed=reverse,
                               old_positions=np.flatnonzero(old_line).tolist(), new_positions=np.flatnonzero(new_line).tolist(),
                               expected_single_peak=expected)
                    result['steps'].append(row)
                    if len(row['old_positions']) != 2 or row['new_positions'] != [expected]:
                        fail(f'axis step {delta}/{axis}/{reverse}: not single correctly localized peak')
        for amplitude, seed, gray in noise_fixtures():
            roi = (slice(2, -2), slice(2, -2))
            model = image_math(gray, mode)
            assert not (model['edge'] & ~model['v41_edge']).any()
            result['noise'].append(dict(amplitude=amplitude, seed=seed, pixels=int(model['edge'][roi].size),
                                        old_false_edges=int(model['v41_edge'][roi].sum()), new_false_edges=int(model['edge'][roi].sum())))
            for axis in (0, 1):
                p = np.pad(gray, 1, mode='edge')
                smoothed = ((p[:-2, 1:-1]+2*gray+p[2:, 1:-1]) if axis == 0
                            else (p[1:-1, :-2]+2*gray+p[1:-1, 2:]))//4
                m = image_math(smoothed, mode)
                assert not (m['edge'] & ~m['v41_edge']).any()
                result['correlated_noise'].append(dict(amplitude=amplitude, seed=seed, axis=axis,
                    old_false_edges=int(m['v41_edge'][roi].sum()), new_false_edges=int(m['edge'][roi].sum())))
        result['noise_totals'] = []
        for amplitude, limit in {8: 0, 16: 50, 24: 2843}.items():
            rows = [row for row in result['noise'] if row['amplitude'] == amplitude]
            old, new = sum(row['old_false_edges'] for row in rows), sum(row['new_false_edges'] for row in rows)
            assert old == limit and sum(row['pixels'] for row in rows) == 93744
            result['noise_totals'].append(dict(amplitude=amplitude, old_false_edges=old, new_false_edges=new, limit=limit, pixels=93744))
            if new > limit:
                fail(f'noise amplitude{amplitude}: fixed cap exceeded')
        y, x = np.indices((48, 64))
        for delta in (18, 64):
            gray = 32+(((x >= 20) & (x <= 22) | (x >= 26) & (x <= 28)) & (y >= 8) & (y <= 39))*delta
            line = image_math(gray, mode)['edge'][24]
            separated = all(line[left:right+1].any() for left, right in ((19, 20), (22, 23), (25, 26), (28, 29))) and not line[[21, 24, 27]].any()
            result['parallel_stripes'].append(dict(delta=delta, positions=np.flatnonzero(line).tolist(), separated=bool(separated)))
            if not separated:
                fail(f'parallel stripes delta{delta}: boundary merged/missing')
        impulse = np.full((48, 64), 64, dtype=np.int32)
        impulse[20, 20], impulse[30, 40] = 255, 0
        result['salt_pepper_edges'] = int(image_math(impulse, mode)['edge'].sum())
        if result['salt_pepper_edges']:
            fail('salt/pepper survived')
        result['diagonal_reduction'] = sum(row['old_count']-row['new_count'] for row in result['old_shapes']
            if row['kind'] == 'diagonal' and row['delta'] == 64)
        result['eligible'] = not result['failures']
        candidates[name] = result
    if candidates['A']['eligible'] and candidates['A']['diagonal_reduction'] > 0:
        selected = 'A'
    elif candidates['B']['eligible']:
        selected = 'B'
    else:
        selected = None
    files = [Path(__file__), W/'tests/reference_thin.py', W/'tests/reference_v41.py', W/'tests/reference_v4.py',
             W/'tests/reference_v3.py', W/'tests/reference_v2.py', W/'tests/quality_v3.py', W/'tests/quality_candidates.py']
    report = dict(result='SYNTHETIC_GATE_PASS' if selected else 'SYNTHETIC_GATE_FAIL', selected_candidate=selected,
                  candidates=candidates, approved_gates_unchanged=True, synthetic_only=True,
                  rtl_checked=False, hardware_checked=False, source_sha256={str(p): sha(p) for p in files})
    (R/'candidate-quality.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(result=report['result'], selected_candidate=selected, candidates={key: {
        k: value[k] for k in ('eligible', 'diagonal_reduction', 'noise_totals', 'steps', 'failures')
    } for key, value in candidates.items()}), indent=2), flush=True)
    if not selected:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
