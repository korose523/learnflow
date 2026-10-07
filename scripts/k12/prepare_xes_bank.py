"""Reuse official, locally available XES3G5M for offline K12 evaluation.

No recruitment, network APIs, model inference or production DB writes. Counts
refer to supplied processed question-level records, not original interactions.
"""
import csv,hashlib,json,re,sys
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/xes3g5m/XES3G5M'
OUT=ROOT/'results/k12'
SOURCE_URL='https://github.com/ai4ed/XES3G5M'


def hashfile(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def numeric_answer(value):
    if not isinstance(value,list) or len(value)!=1:return None
    text=str(value[0]).replace('$$','').replace('$','').strip()
    text=re.sub(r'\\(?:d?frac)\{([+-]?\d+)\}\{([+-]?\d+)\}',r'\1/\2',text)
    return text if re.fullmatch(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:/[+-]?\d+)?',text) else None


def read_sequences(path):
    agg=defaultdict(lambda:[0,0]);users=set();invalid=0;records=0
    with path.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            users.add(row['uid'])
            qs=row['questions'].split(','); rs=row['responses'].split(',')
            if len(qs)!=len(rs):raise ValueError('Question/response lengths differ')
            for q,response in zip(qs,rs):
                if q in ('','-1') or response not in ('0','1'):invalid+=1;continue
                agg[q][0]+=1;agg[q][1]+=int(response);records+=1
    return agg,users,{'provided_answer_records':records,'skipped_padding_or_invalid':invalid,'provided_unique_students':len(users)}


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    metadata=DATA/'metadata/questions.json';questions=json.loads(metadata.read_text())
    paths={'train':DATA/'question_level/train_valid_sequences_quelevel.csv','test':DATA/'question_level/test_quelevel.csv'}
    train,utrain,train_meta=read_sequences(paths['train']);test,utest,test_meta=read_sequences(paths['test'])
    overlap=len(utrain & utest)
    items=[];types=Counter();reasons=Counter()
    for qid,q in sorted(questions.items(),key=lambda x:int(x[0])):
        types[str(q.get('type'))]+=1
        content=q.get('content') or '';answer=numeric_answer(q.get('answer'))
        image=bool(re.search(r'<img|question_\d+-|!\[|https?://.*\.(?:png|jpg)',content,re.I))
        supported=answer is not None and not image and bool(content.strip())
        if image:reasons['requires_image']+=1
        if answer is None:reasons['non_single_numeric_answer']+=1
        nt,ct=train.get(qid,[0,0]);nv,cv=test.get(qid,[0,0])
        probability=(ct+.5)/(nt+1) if nt else None
        items.append({'source':'XES3G5M','source_url':SOURCE_URL,'source_item_id':qid,'task_id':'xes-'+qid,
            'content':content,'original_answer':q.get('answer'),'normalized_numeric_answer':answer,
            'options':q.get('options'),'analysis':q.get('analysis'),'kc_routes':q.get('kc_routes',[]),
            'original_type':q.get('type'),'requires_image':image,'numeric_app_compatible':supported,
            'train_n':nt,'train_correct':ct,'train_smoothed_success':probability,
            'test_n':nv,'test_correct':cv,'test_success':cv/nv if nv else None,
            'difficulty_source':'train_observed_response_probability_not_IRT_or_expert_label'})
    bank={'dataset':'XES3G5M','status':'PUBLIC_DATA_OFFLINE_BANK','license':'MIT (official repository and paper supplementary material)',
        'license_url':SOURCE_URL+'/blob/main/LICENSE','items':items}
    (OUT/'xes_question_bank.json').write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n')
    aligned=[x for x in items if x['train_n']>=30 and x['test_n']>=30]
    metrics=None
    if not overlap and len(aligned)>=3:
        from scipy.stats import spearmanr
        from numpy.random import default_rng
        import numpy as np
        a=np.array([1-x['train_smoothed_success'] for x in aligned]);b=np.array([1-x['test_success'] for x in aligned])
        point=float(spearmanr(a,b).statistic);rng=default_rng(20261007);draws=[]
        for _ in range(2000):
            ix=rng.integers(0,len(a),len(a));v=float(spearmanr(a[ix],b[ix]).statistic)
            if np.isfinite(v):draws.append(v)
        metrics={'criterion':'held-out students observed item error rate','estimator':'train students smoothed inverse success rate','n_items':len(aligned),'min_records_each_split':30,'spearman':point,
            'bootstrap_unit':'item_conditional_on_fitted_observed_rates','bootstrap_seed':20261007,'bootstrap_valid':len(draws),'ci95_percentile':np.quantile(draws,[.025,.975]).tolist(),
            'interpretation':'Cross-student descriptive reproducibility of observed rates; not learning gain, causal difficulty or independent ability-adjusted IRT.'}
    inventory={'dataset':'XES3G5M','source_url':SOURCE_URL,'metadata_items':len(items),'question_types':dict(types),
        'numeric_text_app_compatible':sum(x['numeric_app_compatible'] for x in items),'unsupported_reasons_overlap':dict(reasons),
        'train':train_meta,'test':test_meta,'train_test_student_overlap':overlap,'heldout_observed_rate_check':metrics,
        'source_sha256':{str(p.relative_to(ROOT)):hashfile(p) for p in [metadata,*paths.values()]},
        'limitations':['Provided sequences are processed/truncated; record counts cannot reconstruct original interactions.','Many items require images, multiple blanks or option grading; the current numeric research adapter cannot handle all 7652 items.','No original student identifiers are included in the prepared item bank or inventory.','School grade and knowledge routes do not provide an independently calibrated item difficulty scale.']}
    (OUT/'xes_bank_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in inventory.items() if k not in ('source_sha256','limitations')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
