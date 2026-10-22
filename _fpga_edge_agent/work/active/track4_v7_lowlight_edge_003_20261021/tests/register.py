"""Approved v3 local software delivery; no board or Flash access."""
from pathlib import Path
import datetime, hashlib, json, sys
from review_bitgen import review
sys.stdout.reconfigure(encoding='utf-8')
w=Path(__file__).resolve().parents[1];a=w.parents[2]
task='TRACK4-V7-LOWLIGHT-EDGE-003';session=task+'-20261021'
r=a/'reports'/task;stage=a/'artifacts/staging'/task
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
auth=read(r/'approval-v3.json');checks=read(r/'checks.json')
assert auth['reply_exact']=='批准优化v3'
assert sha(r/'approved-design-v3.md')==auth['approved_design_sha256']=='717cffb801e440de98a5932a924594f0a0897cdc5b1d7259e7de5355f0d65cbf'
assert checks['state']=='SOFTWARE_CHECKED' and sha(r/'warning-review.json')==checks['warning_review_sha256']
pgm=read(sorted(r.glob('build-pgm-*.json'))[-1]);assert pgm['returncode']==0 and not pgm['hardware_operation']
selection=read(r/'candidate-selection.json');quality=read(r/'candidate-quality.json')
assert selection['candidate']==quality['selected_candidate']=='B'
assert quality['result']=='SYNTHETIC_GATE_PASS' and quality['candidates']['B']['eligible']
assert selection['weak_min_diff']==18 and selection['threshold_drop']==0 and selection['threshold']==64
assert selection['quality_sha256']==sha(r/'candidate-quality.json') and selection['core_checks_sha256']==sha(r/'weak-core-result.json')
for name in ('weak-core-result.json','simulation-inputs.json','candidate-quality.json'):
    obj=read(r/name)
    hashes=obj if name=='simulation-inputs.json' else obj['sources' if name=='weak-core-result.json' else 'source_sha256']
    for p,h in hashes.items():assert sha(Path(p))==h,p
