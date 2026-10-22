"""Register one approved A comparison bit; preserve the original failed gate."""
from pathlib import Path
import datetime,hashlib,json,sys
from review_bitgen import review
sys.stdout.reconfigure(encoding='utf-8')
w=Path(__file__).resolve().parents[1];a=w.parents[2]
task='TRACK4-V7-MEDIAN-DETAIL-001';session=task+'-20261022';r=a/'reports'/task
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
checks=load(r/'checks.json');accept=load(r/'accepted-noise-tradeoff.json');auth=load(r/'authorization.json')
scene_path=a/'observations/structured/TRACK4-V7-MEDIAN-DETAIL-001-scene-20261022.json'
scene=load(scene_path)
for photo in scene['images']:assert sha(Path(photo['archive_path']))==photo['sha256']
assert checks['state']=='SOFTWARE_CHECKED_WITH_ACCEPTED_NOISE_TRADEOFF'
assert checks['warning_review_sha256']==sha(r/'warning-review.json')
assert checks['acceptance_sha256']==sha(r/'accepted-noise-tradeoff.json')
assert sha(r/'approved-design-median-detail-v1.md')==auth['approved_design_sha256']=='6dc29c14b6a2ab364b9eee37107be94a03602f5818de4f8fb7da9862300203f5'
assert auth['reply_exact']=='批准' and auth['local_audit_exception']
assert accept['user_reply_exact']=='优先恢复弱细节，允许少量杂点增加后上板对比'
assert accept['card_sha256']==sha(r/'accepted-noise-tradeoff.md')
q=load(r/'candidate-quality.json');selection=load(r/'candidate-selection.json')
assert q['result']=='SYNTHETIC_GATE_FAIL' and q['selected_candidate'] is None
assert selection['candidate']=='A' and selection['difference']==16 and selection['similarity']==4
assert q['candidates']['A']['failures']==accept['accepted_failure_messages']
assert selection['quality_sha256']==accept['original_quality_sha256']==sha(r/'candidate-quality.json')
assert selection['acceptance_sha256']==sha(r/'accepted-noise-tradeoff.json')
for name in ('median-core-result.json','frontend-detail-result.json','extra-quality.json'):
 obj=load(r/name);assert obj['result']=='PASS',name
 for p,h in obj.get('sources',obj.get('source_sha256',{})).items():assert sha(Path(p))==h,p
 for p,h in obj.get('actual_baseline',{}).items():assert sha(Path(p))==h,p
for name in ('candidate-quality.json','reference-verification.json'):
 for p,h in load(r/name)['source_sha256'].items():assert sha(Path(p))==h,p
for p,h in load(r/'simulation-inputs.json').items():assert sha(Path(p))==h,p
for case in ('small','fault','reset','lowlight','full'):
 obj=load(r/f'sim-{case}-result.json');assert obj['result']=='PASS'
 for name,h in obj['vector_sha256'].items():assert sha(w/'sim_fullscreen'/name)==h
full=load(r/'sim-full-result.json');assert full['pixels']==10368000 and 'latency=6602' in full['completion']
assert load(sorted(r.glob('mode_boundary-run-*.json'))[-1])['returncode']==0
for flow in ('map','interface','pnr','pgm'):
 obj=load(sorted(r.glob(f'build-{flow}-*.json'))[-1]);assert obj['returncode']==0 and not obj['hardware_operation'] and Path(obj['cwd'])==w
