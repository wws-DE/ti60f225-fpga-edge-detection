"""v3 independent integer reference: v2 union three-of-three weak support."""
import numpy as np
from reference_v2 import window_math as baseline_math, median_image, windows

CANDIDATES = {'A': (16, 8), 'B': (18, 0)}

def window_math(values, threshold=64, weak_diff=18, drop=0, weak_enabled=True):
    base = baseline_math(values, threshold, 20, True)
    a = np.asarray(values, dtype=np.int32)
    dx = a[..., :, 2] - a[..., :, 0]
    dy = a[..., 2, :] - a[..., 0, :]
    gx, gy = base['gx'], base['gy']
    sx = ((gx > 0) & np.all(dx >= weak_diff, axis=-1)) | ((gx < 0) & np.all(dx <= -weak_diff, axis=-1))
    sy = ((gy > 0) & np.all(dy >= weak_diff, axis=-1)) | ((gy < 0) & np.all(dy <= -weak_diff, axis=-1))
    support = ((np.abs(gx) >= np.abs(gy)) & sx) | ((np.abs(gy) >= np.abs(gx)) & sy)
    weak = (base['l1'] > max(int(threshold)-int(drop), 0)) & support & weak_enabled
    return {**base, 'base_edge': base['edge'], 'weak_edge': weak, 'edge': base['edge'] | weak}

def image_math(gray, threshold=64, weak_diff=18, drop=0, weak_enabled=True):
    median = median_image(gray)
    return {'median': median, **window_math(windows(median), threshold, weak_diff, drop, weak_enabled)}
