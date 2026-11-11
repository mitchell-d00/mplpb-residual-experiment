"""Check retained experiment evidence and important read-contract distinctions."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
read = lambda name: json.loads((root/name).read_text())
for name, expected in read('fixture-digests.json').items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
rows = read('decisions.json'); labels = read('labels.json')
assert len(rows) == len(labels)*4 == 56
assert len({(r['case'], r['arm']) for r in rows}) == 56
def row(case, arm): return next(r for r in rows if r['case']==case and r['arm']==arm)
for arm in 'CD':
    for r in rows:
        if r['arm'] == arm:
            assert not r['retrieve']['answer_supported']
    r = row('unsupported', arm)
    assert r['retrieve']['kind'] == 'retrieved'
    assert r['ask']['kind'] == 'not_in_corpus'
    assert row('ambiguous', arm)['retrieve']['kind'] == 'ambiguous'
    for case in ('tampered','duplicate','stale_replaced','stale_withdrawn','withdrawn_chain'):
        assert row(case, arm)['retrieve']['kind'] == 'not_in_corpus'
    for case in ('tampered_successor','wrong_pin'):
        assert row(case, arm)['retrieve']['id'] == 'DOC-0001'
for c in labels:
    assert row(c['case'], 'C')['retrieve'] == row(c['case'], 'D')['retrieve']
    assert row(c['case'], 'C')['ask'] == row(c['case'], 'D')['ask']
logs = [json.loads(line) for line in (root/'commands.jsonl').read_text().splitlines()]
assert len(logs) == 132
for case in ('tampered','tampered_successor','wrong_pin','duplicate'):
    assert next(e for e in logs if e['tag']==case+':validate')['exit_code'] == 1
assert next(e for e in logs if e['tag']=='public:validate')['exit_code'] == 0
public = read('public-records.json')
assert [r['id'] for r in public if r['effective_status']=='current'] == ['SELF-0008']
for r in public:
    assert r['seal'] == r['computed_seal']
    assert hashlib.sha256((root/'public-system'/r['path']).read_bytes()).hexdigest() == r['file_sha256']
e = next(e for e in logs if e['tag']=='public:ask:What is MPLPB?')
answer = json.loads(e['stdout'])
assert answer['id']=='SELF-0008' and answer['answer_supported'] is True
print('PASS: 56 paired decisions; immutable fixture digests; refusal/retrieval distinction; public self-reference chain.')
