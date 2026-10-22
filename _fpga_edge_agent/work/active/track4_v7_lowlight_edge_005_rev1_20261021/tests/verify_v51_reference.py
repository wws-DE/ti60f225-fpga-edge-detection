"""Independent scalar proof of the executed v5.1 numerical feasibility checks."""
from pathlib import Path
import hashlib
import json
import numpy as np
from reference_v5 import direction
from reference_v51 import smooth_signed, image_math, CANDIDATES
from verify_v5_reference import scalar_pixel, scalar_direction
from reference_v41 import image_math as old_image
from quality_candidates import noise_fixtures

W = Path(__file__).resolve().parents[1]
R = W.parents[2] / 'reports/TRACK4-V7-LOWLIGHT-EDGE-005-REV1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def scalar_round(total):
    quotient, remainder = divmod(abs(int(total)), 16)
    result = quotient + int(remainder >= 8)
    return -result if total < 0 else result


def scalar_smooth(a):
    h, w = a.shape
    output = np.empty_like(a, dtype=np.int32)
    for y in range(h):
        for x in range(w):
            total = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    sample = int(a[min(max(y+dy, 0), h-1), min(max(x+dx, 0), w-1)])
                    weight = (2 if dy == 0 else 1)*(2 if dx == 0 else 1)
                    total += weight*sample
            assert -16320 <= total <= 16320
            output[y, x] = scalar_round(total)
    return output


def main():
    totals = np.arange(-16320, 16321, dtype=np.int32)
    absolute = (np.abs(totals)+8)//16
    vector = np.where(totals < 0, -absolute, absolute)
    np.testing.assert_array_equal(vector, [scalar_round(int(v)) for v in totals])
    rng = np.random.default_rng(20261021)
    direction_x = np.r_[rng.integers(-1020, 1021, 65536), [0, 128, 128, 128, -128, -128, -128]]
    direction_y = np.r_[rng.integers(-1020, 1021, 65536), [0, 52, 53, 54, -52, -53, -54]]
    np.testing.assert_array_equal(direction(direction_x, direction_y),
                                  [scalar_direction(int(x), int(y)) for x, y in zip(direction_x, direction_y)])
    samples = [np.full((5, 6), value, dtype=np.int32) for value in (-1020, -1, 0, 1, 1020)]
    samples.append(rng.integers(-1020, 1021, (31, 44), dtype=np.int32))
    y, x = np.indices((13, 18))
    samples.append(np.where((x+y) % 2, 1020, -1020).astype(np.int32))
    for dy in range(3):
        for dx in range(3):
            for value in (-1020, -8, -1, 1, 8, 1020):
                a = np.zeros((7, 8), dtype=np.int32)
                a[dy+2, dx+2] = value
                samples.append(a)
    smooth_pixels = 0
    for sample in samples:
        value = sample
        for _ in range(3):
            expected = scalar_smooth(value)
            actual = smooth_signed(value)
            np.testing.assert_array_equal(actual, expected)
            assert actual.min() >= -1020 and actual.max() <= 1020
            smooth_pixels += actual.size
            value = actual
    filter_pixels = 0
    # Original v5 scalar contract checks must continue to hold at arbitrary thresholds.
    for high in (0, 7, 16, 32, 64, 2047):
        m = rng.integers(0, 2041, (31, 44), dtype=np.int32)
        q = rng.integers(0, 8, (31, 44), dtype=np.int32)
        from reference_v5 import filter_image
        for drop in (32, 40):
            actual = filter_image(m, q, high, drop)['edge']
            expected = np.array([[scalar_pixel(m, q, y, x, high, drop) for x in range(44)] for y in range(31)])
            np.testing.assert_array_equal(actual, expected)
            filter_pixels += actual.size
    failure_inputs = []
    for amplitude, seed, gray in noise_fixtures():
        if seed != 431:
            continue
        old = old_image(gray, 64, 18)
        gx, gy = old['gx'], old['gy']
        for passes in (1, 2, 3):
            sx, sy = scalar_smooth(gx), scalar_smooth(gy)
            np.testing.assert_array_equal(smooth_signed(gx), sx)
            np.testing.assert_array_equal(smooth_signed(gy), sy)
            smooth_pixels += gray.size*2
            gx, gy = sx, sy
            for letter, drop in (('A', 40), ('B', 32)):
                result = image_math(gray, 64, (passes, drop))
                np.testing.assert_array_equal(result['gx'], gx)
                np.testing.assert_array_equal(result['gy'], gy)
                np.testing.assert_array_equal(result['center'], old['median'])
                np.testing.assert_array_equal(result['l1'], np.abs(gx)+np.abs(gy))
                expected = np.array([[scalar_pixel(result['l1'], result['direction'], y, x, 64, drop)
                                      for x in range(gray.shape[1])] for y in range(gray.shape[0])])
                np.testing.assert_array_equal(result['edge'], expected)
                filter_pixels += gray.size
                path = R/f'fixed-noise-amplitude{amplitude}-seed431-P{passes}{letter}.npz'
                np.savez_compressed(path, gray=gray, median=old['median'], gx=gx, gy=gy,
                                    l1=result['l1'], direction=result['direction'],
                                    old_edge=old['edge'], new_edge=result['edge'])
                failure_inputs.append(dict(path=str(path), sha256=sha(path)))
    step = np.full((48, 64), 32, dtype=np.int32)
    step[:, 32:] = 44
    witness = []
    for candidate, config in CANDIDATES.items():
        result = image_math(step, 64, config)
        witness.append(dict(candidate=candidate, mid_row_positions=np.flatnonzero(result['edge'][24]).tolist(),
                            maximum_l1=int(result['l1'].max()), low_threshold=result['low_threshold'],
                            old_edge_count=int(old_image(step, 64, 18)['edge'].sum())))
    files = [Path(__file__), W/'tests/reference_v51.py', W/'tests/reference_v5.py',
             W/'tests/verify_v5_reference.py', W/'tests/quality_v51.py']
    report = dict(result='SCALAR_AND_VECTOR_AGREE', rounding_sums=int(totals.size),
                  direction_vectors=int(direction_x.size), scalar_smoothing_pixels=smooth_pixels,
                  scalar_filter_pixels=filter_pixels, weak_step_witness=witness, failure_inputs=failure_inputs,
                  source_sha256={str(p): sha(p) for p in files}, rtl_checked=False, hardware_checked=False)
    (R/'reference-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('result', 'rounding_sums', 'direction_vectors',
                                          'scalar_smoothing_pixels', 'scalar_filter_pixels', 'weak_step_witness')}, indent=2))


if __name__ == '__main__':
    main()
