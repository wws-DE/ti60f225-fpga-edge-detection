"""Register this verified bit and local reports, then wait for human acceptance."""
from pathlib import Path
import datetime,hashlib,json
from review_bitgen import review

work=Path(__file__).resolve().parents[1]
agent=work.parents[2]
task='TRACK4-V7-LOWLIGHT-EDGE-001'
session=task+'-20261021'
report=agent/'reports'/task
stage=agent/'artifacts/staging'/task
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
auth=read(report/'authorization.json')
assert auth['reply_exact']=='批准优化 v1，继续使用本地报告'
assert sha(report/'approved-design-v1.md')==auth['approved_design_sha256']
checks=read(report/'checks.json')
assert checks['state']=='SOFTWARE_CHECKED'
assert checks['warning_review_sha256']==sha(report/'warning-review.json')
pgm=read(sorted(report.glob('build-pgm-*.json'))[-1])
assert pgm['returncode']==0 and pgm['hardware_operation'] is False
assert read(report/'lowlight-focused-result.json')['result']=='PASS'
for case in ('small','fault','reset','lowlight','full'):
    assert read(report/f'sim-{case}-result.json')['result']=='PASS'
for path,h in read(report/'simulation-inputs.json').items():assert sha(Path(path))==h,path
for path,h in read(report/'lowlight-focused-result.json')['sources'].items():assert sha(Path(path))==h,path
normal={item['relative']:item['after_sha256'] for item in checks['source_normalizations']}
for item in read(report/'build-inputs.json')['files']:
    assert sha(work/item['relative'])==normal.get(item['relative'],item['sha256']),item['relative']
control=read(report/'control-result.json')
assert sha(Path(control['prior_result']))==control['prior_result_sha256']
for relative,h in control['source_sha256'].items():assert sha(work/relative)==h,relative
top=(work/'rtl/ti60f225_oob_top.v').read_text(encoding='utf-8')
old_top=(work.parent/'track4_v7_fullscreen_mode_001_20261021/rtl/ti60f225_oob_top.v').read_text(encoding='utf-8')
restored_top=top.replace("// 普通室内照度首版灵敏度；整帧快照仍由原桥接层负责。\nlocalparam [10:0] SOBEL_EDGE_THRESHOLD = 11'd96;\n",'').replace('.cfg_threshold(SOBEL_EDGE_THRESHOLD)',".cfg_threshold(11'd256)")
assert restored_top==old_top
review()
rollback=agent/'artifacts/staging/TRACK4-V7-FULLSCREEN-MODE-001/v7_fullscreen_mode_001_v1_20261021.bit'
assert sha(rollback)=='759ffa9c928561c7d6ad95d796be101e83495ba25794542141bfd524402cfeb9'
stage.mkdir(parents=True,exist_ok=False)
source=work/'outflow/ti60f225_oob.bit'
bit=stage/'v7_lowlight_edge_001_v1_20261021.bit'
bit.write_bytes(source.read_bytes())
assert bit.stat().st_size>2000000 and sha(bit)==sha(source)
(stage/'SHA256SUMS.txt').write_text(sha(bit)+'  '+bit.name+'\n',encoding='ascii')
final_inputs={}
for item in read(report/'build-inputs.json')['files']:
    p=work/item['relative'];final_inputs[item['relative']]=sha(p)
    target=report/'final-source-snapshot'/item['relative']
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
for p in (work/'tests').iterdir():
    if p.is_file():
        target=report/'final-source-snapshot/tests'/p.name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(report/'final-build-inputs.json').write_text(json.dumps(final_inputs,indent=2),encoding='utf-8')
evidence={p.name:sha(p) for p in report.iterdir() if p.is_file() and
          (p.suffix in ('.json','.log') or p.name=='approved-design-v1.md')}
(report/'evidence-manifest.json').write_text(json.dumps(dict(
    scope='Verification logs, structured reports, original approved design and final source manifest',
    sha256=evidence),indent=2),encoding='utf-8')
