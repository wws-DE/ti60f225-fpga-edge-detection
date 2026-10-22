"""Local XSim verification for the approved five fullscreen modes; no board access."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
from reference_v3 import window_math, windows as gray_windows
from reference_v2 import window_math as baseline_math

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = Path(__file__).resolve().parents[1]
AGENT = WORK.parents[2]
REPORT = AGENT / "reports/TRACK4-V7-LOWLIGHT-EDGE-004"
SIM = WORK / "sim_fullscreen"
TOOLS = Path("C:/AMDDesignTools/2025.2/Vivado/bin")
MODEL = Path("C:/Efinity/2026.1/sim_models/verilog/efx_ram10.v")
SIM.mkdir(exist_ok=True)


def run(name, tool, args, timeout=1800):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    log = REPORT / f"{name}-{stamp}.log"
    argv = [str(TOOLS / (tool + ".bat")), *map(str, args)]
    # cmd's batch CALL treats an unquoted '=' as a separator. Quote every
    # trusted local tool argument so generic_top N=... reaches xelab intact.
    if any(any(c in arg for c in '\"\r\n%&|<>') for arg in argv):
        raise ValueError("Unsupported shell metacharacter in local tool argument")
    command = " ".join('"' + arg + '"' for arg in argv)
    print("START", name, flush=True)
    start = time.time()
    with log.open("wb") as output:
        result = subprocess.run(command, shell=True, cwd=SIM, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text(encoding="utf-8", errors="replace")
    record = dict(name=name, argv=argv, returncode=result.returncode, seconds=time.time()-start, log=str(log))
    log.with_suffix(".json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    if result.returncode or "FATAL_ERROR" in text or "Fatal:" in text or "ERROR:" in text:
        print(text[-6500:], flush=True)
        raise RuntimeError(f"{name} failed; see {log}")
    print("DONE", name, round(record["seconds"], 2), flush=True)
    return text


def snapshot(name, top, parameters=None):
    args = ["--debug", "typical", "--timescale", "1ns/1ps", "--snapshot", name]
    for key, value in (parameters or {}).items():
        args += ["--generic_top", f"{key}={value}"]
    run(name + "-elaborate", "xelab", [*args, "work." + top])


def simulate(name, marker, plusargs=()):
    args = [name, "--runall", "--onerror", "quit", "--onfinish", "quit", "--nolog"]
    for arg in plusargs:
        args += ["--testplusarg", arg]
    text = run(name + "-run", "xsim", args, timeout=3600)
    if marker not in text:
        raise RuntimeError(f"Missing completion marker {marker}: {text[-3000:]}")
    print(next(line for line in text.splitlines() if marker in line), flush=True)
    return text


def compile_control():
    sources = [WORK / "algorithm/control/key_press_debouncer.sv",
               WORK / "rtl/v7_fullscreen_mode_control.sv", WORK / "tests/tb_fullscreen_control.sv"]
    run("control-compile", "xvlog", ["--sv", *sources])


def control():
    compile_control()
    for n in (2, 4, 31):
        name = f"keys_n{n}"
        snapshot(name, "tb_fullscreen_control", {"N": n})
        simulate(name, "FULLSCREEN_CONTROL_PASS")
    snapshot("keys_production", "tb_fullscreen_control", {"N": 1485000, "PRODUCTION": 1})
    simulate("keys_production", "FULLSCREEN_CONTROL_PASS")
    (REPORT / "control-result.json").write_text(json.dumps(dict(result="PASS", debounce_cycles=[2,4,31,1485000]), indent=2), encoding="utf-8")


def compile_video():
    top = (WORK / "rtl/ti60f225_oob_top.v").read_text(encoding="utf-8")
    start = top.index("reg rgb_vs_r = 'd0;")
    serializer = top[start:top.index("//==============================================================================", start)]
    actual = SIM / "actual_serializer.sv"
    actual.write_text("""module actual_serializer(input wire hdmi_tx_slow_clk,rgb_vs,rgb_hs,rgb_de,
input wire [47:0] rgb_datax2,output wire [23:0] actual_rgb,
output wire actual_vs,actual_hs,actual_de);
wire pos_vs;
""" + serializer + """
assign actual_rgb={hdmi_tx_bdata,hdmi_tx_gdata,hdmi_tx_rdata};
assign actual_vs=hdmi_tx_vs;assign actual_hs=hdmi_tx_hs;assign actual_de=hdmi_tx_de;
endmodule
""", encoding="utf-8")
    sources = [MODEL, *sorted((WORK / "algorithm/frontend").glob("*.sv")),
               WORK / "algorithm/control/key_press_debouncer.sv", WORK / "rtl/v7_fullscreen_mode_control.sv",
               WORK / "rtl/v7_algorithm_video_pair.sv", actual, WORK / "tests/tb_five_modes.sv",
               WORK / "tests/tb_mode_boundary.sv"]
    run("video-compile", "xvlog", ["--sv", *sources])
    (REPORT / "simulation-inputs.json").write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2), encoding="utf-8")


def vectors(width, height, frames, name):
    # Independent pixel mathematics; mode order follows the external key schedule.
    y, x = np.indices((height, width), dtype=np.uint32)
    inputs, expected = [], []
    for frame in range(frames):
        r = (x*3+y*7+frame*41) % 256
        g = (x//7*35+y*5+frame*17) % 256
        b = (y//3*63+x*11+frame*71) % 256
        mask = (x+y*17+frame*23) % 193 == 0
        r[mask], g[mask], b[mask] = 255, 0, 255
        rgb = (r << 16) | (g << 8) | b
        if name == "lowlight":
            # Three independently interpretable horizontal bands: weak step,
            # blurred step, and bounded noise with isolated impulse pixels.
            level = np.full((height, width), 16, dtype=np.int32)
            level[:16, 64:] += 18
            level[16:32] += np.clip((x[16:32].astype(np.int32)-61)*10, 0, 40)
            noise = np.random.default_rng(431).integers(-3, 4, (height-32, width))
            level[32:] = 24 + noise
            level[40,20] = 255
            level[40,90] = 255
            r = g = b = level.astype(np.uint32)
            rgb = r*0x010101
        gray = ((77*r+150*g+29*b+128) >> 8).astype(np.int32)
        padded = np.pad(gray, 1, mode="edge")
        windows = np.lib.stride_tricks.sliding_window_view(padded, (3,3))
        median = np.sort(windows.reshape(height, width, 9), axis=-1)[...,4]
        p = np.pad(median, 1, mode="edge")
        gx = -p[:-2,:-2]+p[:-2,2:]-2*p[1:-1,:-2]+2*p[1:-1,2:]-p[2:,:-2]+p[2:,2:]
        gy = -p[:-2,:-2]-2*p[:-2,1:-1]-p[:-2,2:]+p[2:,:-2]+2*p[2:,1:-1]+p[2:,2:]
        selected=json.loads((REPORT/'candidate-selection.json').read_text(encoding='utf-8'))
        new_math=window_math(gray_windows(median),64,selected['weak_min_diff'],selected['threshold_drop'])
        base_edge=baseline_math(gray_windows(median),64,20)['edge']
        assert not (base_edge & ~new_math['edge']).any(), 'v2 edge inclusion' 
        assert np.array_equal(new_math['gx'],gx) and np.array_equal(new_math['gy'],gy)
        edge = new_math['edge']
        if name == "lowlight" and frame == 0:
            old_edge = base_edge
            regions = {"weak_step": (slice(3,12),slice(61,67)),
                       "blurred_step": (slice(20,28),slice(60,69)),
                       "flat_noise_and_impulses": (slice(35,46),slice(3,width-3))}
            metrics = {key: dict(new_edges=int(edge[roi].sum()), old_edges=int(old_edge[roi].sum()),
                                pixels=int(edge[roi].size)) for key,roi in regions.items()}
            assert metrics["weak_step"]["new_edges"] > 0 and metrics["weak_step"]["old_edges"] == 0
            assert metrics["blurred_step"]["new_edges"] >= metrics["blurred_step"]["old_edges"] > 0
            assert metrics["flat_noise_and_impulses"]["new_edges"] == 0
            assert np.max(median[39:42,19:22]) <= 27 and np.max(median[39:42,89:92]) <= 27
            (REPORT/"synthetic-lowlight-metrics.json").write_text(json.dumps(dict(
                synthetic_only=True, threshold_new=64, threshold_old=64, baseline_min_diff=20, regions=metrics,
                sensor_gain_not_simulated=True, real_camera_accuracy_measured=False),indent=2),encoding="utf-8")
        variants = [rgb, gray*0x010101, median*0x010101,
                    edge.astype(np.uint32)*0xffffff, np.where(edge, 0xff0000, rgb)]
        inputs.append(rgb)
        expected.append(variants[frame % 5])
    paths = [SIM / (name + "-input.hex"), SIM / (name + "-gold.hex")]
    for path, arrays in zip(paths, (inputs, expected)):
        with path.open("w", encoding="ascii", newline="\n") as output:
            for array in arrays:
                pairs = array.reshape(-1,2).astype(np.uint64)
                values = pairs[:,0] | (pairs[:,1] << 24)
                output.writelines(f"{int(value):012x}\n" for value in values)
    return paths


def video(cases):
    compile_video()
    if "boundary" in cases:
        snapshot("mode_boundary", "tb_mode_boundary")
        simulate("mode_boundary", "MODE_BOUNDARY_PASS")
    parameters = {"small": (40,12,100,5,0,0), "fault": (40,12,100,3,1,0),
                  "reset": (40,12,100,3,0,1), "full": (1920,1080,1100,5,0,0),
                  "lowlight": (128,48,140,5,0,0)}
    for case in cases:
        if case == "boundary":
            continue
        width, height, ht, frames, fault, reset = parameters[case]
        print("VECTORS", case, width, height, frames, flush=True)
        paths = vectors(width, height, frames, case)
        name = "video_" + case
        snapshot(name, "tb_five_modes", dict(W=width,H=height,HT=ht,FRAMES=frames,FAULT_TEST=fault,RESET_TEST=reset))
        text = simulate(name, "FIVE_MODES_PASS", ["INPUT="+paths[0].as_posix(), "GOLD="+paths[1].as_posix()])
        result = dict(result="PASS", W=width,H=height,frames=frames,pixels=width*height*frames,
                      fault_test=bool(fault),reset_test=bool(reset),
                      vector_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                      completion=next(line for line in text.splitlines() if "FIVE_MODES_PASS" in line))
        (REPORT / ("sim-"+case+"-result.json")).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    cases = sys.argv[1:] or ["control", "boundary", "small", "fault", "reset", "full"]
    if "control" in cases:
        control()
    other = [case for case in cases if case != "control"]
    if other:
        video(other)
