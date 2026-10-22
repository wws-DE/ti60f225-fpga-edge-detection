"""Approved v5.1: fixed signed-gradient smoothing, then unchanged v5 detector."""
import numpy as np
from reference_v5 import windows, direction, filter_image, image_math as raw_image

CANDIDATES = {f'P{passes}{letter}': (passes, drop)
              for passes in (1, 2, 3) for letter, drop in (('A', 40), ('B', 32))}


def smooth_signed(a):
    """Binomial 3x3 /16; nearest integer, exact halves away from zero."""
    a = np.asarray(a, dtype=np.int32)
    kernel = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=np.int32)
    total = (windows(a) * kernel).sum(axis=(-2, -1), dtype=np.int32)
    absolute = (np.abs(total) + 8) // 16
    return np.where(total < 0, -absolute, absolute).astype(np.int32)


def image_math(gray, threshold=64, config=(1, 32)):
    passes, drop = config
    assert passes in (1, 2, 3) and drop in (32, 40)
    raw = raw_image(gray, threshold, drop)
    gx, gy = raw['gx'], raw['gy']
    for _ in range(passes):
        gx, gy = smooth_signed(gx), smooth_signed(gy)
    magnitude = np.abs(gx) + np.abs(gy)
    q = direction(gx, gy)
    return dict(center=raw['center'], median=raw['median'], gx=gx, gy=gy, l1=magnitude,
                raw_gx=raw['gx'], raw_gy=raw['gy'], smooth_passes=passes,
                **filter_image(magnitude, q, threshold, drop))
