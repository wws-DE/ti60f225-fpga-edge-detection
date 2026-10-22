"""Approved v1.1 local RTL checks: legacy subset, expanded RAM windows, stalls/reset."""
from pathlib import Path
import hashlib
import json
import numpy as np
import run_checks as sim
from reference_thin_v11 import filter_windows
from reference_v4 import packed_fields
from reference_v3 import windows

W, R = sim.WORK, sim.REPORT
sim.SIM = W/'sim_thin_core'
sim.SIM.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sources = [sim.MODEL, *sorted((W/'algorithm/edge').glob('*.sv')),
           W/'tests/tb_thin_filter.sv', W/'tests/tb_thin_chain.sv']
sim.run('thin-compile', 'xvlog', ['--sv', *sources])
rng = np.random.default_rng(20261021)
records = []
for direction in range(4):
    for weak in (0, 1):
        for own in (0, 1):
            for mask in range(256):
                pair = np.zeros((2, 3, 3), dtype=np.uint32)
                for lane in range(2):
                    for bit, cell in enumerate((0, 1, 2, 3, 5, 6, 7, 8)):
                        magnitude = (71, 72, 73)[bit % 3]
                        pair[lane].flat[cell] = cell+lane*17 | direction << 8 | ((mask >> bit) & 1) << 11 | magnitude << 12
                    pair[lane, 1, 1] = 99+lane | direction << 8 | weak << 10 | own << 11 | 72 << 12
                records.append((pair, 8, 5))
# Every neighbor direction/seed and real-vs-replicated boundary position.
for direction in range(4):
    for sample in (0, 1, 2, 3, 5, 6, 7, 8):
        for nd in range(4):
            for seed in (0, 1):
                for x, y in ((0, 0), (38, 0), (0, 11), (38, 11), (0, 5), (38, 5), (8, 0), (8, 11), (8, 5)):
                    pair = np.full((2, 3, 3), (72 << 12) | (direction << 8) | 2048, dtype=np.uint32)
                    for lane in range(2):
                        pair[lane, 1, 1] |= 1024
                        pair[lane].flat[sample] = (72 << 12) | (nd << 8) | (seed << 11)
                    records.append((pair, x, y))
for _ in range(2048):
    pair = rng.integers(0, 4096, (2, 3, 3), dtype=np.uint32)
    pair |= rng.integers(0, 1531, (2, 3, 3), dtype=np.uint32) << 12
    records.append((pair, int(rng.integers(0, 20))*2, int(rng.integers(0, 12))))
runs = []
for mode in (0, 1):
    path = sim.SIM/f'filter-{mode}.hex'
    with path.open('w', encoding='ascii') as stream:
        for pair, x, y in records:
            values = filter_windows(pair, x, y, 40, 12, mode)
            center = values[0][0] | values[1][0] << 8
            edge = values[0][1] | values[1][1] << 1
            bits = sum(int(v) << (24*i) for i, v in enumerate(pair.reshape(-1)))
            stream.write(f'{(bits << 40) | (x << 29) | (y << 18) | (center << 2) | edge:0118x}\n')
    name = f'thin_filter_{mode}'
    sim.snapshot(name, 'tb_thin_filter', dict(N=len(records), MODE=mode))
    text = sim.simulate(name, 'THIN_FILTER_PASS', ['DATA='+path.as_posix()])
    runs.append(dict(test='filter', mode=mode, vectors=len(records), sha256=sha(path),
                     completion=next(line for line in text.splitlines() if 'THIN_FILTER_PASS' in line)))


def field(values, index, bits):
    return sum((int(v) & ((1 << bits)-1)) << (bits*lane) for lane, v in enumerate(values[index:index+2]))


configs = [(40, 12, mode, 64) for mode in (0, 1)]
configs += [(8, 5, mode, t) for mode in (0, 1) for t in (0, 7, 16, 32, 2047)]
configs += [(1920, 5, 1, 64)]
for width, height, mode, threshold in configs:
    n = width*height
    center = rng.integers(0, 256, n, dtype=np.uint32)
    gx, gy = rng.integers(-1020, 1021, (2, n), dtype=np.int32)
    # Keep the documented L1 range while exercising zero/sign/ratio boundaries.
    l1 = np.abs(gx)+np.abs(gy)
    gy[l1 > 1530] = 0
    special = [(0, 0), (32, 0), (34, 0), (48, 0), (50, 0), (16, 8), (16, 10), (8, 16), (10, 16),
               (1020, 0), (-1020, 0), (0, 1020), (0, -1020), (765, 765), (-765, -765), (-16, 8), (16, -8)]
    for i, (a, b) in enumerate(special):
        gx[i], gy[i] = a, b
    l1 = np.abs(gx)+np.abs(gy)
    seeds = rng.integers(0, 2, n, dtype=np.uint32)
    packed = packed_fields(center, gx, gy, l1, seeds, threshold, 16).astype(np.uint32) & 4095
    packed |= l1.astype(np.uint32) << 12
    ws = windows(packed.reshape(height, width))
    edges = np.empty(n, dtype=np.uint32)
    for y in range(height):
        for x in range(0, width, 2):
            values = filter_windows(ws[y, x:x+2], x, y, width, height, mode)
            edges[y*width+x:y*width+x+2] = [v[1] for v in values]
    paths = [sim.SIM/f'chain-{width}-{height}-{mode}-{threshold}-{kind}.hex' for kind in ('input', 'gold', 'window')]
    with paths[0].open('w', encoding='ascii') as inp, paths[1].open('w', encoding='ascii') as gold, paths[2].open('w', encoding='ascii') as win:
        for i in range(0, n, 2):
            bits = field(center, i, 8)
            for a in (gx, gy, l1):
                bits = (bits << 22) | field(a, i, 11)
            inp.write(f'{(bits << 2) | field(seeds, i, 1):021x}\n')
            gold.write(f'{(field(packed, i, 24) << 18) | (field(center, i, 8) << 2) | field(edges, i, 1):017x}\n')
            y, x = divmod(i, width)
            packed_windows = sum(int(v) << (24*j) for j, v in enumerate(ws[y, x:x+2].reshape(-1)))
            win.write(f'{packed_windows:0108x}\n')
    name = f'thin_chain_{width}_{height}_{mode}_{threshold}'
    sim.snapshot(name, 'tb_thin_chain', dict(W=width, H=height, MODE=mode, T=threshold))
    text = sim.simulate(name, 'THIN_CHAIN_PASS', ['INPUT='+paths[0].as_posix(), 'GOLD='+paths[1].as_posix(), 'WINDOW='+paths[2].as_posix()])
    runs.append(dict(test='chain', W=width, H=height, mode=mode, threshold=threshold, frames=5, interrupts=3,
                     vectors={p.name: sha(p) for p in paths},
                     completion=next(line for line in text.splitlines() if 'THIN_CHAIN_PASS' in line)))
files = sources + [Path(__file__), W/'tests/reference_thin_v11.py', W/'tests/reference_thin.py', W/'tests/reference_v4.py']
(R/'thin-core-result.json').write_text(json.dumps(dict(result='PASS', runs=runs,
    sources={str(p): sha(p) for p in files}), indent=2)+'\n', encoding='utf-8')
print('THIN_CORE_ALL_PASS', flush=True)
