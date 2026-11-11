"""Build isolated fixtures, freeze labels, run fresh readers, retain all evidence."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = '257e54a51edac272eb6b2441457f38a40485ee4d'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, obj): path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    source = a.source.resolve(); out = a.out.resolve()
    if out.exists() and any(out.iterdir()): raise SystemExit('Use an empty output directory; prior evidence is never overwritten.')
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != PIN: raise SystemExit('Unexpected MPLPB commit: ' + commit)
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True)
    if dirty: raise SystemExit('MPLPB tracked files must be clean')
    sys.path.insert(0, str(source))
    from mplpb_combined import ledger as L
    from mplpb_combined.record import upsert_meta, parse_page
    env = dict(os.environ, PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
    logs = []; labels = []; counter = 0

    def execute(argv, tag, cwd=HERE):
        p = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        logs.append({'tag':tag, 'argv':[str(x) for x in argv], 'cwd':str(cwd), 'exit_code':p.returncode,
                     'stdout':p.stdout, 'stderr':p.stderr})
        with (out / 'commands.jsonl').open('a') as fh: fh.write(json.dumps(logs[-1]) + '\n')
        return p

    def page(root, subject='kettle', body=None, **kw):
        nonlocal counter
        counter += 1
        return L.write(root, title='Source', scope=subject+' color',
                       body=body or 'The '+subject+' color is blue.',
                       owner='Synthetic fixture; not historical author testimony',
                       when=f'2026-11-11T00:{counter:02d}:00Z', **kw)

    def edit(root, r, key, value, reseal=False):
        p = root / r.path; text = upsert_meta(p.read_text(), key, value)
        if reseal: text = upsert_meta(text, 'hash', parse_page(text, r.path).hash_actual)
        p.write_text(text)

    # Expectations are specified here and frozen on disk before any read arm runs.
    # They are not obtained from MPLPB's eligibility or support decisions.
    names = ['intact','revision','tampered','tampered_successor','ambiguous',
             'stale_replaced','stale_withdrawn','withdrawn_chain','unsupported',
             'unknown','wrong_pin','duplicate','rechecked','author_neutral']
    for name in names:
        root = out / 'fixtures' / name; root.mkdir(parents=True)
        q = 'What is the kettle color?'; eligible = []; supported = []; invalid = []; stale = False
        first = page(root)
        if name in ('intact', 'author_neutral'): eligible = [first.id]; supported = [first.id]
        if name in ('revision','tampered_successor','withdrawn_chain','wrong_pin','author_neutral'):
            replacement = L.revise(root, first.id, body='The kettle color is green.', when='2026-11-11T01:00:00Z')
            eligible = [replacement.id]; supported = [replacement.id]; invalid = [first.id]
            if name == 'tampered_successor':
                # P2 tests a half-finished revision: the predecessor still says current.
                edit(root, first, 'status', 'current')
                p = root / replacement.path; p.write_text(p.read_text().replace('color is green.', 'color is red.'))
                eligible = [first.id]; supported = [first.id]; invalid = [replacement.id]
            if name == 'withdrawn_chain':
                L.withdraw(root, replacement.id, when='2026-11-11T02:00:00Z')
                eligible = []; supported = []; invalid = [first.id, replacement.id]
            if name == 'wrong_pin':
                edit(root, first, 'status', 'current')
                edit(root, replacement, 'supersedes', first.id+'@sha256:'+'0'*64, True)
                eligible = [first.id]; supported = [first.id]; invalid = [replacement.id]
        if name == 'tampered':
            p = root / first.path; p.write_text(p.read_text().replace('color is blue.', 'color is red.'))
            invalid = [first.id]
        if name == 'ambiguous':
            other = page(root, body='The kettle color is red.')
            eligible = [first.id, other.id]
        if name in ('stale_replaced','stale_withdrawn','rechecked'):
            derived = L.derive(root, [first.id], title='Source', scope='lantern color',
                               body='The lantern color is blue.', when='2026-11-11T01:00:00Z')
            if name == 'stale_withdrawn': L.withdraw(root, first.id, when='2026-11-11T02:00:00Z')
            else: replacement = L.revise(root, first.id, body='The kettle color is green.', when='2026-11-11T02:00:00Z')
            q = 'What is the lantern color?'; invalid = [derived.id]; stale = name != 'rechecked'
            if name == 'rechecked':
                checked = L.write(root, title='Source', scope='lantern color', body='The lantern color is green.',
                                  derived_from=[replacement.id], supersedes=[derived.id], when='2026-11-11T03:00:00Z')
                eligible = [checked.id]; supported = [checked.id]
        if name == 'unsupported':
            # Valid page with matching scope, but body concerns a different entity.
            replacement = L.revise(root, first.id, body='The lantern color is blue.', when='2026-11-11T01:00:00Z')
            eligible = [replacement.id]; invalid = [first.id]
        if name == 'unknown': q = 'What is the lantern color?'
        if name == 'duplicate':
            shutil.copyfile(root / first.path, root / 'duplicate.html'); invalid = [first.id]
        labels.append(dict(case=name, root=str(root), question=q, eligible_ids=eligible,
                           supported_ids=supported, ineligible_ids=invalid,
                           ambiguous=name == 'ambiguous', stale=stale,
                           note='author_neutral is a synthetic same-owner revision, not the historical Arc'))

    save(out / 'labels.json', labels)
    manifest = {str(p.relative_to(out)):sha(p) for p in sorted((out/'fixtures').rglob('*')) if p.is_file()}
    save(out / 'fixture-digests.json', manifest)
    save(out / 'environment.json', dict(source_commit=commit, python=platform.python_version(),
         platform=platform.platform(), started_at=datetime.now(timezone.utc).isoformat(),
         label_sha256=sha(out/'labels.json'), scripts={p.name:sha(p) for p in [HERE/'run.py', HERE/'adapter.py', HERE/'baseline.py']},
         design='Exploratory, author-context synthetic engineering pilot; not preregistered or blind.'))
    results = []
    for case in labels:
        execute([sys.executable, '-m', 'mplpb_combined', 'validate', case['root']], case['case']+':validate')
        for arm in 'ABCD':
            row = dict(case=case['case'], arm=arm)
            for mode in ('retrieve','ask'):
                p = execute([sys.executable, HERE/'adapter.py', '--source', source, '--arm', arm,
                             '--mode', mode, case['root'], case['question']], case['case']+':'+arm+':'+mode)
                if p.returncode not in (0,2,3): raise RuntimeError(logs[-1])
                data = json.loads(p.stdout)
                rid = data.get('id') or (data.get('source') or {}).get('id')
                row[mode] = dict(kind=data['kind'], id=rid, answer_supported=data.get('answer_supported',False))
            results.append(row)
    save(out / 'decisions.json', results)

    summary = {}
    for arm in 'ABCD':
        pairs = [(c, next(r for r in results if r['arm']==arm and r['case']==c['case'])) for c in labels]
        def metric(n, d): return dict(numerator=n, denominator=d, rate=n/d if d else None)
        risky = [(c,r) for c,r in pairs if c['ineligible_ids']]
        ambiguous = [(c,r) for c,r in pairs if c['ambiguous']]
        stale_cases = [(c,r) for c,r in pairs if c['stale']]
        unsupported = [(c,r) for c,r in pairs if not c['supported_ids']]
        answerable = [(c,r) for c,r in pairs if c['supported_ids']]
        summary[arm] = {
            'ineligible_claim_serving_rate':metric(sum(r['retrieve']['id'] in c['ineligible_ids'] for c,r in risky),len(risky)),
            'ambiguous_ownership_detection':metric(sum(r['retrieve']['kind']=='ambiguous' for c,r in ambiguous),len(ambiguous)),
            'stale_derivative_rejection':metric(sum(r['retrieve']['id'] is None and r['retrieve']['kind']!='retrieved' for c,r in stale_cases),len(stale_cases)),
            'supported_answer_false_promotion':metric(sum(r['ask']['answer_supported'] for c,r in unsupported),len(unsupported)),
            'answerable_query_coverage':metric(sum(r['ask']['answer_supported'] and r['ask']['id'] in c['supported_ids'] for c,r in answerable),len(answerable)),
        }
    save(out / 'summary.json', summary)

    # Unmodified, complete public self-reference corpus: not synthetic labels.
    public = out/'public-system'; shutil.copytree(source/'examples/system', public)
    for args in [('validate',), ('history','SELF-0001')]:
        execute([sys.executable,'-m','mplpb_combined',args[0],public,*args[1:]],'public:'+args[0])
    for q in ['MPLPB system creator', 'What is MPLPB?']:
        for mode in ('retrieve','ask'):
            execute([sys.executable,HERE/'adapter.py','--source',source,'--arm','C','--mode',mode,public,q], 'public:'+mode+':'+q)
    led = L.Ledger(public)
    save(out/'public-records.json', [dict(id=r.id,path=r.path,seal=r.hash,computed_seal=r.hash_actual,
         file_sha256=sha(public/r.path),origin=r.origin,owner=r.fields.get('owner'),
         effective_status=led.effective_status(r),supersedes=[str(x) for x in r.supersedes]) for r in led.records])
    # Reading must not mutate fixtures or public pages.
    assert manifest == {str(p.relative_to(out)):sha(p) for p in sorted((out/'fixtures').rglob('*')) if p.is_file()}
    for p in public.rglob('*'):
        if p.is_file(): assert sha(p) == sha(source/'examples/system'/p.relative_to(public))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
