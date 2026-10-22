"""Fixed approved median-detail quality gates; no RTL/build on failure."""
from pathlib import Path
import hashlib, json
import numpy as np
from reference_median_detail import CANDIDATES, image_math, downstream, median_detail
from reference_thin_v11 import image_math as baseline
from reference_v2 import median_image, windows
from quality_v3 import fixtures
from quality_thin_v11 import extra_fixtures
from quality_candidates import noise_fixtures, geometry_quality, components

W = Path(__file__).resolve().parents[1]
R = W.parents[2]/'reports/TRACK4-V7-MEDIAN-DETAIL-001'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def geometry(item, old, new):
    a, b = geometry_quality(item, old), geometry_quality(item, new)
    off = ~item['truth'] & item['interior']
    return dict(name=item['name'], old_geometry=a, new_geometry=b,
                old_off=int((old & off).sum()), new_off=int((new & off).sum()),
                old_count=int((old & item['interior']).sum()), new_count=int((new & item['interior']).sum()))


def fine_fixtures():
    y, x = np.indices((48, 64))
    interior = (x >= 4) & (x < 60) & (y >= 4) & (y < 44)
    for background in (16, 24, 96, 224):
        for polarity in (-1, 1):
            for delta in (16, 18, 20, 32, 64):
                if not 0 <= background+polarity*delta <= 255:
                    continue
                for direction, distance in enumerate((x-32, x-y-8, y-24, x+y-56)):
                    for width in (1, 2):
                        mask = (distance >= 0) & (distance < width) & (x >= 10) & (x <= 53) & (y >= 8) & (y <= 39)
                        gray = background+polarity*delta*mask.astype(np.int32)
                        n = windows(mask.astype(np.int32), 2)
                        truth = n.max(axis=(-2, -1)) != n.min(axis=(-2, -1))
                        yield dict(name=f'fine-bg{background}-p{polarity}-d{delta}-dir{direction}-w{width}',
                                   kind='fine', delta=delta, gray=gray, truth=truth, interior=interior,
                                   geometry_gray=32+mask.astype(np.int32)*64, width=width)


