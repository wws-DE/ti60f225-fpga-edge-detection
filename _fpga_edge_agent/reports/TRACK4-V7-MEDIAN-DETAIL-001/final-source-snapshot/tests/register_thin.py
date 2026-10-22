"""Freeze approved thin v1.1 software delivery; never access a board."""
from pathlib import Path
import datetime, hashlib, json, sys
from review_bitgen import review
sys.stdout.reconfigure(encoding='utf-8')
w=Path(__file__).resolve().parents[1];a=w.parents[2]
task='TRACK4-V7-EDGE-THIN-001-REV1';session=task+'-20261021'
r=a/'reports'/task;stage=a/'artifacts/staging'/task
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,obj:p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
auth=load(r/'authorization.json');checks=load(r/'checks.json')
assert auth['reply_exact']=='批准' and auth['local_audit_exception'] and not auth['formal_state_updated']
assert sha(r/'approved-design-thin-v1.1.md')==auth['approved_design_sha256']=='fb16f0eef8b7d5fd2c924b7d0cd3475728ef2d493c7837f8c4b20777df935e7c'
assert checks['state']=='SOFTWARE_CHECKED' and sha(r/'warning-review.json')==checks['warning_review_sha256']
static=load(r/'control-plane-static-check.json')
assert static['result']=='FAILED_STATIC_VALIDATION' and 'database' in static['stderr'] and 'schema.sql' in static['stderr']
for rel,h in static['unchanged_formal_files'].items():assert sha(a/rel)==h,rel
for flow in ('map','interface','pnr','pgm'):
 record=load(sorted(r.glob(f'build-{flow}-*.json'))[-1]);assert record['returncode']==0 and not record['hardware_operation'] and Path(record['cwd'])==w
selection=load(r/'candidate-selection.json');quality=load(r/'candidate-quality.json')
assert selection['candidate']==quality['selected_candidate']=='B' and selection['thin_mode']==1
assert quality['result']=='SYNTHETIC_GATE_PASS' and quality['candidates']['B']['eligible'] and not quality['candidates']['B']['failures']
assert selection['threshold']==64 and selection['diagonal_min_diff']==18 and selection['context_threshold_drop']==16
assert selection['quality_sha256']==sha(r/'candidate-quality.json') and selection['core_checks_sha256']==sha(r/'thin-core-result.json')
for name in ('thin-core-result.json','frontend-thin-result.json','reference-verification.json','candidate-quality.json','simulation-inputs.json'):
 obj=load(r/name)
 hashes=obj if name=='simulation-inputs.json' else obj.get('sources',obj.get('source_sha256',{}))
 assert hashes,name
 for p,h in hashes.items():assert sha(Path(p))==h,p
 for p,h in obj.get('actual_baseline',{}).items():assert sha(Path(p))==h,p
for case in ('small','fault','reset','lowlight','full'):
 result=load(r/f'sim-{case}-result.json');assert result['result']=='PASS'
 for filename,h in result['vector_sha256'].items():assert sha(w/'sim_fullscreen'/filename)==h,filename
