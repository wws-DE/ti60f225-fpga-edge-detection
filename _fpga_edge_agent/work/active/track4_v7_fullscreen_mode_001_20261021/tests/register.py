"""Register the verified bit locally and stop for human programming."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

work = Path(__file__).resolve().parents[1]
agent = work.parents[2]
task = "TRACK4-V7-FULLSCREEN-MODE-001"
session = task + "-20261021"
report = agent/"reports"/task
stage = agent/"artifacts/staging"/task
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = read(report/"checks.json")
assert checks["state"] == "SOFTWARE_CHECKED"
assert checks["warning_review_sha256"] == sha(report/"warning-review.json")
pgm = read(sorted(report.glob("build-pgm-*.json"))[-1])
assert pgm["returncode"] == 0 and pgm["hardware_operation"] is False
assert read(report/"authorization.json")["reply_exact"] == "批准此次修改"
stage.mkdir(parents=True, exist_ok=False)
source = work/"outflow/ti60f225_oob.bit"
bit = stage/"v7_fullscreen_mode_001_v1_20261021.bit"
shutil.copy2(source, bit)
assert sha(source) == sha(bit)
(stage/"SHA256SUMS.txt").write_text(sha(bit)+"  "+bit.name+"\n",encoding="ascii")

final_inputs = {}
for item in read(report/"build-inputs.json")["files"]:
    path = work/item["relative"]
    final_inputs[item["relative"]] = sha(path)
(report/"final-build-inputs.json").write_text(json.dumps(final_inputs,indent=2),encoding="utf-8")
final_snapshot = report/"final-source-snapshot"
final_snapshot.mkdir()
for relative in final_inputs:
    target = final_snapshot/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(work/relative,target)
for path in (work/"tests").glob("*"):
    if path.suffix in (".sv",".py"):
        target = final_snapshot/"tests"/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path,target)

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
manifest = dict(task_id=task,session_id=session,timestamp=now,state="WAITING_HUMAN_PROGRAM",
                design_version="v1",authorization_sha256=sha(report/"authorization.json"),
                project=str(work/"ti60f225_oob.xml"),tool="Efinity 2026.1.132",device="Ti60F225/I3",
                bit=dict(path=str(bit),bytes=bit.stat().st_size,sha256=sha(bit)),
                setup_min_ns=checks["setup_min_ns"],hold_min_ns=checks["hold_min_ns"],resources=checks["resources"],
                key3="A3/GPIOL_03,3.3V,active-low",mode_order=["COLOR","GRAY","MEDIAN","SOBEL","OVERLAY"],
                fixed_sobel_threshold=256,debounce_ms=20,full_resolution_compared_pixels=10368000,
                checks_sha256=sha(report/"checks.json"),inputs_manifest_sha256=sha(report/"final-build-inputs.json"),
                rollback_bit=str(agent/"artifacts/downloads/github-releases/handoff-2026-10-19/v7_algorithm_bridge_001_v1_20261018.bit"),
                hardware_programmed=False,hardware_passed=False,local_audit_exception=True,formal_state_updated=False)
(stage/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

guide = f"""# KEY3 五种全屏算法：本次交付与验收

2026-10-21，任务 {task}，设计 v1。代码和软件验证完成；实机状态为 **等待人工下载和观察**。

## 文件

- [本次JTAG下载文件]({bit.as_posix()})
- [Efinity2026.1.132工程]({(work/'ti60f225_oob.xml').as_posix()})
- [五模式控制器]({(work/'rtl/v7_fullscreen_mode_control.sv').as_posix()})
- [顶层接线]({(work/'rtl/ti60f225_oob_top.v').as_posix()})
- [软件检查结果]({(report/'checks.json').as_posix()})

bit大小：{bit.stat().st_size}字节。SHA256：`{sha(bit)}`。

## 下载和本次操作

关闭已连接的Debugger会话。在Programmer选择本次bit、`(local) Quad RS232-HS`、JTAG、设备`1 - 0x10660a79`；沿用先前成功下载的JTAG频率。点击Program FPGA，等下载完成和画面稳定。该过程是临时JTAG配置，断电后须重新下载。

