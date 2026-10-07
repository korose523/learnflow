# M4 correction and conditional evaluation

This evaluation is specified before execution and is exploratory, not externally
preregistered. Historical M4 JSON remains immutable. The new run uses the existing
difficulty_cache.npz only; it is distinct from M1's full-transaction reanalysis.

For each dataset and k=10,25,50,100,200, draw one seeded response sample per item
using the existing prepare/all_variants implementation with seed 20261007 for DBE
and 20261008 for Junyi. Estimate all scores from the same draw, without label-tuned
lambda. Compare success, srw7_cf, m4_full, m4_E_cf, and m4_E_rel against labels.
Compute Kendall tau-b and 2000 paired-item percentile bootstrap intervals for the
difference from success. The bootstrap conditions on fitted score vectors and the
cached response sample; it does not refit fusion or resample students. No
multiplicity correction, no superiority selection, no causal/learning claim.

Extract every k from historical results separately. Historical delta fields use
srw7_cf as baseline, not success. Repeated response subsamples share the same items,
students and labels; their variability is a conditional stability description, not
independent population replication. Do not use the old repeated-subsample paired t
or Cohen d to establish generalizable significance.

Theory checks: V=Cov(z), q=Cov(z,t), beta proportional V^{-1}q under positive definite
V. Under independent single-factor errors V=qq' + diag(1-rho), weights proportional
q/(1-rho), not rho. V=I gives beta=q, and is not the covariance of multiple nonzero
single-factor loadings with independent errors. Spearman V plus split-half q is a
heuristic, not the covariance/loading identity needed by the theorem.

Bradley-Terry identity concerns fractional pairwise evidence with connected graph
and finite scores. Its solution under zero-sum identification is centered u;
logit averaging gives centered u divided by source count. Sampled Bernoulli wins
do not in general give exact recovery. Probability averaging need not change ranks.
