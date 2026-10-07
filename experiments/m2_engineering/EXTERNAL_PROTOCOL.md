# External source adapter check

This bounded second stage was specified after the constructed benchmark, before
its own execution. It is exploratory and is not part of the original 31 cases.
Selection: ActiDoo/gamification-engine is a public Python gamification framework
with MIT source and explicit achievement/reward model classes. A fixed commit and
the original license are preserved. It is not chosen based on a measured audit
score. No application import, database connection or user data is involved.

Question: can the unchanged source-symbol adapter inspect an unrelated real source
file and distinguish selected valid references from known perturbed references?
The three selected model classes are Achievement, Reward and AchievementTriggerStep.
These are source-model objects, not an exhaustive intervention registry. No manual
psychological or seven-field contracts are attributed to this external project.

Checks: three valid class references, nonexistent class, nonexistent file,
root-escaping reference and line-only reference. Expected diagnostics are fixed
before execution. Only reference checking is enabled. Do not infer intervention
schema deficiencies, producer coverage, governance quality, runtime delivery,
independent adoption or end-to-end platform portability from this check.
