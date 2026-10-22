"""Validate the exact software build and expose warnings for review."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

work = Path(__file__).resolve().parents[1]
agent = work.parents[2]
report = agent / "reports/TRACK4-V7-LOWLIGHT-EDGE-004-REV1"
baseline = agent / "work/active/track4_v7_lowlight_edge_003_20261021"
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
    for line in read(folder/"outflow/ti60f225_oob.warn.log").splitlines():
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
focused = json.loads(read(report/"diagonal-core-result.json"))
assert focused["result"] == "PASS"
for path, expected in focused["sources"].items():
    assert sha(Path(path)) == expected, path
selection=json.loads(read(report/'candidate-selection.json'))
quality=json.loads(read(report/'candidate-quality.json'))
assert selection['candidate']=='A' and selection['threshold']==64 and selection['diagonal_min_diff']==18 and selection['context_threshold_drop']==16
assert quality['result']=='SYNTHETIC_GATE_PASS' and quality['selected_candidate']=='A'
assert sha(report/'candidate-quality.json')==selection['quality_sha256']
assert sha(report/'diagonal-core-result.json')==selection['core_checks_sha256']
assert json.loads(read(report/'v3-mode-012-equivalence.json'))['result']=='PASS'
frontend=json.loads(read(report/'frontend-context-result.json'));assert frontend['result']=='PASS'
for path,expected in frontend['sources'].items():assert sha(Path(path))==expected,path
reuse=json.loads(read(report/'context-evidence-reuse.json'));assert reuse['result']=='PASS_REUSED_UNCHANGED'
assert sha(Path(reuse['prior_result']))==reuse['prior_result_sha256']
for path,expected in reuse['shared_source_sha256'].items():assert sha(work/path)==expected,path
for case in ("small","fault","reset","lowlight","full"):
    assert json.loads(read(report/("sim-"+case+"-result.json")))["result"] == "PASS"
for path, expected in json.loads(read(report/"simulation-inputs.json")).items():
    assert sha(Path(path)) == expected, path
result = dict(state="AWAITING_WARNING_REVIEW",setup_min_ns=min(x[3] for x in setup),
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
    result.update(state="SOFTWARE_CHECKED", warning_review_sha256=sha(report/"warning-review.json"))
(report/"checks.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ("setup_relationships","hold_relationships")},indent=2))
print("ADDED WARNINGS",json.dumps(delta["added"],indent=2))