equiv=load(r/'thin11-mode-01-equivalence.json');assert equiv['result']=='PASS' and equiv['pixels']==4147200
assert sha(Path(equiv['baseline']))==equiv['baseline_full_file_sha256'] and sha(Path(equiv['current']))==equiv['current_full_file_sha256']
control=load(r/'control-result.json');assert sha(Path(control['prior_result']))==control['prior_result_sha256']
for rel,h in control['source_sha256'].items():assert sha(w/rel)==h
static=load(r/'control-plane-static-check.json');assert static['result']=='FAILED_STATIC_VALIDATION' and 'schema.sql' in static['stderr']
for rel,h in static['unchanged_formal_files'].items():assert sha(a/rel)==h
base=Path(auth['baseline']);initial=load(r/'initial-inputs.json');assert len(initial)==161
for rel,h in initial.items():assert sha(base/rel)==h,rel
inputs=load(r/'build-inputs.json')['files'];assert len(inputs)==162
normal={x['relative']:x['after_sha256'] for x in checks['source_normalizations']}
for item in inputs:assert sha(w/item['relative'])==normal.get(item['relative'],item['sha256']),item['relative']
review()
rollback=a.parent/'FPGA_细化v1.1.bit';assert sha(rollback)=='c407819ed8fcbbf0bc5e9a9b38d219299d2f6489988d1c19dda036f44e21bd43'
source=w/'outflow/ti60f225_oob.bit';assert source.stat().st_size>2000000
stage=a/'artifacts/staging'/task;desktop=a.parent/'FPGA_保边中值v1_A.bit'
assert not stage.exists() and not desktop.exists(),'Inspect existing partial delivery before retry'
stage.mkdir(parents=True);now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
bit=stage/f'median_detail_v1_A_{now:%Y%m%d}.bit';bit.write_bytes(source.read_bytes());desktop.write_bytes(bit.read_bytes())
assert sha(bit)==sha(desktop)==sha(source)
(stage/'SHA256SUMS.txt').write_text(sha(bit)+'  '+bit.name+'\n',encoding='ascii')
final={};tests={}
for item in inputs:
 rel=item['relative'];p=w/rel;final[rel]=sha(p);dest=r/'final-source-snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
for p in (w/'tests').iterdir():
 if p.is_file():
  tests[p.name]=sha(p);dest=r/'final-source-snapshot/tests'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
write(r/'final-build-inputs.json',final);write(r/'final-test-inputs.json',tests)
manifest=dict(task_id=task,session_id=session,timestamp=now.isoformat(),state='WAITING_HUMAN_PROGRAM',
 design_version='保边中值v1 A：用户接受已知噪声取舍的对比版',project=str(w/'ti60f225_oob.xml'),tool='Efinity2026.1.132',device='Ti60F225/I3',
 scene_observation=dict(path=str(scene_path),sha256=sha(scene_path)),original_design_sha256=auth['approved_design_sha256'],authorization_sha256=sha(r/'authorization.json'),
 acceptance_sha256=sha(r/'accepted-noise-tradeoff.json'),quality_state='ACCEPTED_WITH_KNOWN_NOISE_TRADEOFF',original_quality_result='SYNTHETIC_GATE_FAIL',
 accepted_correlated_noise_cases=accept['accepted_correlated_cases'],bit=dict(path=str(bit),desktop_path=str(desktop),bytes=bit.stat().st_size,sha256=sha(bit)),
 parameters=dict(candidate='A',difference=16,similarity=4,median_stages=9,video_latency_cycles=6602,sobel_threshold=64,thin_mode=1,sensor_configuration='unchanged'),
 setup_min_ns=checks['setup_min_ns'],hold_min_ns=checks['hold_min_ns'],resources=checks['resources'],mode_order=['COLOR','GRAY','MEDIAN','SOBEL','OVERLAY'],
 full_video_compared_pixels=10368000,unchanged_first_two_mode_pixels=4147200,checks_sha256=sha(r/'checks.json'),inputs_manifest_sha256=sha(r/'final-build-inputs.json'),
 test_inputs_manifest_sha256=sha(r/'final-test-inputs.json'),rollback_bit=dict(path=str(rollback),sha256=sha(rollback)),control_plane_static_result=static['result'],
 hardware_programmed=False,hardware_passed=False,real_camera_accuracy_measured=False,formal_state_updated=False,local_audit_exception=True)
