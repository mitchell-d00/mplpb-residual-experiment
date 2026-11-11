"""Conventional fail-closed reference gate for this experiment's narrow format.

No MPLPB imports. Shares the published serialization contract, not reader code.
Supports explicit origins, pinned lineage, withdrawals, exact scope ownership,
and a single affirmative color grammar. This is not a full MPLPB replacement.
"""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

FIELDS = ('document-id kind scope when-to-use not-for status hash origin '
          'origin-depth derived-from supersedes ratified-by points-to owner '
          'updated category external source-authorship clarify-options').split()
LATE = 'not-for external source-authorship clarify-options'.split()


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return 'sha256:' + hashlib.sha256(raw.encode()).hexdigest()


class Header(HTMLParser):
    def __init__(self):
        super().__init__(); self.fields = {}; self.title = ''; self.head = False
        self.in_title = False; self.duplicate = False

    def handle_starttag(self, tag, attrs):
        if tag == 'head': self.head = True
        if not self.head: return
        if tag == 'title': self.in_title = True
        if tag == 'meta':
            a = dict(attrs); name = a.get('name', '')
            if name.startswith('mplpb:'):
                key = name[6:]
                if key in self.fields: self.duplicate = True
                self.fields[key] = a.get('content', '').strip()

    def handle_endtag(self, tag):
        if tag == 'head': self.head = False
        if tag == 'title': self.in_title = False

    def handle_data(self, data):
        if self.in_title: self.title += data


class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)
    def handle_endtag(self, tag): self.parts.append('\n')


def load(root):
    records = []
    for path in sorted(Path(root).rglob('*.html')):
        raw = path.read_text(); h = Header(); h.feed(raw); f = h.fields
        if not f.get('document-id'): continue
        m = re.search(r'<body[^>]*>(.*)</body>', raw, re.I | re.S)
        body = m.group(1).replace('\r\n', '\n').replace('\r', '\n').strip() if m else ''
        hashed = {k: f.get(k, '') for k in FIELDS if k not in ['status', 'hash'] + LATE}
        hashed.update({k: f[k] for k in LATE if f.get(k)})
        actual = digest({'fields': hashed, 'title': h.title.strip(), 'body': body})
        t = Text(); t.feed(body)
        prose = Text(); prose.feed(re.sub(r'<h[1-6]\b[^>]*>.*?</h[1-6]>', '', body, flags=re.I | re.S))
        records.append(dict(f=f, id=f['document-id'], path=path.relative_to(root).as_posix(),
                            actual=actual, duplicate=h.duplicate, text=' '.join(' '.join(t.parts).split()),
                            prose=' '.join(' '.join(prose.parts).split())))
    return records


def refs(r, key):
    return [token.partition('@')[::2] for token in r['f'].get(key, '').split()]


def eligible(root, records):
    by_id = {}
    for r in records: by_id.setdefault(r['id'], []).append(r)

    def valid(r, seen=()):
        f = r['f']
        if r['id'] in seen or len(by_id[r['id']]) != 1 or r['duplicate']: return False
        if f.get('hash') != r['actual'] or f.get('status') not in ('current', 'retired'): return False
        if f.get('origin') not in ('human', 'machine') or not f.get('scope'): return False
        if f.get('kind', '') not in ('', 'page') or f.get('ratified-by'): return False
        parents = []; previous = []
        for key, group in [('derived-from', parents), ('supersedes', previous)]:
            for rid, pin in refs(r, key):
                targets = by_id.get(rid, [])
                if len(targets) != 1 or not pin or targets[0]['actual'] != pin: return False
                p = targets[0]
                if not valid(p, seen + (r['id'],)): return False
                group.append(int(p['f']['origin-depth']))
        source_depth = 1 + max(parents) if parents else int(f['origin'] == 'machine')
        return f.get('origin-depth') == str(max([source_depth] + previous))

    retired = set()
    log = Path(root) / '_log/ledger.jsonl'; prev = ''
    if log.exists():
        try:
            for seq, line in enumerate(log.read_text().splitlines(), 1):
                e = json.loads(line)
                if e['seq'] != seq or e['prev'] != prev or e['entry_hash'] != digest({k:v for k,v in e.items() if k != 'entry_hash'}): return []
                prev = e['entry_hash']
                if e['event'] == 'retire' and not e.get('note', '').startswith('superseded by '):
                    retired.add((e['id'], e['hash'], e['path']))
        except (ValueError, KeyError, TypeError): return []
    good = [r for r in records if valid(r)]
    superseded = {rid for r in good for rid, pin in refs(r, 'supersedes')}

    def current(r, seen=()):
        if r['id'] in seen or r not in good: return False
        if r['f']['status'] != 'current' or r['id'] in superseded: return False
        if (r['id'], r['f']['hash'], r['path']) in retired: return False
        return all(current(by_id[rid][0], seen + (r['id'],)) for rid, pin in refs(r, 'derived-from'))
    return [r for r in good if current(r)]


def read(root, question, arm, mode):
    records = load(root)
    q = re.fullmatch(r'What is the ([A-Za-z]+) color\?', question)
    if not q: return {'kind': 'not_in_corpus', 'id': None, 'answer_supported': False}
    subject = q[1].lower(); scope = subject + ' color'
    selected = eligible(root, records) if arm == 'D' else records
    owners = [r for r in selected if r['f'].get('scope', '').lower() == scope]
    if arm == 'D' and len(owners) > 1:
        return {'kind': 'ambiguous', 'id': None, 'answer_supported': False}
    if arm == 'B': owners.sort(key=lambda r:(r['f'].get('updated', ''), r['id']), reverse=True)
    if not owners: return {'kind': 'not_in_corpus', 'id': None, 'answer_supported': False}
    r = owners[0]
    if mode == 'retrieve': return {'kind': 'retrieved', 'id': r['id'], 'text': r['text'], 'answer_supported': False}
    if arm == 'D':
        # Whole affirmative sentence; quoted, conditional and unsupported prose stop.
        sentence = re.fullmatch(r'The ' + re.escape(subject) + r' color is (blue|green|red)\.', r['prose'], re.I)
        if not sentence: return {'kind': 'not_in_corpus', 'id': None, 'answer_supported': False}
    return {'kind': 'return', 'id': r['id'], 'text': r['text'], 'answer_supported': True}
