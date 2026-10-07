import hashlib
import json
import random
import sys
from pathlib import Path
import numpy as np
from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "results/code"))
import run_m4 as M


def main():
    out = Path(__file__).parent
    historical = json.loads((ROOT / "results/code/m4_results.json").read_text())
    cache = M.load_cache(M.NPZ)
    names = ["success", "srw7_cf", "m4_full", "m4_E_cf", "m4_E_rel"]
    report = {"status": "exploratory_conditional_fixed_score_evaluation", "bootstrap": 2000,
              "seed": 20261007, "protocol_sha256": hashlib.sha256((out / "PROTOCOL_correction.md").read_bytes()).hexdigest(),
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [M.NPZ, ROOT / "results/code/run_m4.py", ROOT / "results/code/m4_lib.py", ROOT / "results/code/m4_results.json"]},
              "historical": {}, "new_evaluation": {}, "theory": {}}
    for label in ("P1_dbe_teacher_labels", "P1_junyi_platform_labels"):
        report["historical"][label] = {}
        for k, row in historical["protocols"][label].items():
            report["historical"][label][k] = {n: {"tau_b": row[n]["tau_b"],
                "difference_from_success": row[n]["tau_b"] - row["success"]["tau_b"]} for n in names}
    for tag, seed in [("D", 20261007), ("J", 20261008)]:
        labels = np.array(cache[tag + "_y"][1]); full = cache[tag + "_full"][1]
        ncol = 6 if tag == "D" else 8
        caps = [min(int(full[i * ncol]), M.K_SLOTS) for i in range(len(labels))]
        rng = random.Random(seed); boot = np.random.default_rng(seed)
        report["new_evaluation"][tag] = {}
        for k in (10, 25, 50, 100, 200):
            z, z1, z2, counts, fields = M.prepare(cache, tag, tag, caps, rng, k)
            rho = None
            if tag == "D":
                rho = {j: M.unit_unreliability_from_half(M.spearman(z1[j], z2[j]), max(1, k // 4)) for j in M.D_MISSING}
            scores, _, _ = M.all_variants(z, z1, z2, k, None if tag == "D" else M.J_DROP, counts, rho)
            vectors = {n: np.array(scores[n]) for n in names}
            point = {n: float(kendalltau(vectors[n], labels).statistic) for n in names}
            differences = {n: [] for n in names if n != "success"}
            for _ in range(2000):
                idx = boot.integers(0, len(labels), len(labels)); y = labels[idx]
                base = kendalltau(vectors["success"][idx], y).statistic
                for n in differences:
                    v = kendalltau(vectors[n][idx], y).statistic - base
                    if np.isfinite(v): differences[n].append(float(v))
            row = {"n_items": len(labels), "score_vectors": {n: vectors[n].tolist() for n in names}, "labels": labels.tolist(), "estimates": {}}
            for n in names:
                row["estimates"][n] = {"tau_b": point[n], "difference_from_success": point[n] - point["success"]}
                if n in differences:
                    row["estimates"][n]["conditional_paired_item_ci"] = np.quantile(differences[n], [.025, .975]).tolist()
                    row["estimates"][n]["valid_bootstraps"] = len(differences[n])
            report["new_evaluation"][tag][str(k)] = row
            print(tag, k, row["estimates"], flush=True)
    rho = np.array([.25, .81]); q = np.sqrt(rho); V = np.outer(q, q) + np.diag(1 - rho)
    beta = np.linalg.solve(V, q); expected = q / (1 - rho)
    report["theory"] = {"rho": rho.tolist(), "q": q.tolist(), "covariance": V.tolist(),
        "beta_normalized": (beta / beta.sum()).tolist(), "independent_error_normalized": (expected / expected.sum()).tolist(),
        "reliability_normalized": (rho / rho.sum()).tolist(), "identity_covariance_normalized": (q / q.sum()).tolist(),
        "single_factor_identity_residual_max": float(np.abs(V - np.eye(2)).max())}
    (out / "m4_correction_evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("Saved", out / "m4_correction_evaluation.json")


if __name__ == "__main__":
    main()