| 次序 | 操作/预期全屏画面 |
|---|---|
| 初始 | 彩色原图 |
| KEY3第1次 | 灰度 |
| KEY3第2次 | 3×3中值滤波后的灰度 |
| KEY3第3次 | Sobel黑白边缘，白色为边缘 |
| KEY3第4次 | 彩色原图加红色边缘 |
| KEY3第5次 | 回到彩色原图 |

KEY3低有效，有20ms消抖；按住只切换一次，松开再按才继续。KEY0保持整机复位，等待原启动过程后回到彩色。KEY1/KEY2本次没有接入控制，阈值固定为256。

## 一次功能验收

1. 先确认初始全屏彩色实时；逐次按下、松开KEY3，核对上表五种模式及循环。
2. 各模式下移动镜头前物体，确认画面持续更新，无失去HDMI信号、黑屏、停帧或明显错行。
3. 在彩色模式长按KEY3约1秒，应只进入灰度一次；松开约0.1秒后再按，应进入中值。
4. 按KEY0复位，等待画面恢复后应为彩色。
5. 反馈实际下载文件、下载日志、模式顺序、长按/复位结果及异常发生在哪一步；有异常时保留现象，不继续叠加功能。

本次交付后停止，等待上述功能验收。尚未自动操作开发板，也未记录本次bit为硬件通过。

## 已完成的软件证据

- XSim2025.2：N=2/4/31和生产N=1,485,000的消抖、启动按住、抖动、长按、释放重按及循环通过。
- 同沿模式更新/VS采样规则、非法状态回退、活动区复位、故障回退与后续恢复通过。
- 1920×1080五帧，10,368,000像素与独立整数参考逐位一致；实际顶层串行化逻辑也参与核对。此为合成图样仿真，不代替摄像实机验收。
- Efinity map/interface/pnr/pgm全部通过；18组setup及18组hold关系均与基线对应，最小setup {checks['setup_min_ns']}ns、hold {checks['hold_min_ns']}ns。
- KEY3实际生成引脚为A3/GPIOL_03、3.3V、弱上拉；首级同步器D匹配唯一。资源XLR {checks['resources']['xlr']}、RAM {checks['resources']['ram']}、DSP {checks['resources']['dsp']}。
- 新增的异步输入同步器首级提示已逐项复核；继承CSI/DDR等历史告警的范围和记录保存在warning-review.json，不声称消除了全部历史CDC/约束问题。

## 软件过程中修正的配置问题

首次Windows batch调用把参数等号拆分，已修正受控参数引用；首次peri.xml按键节点放在全局配置/总线之后，不符合厂商XSD顺序，已移至正确位置并通过XSD和接口检查。原失败日志完整保留。Efinity重写工程XML的声明/属性排列已逐元素、属性、值和子节点顺序验证语义相同。最终源码快照、输入哈希和构建日志均在本报告目录。

## 回退

需要回退时由用户加载[原五分区发布版]({Path(manifest['rollback_bit']).as_posix()})。原工程和旧构建产物保留；本次没有升级IP、安装软件或改写正式数据库/硬件节点状态。
"""
(report/"交付与验收说明.md").write_text(guide,encoding="utf-8")
(work/"使用说明.md").write_text(guide,encoding="utf-8")
event = dict(project_id="FPGA_EDGE_TI60",session_id=session,task_id=task,event_id=session+"-002",
             timestamp=now,event_type="SOFTWARE_VERIFIED_ARTIFACT_REGISTERED",state="WAITING_HUMAN_PROGRAM",
             manifest=str(stage/"manifest.json"),bit_sha256=sha(bit),hardware_operation=False,formal_state_updated=False)
for dest in (agent/"runtime/events/2026/10"/("session-"+session+".jsonl"),
             agent/"side_effects/ledger"/("session-"+session+".jsonl")):
    with dest.open("a",encoding="utf-8") as stream:
        stream.write(json.dumps(event,ensure_ascii=False)+"\n")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
