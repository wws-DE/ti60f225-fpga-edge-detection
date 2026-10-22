"""Independent scalar comparison and failure localization for approved thinning v1."""
from pathlib import Path
import hashlib
import json
import numpy as np
from reference_thin import image_math, filter_windows, CANDIDATES
from reference_v4 import filter_windows as old_filter_windows
from reference_v3 import windows
from quality_thin import extra_fixtures
from quality_v3 import fixtures
from quality_candidates import noise_fixtures

W = Path(__file__).resolve().parents[1]
R = W.parents[2] / 'reports/TRACK4-V7-EDGE-THIN-001'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    images = [item['gray'] for item in fixtures()] + [item['gray'] for item in extra_fixtures()]
    images += [gray for _, seed, gray in noise_fixtures() if seed == 431]
    checked = 0
    old_checked = 0
    for mode in CANDIDATES.values():
        for gray in images:
            model = image_math(gray, mode)
            packed = windows(model['packed24'])
            h, w = gray.shape
            for y in range(h):
                for x in range(0, w, 2):
                    pair = packed[y, x:x+2]
                    result = filter_windows(pair, x, y, w, h, mode)
                    original = old_filter_windows(pair & 4095, x, y, w, h)
                    for lane, (center, edge, old) in enumerate(result):
                        assert center == int(model['center'][y, x+lane])
                        assert edge == int(model['edge'][y, x+lane]), (mode, y, x+lane)
                        assert old == int(model['v41_edge'][y, x+lane]) == original[lane][1]
                        assert not edge or old
                        checked += 1
                        old_checked += 1
    item = next(i for i in extra_fixtures() if i['name'] == 'y_junction-d18')
    mask = item['gray'] > 32
    p = np.pad(mask, 1, mode='edge')
    target = mask & (~p[:-2, 1:-1] | ~p[2:, 1:-1] | ~p[1:-1, :-2] | ~p[1:-1, 2:]) & item['interior']
    evidence = []
    for name, mode in CANDIDATES.items():
        model = image_math(item['gray'], mode)
        covered_before = windows(model['v41_edge']).max(axis=(-2, -1))
        covered_after = windows(model['edge']).max(axis=(-2, -1))
        misses = np.argwhere(target & covered_before & ~covered_after)
        assert misses.tolist() == [[23, 31]]
        # This seed at (22,31) is deleted due to an equal same-direction seed above.
        cy, cx = 22, 31
        assert model['seed'][cy, cx] and model['v41_edge'][cy, cx] and not model['edge'][cy, cx]
        assert model['direction'][cy, cx] == model['direction'][cy-1, cx] == 2
        assert model['l1'][cy, cx] == model['l1'][cy-1, cx] == 72
        path = R/f'failed-y-junction-d18-{name}.npz'
        np.savez_compressed(path, gray=item['gray'], target=target, packed24=model['packed24'], seed=model['seed'],
                            direction=model['direction'], magnitude=model['l1'],
                            old_edge=model['v41_edge'], new_edge=model['edge'])
        evidence.append(dict(candidate=name, path=str(path), sha256=sha(path), missed_target_yx=[23, 31],
                             deleted_seed_yx=[22, 31], center_direction=2, center_magnitude=72,
                             equal_winner_yx=[21, 31],
                             seed_direction_window=model['direction'][cy-1:cy+2, cx-1:cx+2].tolist(),
                             seed_window=model['seed'][cy-1:cy+2, cx-1:cx+2].astype(int).tolist()))
    files = [Path(__file__), W/'tests/reference_thin.py', W/'tests/quality_thin.py', W/'tests/reference_v4.py']
    report = dict(result='SCALAR_AND_VECTOR_AGREE', scalar_thinning_pixels=checked,
                  legacy_scalar_comparisons=old_checked, failed_y_junction=evidence,
                  source_sha256={str(p): sha(p) for p in files}, rtl_checked=False, hardware_checked=False)
    (R/'reference-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('result', 'scalar_thinning_pixels', 'legacy_scalar_comparisons',
                                          'failed_y_junction')}, indent=2))


if __name__ == '__main__':
    main()
