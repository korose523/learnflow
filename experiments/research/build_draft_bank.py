"""Generate 300 distinct numeric items for TECHNICAL rehearsal, not calibration.

No LLM, API, learner data or runtime database is used. Answers use exact Fraction.
Difficulty labels are nominal placeholders and must not be treated as fitted IRT.
"""
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOPICS = ('一元一次方程','分数运算','比例应用','整数与运算顺序')
PHASE_COUNTS = {'pretest':10,'practice':45,'posttest':10,'delayed':10}


def build():
    items=[]
    for topic_index,topic in enumerate(TOPICS):
        index=0
        for phase,count in PHASE_COUNTS.items():
            for local in range(count):
                index+=1; n=index; level=local%5
                if topic_index==0:
                    a=2+n%7; x=n-25; b=11+3*n
                    content=f'求 x：{a}x + {b} = {a*x+b}。'; answer=Fraction(x)
                elif topic_index==1:
                    a=n+2;b=3+n%13;c=n+5;d=5+n%17
                    content=f'计算 {a}/{b} + {c}/{d}，用最简分数或小数表示。';answer=Fraction(a,b)+Fraction(c,d)
                elif topic_index==2:
                    a=3+n%11; k=n+4; b=2+n%9
                    content=f'{a} 个同价物品共需 {a*k} 元，{b} 个这样的物品共需多少元？';answer=Fraction(b*k)
                else:
                    a=n+7;b=2+n%9;c=n+3
                    content=f'计算 ({a} + {b}) × {c} - {a}。';answer=Fraction((a+b)*c-a)
                value=str(answer.numerator) if answer.denominator==1 else f'{answer.numerator}/{answer.denominator}'
                task_id=hashlib.sha256(f'research-draft-v1:{topic}:{phase}:{local}'.encode()).hexdigest()[:32]
                items.append({'task_id':task_id,'topic':topic,'phase':phase,'content':content,'correct_answer':value,
                    'difficulty_elo':900+250*level,'expert_reviewed':False,'calibration_source':None,
                    'source':'generated_draft_v1','answer_method':'exact_fraction','nominal_level':level+1})
    assert len(items)==300 and len({x['content'] for x in items})==300
    assert len({x['task_id'] for x in items})==300
    return {'bank_version':'draft-v1','status':'UNREVIEWED_UNCALIBRATED_TECHNICAL_REHEARSAL_ONLY',
            'topics':list(TOPICS),'phase_pool_counts':PHASE_COUNTS,'items':items,
            'warning':'Nominal Elo values do not estimate empirical difficulty. Expert review, parallel-form equating and calibration are required before any live study.'}


if __name__=='__main__':
    destination=ROOT/'experiments/research/math_bank_draft_v1.json'
    destination.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n')
    print(f'Generated 300 draft items: {destination}')