for case in ('small','fault','reset','lowlight','full'):assert read(r/f'sim-{case}-result.json')['result']=='PASS'
equiv=read(r/'v2-mode-012-equivalence.json');assert equiv['result']=='PASS' and equiv['pixels']==6220800
assert equiv['script_sha256']==sha(w/'tests/verify_modes.py')
for rel,h in equiv['unchanged_source_sha256'].items():assert sha(w/rel)==h,rel
control=read(r/'control-result.json');assert sha(Path(control['prior_result']))==control['prior_result_sha256']
for rel,h in control['source_sha256'].items():assert sha(w/rel)==h,rel
normal={x['relative']:x['after_sha256'] for x in checks['source_normalizations']}
inputs=read(r/'build-inputs.json');assert len(inputs['files'])==156
for item in inputs['files']:assert sha(w/item['relative'])==normal.get(item['relative'],item['sha256']),item['relative']
review()
rollback=a/'artifacts/staging/TRACK4-V7-LOWLIGHT-EDGE-002/v7_lowlight_edge_002_v2_20261021.bit'
assert sha(rollback)=='d152bfc760fac94cb87da6f4b0b3728eb5d927879262092cb1772f2658d65e32'
stage.mkdir(parents=True,exist_ok=False)
bit=stage/'v7_lowlight_edge_003_v3_20261021.bit';source=w/'outflow/ti60f225_oob.bit'
bit.write_bytes(source.read_bytes());assert sha(bit)==sha(source) and bit.stat().st_size>2000000
(stage/'SHA256SUMS.txt').write_text(sha(bit)+'  '+bit.name+'\n',encoding='ascii')
final_inputs={};test_inputs={}
for item in inputs['files']:
    p=w/item['relative'];final_inputs[item['relative']]=sha(p)
    target=r/'final-source-snapshot'/item['relative'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
for p in (w/'tests').iterdir():
    if p.is_file():
        target=r/'final-source-snapshot/tests'/p.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
        test_inputs[p.name]=sha(p)
(r/'final-build-inputs.json').write_text(json.dumps(final_inputs,indent=2),encoding='utf-8')
(r/'final-test-inputs.json').write_text(json.dumps(test_inputs,indent=2),encoding='utf-8')
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
manifest=dict(task_id=task,session_id=session,timestamp=now,state='WAITING_HUMAN_PROGRAM',design_version='优化v3',
    approved_design_sha256=auth['approved_design_sha256'],authorization_sha256=sha(r/'approval-v3.json'),
    project=str(w/'ti60f225_oob.xml'),tool='Efinity 2026.1.132',device='Ti60F225/I3',
    bit=dict(path=str(bit),bytes=bit.stat().st_size,sha256=sha(bit)),
    parameters=dict(sobel_threshold=64,base_min_diff=20,base_support=2,weak_enabled=True,weak_min_diff=18,weak_support=3,weak_threshold_drop=0,
        combination='OR; same dominant axis and sign; ties accept either',sensor_gain_registers='0x81/0x2A',median_enabled=True),
    setup_min_ns=checks['setup_min_ns'],hold_min_ns=checks['hold_min_ns'],resources=checks['resources'],
    mode_order=['COLOR','GRAY','MEDIAN','SOBEL','OVERLAY'],full_resolution_compared_pixels=10368000,
    checks_sha256=sha(r/'checks.json'),selection_sha256=sha(r/'candidate-selection.json'),
    inputs_manifest_sha256=sha(r/'final-build-inputs.json'),test_inputs_manifest_sha256=sha(r/'final-test-inputs.json'),
    rollback_bit=dict(path=str(rollback),sha256=sha(rollback)),
    hardware_programmed=False,hardware_passed=False,real_camera_accuracy_measured=False,local_audit_exception=True,formal_state_updated=False)
guide=f"""# 优化v3：弱细节补边交付与验收

2026-10-21，任务{task}，按用户“批准优化v3”实施。软件验证/构建通过，状态WAITING_HUMAN_PROGRAM；真实画质等待你验收。

## 文件与下载

- [新JTAG bit]({bit.as_posix()})
- [Efinity2026.1.132工程]({(w/'ti60f225_oob.xml').as_posix()})
- [桥接：选定候选B]({(w/'rtl/v7_algorithm_video_pair.sv').as_posix()})
- [frontend：参数透传]({(w/'algorithm/frontend/frontend_frame_pair.sv').as_posix()})
- [Sobel：弱支持及S6合并]({(w/'algorithm/frontend/sobel_pair.sv').as_posix()})
- [v2回退bit]({rollback.as_posix()})
- [候选筛选]({(r/'candidate-quality.json').as_posix()})、[软件检查]({(r/'checks.json').as_posix()})

新bit：{bit.stat().st_size}字节；SHA256 `{sha(bit)}`。

在Programmer中加载上方新bit，沿用成功设置：`(local) Quad RS232-HS`、`JTAG`、`1 - 0x10660a79`、10MHz。由你点击Program FPGA，确认成功后观察画面。JTAG配置断电后需重新下载。

## 本次变化与理想效果

v2的T64、D20、至少2/3同向支持分支完整保留；并行补充D18、三项全部同向支持的弱分支，两者取并集，Sobel与红边叠加共用最终edge。新分支默认关闭，只有目标桥接启用。六级Sobel、视频延迟4402周期、相机增益、中值和五模式按键沿用v2。

理想直线阶跃灰度差18、19可由弱分支补出；v2的D20支持无法放行这种理想窗口。目标是补回灰度/中值里仍可见的细小、低对比度轮廓。此为数学/合成性质，不能推成实机识别率百分比；本次没有单像素细化，原中值已经抹去的细节也无法恢复。

候选A(D16、弱阈值56)因背景误检超出批准上限被排除；交付采用B(D18、弱阈值64)。合成噪声各档93744个平坦ROI像素：±8为0→0，±16为49→56，±24为2754→2885，均在0/58/3304上限内。实际噪点和闪烁仍需你确认。

## 一次验收

保持普通室内光照、镜头位置和目标一致，与v2对照。用KEY3依次切换彩色→灰度→中值→Sobel→红边叠加。建议选择书本边框、小字笔画、手指轮廓、细线和圆弧，再看白墙或纸面。

| 验收项 | 理想效果 | 请描述的异常 |
|---|---|---|
| 弱/细小轮廓 | v2漏掉而中值可见的轮廓能补出 | 仍漏检、断裂、只增加背景亮点 |
| 相邻细线及圆弧 | 边界可区分、与物体贴合 | 粘连、异常增粗、断弧或红边错位 |
| 平坦背景 | 新增噪点仍可接受 | 大量新红点或明显闪烁 |
| 切换及视频 | 各模式持续实时，长按仅一次 | 停帧、黑屏、错行或模式异常 |

若效果变差，可由你加载上方v2回退bit。反馈时说明光照、目标、Sobel和叠加现象即可。

## 软件证据与范围

- 13组Sobel配置通过：A、B及关闭弱分支各257156组双像素；另10组阈值0/7/8/2047和输出kind边界各2180组。对真实v2核并行检查中心、梯度、身份、握手及edge包含关系；随机反压、长停顿、气泡、flush/frame_start/rst通过。
- 原几何定位容差1像素、8连通规则保持；弱竖线/横线/矩形改善，高对比七类轮廓完整连续；固定相邻三像素细线的四条边界保持分离，盐/椒经中值仍零边缘。没有放宽测试门槛。
- 小尺寸五模式、同沿VS/模式、帧配置稳定、首有效帧、故障回退及活动区复位通过；1080p五帧10368000像素与参考及实际顶层串行化比对通过，彩色/灰度/中值6220800像素与v2预期帧逐字节一致。
- Efinity map/interface/pnr及软件位流生成通过；18组setup、18组hold均非负，最小{checks['setup_min_ns']}ns/{checks['hold_min_ns']}ns。XLR {checks['resources']['xlr']}，RAM {checks['resources']['ram']}，DSP {checks['resources']['dsp']}。全部新增告警及历史告警差异见warning-review.json、flow-warning-delta.json、bitgen-warning-review.json。

仅三个业务源改变；正式数据库/PROJECT_STATE/TASK_LEDGER/Approval Manifest未写入，使用本次批准的本地报告和追加审计。
按[fpga-hardware-node-gate]({(a/'skills/fpga-hardware-node-gate/SKILL.md').as_posix()})的“停止在WAITING_HUMAN_PROGRAM”要求，交付后停止，等待你下载和验收；未操作FPGA/Flash/Debugger，硬件通过为false。理解验收未检验，不以考试阻塞交付。
"""
(r/'交付与验收说明.md').write_text(guide,encoding='utf-8');(w/'使用说明.md').write_text(guide,encoding='utf-8')
evidence={p.name:sha(p) for p in r.iterdir() if p.is_file() and p.name!='evidence-manifest.json'}
(r/'evidence-manifest.json').write_text(json.dumps(dict(scope='Root reports at registration; final build/test snapshots bound separately',sha256=evidence),indent=2),encoding='utf-8')
manifest['evidence_manifest_sha256']=sha(r/'evidence-manifest.json')
(stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
event=dict(project_id='FPGA_EDGE_TI60',session_id=session,task_id=task,event_id=session+'-003',timestamp=now,event_type='V3_SOFTWARE_VERIFIED_BIT_REGISTERED',state='WAITING_HUMAN_PROGRAM',bit_sha256=sha(bit),manifest=str(stage/'manifest.json'),hardware_operation=False,formal_state_updated=False)
for folder in ('runtime/events/2026/10','side_effects/ledger'):
    with (a/folder/('session-'+session+'.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
