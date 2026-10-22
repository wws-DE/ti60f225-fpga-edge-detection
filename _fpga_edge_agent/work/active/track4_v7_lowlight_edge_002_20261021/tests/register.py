"""Local v2 software delivery. Never programs FPGA or Flash."""
from pathlib import Path
import datetime,hashlib,json,sys
from review_bitgen import review

sys.stdout.reconfigure(encoding='utf-8')
w=Path(__file__).resolve().parents[1];a=w.parents[2]
task='TRACK4-V7-LOWLIGHT-EDGE-002';session=task+'-20261021'
r=a/'reports'/task;stage=a/'artifacts/staging'/task
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
auth=read(r/'authorization.json');checks=read(r/'checks.json')
assert auth['reply_exact']=='批准优化v2'
assert sha(r/'approved-design-v2.md')==auth['approved_design_sha256']=='98df9817e492e80baa2df5be0e4b20f3c0f1e12e530859ca29760d3c502a0683'
assert checks['state']=='SOFTWARE_CHECKED' and sha(r/'warning-review.json')==checks['warning_review_sha256']
pgm=read(sorted(r.glob('build-pgm-*.json'))[-1]);assert pgm['returncode']==0 and not pgm['hardware_operation']
selection=read(r/'candidate-selection.json');quality=read(r/'candidate-quality.json')
assert selection['selected_d']==quality['selected_d']==20 and quality['result']=='SYNTHETIC_GATE_PASS'
assert selection['quality_sha256']==sha(r/'candidate-quality.json') and selection['core_checks_sha256']==sha(r/'coherent-core-result.json')
assert quality['reference_sha256']==sha(w/'tests/reference_v2.py') and quality['benchmark_sha256']==sha(w/'tests/quality_candidates.py')
for p,h in read(r/'coherent-core-result.json')['sources'].items():assert sha(Path(p))==h,p
for p,h in read(r/'simulation-inputs.json').items():assert sha(Path(p))==h,p
for case in ('small','fault','reset','lowlight','full'):assert read(r/f'sim-{case}-result.json')['result']=='PASS'
assert read(r/'v1-mode-012-equivalence.json')['result']=='PASS'
control=read(r/'control-result.json');assert sha(Path(control['prior_result']))==control['prior_result_sha256']
for rel,h in control['source_sha256'].items():assert sha(w/rel)==h,rel
normal={item['relative']:item['after_sha256'] for item in checks['source_normalizations']}
for item in read(r/'build-inputs.json')['files']:assert sha(w/item['relative'])==normal.get(item['relative'],item['sha256']),item['relative']
review()
rollback=a/'artifacts/staging/TRACK4-V7-LOWLIGHT-EDGE-001/v7_lowlight_edge_001_v1_20261021.bit'
assert sha(rollback)=='32d81151f7c7e6bda332daa4a08103adb255965a667247d084c97dca53520a6f'
stage.mkdir(parents=True,exist_ok=False)
bit=stage/'v7_lowlight_edge_002_v2_20261021.bit';source=w/'outflow/ti60f225_oob.bit'
bit.write_bytes(source.read_bytes());assert sha(bit)==sha(source) and bit.stat().st_size>2000000
(stage/'SHA256SUMS.txt').write_text(sha(bit)+'  '+bit.name+'\n',encoding='ascii')
final_inputs={}
for item in read(r/'build-inputs.json')['files']:
    p=w/item['relative'];final_inputs[item['relative']]=sha(p)
    target=r/'final-source-snapshot'/item['relative'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
for p in (w/'tests').iterdir():
    if p.is_file():
        target=r/'final-source-snapshot/tests'/p.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(r/'final-build-inputs.json').write_text(json.dumps(final_inputs,indent=2),encoding='utf-8')
now=datetime.datetime.now().astimezone().isoformat()
manifest=dict(task_id=task,session_id=session,timestamp=now,state='WAITING_HUMAN_PROGRAM',design_version='优化v2',
    approved_design_sha256=auth['approved_design_sha256'],authorization_sha256=sha(r/'authorization.json'),
    project=str(w/'ti60f225_oob.xml'),tool='Efinity 2026.1.132',device='Ti60F225/I3',
    bit=dict(path=str(bit),bytes=bit.stat().st_size,sha256=sha(bit)),
    parameters=dict(sobel_threshold=64,coherence_enabled=True,minimum_directional_difference=20,support='at least 2 of 3 on dominant gradient axis; sign aligned; ties accept either axis',sensor_gain_registers='0x81/0x2A',median_enabled=True),
    setup_min_ns=checks['setup_min_ns'],hold_min_ns=checks['hold_min_ns'],resources=checks['resources'],
    mode_order=['COLOR','GRAY','MEDIAN','SOBEL','OVERLAY'],full_resolution_compared_pixels=10368000,
    checks_sha256=sha(r/'checks.json'),selection_sha256=sha(r/'candidate-selection.json'),
    inputs_manifest_sha256=sha(r/'final-build-inputs.json'),rollback_bit=dict(path=str(rollback),sha256=sha(rollback)),
    hardware_programmed=False,hardware_passed=False,real_camera_accuracy_measured=False,local_audit_exception=True,formal_state_updated=False)
guide=f'''# 弱轮廓与方向一致性抑噪：优化v2交付和验收

2026-10-21，任务{task}。本次按“批准优化v2”执行。软件验证和构建完成，状态 **WAITING_HUMAN_PROGRAM**，等待你下载并观察；尚未验证真实摄像头画质。

## 文件

- [新JTAG下载bit]({bit.as_posix()})
- [Efinity2026.1.132工程]({(w/'ti60f225_oob.xml').as_posix()})
- [顶层阈值64]({(w/'rtl/ti60f225_oob_top.v').as_posix()})
- [桥接选定D20]({(w/'rtl/v7_algorithm_video_pair.sv').as_posix()})
- [Sobel方向支持旁路]({(w/'algorithm/frontend/sobel_pair.sv').as_posix()})
- [候选质量结果]({(r/'candidate-quality.json').as_posix()})、[软件检查]({(r/'checks.json').as_posix()})
- [v1回退bit]({rollback.as_posix()})

bit大小：{bit.stat().st_size}字节；SHA256：`{sha(bit)}`。

## 本版效果与边界

阈值96→64；新增主梯度方向上的同号支持：相邻三行/三列至少两项灰度跨度≥20。强度判断与方向支持同时满足才输出edge。Sobel和红边叠加共用这份edge；目标是检出连续弱轮廓，并减少孤立杂点。v1增益0x81/0x2A、曝光、中值、五模式按键和视频时序沿用。

理想直线阶跃最低灰度差由v1的25变为20，属于数学边界，不能解释为真实识别率提高某个百分比。相机增益本轮没有继续提高，不以进一步放大源噪声来提亮。算法仍可能过滤极短真实细节，相关噪声或规则纹理也可能满足支持规则；细线、角点和曲线需要重点观察。

## 人工下载

保持此前成功的供电、相机/HDMI和USB下载连接，关闭占用下载器的Debugger会话。在Programmer中选本说明的**新bit**、`(local) Quad RS232-HS`、`JTAG`、设备`1 - 0x10660a79`，沿用此前成功的10MHz设置。点击Program FPGA，待成功日志和相机画面稳定。JTAG配置断电后需重新下载。本次不做Flash固化。

## 一次功能验收

在同一普通室内光照下，保持相机位置和目标不变，先记录v1，再下载v2比较。每次按下并松开KEY3，仍按彩色→灰度→中值→Sobel→红边叠加→彩色循环。

| 检查项 | 理想表现 | 请反馈的异常 |
|---|---|---|
| 书本边框、字迹、手掌等弱轮廓 | 比v1更易检出、连续程度更好 | 轮廓仍缺失、出现新断裂或细节被过度滤掉 |
| 白墙、纸面等平坦背景 | Sobel杂点、红点和闪烁减少 | 背景噪点更多或大面积红色 |
| 斜线、圆弧、细线、角点 | 轮廓保持连续并贴合物体 | 明显断线、缺角、细线消失或红边错位 |
| 模式与视频 | 持续实时、模式顺序正确、长按仅切一次 | 停帧、黑屏、错行或按键异常 |

部分合成图样的边缘响应会变细；仅凭亮点数量减少不能判轮廓丢失，也不能仅凭数量增多判准确率提升。请结合实际目标的完整轮廓和噪声位置反馈。明显异常时由你加载上方v1回退，保留同场景照片或现象，待下一轮分析。

## 软件证据及限制

- D16和D20，以及关闭新功能的v1兼容路径：每个配置201,760组双像素，数值/中心/坐标/标志逐位通过；随机反压、长停顿、flush、frame_start、rst和输入气泡通过。原v1 Sobel核并行比较确认梯度、中心和握手不变。
- 合成几何：Δ20连续横/竖/矩形弱边界覆盖改善；高对比斜线和曲线几何点全部在1像素定位带内被连续输出覆盖；环形内外边界分别检查。测试输入没有真实相机噪声或曝光。
- D16因噪声增加被排除。选定D20：±8噪声档误边缘0→0；±16档193→49；±24档4403→2754。每档93,744个平坦ROI像素，固定种子431/432/433。不能外推为实机降噪或准确率百分比。
- 初筛曾错误使用边缘像素总数代理“轮廓保留”，把变细的连续轮廓判丢失。原脚本、失败结果及诊断完整保留；随后按设计的真实几何覆盖/连通性纠正测量方法，输入、候选、算法和噪声门槛均未放宽，过程见设计I节。
- 弱光图样五模式、首有效帧阈值64、帧内配置稳定、同沿模式/VS、故障回退和活动区复位通过。1080p五帧10,368,000像素和实际顶层串行化比对通过，视频延迟4402周期。彩色/灰度/中值共6,220,800像素与v1参考完全一致。
- Efinity map/interface/pnr/pgm软件流程通过；18组setup和18组hold均非负，最小{checks['setup_min_ns']}ns/{checks['hold_min_ns']}ns；XLR {checks['resources']['xlr']}，RAM {checks['resources']['ram']}，DSP {checks['resources']['dsp']}。告警复核见warning-review.json及bitgen-warning-review.json，不代签全部历史CDC/约束或真实硬件结果。

本轮只修改独立副本中批准的四个业务文件及必要tests/说明。v1源码和bit保留，正式数据库/PROJECT_STATE/TASK_LEDGER未写入，全部使用批准的本地报告及追加审计。交付后停止等待你验收。
'''
(r/'交付与验收说明.md').write_text(guide,encoding='utf-8');(w/'使用说明.md').write_text(guide,encoding='utf-8')
evidence={p.name:sha(p) for p in r.iterdir() if p.is_file() and p.name!='evidence-manifest.json'}
(r/'evidence-manifest.json').write_text(json.dumps(dict(scope='All top-level report files at registration; sources bound by final input manifest and final-source-snapshot',sha256=evidence),indent=2),encoding='utf-8')
manifest['evidence_manifest_sha256']=sha(r/'evidence-manifest.json')
(stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
event=dict(project_id='FPGA_EDGE_TI60',session_id=session,task_id=task,event_id=session+'-003',timestamp=now,event_type='V2_SOFTWARE_VERIFIED_BIT_REGISTERED',state='WAITING_HUMAN_PROGRAM',bit_sha256=sha(bit),manifest=str(stage/'manifest.json'),hardware_operation=False,formal_state_updated=False)
for folder in ('runtime/events/2026/10','side_effects/ledger'):
    with (a/folder/('session-'+session+'.jsonl')).open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
