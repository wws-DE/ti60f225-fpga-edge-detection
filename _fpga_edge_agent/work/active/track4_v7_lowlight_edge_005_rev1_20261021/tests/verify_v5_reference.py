"""Independent scalar verification of the approved v5 feasibility calculation."""
from pathlib import Path
import hashlib
import json
import numpy as np
from reference_v5 import direction, filter_image, image_math, CANDIDATES
from reference_v41 import image_math as old_image
from quality_candidates import noise_fixtures

W = Path(__file__).resolve().parents[1]
R = W.parents[2] / 'reports/TRACK4-V7-LOWLIGHT-EDGE-005'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def scalar_direction(gx, gy):
    if gx == 0 and gy == 0:
        return 0
    if abs(gy)*256 < abs(gx)*106:
        return 0 if gx > 0 else 4
    if abs(gx)*256 < abs(gy)*106:
        return 2 if gy > 0 else 6
    if gx > 0:
        return 1 if gy > 0 else 7
    return 3 if gy > 0 else 5


def scalar_pixel(m, q, y, x, high, drop):
    h, w = m.shape
    if y == 0 or x == 0 or y == h-1 or x == w-1:
        return False
    low = max(high-drop, 0)
    centre, angle = int(m[y, x]), int(q[y, x])
    if centre <= low or centre == 0:
        return False
    # Unit vectors express the geometry without the vector model's index tables.
    nx, ny = ((1, 0), (1, 1), (0, 1), (-1, 1))[angle % 4]
    if centre <= int(m[y-ny, x-nx]) or centre < int(m[y+ny, x+nx]):
        return False
    tx, ty = -ny, nx
    any_neighbor, positive, negative = False, False, False
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nm, nq = int(m[y+dy, x+dx]), int(q[y+dy, x+dx])
            distance = abs(nq-angle)
            compatible = nm > low and nm > 0 and min(distance, 8-distance) <= 1
            if compatible:
                any_neighbor = True
                projection = tx*dx+ty*dy
                positive |= projection > 0
                negative |= projection < 0
    return (centre > high and any_neighbor) or (positive and negative)


def main():
    rng = np.random.default_rng(20261021)
    gx = np.r_[rng.integers(-1020, 1021, 65536), [0, 128, 128, 128, -128, -128, -128]]
    gy = np.r_[rng.integers(-1020, 1021, 65536), [0, 52, 53, 54, -52, -53, -54]]
    scalar = np.array([scalar_direction(int(x), int(y)) for x, y in zip(gx, gy)])
    np.testing.assert_array_equal(direction(gx, gy), scalar)
    checked = 0
    for h, w in ((5, 6), (7, 10), (31, 44)):
        for high in (0, 7, 16, 32, 64, 2047):
            m = rng.integers(0, 1531, (h, w), dtype=np.int32)
            q = rng.integers(0, 8, (h, w), dtype=np.int32)
            for drop in CANDIDATES.values():
                actual = filter_image(m, q, high, drop)['edge']
                expected = np.array([[scalar_pixel(m, q, y, x, high, drop) for x in range(w)] for y in range(h)])
                np.testing.assert_array_equal(actual, expected)
                checked += h*w
    # Raw derivatives and median are unchanged, and must match the real v4.1 reference.
    raw_pixel_checks = 0
    saved = []
    for amp, seed, gray in noise_fixtures():
        old = old_image(gray, 64, 18)
        new = image_math(gray, 64, 32)
        for key in ('median', 'gx', 'gy', 'l1'):
            np.testing.assert_array_equal(old[key], new[key])
        raw_pixel_checks += gray.size
        # An independent scalar walk of one full fixed noise plane per amplitude.
        if seed == 431:
            for candidate, drop in CANDIDATES.items():
                new = image_math(gray, 64, drop)
                expected = np.array([[scalar_pixel(new['l1'], new['direction'], y, x, 64, drop)
                                      for x in range(gray.shape[1])] for y in range(gray.shape[0])])
                np.testing.assert_array_equal(new['edge'], expected)
                checked += gray.size
                path = R/f'fixed-noise-amplitude{amp}-seed431-{candidate}.npz'
                np.savez_compressed(path, gray=gray, median=new['median'], gx=new['gx'], gy=new['gy'],
                                    l1=new['l1'], direction=new['direction'], old_edge=old['edge'], new_edge=new['edge'])
                saved.append(dict(path=str(path), sha256=sha(path)))
    # The hand-calculated missing weak step must be restored to one peak column.
    step = np.full((48, 64), 32, dtype=np.int32)
    step[:, 32:] = 44
    witness = []
    for candidate, drop in CANDIDATES.items():
        new, old = image_math(step, 64, drop), old_image(step, 64, 18)
        assert new['gx'][24, 31] == 48 and new['gy'][24, 31] == 0
        assert not old['edge'].any()
        assert np.flatnonzero(new['edge'][24]).tolist() == [31]
        witness.append(dict(candidate=candidate, old_edge_count=int(old['edge'].sum()),
                            new_edge_count=int(new['edge'].sum()), mid_row_positions=[31]))
    files = [Path(__file__), W/'tests/reference_v5.py', W/'tests/quality_v5.py']
    report = dict(result='SCALAR_AND_VECTOR_AGREE', direction_vectors=int(gx.size),
                  scalar_filter_pixels=checked, unchanged_raw_gradient_pixels=raw_pixel_checks,
                  weak_step_witness=witness, saved_failure_inputs=saved,
                  source_sha256={str(p): sha(p) for p in files}, rtl_checked=False, hardware_checked=False)
    (R/'reference-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('result', 'direction_vectors', 'scalar_filter_pixels',
                                          'unchanged_raw_gradient_pixels', 'weak_step_witness')}, indent=2))


if __name__ == '__main__':
    main()
