"""Approved median-detail v1: fixed A/B; unchanged downstream v1.1 rule."""
import numpy as np
from reference_v2 import windows, median_image
from reference_v41 import window_math
from reference_v4 import packed_fields, context_image

CANDIDATES = {'A': (16, 4), 'B': (18, 8)}


def detail_windows(values, difference, similarity):
    a = np.asarray(values, dtype=np.int32)
    a = a.reshape(*a.shape[:-2], 9)
    c = a[..., 4]
    keep = np.zeros_like(c, dtype=bool)
    for first, last in ((1, 7), (0, 8), (3, 5), (2, 6)):
        background = a[..., [i for i in range(9) if i not in (4, first, last)]]
        tangent = (np.abs(a[..., first]-c) <= similarity) & (np.abs(a[..., last]-c) <= similarity)
        delta = background-c[..., None]
        polarity = np.all(delta <= -difference, axis=-1) | np.all(delta >= difference, axis=-1)
        stable = np.ptp(background, axis=-1) <= 2*similarity
        keep |= tangent & polarity & stable
    return np.where(keep, c, np.sort(a, axis=-1)[..., 4]), keep


def scalar_window(values, x, y, width, height, difference, similarity, median_enable=True, detail_enable=True):
    """Independent scalar geometry; do not call vector qualification."""
    p = [[int(z) for z in row] for row in values]
    c = p[1][1]
    old = sorted(z for row in p for z in row)[4]
    if not median_enable:
        return c, False
    if detail_enable and 0 < x < width-1 and 0 < y < height-1:
        for dy, dx in ((1, 0), (1, 1), (0, 1), (1, -1)):
            ends = [p[1-dy][1-dx], p[1+dy][1+dx]]
            other = [p[1+oy][1+ox] for oy in (-1, 0, 1) for ox in (-1, 0, 1)
                     if (oy, ox) not in ((0, 0), (dy, dx), (-dy, -dx))]
            if max(abs(t-c) for t in ends) > similarity:
                continue
            if not (max(other) <= c-difference or min(other) >= c+difference):
                continue
            if max(other)-min(other) <= 2*similarity:
                return c, True
    return old, False


def median_detail(gray, difference, similarity, median_enable=True, detail_enable=True):
    gray = np.asarray(gray, dtype=np.int32)
    if not median_enable:
        return gray.copy(), np.zeros_like(gray, dtype=bool)
    values, keep = detail_windows(windows(gray), difference, similarity)
    keep[[0, -1], :] = False
    keep[:, [0, -1]] = False
    keep &= detail_enable
    return np.where(keep, gray, median_image(gray)), keep


def downstream(median):
    """Same seed, context and guarded axis peak selection as frozen v1.1."""
    m = window_math(windows(median), 64, 18)
    seed, magnitude = m['edge'], m['l1']
    packed = packed_fields(m['center'], m['gx'], m['gy'], magnitude, seed, 64, 16)
    post = context_image(packed)
    direction = post['direction']
    h, w = median.shape
    y, x = np.indices(median.shape)
    sp, dp, mp = np.pad(seed, 1), np.pad(direction, 1), np.pad(magnitude, 1)
    at = lambda p, dy, dx: p[1+dy:1+dy+h, 1+dx:1+dx+w]
    mixed = np.zeros_like(seed)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                mixed |= at(sp, dy, dx) & (at(dp, dy, dx) != direction)
    remove = np.zeros_like(seed)
    for axis, pair in ((0, ((0, -1), (0, 1))), (2, ((-1, 0), (1, 0)))):
        inside, winner = np.ones_like(seed), np.zeros_like(seed)
        for index, (dy, dx) in enumerate(pair):
            inside &= (x+dx >= 0) & (x+dx < w) & (y+dy >= 0) & (y+dy < h)
            nm = at(mp, dy, dx)
            winner |= at(sp, dy, dx) & (at(dp, dy, dx) == direction) & (nm >= magnitude if index == 0 else nm > magnitude)
        remove |= (direction == axis) & seed & (magnitude > 0) & inside & winner & ~mixed
    return {**m, **post, 'seed': seed, 'median': median, 'edge': post['edge'] & ~remove}


def image_math(gray, candidate='A'):
    median, keep = median_detail(gray, *CANDIDATES[candidate])
    return {**downstream(median), 'detail_keep': keep}
