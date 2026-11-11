"""Fresh-process read entry point; only arm C imports MPLPB enforcement."""
import argparse
import json
import sys

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--arm', choices='ABCD', required=True)
p.add_argument('--mode', choices=['retrieve', 'ask'], required=True)
p.add_argument('root'); p.add_argument('question')
a = p.parse_args()
if a.arm == 'C':
    sys.path.insert(0, a.source)
    if a.mode == 'retrieve':
        from mplpb_combined.retrieval import retrieve
        result = retrieve(a.root, a.question)
    else:
        from mplpb_answers.__main__ import main
        sys.exit(main(['ask', a.root, a.question, '--answer-mode', 'strict', '--json']))
else:
    from baseline import read
    result = read(a.root, a.question, a.arm, a.mode)
print(json.dumps(result, indent=2))
sys.exit({'retrieved':0, 'return':0, 'ambiguous':2, 'not_in_corpus':3}[result['kind']])
