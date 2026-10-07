"""Publication figure generated directly from paired bootstrap JSON."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/figures';OUT.mkdir(exist_ok=True)
d=json.loads((ROOT/'results/m1/m1_criteria_results.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(7.0,2.7),layout='constrained')
for y,key in [(1,'a1'),(0,'a2')]:
 x=d[key]['paired_bootstrap'];mean=x['fusion_minus_success'];lo,hi=x['difference_ci']
 ax.errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt='o',capsize=4,color='#18517a',markersize=6)
 ax.text(.99,y+0.18,f'{mean:+.4f} [{lo:+.4f}, {hi:+.4f}]',transform=ax.get_yaxis_transform(),ha='right',fontsize=9)
ax.axvline(0,color='#555555',linewidth=1,linestyle='--')
ax.set_yticks([1,0],['Junyi: held-out 1PL criterion\n1,274 items, seven signals','DBE-KT22: teacher labels\n212 items, five signals'])
ax.set_xlabel('Spearman correlation difference (fusion minus success rate)')
ax.set_xlim(-.12,.19);ax.set_ylim(-.5,1.55);ax.spines[['top','right']].set_visible(False)
for fmt in ['pdf','svg','png']:fig.savefig(OUT/f'm1_paired_criterion_differences.{fmt}',dpi=300)
print('Exported figure in PDF/SVG/PNG')
