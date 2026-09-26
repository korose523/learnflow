import sys, random, math
from collections import defaultdict
sys.path.insert(0, "E:/learnflow/results/m1")
import verify_m1_criteria as V

def gen(J, N, Rr):
    rng = random.Random(7)
    true_b = sorted(rng.uniform(-1.5, 1.5) for _ in range(J))
    responses = []
    for p in range(N):
        theta = rng.gauss(0, 1)
        for j in rng.sample(range(J), Rr):
            p1 = 1.0 / (1.0 + math.exp(-(theta - true_b[j])))
            c = 1 if rng.random() < p1 else 0
            responses.append((p, j, c))
    return responses, true_b

def hybrid(responses, n_persons, n_items, n_iter=60, n_nodes=21, lo=-5.0, hi=5.0):
    theta = [lo + (hi - lo) * i / (n_nodes - 1) for i in range(n_nodes)]
    raw = [math.exp(-0.5 * t * t) for t in theta]; sw = sum(raw); w = [r / sw for r in raw]
    by_person = defaultdict(list)
    for p, j, c in zip([r[0] for r in responses], [r[1] for r in responses], [r[2] for r in responses]):
        by_person[p].append((j, c))
    b = [0.0] * n_items
    for it in range(n_iter):
        # SLOW verified E-step -> r[p]
        r = {}
        for p in range(n_persons):
            items = by_person.get(p, [])
            if not items:
                r[p] = list(w); continue
            like = []
            for q in range(n_nodes):
                acc = w[q]
                for (j, c) in items:
                    p1 = 1.0 / (1.0 + math.exp(-(theta[q] - b[j])))
                    acc *= p1 if c == 1 else (1.0 - p1)
                like.append(acc)
            tot = sum(like)
            r[p] = list(w) if tot <= 0 else [lk / tot for lk in like]
        # FAST M-step via R/C built from r[p]
        R = [[0.0] * n_nodes for _ in range(n_items)]
        C = [[0.0] * n_nodes for _ in range(n_items)]
        for p in range(n_persons):
            rp = r[p]
            for (j, c) in by_person[p]:
                Rj = R[j]; Cj = C[j]
                for q in range(n_nodes):
                    Rj[q] += rp[q]
                    if c == 1: Cj[q] += rp[q]
        for j in range(n_items):
            S = sum(C[j]); bj = b[j]
            for _ in range(25):
                fval = 0.0; dfval = 0.0
                for q in range(n_nodes):
                    pr = 1.0 / (1.0 + math.exp(-(theta[q] - bj)))
                    fval += R[j][q] * pr
                    dfval += R[j][q] * pr * (1.0 - pr)
                fval -= S; dfval = -dfval
                if abs(dfval) < 1e-12: break
                step = fval / dfval
                if step > 2.0: step = 2.0
                elif step < -2.0: step = -2.0
                bj -= step
                if abs(step) < 1e-6: break
            b[j] = bj
    return b

resp, tb = gen(15, 1000, 7)
b = hybrid(resp, 1000, 15)
print("HYBRID (slow E-step + fast M-step):")
print("  b =", [round(x, 2) for x in b])
print("  mean|b| =", round(sum(abs(x) for x in b)/15, 3))
print("  rho(true, b) =", round(V.spearman_rho(tb, b), 3))