now=datetime.datetime.now().astimezone().isoformat()
manifest=dict(task_id=task,session_id=session,timestamp=now,state='WAITING_HUMAN_PROGRAM',
    design_version='v1',approved_design_sha256=auth['approved_design_sha256'],
    authorization_sha256=sha(report/'authorization.json'),project=str(work/'ti60f225_oob.xml'),
    tool='Efinity 2026.1.132',device='Ti60F225/I3',
    bit=dict(path=str(bit),bytes=bit.stat().st_size,sha256=sha(bit)),
    parameters=dict(sensor_3e08='0x81',sensor_3e09='0x2A',analog_gain_nominal=4.043,
                    prior_analog_gain_nominal=2.021,sobel_threshold=96,prior_sobel_threshold=256,
                    median_enabled=True,exposure_changed=False),
    setup_min_ns=checks['setup_min_ns'],hold_min_ns=checks['hold_min_ns'],resources=checks['resources'],
    mode_order=['COLOR','GRAY','MEDIAN','SOBEL','OVERLAY'],key_control_changed=False,
    full_resolution_compared_pixels=10368000,
    checks_sha256=sha(report/'checks.json'),inputs_manifest_sha256=sha(report/'final-build-inputs.json'),
    evidence_manifest_sha256=sha(report/'evidence-manifest.json'),
    rollback_bit=dict(path=str(rollback),sha256=sha(rollback)),
    hardware_programmed=False,hardware_passed=False,local_audit_exception=True,formal_state_updated=False)
(stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
guide=f'''# 普通室内光线边缘优化 v1：下载与验收

2026-10-21，任务 {task}。独立副本、软件仿真和Efinity构建完成，状态为 **WAITING_HUMAN_PROGRAM：等待人工下载和观察**。尚未测得实机准确度或读取传感器实际增益，不能把编译通过视作画面改善验收。

## 本次文件

- [本次JTAG下载bit]({bit.as_posix()})
- [Efinity2026.1.132工程]({(work/'ti60f225_oob.xml').as_posix()})
- [相机增益ROM：SENSOR_ANALOG_GAIN]({(work/'rtl/cam_i2c_ctrl/i2c/i2c_master_reg_rom.v').as_posix()})
- [顶层阈值：SOBEL_EDGE_THRESHOLD]({(work/'rtl/ti60f225_oob_top.v').as_posix()})
- [软件检查]({(report/'checks.json').as_posix()})、[弱光合成图样对照]({(report/'synthetic-lowlight-metrics.json').as_posix()})
- [回退：已验收按键切换的五模式bit]({rollback.as_posix()})

新bit大小：{bit.stat().st_size}字节。SHA256：`{sha(bit)}`。

## 改动及理想效果

| 项目 | 前版 | 本版 | 理想效果与观察点 |
|---|---|---|---|
| SC431HAI模拟增益 | 0x3E08/09=0x80/0x2A，手册约2.021倍 | 0x81/0x2A，手册约4.043倍 | 普通室内彩色和灰度更明亮、细节更可辨；同时检查噪声和过曝 |
| Sobel严格大于阈值 | 256 | 96 | 较弱轮廓更容易检出，Sobel与红边叠加使用同一份边缘结果 |
| 中值降噪与五模式按键 | 已验收版 | 保留 | 五种画面实时，顺序正确，长按只切换一次 |

曝光时长、相机帧长/窗口、镜像、DDR/HDMI时序和引脚均未调整。增益影响所有模式，阈值影响Sobel和红边叠加。此为固定参数首版，不是自动曝光或自动阈值；原图若仍有光学失焦/运动模糊，需要依据实际现象另行处理。

## 人工下载

1. 保持原先成功的供电、相机、HDMI和下载连接，关闭占用下载器的Debugger会话。
2. 打开Programmer，选择**本说明中的新bit**，不要继续使用旧的fullscreen或algorithm_bridge路径。
3. 沿用 `(local) Quad RS232-HS`、`JTAG`、设备 `1 - 0x10660a79` 和先前成功的频率（此前为10MHz），点击Program FPGA，等待成功日志。
4. 等相机启动、画面稳定；需要重启初始化时按原KEY0复位并等待恢复。JTAG为临时配置，断电后需重新下载。本次不做Flash固化。

## 本次只验收室内光线下的边缘改善

使用固定的普通室内照明，保持镜头距离、方向和目标不变；可选黑字白纸、书本外框或手掌轮廓。先记录旧五模式版，再加载新bit比较，不额外打强光。每次按KEY3并松开，顺序仍是彩色→灰度→中值→Sobel→红边叠加→彩色。

| 观察项 | 通过时理想表现 | 请反馈的问题 |
|---|---|---|
| 彩色/灰度 | 较前版明亮、目标细节较易辨认 | 仍偏暗、明显发白过曝或颜色异常 |
| Sobel | 目标轮廓比前版更完整，普通光线也能检出 | 轮廓仍大量缺失、闪烁或平面布满噪声边缘 |
| 红边叠加 | 红边贴合真实物体轮廓，较前版减少漏检 | 红边错位、背景满屏红点、边缘不稳定 |
| 原有操作 | 画面持续实时，模式顺序和长按行为保持 | 黑屏、停帧、错行、模式切换异常 |

请说明实际下载文件、普通照明下画面是否更亮、哪种轮廓改善/仍漏检、有无噪声或过曝；可提供同一场景的新旧照片。仅边缘数量增加不算准确度通过。明显异常时由你加载上方回退bit，保留现象供下一轮分析。

## 软件验证

- 原ROM和初始化状态机：两次完整164项、在途复位重启、末尾项及地址/数据保持通过；唯一配置数据变化为0x3E08。写完成由testbench模拟，不能证明实机ACK。
- Sobel数值：两个阈值各13组双像素，含平坦、正负/水平/垂直梯度、Δ24/25等边界，与独立整数参考一致；L1=96不检出，L1=100检出，旧阈值256下100不检出。
- 弱/模糊阶跃及受限噪声/孤立亮点合成图样：完整五模式与独立灰度/排序中值/Sobel参考一致；所定义平坦ROI零边缘。合成噪声不代表真实传感器噪声，未模拟增益和实际成像。
- 首有效帧阈值96、帧中配置扰动不改当前帧、同沿模式/VS采样、活动区复位、故障回退/恢复通过。
- 1920×1080五帧10,368,000像素及实际顶层串行化比对通过，桥接延迟4402周期；按键控制源码和消抖器哈希与已验收版一致，复用前版消抖测试证据。
- Efinity2026.1.132 map/interface/pnr/pgm软件流程完成；18组setup和18组hold关系均非负，最小分别{checks['setup_min_ns']}ns、{checks['hold_min_ns']}ns；XLR {checks['resources']['xlr']}、RAM {checks['resources']['ram']}、DSP {checks['resources']['dsp']}。
- 告警相对已验收五模式版的增删及既有CSI/DDR等提示见warning-review.json；不宣称消除了历史CDC/约束问题。构建输入、日志和最终源码快照保存在本任务报告目录。

本轮依用户批准使用本地报告、staging和追加审计；正式数据库/PROJECT_STATE/TASK_LEDGER未写入。原工程及旧bit保留；本次未操作真实板卡。交付后停止，待你验收再继续。
'''
(report/'交付与验收说明.md').write_text(guide,encoding='utf-8')
(work/'使用说明.md').write_text(guide,encoding='utf-8')
event=dict(project_id='FPGA_EDGE_TI60',session_id=session,task_id=task,event_id=session+'-002',
    timestamp=now,event_type='SOFTWARE_VERIFIED_ARTIFACT_REGISTERED',state='WAITING_HUMAN_PROGRAM',
    manifest=str(stage/'manifest.json'),bit_sha256=sha(bit),hardware_operation=False,formal_state_updated=False)
for folder in ('runtime/events/2026/10','side_effects/ledger'):
    with (agent/folder/('session-'+session+'.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