guide=f'''# 保边中值v1 A：细节优先的上板对比版

{now:%Y-%m-%d}，任务{task}，状态WAITING_HUMAN_PROGRAM。这是原已批准A（D16/S4）的实现；按你随后选择“优先恢复弱细节，允许少量杂点增加后上板对比”，接受下述已知取舍。没有把原数学噪声失败改写为通过。

## 文件和烧录

- [桌面烧录文件]({desktop.as_posix()})
- [登记的同一bit]({bit.as_posix()})
- [Efinity2026.1.132工程]({(w/'ti60f225_oob.xml').as_posix()})
- [新增保边中值模块]({(w/'algorithm/frontend/median9_detail_pair.sv').as_posix()})
- [细化v1.1回退]({rollback.as_posix()})
- [完整软件检查]({(r/'checks.json').as_posix()})、[用户接受的取舍]({(r/'accepted-noise-tradeoff.md').as_posix()})

bit大小{bit.stat().st_size}字节，SHA256 `{sha(bit)}`。桌面、登记和工程outflow文件字节相同。

由你在Programmer选择FPGA_保边中值v1_A.bit，沿用已成功的 `(local) Quad RS232-HS`、JTAG、`1 - 0x10660a79`、10MHz，手动Program FPGA并确认完成日志。JTAG断电后需重新配置；本轮没有Flash固化。

## 改了什么与理想效果

普通九点中值并行检查原灰度窗口：某方向两端与中心相近（差≤4），其他六点为同极性异色背景（差≥16且背景跨度≤8），真实内部像素才恢复该中心原灰度，其余仍用原中值。原中值排序器、Sobel T64/D20/D18、空间连接、细化B、相机曝光/增益、时钟/引脚和五模式顺序沿用。九级中值和显示6602周期不变。

希望中值模式保留更多原灰度中可见的窄线，部分小轮廓能继续传给Sobel/红边。它只保护特定细线结构，弯曲/短端点、复杂背景或较缓的大范围明暗过渡仍可能漏检；不承诺一版解决普通光照、近距离及全部断点。

你的照片确认灰度→中值→Sobel，部分补光、约80–95cm，并希望木纹、细线、外轮廓都保留。照片中部分木纹在中值仍可见，说明后续还需要弱边判定优化；屏摄未用来拟合原始像素阈值。木纹白边不能一律叫噪点，物理接缝两侧也可能确实各有一条边。

## 已知取舍

原数学质量报告仍为SYNTHETIC_GATE_FAIL。A三档普通平坦噪声（每档93744像素）0/47/2735，满足原0/49/2735上限；四个相关噪声用例分别0→2、24→26、40→42、22→32（每幅ROI31248像素）。这些是合成测试数，不代表实机噪点比例。你已允许少量新增杂点后对比，因此只接受这四项已披露增加；其他门槛继续检查。B未交付。质量状态为ACCEPTED_WITH_KNOWN_NOISE_TRADEOFF，实际可接受程度仍由本次人工验收决定。

## 一次验收

先在相同目标、距离和普通室内照明下，与细化v1.1对照；不额外补光是后续真实目标条件。再从当前约80–95cm逐步靠近，在灰度仍看清的距离比较。

| 观察项 | 理想效果 | 请反馈的异常 |
|---|---|---|
| 灰度→中值细节 | 原先被删除的部分窄木纹、小笔画得以保留 | 灰度清楚，中值仍消失；或细线被打断 |
| Sobel/红边 | 部分新保留细线能形成贴合的边缘 | 中值已清楚，Sobel仍漏检；新增断点/错位 |
| 平坦背景 | 少量杂点在你可接受范围内 | 明显闪烁、成片杂边、噪点影响观察 |
| 近距离/实时性 | 灰度清楚范围内尽量保留细节；五模式实时、长按一次 | 模式异常、黑屏、停帧、错行 |

KEY3仍按彩色→灰度→中值→Sobel→红边叠加循环。反馈时区分“中值消失”和“中值可见但Sobel不出边”，并注明有无补光及大致距离。杂点不可接受时由你手动加载上方细化v1.1回退。本次交付后停止等验收，不同时改弱边/断点算法。

## 软件证据与限制

- 数学标量/向量90542组窗口、61440图像像素/控制/边界组合一致；未改下游重建在503808个基线像素逐位一致。原82几何、256细线、8阶跃、9平坦噪声、18相关噪声、6脉冲，以及补充768组位置/窄线/转角/分支/带噪几何与邻线分离完成；只有已接受四项相关噪声例外。
- 新模块三尺寸各12000组双像素窗口，真实原median9并行比较，包含长停顿、关闭保护/中值、复位/启动/flush；完整frontend六配置、18完整帧、取消/坏输入/恢复、状态计数、默认关闭与owner兼容通过。
- 小尺寸五模式、同沿帧切换、故障和复位、低光合成图及1080p五帧10368000像素、实际serializer通过；彩色/灰度4147200像素与原版预期逐字节相同。中值/Sobel/红边按新参考比较，未沿用不成立的旧边缘子集断言。
- Efinity map/interface/pnr/位流生成完成；18setup/18hold关系非负，最小{checks['setup_min_ns']}ns/{checks['hold_min_ns']}ns；XLR{checks['resources']['xlr']}、RAM{checks['resources']['ram']}、DSP{checks['resources']['dsp']}。告警逐项记录于warning-review.json与bitgen-warning-review.json；历史告警没有宣称全解决。
- 首次布局布线XLR25229超过25000，保存原实现后共享四个相对邻居对的比较，改为24991；数值/接口/九级不变，局部/前端/全视频和构建全部重跑。综合日志会追加多轮，告警比较按当前完整轮次与构建时间绑定，不把旧实现消息当新增。
- 首次局部TB把跨job累计数误当单job计数（672对512），改为验证各job的计数增量后重跑全部三配置；RTL及数学期望未因此改变，原失败日志保留。
- 控制面静态校验因已有database/schema.sql缺失未完成；继续已批准的本地报告/追加审计，正式DB/PROJECT_STATE/TASK_LEDGER/APPROVAL_MANIFEST不变，不宣称数据库或硬件验收通过。

依[fpga-hardware-node-gate]({(a/'skills/fpga-hardware-node-gate/SKILL.md').as_posix()})“停止在WAITING_HUMAN_PROGRAM”，等待你手动下载观察；没有自动FPGA/Flash/Debugger操作。
'''
(r/'交付与验收说明.md').write_text(guide,encoding='utf-8');(w/'使用说明.md').write_text(guide,encoding='utf-8')
write(r/'delivery-identity.json',dict(bit=manifest['bit'],source_bit=str(source),state=manifest['state'],quality_state=manifest['quality_state'],hardware_passed=False))
evidence={p.name:sha(p) for p in r.iterdir() if p.is_file() and p.name!='delivery-evidence-manifest.json'}
write(r/'delivery-evidence-manifest.json',dict(scope='Root files at this delivery; original precheck evidence-manifest remains preserved',sha256=evidence))
manifest['delivery_evidence_manifest_sha256']=sha(r/'delivery-evidence-manifest.json');write(stage/'manifest.json',manifest)
event=dict(project_id='FPGA_EDGE_TI60',session_id=session,task_id=task,event_id=session+'-006',timestamp=now.isoformat(),event_type='MEDIAN_A_BIT_REGISTERED_USER_ACCEPTED_NOISE_TRADEOFF',state='WAITING_HUMAN_PROGRAM',bit_sha256=sha(bit),manifest=str(stage/'manifest.json'),hardware_operation=False,formal_state_updated=False)
for folder in ('runtime/events/2026/10','side_effects/ledger'):
 with (a/folder/('session-'+session+'.jsonl')).open('a',encoding='utf-8') as out:out.write(json.dumps(event,ensure_ascii=False)+'\n')
for rel,h in final.items():assert sha(w/rel)==sha(r/'final-source-snapshot'/rel)==h
for rel,h in tests.items():assert sha(w/'tests'/rel)==sha(r/'final-source-snapshot/tests'/rel)==h
for rel,h in evidence.items():assert sha(r/rel)==h
assert sha(bit)==sha(desktop)==sha(source)
print(json.dumps(manifest,ensure_ascii=False,indent=2));print('FROZEN_DELIVERY_VERIFIED')