boundary=load(sorted(r.glob('mode_boundary-run-*.json'))[-1]);assert boundary['returncode']==0
full=load(r/'sim-full-result.json');assert full['pixels']==10368000 and 'latency=6602' in full['completion']
equiv=load(r/'v41-mode-012-equivalence.json');assert equiv['result']=='PASS' and equiv['pixels']==6220800
assert sha(Path(equiv['baseline']))==equiv['baseline_full_file_sha256'] and sha(Path(equiv['current']))==equiv['current_full_file_sha256']
control=load(r/'control-result.json');assert sha(Path(control['prior_result']))==control['prior_result_sha256']
for rel,h in control['source_sha256'].items():assert sha(w/rel)==h,rel
baseline=Path(auth['baseline']);baseline_manifest=a/'reports/TRACK4-V7-LOWLIGHT-EDGE-004-REV1/final-build-inputs.json'
assert sha(baseline_manifest)==auth['baseline_manifest_sha256']=='944b77610c16d2269340a917ab2869270089d280c3a68fc720f78e470a00ac4b'
old_inputs=load(baseline_manifest);assert len(old_inputs)==159
for rel,h in old_inputs.items():assert sha(baseline/rel)==h,rel
normal={x['relative']:x['after_sha256'] for x in checks['source_normalizations']}
inputs=load(r/'build-inputs.json');assert len(inputs['files'])==162
for item in inputs['files']:assert sha(w/item['relative'])==normal.get(item['relative'],item['sha256']),item['relative']
changed=sorted(rel for rel,h in old_inputs.items() if sha(w/rel)!=h)
assert changed==['algorithm/frontend/frontend_frame_pair.sv','rtl/v7_algorithm_video_pair.sv','ti60f225_oob.xml'],changed
review()
rollback=a/'artifacts/staging/TRACK4-V7-LOWLIGHT-EDGE-004-REV1/v7_lowlight_edge_004_v4_1_20261021.bit'
assert sha(rollback)=='c194210fb0ff0e3f5e81da6746557b36e280fb16c0aa3ec24fa057e5c25ac77f'
source=w/'outflow/ti60f225_oob.bit';assert source.stat().st_size>2000000
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)));stamp=now.strftime('%Y%m%d')
bit=stage/f'edge_thin_v1_1_{stamp}.bit';desktop=a.parent/'FPGA_细化v1.1.bit'
assert not stage.exists() and not desktop.exists(), 'Inspect existing delivery before attempting registration again'
stage.mkdir(parents=True)
bit.write_bytes(source.read_bytes());desktop.write_bytes(bit.read_bytes())
assert sha(bit)==sha(desktop)==sha(source)
(stage/'SHA256SUMS.txt').write_text(sha(bit)+'  '+bit.name+'\n',encoding='ascii')
final_inputs={};test_inputs={}
for item in inputs['files']:
 p=w/item['relative'];final_inputs[item['relative']]=sha(p)
 target=r/'final-source-snapshot'/item['relative'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
for p in (w/'tests').iterdir():
 if p.is_file():
  target=r/'final-source-snapshot/tests'/p.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());test_inputs[p.name]=sha(p)