def main():
    original = list(fixtures())+list(extra_fixtures())
    candidates = {}
    baseline_agreement = 0
    failures_saved = []
    for name, (d, s) in CANDIDATES.items():
        result = dict(parameters=dict(difference=d, similarity=s), old_shapes=[], fine_shapes=[],
                      steps=[], noise=[], correlated_noise=[], impulses=[], failures=[])
        fail = result['failures'].append
        for item in original:
            old_model = baseline(item['gray'], 1)
            reconstructed = downstream(median_image(item['gray']))
            for field in ('edge', 'seed', 'gx', 'gy', 'l1', 'median'):
                assert np.array_equal(reconstructed[field], old_model[field]), (item['name'], field)
            baseline_agreement += item['gray'].size
            new_model = image_math(item['gray'], name)
            row = geometry(item, old_model['edge'], new_model['edge'])
            result['old_shapes'].append(row)
            if (row['new_geometry']['covered'] < row['old_geometry']['covered'] or
                row['new_geometry']['complete_connected_contours'] < row['old_geometry']['complete_connected_contours'] or
                row['new_off'] > row['old_off']):
                fail(item['name']+': old geometry/off-band regression')
        gains = 0
        for item in fine_fixtures():
            old = baseline(item['gray'], 1)
            new = image_math(item['gray'], name)
            metric_item = {**item, 'gray': item['geometry_gray']}
            row = geometry(metric_item, old['edge'], new['edge'])
            row.update(delta=item['delta'], width=item['width'], recovered_median=int((new['detail_keep'] & (new['median'] != old['median'])).sum()))
            result['fine_shapes'].append(row)
            if row['new_geometry']['covered'] < row['old_geometry']['covered'] or row['new_off'] > row['old_off']:
                fail(item['name']+': fine geometry/off-band regression')
            if item['delta'] in (18, 20):
                gains += max(0, row['new_geometry']['covered']-row['old_geometry']['covered'])
        result['fine_coverage_gain_d18_d20'] = gains
        if gains <= 0:
            fail('No final Sobel geometry improvement at delta18/20')
        for delta in (18, 64):
            for axis in (0, 1):
                for reverse in (False, True):
                    y, x = np.indices((48, 64))
                    mask = y >= 24 if axis == 0 else x >= 32
                    gray = 32+np.logical_xor(mask, reverse)*delta
                    line = image_math(gray, name)['edge'][:, 24] if axis == 0 else image_math(gray, name)['edge'][24]
                    wanted = 23 if axis == 0 else 31
                    result['steps'].append(dict(delta=delta, axis=axis, reverse=reverse, positions=np.flatnonzero(line).tolist()))
                    if np.flatnonzero(line).tolist() != [wanted]:
                        fail(f'Step single peak regressed {delta}/{axis}/{reverse}')
        for amp, seed, gray in noise_fixtures():
            old = baseline(gray, 1)
            new = image_math(gray, name)
            roi = (slice(2, -2), slice(2, -2))
            row = dict(amplitude=amp, seed=seed, pixels=int(gray[roi].size),
                       old_edges=int(old['edge'][roi].sum()), new_edges=int(new['edge'][roi].sum()),
                       restored_median=int(new['detail_keep'][roi].sum()))
            result['noise'].append(row)
            if row['new_edges'] > row['old_edges'] and len([p for p in failures_saved if p.startswith(name)]) < 3:
                path = R/f'{name}-noise-amp{amp}-seed{seed}.npz'
                np.savez_compressed(path, gray=gray, old_median=old['median'], new_median=new['median'],
                                    restored=new['detail_keep'], old_edge=old['edge'], new_edge=new['edge'])
                failures_saved.append(path.name)
            for axis in (0, 1):
                p = np.pad(gray, 1, mode='edge')
                smooth = ((p[:-2, 1:-1]+2*gray+p[2:, 1:-1]) if axis == 0 else
                          (p[1:-1, :-2]+2*gray+p[1:-1, 2:]))//4
                a, b = baseline(smooth, 1)['edge'], image_math(smooth, name)['edge']
                row = dict(amplitude=amp, seed=seed, axis=axis, old_edges=int(a[roi].sum()), new_edges=int(b[roi].sum()))
                result['correlated_noise'].append(row)
                if row['new_edges'] > row['old_edges']:
                    fail(f'Correlated noise increased {amp}/{seed}/{axis}')
        result['noise_totals'] = []
        for amp, cap in ((8, 0), (16, 49), (24, 2735)):
            rows = [q for q in result['noise'] if q['amplitude'] == amp]
            old_total, new_total = sum(q['old_edges'] for q in rows), sum(q['new_edges'] for q in rows)
            assert old_total == cap and sum(q['pixels'] for q in rows) == 93744
            result['noise_totals'].append(dict(amplitude=amp, old_edges=old_total, new_edges=new_total, cap=cap, pixels=93744))
            if new_total > cap:
                fail(f'Fixed flat noise cap exceeded amplitude{amp}')
        for polarity, value in ((1, 255), (-1, 0)):
            for length in (1, 2, 3):
                gray = np.full((48, 64), 64, dtype=np.int32)
                gray[20:20+length, 30] = value
                new = image_math(gray, name)
                result['impulses'].append(dict(polarity=polarity, length=length, edges=int(new['edge'].sum()), median_restored=int(new['detail_keep'].sum())))
                if length == 1 and new['edge'].any():
                    fail('Isolated salt/pepper retained')
        result['eligible'] = not result['failures']
        candidates[name] = result
    eligible = [n for n in CANDIDATES if candidates[n]['eligible']]
    chosen = min(eligible, key=lambda n: (-candidates[n]['fine_coverage_gain_d18_d20'],
        sum(q['new_edges'] for q in candidates[n]['noise_totals']), n)) if eligible else None
    sources = [Path(__file__), W/'tests/reference_median_detail.py', *[W/'tests'/n for n in (
        'reference_thin_v11.py', 'reference_thin.py', 'reference_v41.py', 'reference_v4.py', 'reference_v3.py',
        'reference_v2.py', 'quality_candidates.py', 'quality_v3.py', 'quality_thin_v11.py')]]
    record = dict(result='SYNTHETIC_GATE_PASS' if chosen else 'SYNTHETIC_GATE_FAIL', selected_candidate=chosen,
                  candidates=candidates, unchanged_downstream_baseline_compared_pixels=baseline_agreement,
                  failed_inputs={n: sha(R/n) for n in failures_saved},
                  source_sha256={str(p): sha(p) for p in sources}, synthetic_only=True, rtl_checked=False, hardware_checked=False)
    (R/'candidate-quality.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(dict(result=record['result'], selected_candidate=chosen,
        candidates={n:{k:v for k,v in q.items() if k in ('eligible', 'noise_totals', 'fine_coverage_gain_d18_d20', 'failures')} for n,q in candidates.items()}), indent=2), flush=True)
    if chosen is None:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
