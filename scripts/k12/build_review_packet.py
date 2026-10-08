"""Build a local review packet; never approve items or mutate the database."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True)
args=parser.parse_args()
bank_path=ROOT/'results/k12/xes_question_bank.json'
audit_path=ROOT/'results/k12/math_render_audit_20261008.json'
audit=json.loads(audit_path.read_text())
assert hashlib.sha256(bank_path.read_bytes()).hexdigest()==audit['source_hashes']['bank'],'Audit bank hash mismatch'
items={item['task_id']:item for item in json.loads(bank_path.read_text())['items']}
flags={}
for row in audit['strict_warnings']:
    flags.setdefault(row['task_id'],set()).add('math_warning:'+row['code'])
for row in audit['content_review_flags']:
    flags.setdefault(row['task_id'],set()).add(row['reason'])
rows=[{'task_id':key,'review_reasons':sorted(flags[key]),'source_item':items[key],'review_status':'NOT_REVIEWED'} for key in sorted(flags)]
output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps({'scope':'flagged_subset_not_full_bank_or_expert_approval','bank_sha256':audit['source_hashes']['bank'],'audit_sha256':hashlib.sha256(audit_path.read_bytes()).hexdigest(),'items':rows},ensure_ascii=False,indent=2))
print(json.dumps({'review_items':len(rows),'output':str(output),'approved':0}))
