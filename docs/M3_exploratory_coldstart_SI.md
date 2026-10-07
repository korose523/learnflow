# M3 supplementary exploratory cold-start record

These are historical exploratory summaries, not the central evidence of the current offline manuscript. They are not newly rerun, matched criterion-only comparisons.

| Analysis | k=10 | k=500 | Provenance and boundary |
|---|---:|---:|---|
| In-pool summary | +0.0271 | −0.0695 | Earlier configuration, outcome and pool weighting must be checked against junyi_m3_v3 |
| Sign-corrected in-pool shrinkage | +6.447 pp | <0.35 pp for k≥250 | o11 optimization and landing checks; changes configuration as well as criterion |
| Junyi held-out summary | −0.0267 | −0.1222 | Held-out configuration is not shown to match corrected in-pool shrinkage |
| DBE held-out summary | −0.1752 | −0.2113 | Different dataset and signal availability |

The fitted expression λ*(k)=1/(1+(k/27.3)^0.895) is exploratory. The table mixes reporting units inherited from its source summaries and must not be read as one harmonized gain metric. It is not evidence of an LLM-specific causal loss, a learning effect, or a sign reversal caused solely by the evaluation criterion. A retained historical output is not a substitute for matched reruns with explicit outcomes and configurations. The main paper makes no deployment guarantee from these figures.
