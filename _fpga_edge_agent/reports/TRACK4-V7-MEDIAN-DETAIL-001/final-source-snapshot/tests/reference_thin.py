"""Approved protected thinning v1; original v4.1 detection followed by deletion only."""
import numpy as np
from reference_v41 import image_math as baseline_image
from reference_v3 import windows

CANDIDATES = {'A': 0, 'B': 1}
NORMAL = {0: ((0, -1), (0, 1)), 1: ((-1, -1), (1, 1)),
          2: ((-1, 0), (1, 0)), 3: ((-1, 1), (1, -1))}


def image_math(gray, mode=0):
    base = baseline_image(gray, 64, 18)
    old, seed, direction, magnitude = base['edge'], base['seed'], base['direction'], base['l1']
    h, w = old.shape
    y, x = np.indices(old.shape)
    p_seed, p_dir, p_mag = np.pad(seed, 1), np.pad(direction, 1), np.pad(magnitude, 1)
    removed = np.zeros_like(old)
    for axis, (before, after) in NORMAL.items():
        if mode == 1 and axis in (1, 3):
            continue
        allowed, winner = np.ones_like(old), np.zeros_like(old)
        for index, (dy, dx) in enumerate((before, after)):
            real = (x+dx >= 0) & (x+dx < w) & (y+dy >= 0) & (y+dy < h)
            allowed &= real
            ns = p_seed[1+dy:1+dy+h, 1+dx:1+dx+w]
            nd = p_dir[1+dy:1+dy+h, 1+dx:1+dx+w]
            nm = p_mag[1+dy:1+dy+h, 1+dx:1+dx+w]
            stronger = nm >= magnitude if index == 0 else nm > magnitude
            winner |= ns & (nd == direction) & stronger
        removed |= (direction == axis) & seed & (magnitude > 0) & allowed & winner
    new = old & ~removed
    packed = (base['packed'].astype(np.uint32) & 4095) | (magnitude.astype(np.uint32) << 12)
    return {**base, 'v41_edge': old, 'edge': new, 'thin_removed': old & ~new,
            'retain': ~removed, 'packed24': packed}


def filter_windows(values, x_even, y, width, height, mode=0):
    """Scalar specification, independent from the vector shift implementation."""
    result = []
    tangent = {0: (1, 7), 1: (2, 6), 2: (3, 5), 3: (0, 8)}
    normal = {0: (3, 5), 1: (0, 8), 2: (1, 7), 3: (2, 6)}
    for lane, window in enumerate(values):
        flat = np.asarray(window).reshape(-1)
        cx, cy = x_even+lane, y
        center = int(flat[4])
        d, seed, weak, m = (center >> 8) & 3, bool(center & 2048), bool(center & 1024), (center >> 12) & 2047

        def real(i):
            return 0 <= cx+i % 3-1 < width and 0 <= cy+i // 3-1 < height

        def has_seed(i):
            return real(i) and bool(int(flat[i]) & 2048)

        if seed:
            old = any(has_seed(i) for i in range(9) if i != 4)
        else:
            a, b = tangent[d]
            old = weak and has_seed(a) and has_seed(b)
            old &= (((int(flat[a]) >> 8) & 3) ^ d) != 2
            old &= (((int(flat[b]) >> 8) & 3) ^ d) != 2
        keep = True
        before, after = normal[d]
        if seed and m > 0 and real(before) and real(after) and (mode == 0 or d in (0, 2)):
            for i, greater_equal in ((before, True), (after, False)):
                neighbor = int(flat[i])
                nm, nd = (neighbor >> 12) & 2047, (neighbor >> 8) & 3
                if has_seed(i) and nd == d and (nm >= m if greater_equal else nm > m):
                    keep = False
        result.append((center & 255, int(old and keep), int(old)))
    return result
