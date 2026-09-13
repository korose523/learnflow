import json, os, numpy as np
base = r"E:/learnflow\results\code"
out = []
def log(s=""):
    out.append(str(s))

npz = base + "/difficulty_cache.npz"
log(f"npz_exists = {os.path.isfile(npz)}")
d = json.load(open(base + "/o8_fusion_variants.json", encoding="utf-8"))
r = d["results"]
ks = [10, 25, 50, 100, 200]

log("=== fused6_drop_upgrade - fused7 (heldout_at_lambda_star, percentage points) ===")
for k in ks:
    a = r["fused6_drop_upgrade"][str(k)]["heldout_at_lambda_star"]
    b = r["fused7"][str(k)]["heldout_at_lambda_star"]
    log(f"  k={k:<4d}  {round((a-b)*100,3):+.3f} pp   (fused6={a:.4f}  fused7={b:.4f})")

log("=== gain_vs_success_pp (各自相对 pure success) ===")
for v in ["fused7", "fused6_drop_upgrade"]:
    log(f"  {v}: {[r[v][str(k)]['gain_vs_success_pp'] for k in ks]}")

log("=== empirical lambda_star_mean per k ===")
for v in ["fused7", "fused6_drop_upgrade", "fused3_success_hint_attempts"]:
    log(f"  {v}: {[r[v][str(k)]['lambda_star_mean'] for k in ks]}")

l7 = np.array([r["fused7"][str(k)]["lambda_star_mean"] for k in ks])
y = np.log(1.0 / l7 - 1.0)
x = np.log(np.array(ks, dtype=float))
p, intercept = np.polyfit(x, y, 1)
c = np.exp(-intercept / p)
log(f"  fit fused7: lambda*(k) ~ 1/(1+(k/{c:.2f})^{p:.3f})")

l6 = np.array([r["fused6_drop_upgrade"][str(k)]["lambda_star_mean"] for k in ks])
y6 = np.log(1.0 / l6 - 1.0)
p6, ic6 = np.polyfit(x, y6, 1)
c6 = np.exp(-ic6 / p6)
log(f"  fit fused6: lambda*(k) ~ 1/(1+(k/{c6:.2f})^{p6:.3f})")

log("  chapter-claimed closed form: lambda*(k)=1/(1+(k/27.3)^0.895)")
log(f"  that closed form at k=10/25/50/100/200 = "
    f"{[round(1/(1+(k/27.3)**0.895),3) for k in ks]}")
log(f"  empirical fused7 lambda*  at those k = {[round(float(v),3) for v in l7]}")

with open(base + "/o8_verify.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
