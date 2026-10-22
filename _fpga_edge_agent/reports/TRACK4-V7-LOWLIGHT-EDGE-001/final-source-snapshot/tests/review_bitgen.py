"""Review the actual bit-generator warning against the accepted baseline."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET

def review():
    w=Path(__file__).resolve().parents[1];a=w.parents[2]
    r=a/'reports/TRACK4-V7-LOWLIGHT-EDGE-001'
    old=a/'reports/TRACK4-V7-FULLSCREEN-MODE-001'
    current=sorted(r.glob('build-pgm-*.log'))[-1]
    baseline=sorted(old.glob('build-pgm-*.log'))[-1]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    warnings=lambda p:[line.strip() for line in p.read_text(encoding='utf-8',errors='replace').splitlines() if re.match(r'\s*(WARNING|ERROR)',line)]
    assert warnings(current)==warnings(baseline)==['WARNING: cannot find correct IV value']
    ns={'e':'http://www.efinixinc.com/enf_proj'}
    node=ET.parse(w/'ti60f225_oob.xml').getroot()
    security={p.get('name'):p.get('value') for p in node.findall('e:security/e:param',ns)}
    assert security['enable_bitstream_encrypt']=='off'
    generator=w/'outflow/ti60f225_oob.pgm.out'
    text=generator.read_text(encoding='utf-8',errors='replace')
    assert not warnings(generator)
    assert 'Finished generating "outflow\\ti60f225_oob.hex"' in text
    record=dict(result='REVIEWED_INHERITED',warning=warnings(current),new_warnings=[],
        baseline_log=str(baseline),baseline_log_sha256=sha(baseline),current_log_sha256=sha(current),
        bitstream_encryption='off',generator_log=str(generator),generator_log_sha256=sha(generator),
        tool_source='C:/Efinity/2026.1/scripts/efx_run.py:934-939',
        assessment='The wrapper checks absent fixed IV while encryption is disabled; identical to accepted baseline. Actual bitstream generator has no warnings/errors and completes. No configuration/security changes were made.')
    (r/'bitgen-warning-review.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('BITGEN_WARNING_REVIEW_PASS')
    return record

if __name__=='__main__':review()
