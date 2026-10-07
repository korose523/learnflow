"""Deterministic paired simulator replay from archived Junyi calibration.

The outcome is response success, not learning gain. Latent skill and calibrated
probabilities are fixed. Strategies share initial decile/strand and uniforms.
This new run is distinct from the historical v2 summary and overwrites no archive.
"""
import csv,hashlib,json
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'results/code/junyi_m3_cache.json'
META=ROOT/'data/junyi/Info_Content.csv'
POLICIES=('flow_zone','ability_correct','ability_inverted','all_easy','all_hard','random')
LEVELS=('easy','normal','hard')


def main():
    cache=json.loads(CACHE.read_text())
    with META.open() as f:meta={x['ucid']:(x['level3_id'],x['difficulty']) for x in csv.DictReader(f)}
    pools=defaultdict(lambda:defaultdict(list))
    for key,(n,correct) in sorted(cache['pt'].items()):
        item,decile=key.rsplit('|',1)
        if n<500 or item not in meta:continue
        strand,level=meta[item]
        if level not in LEVELS:continue
        pools[int(decile),strand][level].append(correct/n)
    eligible=sorted(key for key,pool in pools.items() if all(pool.get(level) for level in LEVELS))
    if not eligible:raise ValueError('No complete three-level pool')
    rng=np.random.default_rng(20261007);n_sims=500;horizon=40
    # Equal decile sampling, followed by uniform strand sampling within decile.
    by_decile=defaultdict(list)
    for key in eligible:by_decile[key[0]].append(key)
    deciles=sorted(by_decile);keys=[]
    for _ in range(n_sims):
        d=deciles[int(rng.integers(len(deciles)))];keys.append(by_decile[d][int(rng.integers(len(by_decile[d])))])
    item_uniforms=rng.random((n_sims,horizon));outcome_uniforms=rng.random((n_sims,horizon));action_uniforms=rng.random((n_sims,horizon))
    scores={p:np.zeros(n_sims) for p in POLICIES}
    for run,(d,strand) in enumerate(keys):
        arms=pools[d,strand];means={level:float(np.mean(arms[level])) for level in LEVELS}
        for policy in POLICIES:
            total=0
            for t in range(horizon):
                if policy=='flow_zone':level=min(LEVELS,key=lambda x:abs(means[x]-.75))
                elif policy=='ability_correct':level='hard' if d>=7 else ('normal' if d>=3 else 'easy')
                elif policy=='ability_inverted':level='easy' if d>=7 else ('hard' if d>=3 else 'normal')
                elif policy=='all_easy':level='easy'
                elif policy=='all_hard':level='hard'
                else:level=LEVELS[min(2,int(action_uniforms[run,t]*3))]
                choices=arms[level];p=choices[min(len(choices)-1,int(item_uniforms[run,t]*len(choices)))]
                total+=int(outcome_uniforms[run,t]<np.clip(p,.05,.98))
            scores[policy][run]=total/horizon
    boot=rng.integers(0,n_sims,(2000,n_sims));results={}
    for p,values in scores.items():
        ci=np.quantile(values[boot].mean(axis=1),[.025,.975])
        results[p]={'mean_success':float(values.mean()),'se_across_scenarios':float(values.std(ddof=1)/np.sqrt(n_sims)),'ci95_percentile':ci.tolist()}
    comparisons={}
    for comparator in ['ability_correct','ability_inverted','all_easy','all_hard','random']:
        delta=scores['flow_zone']-scores[comparator]
        comparisons['flow_zone_minus_'+comparator]={'mean_difference':float(delta.mean()),'paired_ci95':np.quantile(delta[boot].mean(axis=1),[.025,.975]).tolist()}
    result={'run':'offline-replay-20261007','seed':20261007,'bootstrap_n':2000,'bootstrap_unit':'paired_simulation_scenario',
        'n_scenarios':n_sims,'horizon':horizon,'eligible_decile_strand_pools':len(eligible),'calibration_users':len(cache['user_dec']),
        'results':results,'paired_comparisons_exploratory_no_multiplicity_adjustment':comparisons,
        'per_scenario_scores':{p:v.tolist() for p,v in scores.items()},
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CACHE,META]},
        'scope':'Response-success simulation under fixed calibrated probabilities, not learning, causal transitions, policy superiority in humans or memory-state validation. Intervals condition on the archive and do not resample source students.'}
    out=ROOT/'results/m3/offline_policy_replay_20261007.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_scenario_scores','source_sha256')},indent=2))

if __name__=='__main__':main()
