"""Full frontend integration with an unchanged real v4.1 frontend in parallel."""
from pathlib import Path
import hashlib
import json
import numpy as np
import run_checks as sim
from reference_thin_v11 import image_math as new_image
from reference_v41 import image_math as v41_image
from reference_v3 import image_math as v3_image

W, R = sim.WORK, sim.REPORT
sim.SIM = W/'sim_frontend_thin'
sim.SIM.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
B = W.parent/'track4_v7_lowlight_edge_004_rev1_20261021'
original = B/'algorithm/frontend/frontend_frame_pair.sv'
assert sha(B/'algorithm/frontend/sobel_pair.sv') == sha(W/'algorithm/frontend/sobel_pair.sv')
text = original.read_text(encoding='utf-8').replace('module frontend_frame_pair #(', 'module frontend_frame_pair_baseline #(', 1)
baseline = sim.SIM/'frontend_frame_pair_baseline.sv'
baseline.write_text(text, encoding='utf-8')
sources = [sim.MODEL, *sorted((W/'algorithm/frontend').glob('*.sv')),
           *sorted((W/'algorithm/edge').glob('*.sv')), baseline, W/'tests/tb_frontend_thin.sv']
sim.run('frontend-thin-compile', 'xvlog', ['--sv', *sources])
configs = [(8, 5, 1, 1, 0, 0), (40, 12, 1, 1, 0, 0),
           (8, 5, 1, 0, 1, 0), (8, 5, 0, 0, 1, 0),
           (8, 5, 1, 0, 1, 1), (8, 5, 1, 1, 1, 1)]
runs = []
for width, height, context, thin, compare, owner in configs:
    y, x = np.indices((height, width), dtype=np.uint32)
    r, g, b = (x*17+y*31) % 256, (x*41+y*7) % 256, (x*3+y*61) % 256
    if width == 40:
        r = g = b = (32+(x >= 20)*64).astype(np.uint32)
    rgb = (r << 16) | (g << 8) | b
    gray = ((77*r+150*g+29*b+128) >> 8).astype(np.int32)
    m = new_image(gray, 1) if thin and context else (v41_image(gray, 64, 18) if context else v3_image(gray, 64, 18, 0))
    paths = [sim.SIM/f'{width}-{height}-{context}-{thin}-{owner}-{kind}.hex' for kind in ('input', 'gold0', 'gold1')]
    with paths[0].open('w', encoding='ascii') as stream:
        for a, b in rgb.reshape(-1, 2):
            stream.write(f'{int(a) | int(b) << 24:012x}\n')
    for kind, path in enumerate(paths[1:]):
        centers, edges = m['median'].reshape(-1), m['edge'].reshape(-1)
        with path.open('w', encoding='ascii') as stream:
            for i in range(0, width*height, 2):
                center = int(centers[i]) | int(centers[i+1]) << 8
                edge = (int(edges[i]) | int(edges[i+1]) << 1) if kind else 0
                stream.write(f'{(center << 2) | edge:05x}\n')
    name = f'frontend_thin_{width}_{height}_{context}_{thin}_{owner}'
    sim.snapshot(name, 'tb_frontend_thin', dict(W=width, H=height, CONTEXT=context, THIN=thin, COMPARE=compare, OWNER=owner))
    output = sim.simulate(name, 'FRONTEND_THIN_PASS', ['INPUT='+paths[0].as_posix(),
                         'GOLD0='+paths[1].as_posix(), 'GOLD1='+paths[2].as_posix()])
    runs.append(dict(W=width, H=height, context=bool(context), thin=bool(thin), compare_real_v41=bool(compare),
                     owner=bool(owner), vectors={p.name: sha(p) for p in paths},
                     completion=next(line for line in output.splitlines() if 'FRONTEND_THIN_PASS' in line)))
files = sources+[Path(__file__), W/'tests/reference_thin_v11.py', W/'tests/reference_thin.py',
                 W/'tests/reference_v41.py', W/'tests/reference_v4.py', W/'tests/reference_v3.py']
(R/'frontend-thin-result.json').write_text(json.dumps(dict(result='PASS', runs=runs,
    sources={str(p): sha(p) for p in files}, actual_baseline={str(original): sha(original)}), indent=2)+'\n', encoding='utf-8')
print('FRONTEND_THIN_ALL_PASS', flush=True)
