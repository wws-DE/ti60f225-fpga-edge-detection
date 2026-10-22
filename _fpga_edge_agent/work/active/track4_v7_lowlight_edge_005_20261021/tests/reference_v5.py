"""Approved v5 mathematical model; image coordinates, independent of RTL stages."""
import numpy as np

CANDIDATES = {'A': 40, 'B': 32}
NORMAL = {0: (3, 5), 1: (0, 8), 2: (1, 7), 3: (2, 6)}
TANGENT = {0: ((0, 1, 2), (6, 7, 8)),
           1: ((1, 2, 5), (3, 6, 7)),
           2: ((0, 3, 6), (2, 5, 8)),
           3: ((0, 1, 3), (5, 7, 8))}


def windows(a, radius=1):
    a = np.asarray(a)
    return np.lib.stride_tricks.sliding_window_view(
        np.pad(a, radius, mode='edge'), (2 * radius + 1,) * 2)


def direction(gx, gy):
    gx, gy = np.asarray(gx, dtype=np.int32), np.asarray(gy, dtype=np.int32)
    ax, ay = np.abs(gx), np.abs(gy)
    q = np.where(gx >= 0, np.where(gy >= 0, 1, 7), np.where(gy >= 0, 3, 5))
    q = np.where(256 * ay < 106 * ax, np.where(gx >= 0, 0, 4), q)
    q = np.where(256 * ax < 106 * ay, np.where(gy >= 0, 2, 6), q)
    return np.where((gx == 0) & (gy == 0), 0, q).astype(np.int32)


def filter_image(magnitude, q, threshold=64, drop=32):
    """One raw-gradient window; support never uses newly detected edges."""
    m, q = np.asarray(magnitude, dtype=np.int32), np.asarray(q, dtype=np.int32)
    h, w = m.shape
    low = max(int(threshold) - int(drop), 0)
    mp, qp = np.pad(m, 1), np.pad(q, 1)
    support, neighbor_magnitude = [], []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nm = mp[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            nq = qp[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            delta = (nq - q) % 8
            neighbor_magnitude.append(nm)
            support.append((nm > low) & (nm > 0) & ((delta == 0) | (delta == 1) | (delta == 7)))
    any_neighbor = np.logical_or.reduce([s for i, s in enumerate(support) if i != 4])
    peak, bilateral = np.zeros_like(m, dtype=bool), np.zeros_like(m, dtype=bool)
    for axis in range(4):
        left, right = NORMAL[axis]
        a, b = TANGENT[axis]
        selected = q % 4 == axis
        peak |= selected & (m > neighbor_magnitude[left]) & (m >= neighbor_magnitude[right]) & (m > 0)
        bilateral |= selected & np.logical_or.reduce([support[i] for i in a]) & np.logical_or.reduce([support[i] for i in b])
    peak[[0, -1], :] = False
    peak[:, [0, -1]] = False
    weak = (m > low) & (m > 0)
    strong = m > threshold
    edge = peak & weak & ((strong & any_neighbor) | bilateral)
    return dict(edge=edge, peak=peak, weak=weak, strong=strong,
                any_neighbor=any_neighbor, bilateral=bilateral, direction=q, low_threshold=low)


def image_math(gray, threshold=64, drop=32):
    gray = np.asarray(gray, dtype=np.int32)
    median = np.median(windows(gray), axis=(-2, -1)).astype(np.int32)
    a = windows(median)
    gx = (a[..., 0, 2] + 2 * a[..., 1, 2] + a[..., 2, 2]
          - a[..., 0, 0] - 2 * a[..., 1, 0] - a[..., 2, 0])
    gy = (a[..., 2, 0] + 2 * a[..., 2, 1] + a[..., 2, 2]
          - a[..., 0, 0] - 2 * a[..., 0, 1] - a[..., 0, 2])
    magnitude = np.abs(gx) + np.abs(gy)
    q = direction(gx, gy)
    return dict(center=median, median=median, gx=gx, gy=gy, l1=magnitude,
                **filter_image(magnitude, q, threshold, drop))


def blur_image(gray, weights):
    """Separable symmetric filter; a single final integer division, edge padding."""
    weights = np.asarray(weights, dtype=np.int32)
    kernel = weights[:, None] * weights[None, :]
    return (windows(np.asarray(gray, dtype=np.int32), len(weights) // 2) * kernel).sum(
        axis=(-2, -1)) // int(weights.sum() ** 2)
