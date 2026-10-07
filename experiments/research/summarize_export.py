"""Describe a research CSV, enforcing dry-run/live separation; no effect claims."""
import argparse,csv,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def summarize(path, expected_mode):
    rows=list(csv.DictReader(Path(path).open(newline='',encoding='utf-8-sig')))
    if any(r['mode']!=expected_mode for r in rows):raise ValueError('Mixed or unexpected mode. Dry runs cannot become human evidence.')
    protocols={(r['study_id'],r['protocol_hash']) for r in rows}
    if len(protocols)>1:raise ValueError('One study/protocol per summary')
    groups=defaultdict(list)
    for row in rows:groups[(row['research_id'],row['topic'],row['phase'])].append(row)
    records=[]
    for (pid,topic,phase),values in sorted(groups.items()):
        if len({r['trial_id'] for r in values})!=len(values):raise ValueError('Duplicate trial rows')
        records.append({'research_id':pid,'topic':topic,'phase':phase,'n_answers':len(values),
            'correct_rate':statistics.mean(int(r['is_correct']) for r in values),
            'target_success':float(values[0]['target_success']),
            'mean_predicted_success':statistics.mean(float(r['predicted_success']) for r in values),
            'mean_client_response_ms':statistics.mean(int(r['response_ms']) for r in values),
            'mean_server_elapsed_ms':statistics.mean(int(r['server_elapsed_ms']) for r in values)})
    return {'mode':expected_mode,'n_rows':len(rows),'n_participants':len({r['research_id'] for r in rows}),
        'analysis_status':'DESCRIPTIVE_RECORD_QA_ONLY_NOT_CONFIRMATORY','groups':records,
        'limitations':['Missing participants are not represented by answered-trial export. Join the enrolment/withdrawal ledger for intention-to-treat analysis.','Protocol window and total-session duration must be assessed using session metadata.','No validated difficulty calibration or causal learning effect is established by this script.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv');p.add_argument('--mode',choices=['dry_run','live'],required=True);p.add_argument('--output',required=True)
    a=p.parse_args();Path(a.output).write_text(json.dumps(summarize(a.csv,a.mode),ensure_ascii=False,indent=2)+'\n')
