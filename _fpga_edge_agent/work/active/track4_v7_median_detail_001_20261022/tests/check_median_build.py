"""Validate the exact software build and expose warnings for review."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import datetime

work = Path(__file__).resolve().parents[1]
agent = work.parents[2]
report = agent / "reports/TRACK4-V7-MEDIAN-DETAIL-001"
baseline = agent / "work/active/track4_v7_edge_thin_001_rev1_20261021"
read = lambda p: p.read_text(encoding="utf-8-sig", errors="replace")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

for stage in ("map", "interface", "pnr"):
    record = json.loads(read(sorted(report.glob(f"build-{stage}-*.json"))[-1]))
    assert record["returncode"] == 0, stage

normalizations = []
for item in json.loads(read(report/"build-inputs.json"))["files"]:
    path = work/item["relative"]
    if sha(path) != item["sha256"]:
        assert item["relative"] == "ti60f225_oob.xml", item["relative"]
        before = report/"source-snapshot"/item["relative"]
        assert sha(before) == item["sha256"]
        def semantics(node):
            return (node.tag, sorted(node.attrib.items()), (node.text or "").strip(),
                    (node.tail or "").strip(), tuple(semantics(child) for child in node))
        # efx_run rewrites the declaration and namespace/attribute ordering.
        # Every actual element, attribute, text value and child order must match.
        assert semantics(ET.parse(before).getroot()) == semantics(ET.parse(path).getroot())
        normalizations.append(dict(relative=item["relative"], before_sha256=item["sha256"],
                                   after_sha256=sha(path), reason="Efinity XML serialization; exact element/attribute/value/order equivalence"))

def relationships(path):
    text = read(path).split("Setup (Max) Clock Relationship")[1].split("Hold (Min) Clock Relationship")
    def parse(section):
        return [(a,b,float(c),float(d)) for a,b,c,d in re.findall(
            r"^\s*(\S+)\s+(\S+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+\(R-R\)", section, re.M)]
    return parse(text[0]), parse(text[1].split("NOTE:")[0])

setup, hold = relationships(work/"outflow/ti60f225_oob.timing.rpt")
old_setup, old_hold = relationships(baseline/"outflow/ti60f225_oob.timing.rpt")
for actual, old in ((setup,old_setup),(hold,old_hold)):
    assert len(actual) == len(old) == 18
    assert {x[:3] for x in actual} == {x[:3] for x in old}
    assert min(x[3] for x in actual) >= 0, actual

peri = ET.parse(work/"ti60f225_oob.peri.xml").getroot()
ns = {"p":"http://www.efinixinc.com/peri_design_db"}
gpios = peri.findall(".//p:comp_gpio",ns)
key = [node for node in gpios if node.get("name") == "key_mode_n"]
assert len(key) == 1 and key[0].get("gpio_def") == "GPIOL_03"
assert key[0].get("io_standard") == "3.3 V LVCMOS"
assert key[0][0].get("pull_option") == "weak pullup"
assert sum(node.get("gpio_def") == "GPIOL_03" for node in gpios) == 1
netlist = read(work/"outflow/ti60f225_oob.map.v")
head = "fullscreen_mode_control/mode_key/key_sync_first~FF"
assert len(re.findall(r"EFX_FF\s+\\" + re.escape(head) + r"\s", netlist)) == 1
assert "key_mode_n" in netlist and "fullscreen_mode_control/mode_key/key_sync_second" in netlist
expected_pad_note = ("WARNING  : Synchronizer chain starting at cell " + head +
                     " is driven by a non-sequential source key_mode_n:inpad [FlowMsg::SyncHeadDrivenByNonSeq]")
pad_notes = []
for name in ("ti60f225_oob.place.out", "ti60f225_oob.route.out"):
    text = read(work/"outflow"/name)
    for line in text.splitlines():
        if ("WARNING" in line or "ERROR" in line) and ("key_mode_n" in line or "fullscreen_mode_control" in line):
            # A physical asynchronous button is deliberately driven by an input
            # pad. Recognize only this exact message; retain it for review.
            assert line.strip() == expected_pad_note, line
            pad_notes.append(dict(file=name,message=line.strip()))

place = read(work/"outflow/ti60f225_oob.place.rpt")
resources = {key:int(re.search(r"^"+re.escape(label)+r":\s*(\d+)",place,re.M)[1])
             for key,label in (("xlr","XLRs"),("ram","Memory Blocks"),("dsp","DSP Blocks"))}
old_place=read(baseline/"outflow/ti60f225_oob.place.rpt")
old_xlr=int(re.search(r"^XLRs:\s*(\d+)",old_place,re.M)[1])
assert resources["xlr"]<=25000
assert resources["ram"] <= 185 and resources["dsp"] == 0, resources

def warnings(folder):
    counts = Counter()
    log=folder/"outflow/ti60f225_oob.warn.log"
    whole=read(log);sections=whole.split("// Efinity Synthesis Started")
    assert len(sections)>=2, str(log)
    section=sections[-1]
    stamp=re.search(r"^// (.+)$",section,re.M)[1].strip()
    started=datetime.datetime.strptime(stamp,"%b %d, %Y %H:%M:%S")
    build_report=report if folder==work else agent/"reports/TRACK4-V7-EDGE-THIN-001-REV1"
    build=json.loads(read(sorted(build_report.glob('build-map-*.json'))[-1]))
    lo=datetime.datetime.fromisoformat(build['started_at']).replace(tzinfo=None)
    hi=datetime.datetime.fromisoformat(build['ended_at']).replace(tzinfo=None)
    assert lo-datetime.timedelta(seconds=2)<=started<=hi+datetime.timedelta(seconds=2),(log,stamp,lo,hi)
    scope=dict(path=str(log),sha256=sha(log),synthesis_sections=len(sections)-1,selected='last complete synthesis run',selected_timestamp=stamp,selected_section_sha256=__import__('hashlib').sha256(section.encode('utf-8')).hexdigest(),build_record=build)
    (report/("map-warning-scope-current.json" if folder==work else "map-warning-scope-baseline.json")).write_text(json.dumps(scope,indent=2),encoding='utf-8')
    for line in section.splitlines():
        if line.startswith("[EFX-"):
            line = re.sub(r"\([^\n]*?[/\\](rtl|ip|algorithm)[/\\](.*?):\d+\)",
                          lambda m:"("+m[1]+"/"+m[2].replace("\\","/")+":LINE)",line)
            line = re.sub(r"\([^\n]*?[/\\]debug_top.v:(\d+)\)",r"(debug_top.v:\1)",line)
            counts[line] += 1
    return counts

new, old = warnings(work), warnings(baseline)
delta = dict(added=list((new-old).elements()), removed=list((old-new).elements()))
(report/"warning-delta.json").write_text(json.dumps(delta,indent=2),encoding="utf-8")
assert json.loads(read(report/"control-result.json"))["result"] == "PASS"
for name in ('median-core-result.json','frontend-detail-result.json','extra-quality.json'):
    evidence=json.loads(read(report/name));assert evidence['result']=='PASS',name
    for path,expected in evidence.get('sources',evidence.get('source_sha256',{})).items(): assert sha(Path(path))==expected,path
    for path,expected in evidence.get('actual_baseline',{}).items(): assert sha(Path(path))==expected,path
reference=json.loads(read(report/'reference-verification.json'))
assert reference['result']=='SCALAR_VECTOR_AGREE_FAILURE_CONFIRMED'
for path,expected in reference['source_sha256'].items():assert sha(Path(path))==expected,path
selection=json.loads(read(report/'candidate-selection.json'))
quality=json.loads(read(report/'candidate-quality.json'))
acceptance=json.loads(read(report/'accepted-noise-tradeoff.json'))
assert selection['candidate']=='A' and selection['difference']==16 and selection['similarity']==4
assert selection['quality_state']==acceptance['quality_state']=='ACCEPTED_WITH_KNOWN_NOISE_TRADEOFF'
assert quality['result']=='SYNTHETIC_GATE_FAIL' and quality['selected_candidate'] is None
assert quality['candidates']['A']['failures']==acceptance['accepted_failure_messages']
assert [(x['old_edges'],x['new_edges']) for x in acceptance['accepted_correlated_cases']]==[(0,2),(24,26),(40,42),(22,32)]
assert selection['quality_sha256']==reference['quality_sha256']==acceptance['original_quality_sha256']==sha(report/'candidate-quality.json')
assert selection['acceptance_sha256']==sha(report/'accepted-noise-tradeoff.json')
assert sha(report/'accepted-noise-tradeoff.md')==acceptance['card_sha256']
for path,expected in quality['source_sha256'].items():assert sha(Path(path))==expected,path
assert json.loads(read(report/'thin11-mode-01-equivalence.json'))['result']=='PASS'
control=json.loads(read(report/'control-result.json'))
assert sha(Path(control['prior_result']))==control['prior_result_sha256']
for path,expected in control['source_sha256'].items():assert sha(work/path)==expected,path
boundary=json.loads(read(sorted(report.glob('mode_boundary-run-*.json'))[-1]));assert boundary['returncode']==0
for case in ("small","fault","reset","lowlight","full"):
    assert json.loads(read(report/("sim-"+case+"-result.json")))["result"] == "PASS"
for path, expected in json.loads(read(report/"simulation-inputs.json")).items():
    assert sha(Path(path)) == expected, path
result = dict(state="AWAITING_WARNING_REVIEW",quality_state="ACCEPTED_WITH_KNOWN_NOISE_TRADEOFF",acceptance_sha256=sha(report/"accepted-noise-tradeoff.json"),setup_min_ns=min(x[3] for x in setup),
              hold_min_ns=min(x[3] for x in hold),setup_relationships=setup,hold_relationships=hold,
              resources=resources,source_normalizations=normalizations,key_gpio="A3/GPIOL_03 3.3V weak pullup",
              synchronizer_head_matches=1,async_pad_notes=pad_notes,hardware_programmed=False,hardware_passed=False)
if "--accept-review" in sys.argv:
    review = json.loads(read(report/"warning-review.json"))
    flow = json.loads(read(report/"flow-warning-delta.json"))
    assert review["reviewed_map_added"] == delta["added"]
    assert review["reviewed_flow_added"] == flow["added"]
    assert not review["unreviewed"]
    assert review["source_normalizations"] == normalizations
    result.update(state="SOFTWARE_CHECKED_WITH_ACCEPTED_NOISE_TRADEOFF", warning_review_sha256=sha(report/"warning-review.json"))
(report/"checks.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ("setup_relationships","hold_relationships")},indent=2))
print("ADDED WARNINGS",json.dumps(delta["added"],indent=2))
