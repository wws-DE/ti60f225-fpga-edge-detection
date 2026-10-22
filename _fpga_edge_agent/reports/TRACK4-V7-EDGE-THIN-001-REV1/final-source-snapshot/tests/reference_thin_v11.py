"""Approved v1.1 junction guard; retain the frozen v1 thinning calculation."""
import numpy as np
from reference_thin import CANDIDATES, image_math as v1_image, filter_windows as v1_filter


def image_math(gray, mode=0):
    model = v1_image(gray, mode)
    seed, direction = model['seed'], model['direction']
    h, w = seed.shape
    sp, dp = np.pad(seed, 1), np.pad(direction, 1)
    mixed = np.zeros_like(seed)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            neighbor = sp[1+dy:1+dy+h, 1+dx:1+dx+w]
            nd = dp[1+dy:1+dy+h, 1+dx:1+dx+w]
            mixed |= neighbor & (nd != direction)
    retain = model['retain'] | mixed
    edge = model['v41_edge'] & retain
    return {**model, 'v1_edge': model['edge'], 'mixed_direction': mixed, 'retain': retain,
            'edge': edge, 'thin_removed': model['v41_edge'] & ~edge}


def filter_windows(values, x_even, y, width, height, mode=0):
    original = v1_filter(values, x_even, y, width, height, mode)
    result = []
    for lane, (center, edge_v1, old) in enumerate(original):
        flat = np.asarray(values[lane]).reshape(-1)
        direction = (int(flat[4]) >> 8) & 3
        mixed = False
        for index in range(9):
            if index == 4:
                continue
            nx, ny = x_even+lane+index % 3-1, y+index // 3-1
            if 0 <= nx < width and 0 <= ny < height:
                neighbor = int(flat[index])
                mixed |= bool(neighbor & 2048) and ((neighbor >> 8) & 3) != direction
        result.append((center, int(bool(edge_v1) or (bool(old) and mixed)), old))
    return result