write(r/'final-build-inputs.json',final_inputs);write(r/'final-test-inputs.json',test_inputs)
manifest=dict(task_id=task,session_id=session,timestamp=now.isoformat(),state='WAITING_HUMAN_PROGRAM',design_version='细化v1.1',approved_design_sha256=auth['approved_design_sha256'],authorization_sha256=sha(r/'authorization.json'),project=str(w/'ti60f225_oob.xml'),tool='Efinity 2026.1.132',device='Ti60F225/I3',bit=dict(path=str(bit),desktop_path=str(desktop),bytes=bit.stat().st_size,sha256=sha(bit)),parameters=dict(candidate='B',thin_mode=1,sobel_threshold=64,diagonal_min_diff=18,context_threshold_drop=16,video_latency_cycles=6602,rule='v4.1 edge AND direction-junction-protected axis-only peak retention',diagonal_handling='retain v4.1 edges',sensor_gain='unchanged 0x81/0x2A'),setup_min_ns=checks['setup_min_ns'],hold_min_ns=checks['hold_min_ns'],resources=checks['resources'],mode_order=['COLOR','GRAY','MEDIAN','SOBEL','OVERLAY'],full_resolution_compared_pixels=full['pixels'],unchanged_first_three_mode_pixels=equiv['pixels'],checks_sha256=sha(r/'checks.json'),selection_sha256=sha(r/'candidate-selection.json'),inputs_manifest_sha256=sha(r/'final-build-inputs.json'),test_inputs_manifest_sha256=sha(r/'final-test-inputs.json'),baseline_manifest_sha256=sha(baseline_manifest),unchanged_original_inputs=156,changed_existing_inputs=changed,new_modules=['algorithm/edge/edge_thin_pack_pair.sv','algorithm/edge/edge_thin_window_pair.sv','algorithm/edge/edge_thin_filter_pair.sv'],rollback_bit=dict(path=str(rollback),desktop_path=str(a.parent/'FPGA_v4.1.bit'),sha256=sha(rollback)),hardware_programmed=False,hardware_passed=False,real_camera_accuracy_measured=False,local_audit_exception=True,formal_state_updated=False,control_plane_static_result=static['result'],control_plane_static_evidence_sha256=sha(r/'control-plane-static-check.json'))
guide=f'''# 细化 v1.1：直边收窄与交点保护

{now.strftime('%Y-%m-%d')}，任务 {task}。按用户“批准”实施，算法/视频仿真和位流生成已完成；状态 WAITING_HUMAN_PROGRAM，实际画质待人工验收。

## 文件

- [桌面烧录文件]({desktop.as_posix()})
- [登记的同一 bit]({bit.as_posix()})
- [Efinity 2026.1.132 工程]({(w/'ti60f225_oob.xml').as_posix()})
- [本版核心判定代码]({(w/'algorithm/edge/edge_thin_filter_pair.sv').as_posix()})
- [v4.1 回退文件]({(a.parent/'FPGA_v4.1.bit').as_posix()})
- [完整软件检查]({(r/'checks.json').as_posix()})、[数学质量检查]({(r/'candidate-quality.json').as_posix()})

大小 {bit.stat().st_size} 字节，SHA256 `{sha(bit)}`。桌面文件、登记文件、工程 outflow 文件逐字节相同。

## 本次修改与理想效果

在 v4.1 原边点基础上，只对方向一致的横竖直边保留局部梯度峰值，减少相邻重复边点。同方向梯度相等时按固定前后规则留一个峰；真实邻居存在不同方向 seed 时保留交点。原断点补出的点、边界缺邻居和斜边均保守保留。没有降低阈值、增加相机增益或新建边点；灰度、中值和彩色图像不改。

理想效果是 Sobel 白边与红色叠加中的横竖直线更细，位置仍贴合原物体，Y/T/十字交点、角点和细字笔画继续连接。斜线、曲线转角附近可能保留较宽边，不能宣称全图都是单像素。本节点先验收“边线变细”；弱暗轮廓恢复、锯齿和断点的进一步改善仍待后续节点。

## 一次上板验收

由你在 Programmer 的 Bitstream File 选择上方 **FPGA_细化v1.1.bit**，沿用已成功设置：`(local) Quad RS232-HS`、`JTAG`、`1 - 0x10660a79`、10 MHz，再点击 Program FPGA 并确认完成日志。JTAG 是临时配置，断电需重新下载；本轮没有 Flash 固化。

同一室内光照、镜头距离与目标下，与 FPGA_v4.1.bit 对照；KEY3 顺序仍为彩色→灰度→中值→Sobel→红边叠加，长按只切一次。

| 观察目标 | 理想效果 | 需反馈的异常 |
|---|---|---|
| 书本/纸张横竖直边 | 重复宽边减少，边线更细且贴合 | 边线整体消失、错位或明显闪烁 |
| 小字、细线、Y/T/十字交点 | 原有笔画、分支连接保留，相邻细线分开 | 新断裂、角点丢失、分支被切开 |
| 斜线和圆弧 | 连续性接近 v4.1，保守保留 | 明显新增缺口或轮廓丢失 |
| 背景与实时显示 | 噪点不增加，五模式实时、红边贴合 | 背景杂边增加、错行、黑屏或停帧 |

如有明显退步，由你改选 v4.1 回退文件。反馈时说明目标、光照、发生问题的模式与位置。本次交付后停止，等这一个功能验收再继续。

## 已完成的软件验证

- 独立标量与向量参考对比各 700416 像素；逐像素 v1⇒v1.1⇒v4.1 子集关系通过。70 幅原几何与 12 幅新增几何、相邻细线、短笔画、噪声检查通过；弱 Y 形恢复 92/92 几何覆盖和一条完整连通轮廓。
- 固定 A/B 候选按原批准规则选择 B：A 没有测得要求的额外斜边收窄，B 保留斜边。8 组正反横竖阶跃从 2 像素变为 1 像素。每档 93744 像素固定噪声 ROI，v4.1 的 0/50/2843 变为 B 的 0/49/2735；这是合成测试，不是实机降噪率。
- RTL 过滤器每候选 8448 组双像素窗口，停顿/有效性/原 v4.1 子集检查通过。打包、扩宽 RAM、窗口和过滤链 13 组配置共 65 帧、39 次复位/启动/取消打断；逐个 432 bit 窗口和坐标比对通过。完整 frontend 6 组配置、18 帧和状态/故障恢复，以及原实现默认关闭和外部 owner 兼容检查通过。
- 边界切换、小尺寸、故障、复位、低光合成图及 1080p 五帧 10368000 像素、实际顶层串行化对比通过；延迟仍 6602 周期。前三模式 6220800 像素与 v4.1 预期逐字节相同，实际 RTL 由完整视频仿真核对。按键消抖/控制器复用哈希一致的既有证据，集成本次重测。
- 低光用例改为本节点的细化目标：弱斜边保持、模糊直边单峰、平坦噪声/脉冲不增加；独立梯度对比保留。它不代表提高了低光灵敏度。
- Efinity map/interface/pnr/位流生成通过，18 setup/18 hold 均非负，最小余量 {checks['setup_min_ns']} ns/{checks['hold_min_ns']} ns；XLR {checks['resources']['xlr']}、RAM {checks['resources']['ram']}、DSP {checks['resources']['dsp']}。综合告警无新增，1287 条布局布线告警与 v4.1 一致；历史告警未宣称全部解决。位流包装器继承 IV 提示，实际位流生成器无告警/错误，详见 warning-review.json 与 bitgen-warning-review.json。
- 首次完整视频仿真被会话中断且无完成记录，该记录未算通过；仅完整视频项重新运行后取得 PASS。基线 159 项哈希不变；本版构建 162 项，其中原有 3 项修改、156 项保持，新增 3 个细化模块。源码、测试、构建日志和产物身份均冻结登记。

控制面静态校验因现有 database/schema.sql 缺失而未完成，原始错误见 control-plane-static-check.json；没有将该项标为通过，也未修补数据库结构。按已批准例外继续本地报告/追加审计，正式数据库和 PROJECT_STATE/TASK_LEDGER/APPROVAL_MANIFEST 未改。依照 [fpga-hardware-node-gate]({(a/'skills/fpga-hardware-node-gate/SKILL.md').as_posix()}) 的“停止在 WAITING_HUMAN_PROGRAM”要求，此处等待你手动下载验收。没有自动烧写、Flash 或调试器操作，硬件通过为 false。
'''
(r/'交付与验收说明.md').write_text(guide,encoding='utf-8');(w/'使用说明.md').write_text(guide,encoding='utf-8')
write(r/'delivery-identity.json',dict(state='WAITING_HUMAN_PROGRAM',bit=manifest['bit'],source_bit=str(source),identical_sha256=sha(source),baseline_159_inputs_unchanged=True,hardware_passed=False))
evidence={p.name:sha(p) for p in r.iterdir() if p.is_file() and p.name!='evidence-manifest.json'}
write(r/'evidence-manifest.json',dict(scope='Root report files at registration; final source and test snapshots bound by separate manifests',sha256=evidence));manifest['evidence_manifest_sha256']=sha(r/'evidence-manifest.json')
write(stage/'manifest.json',manifest)
event=dict(project_id='FPGA_EDGE_TI60',session_id=session,task_id=task,event_id=session+'-003',timestamp=now.isoformat(),event_type='THIN_V1_1_SOFTWARE_VERIFIED_BIT_REGISTERED',state='WAITING_HUMAN_PROGRAM',bit_sha256=sha(bit),manifest=str(stage/'manifest.json'),desktop_bit=str(desktop),hardware_operation=False,formal_state_updated=False)
for folder in ('runtime/events/2026/10','side_effects/ledger'):
 with (a/folder/('session-'+session+'.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
# Verify frozen delivery, evidence and snapshots immediately without changing any report.
assert sha(desktop)==sha(bit)==sha(source)
for rel,h in final_inputs.items():assert sha(w/rel)==sha(r/'final-source-snapshot'/rel)==h
for rel,h in test_inputs.items():assert sha(w/'tests'/rel)==sha(r/'final-source-snapshot/tests'/rel)==h
for rel,h in evidence.items():assert sha(r/rel)==h,rel
assert sha(a.parent/'FPGA_v4.1.bit')==sha(rollback)
print(json.dumps(manifest,ensure_ascii=False,indent=2));print('FROZEN_DELIVERY_VERIFIED')
