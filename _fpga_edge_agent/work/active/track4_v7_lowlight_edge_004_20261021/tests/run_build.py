"""Approved Efinity software flows only. Does not connect to hardware."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
work = Path(__file__).resolve().parents[1]
agent = work.parents[2]
report = agent / "reports/TRACK4-V7-LOWLIGHT-EDGE-003"
tool = Path("C:/Efinity/2026.1")
env = os.environ.copy()
env.pop("PYTHONUTF8", None)
env.pop("PYTHONIOENCODING", None)
env.update(EFINITY_HOME=tool.as_posix(), PYTHONHOME=str(tool/"python311"),
           EFXPT_HOME=str(tool/"pt"), EFXPGM_HOME=str(tool/"pgm"), EFXDBG_HOME=str(tool/"debugger"),
           EFXIPM_HOME=str(tool/"ipm"), EFXSVF_HOME=str(tool/"debugger/svf_player"),
           EFXSERDESDBG_HOME=str(tool/"debugger/serdes_debug_tool"),
           EFINITY_USER_DIR_INI=str(Path(env["LOCALAPPDATA"])/"efinity/user_dir.ini"),
           QT_PLUGIN_PATH=str(tool/"python311"), QT_QPA_PLATFORM_PLUGIN_PATH=str(tool/"python311/platforms"),
           QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu")
env["PATH"] = os.pathsep.join(str(tool/p) for p in ["python311/bin","bin","pgm/bin","debugger/bin","scripts"]) + os.pathsep + env["PATH"]

for stage in sys.argv[1:]:
    if stage not in ("map", "interface", "pnr", "pgm"):
        raise ValueError(stage)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    log = report / f"build-{stage}-{stamp}.log"
    output = log.with_suffix(".json")
    argv = [str(tool/"python311/bin/python.exe"), str(tool/"scripts/efx_run.py"),
            "ti60f225_oob.xml", "--flow", stage, "--output_dir", "outflow",
            "--work_dir", "work_compile", "--timeout", "10800"]
    record = dict(stage=stage, argv=argv, cwd=str(work), started_at=datetime.datetime.now().astimezone().isoformat(), hardware_operation=False)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("START", stage, flush=True)
    with log.open("wb") as stream:
        result = subprocess.run(argv, cwd=work, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=11000)
    record.update(returncode=result.returncode, ended_at=datetime.datetime.now().astimezone().isoformat())
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("DONE", stage, result.returncode, str(log), flush=True)
    if result.returncode:
        print(log.read_text(encoding="utf-8", errors="replace")[-5000:], flush=True)
        raise SystemExit(result.returncode)
