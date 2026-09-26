import sys, random, math
from collections import defaultdict
sys.path.insert(0, "E:/learnflow/results/m1")
import verify_m1_criteria as V

def fit_irt_1pl_fixed(responses_p, responses_j, responses_c, n_persons, n_items,
                      n_iter=80, n_nodes=21, lo=-5.0, hi=5.0):
    theta = [lo + (hi - lo) * i / (n_nodes - 1) for i in range(n_nodes)]
    raw = [math.exp(-0.5 * t * t) for t in theta]; sw = sum(raw); w = [r / sw for r in raw]
    by_person = defaultdict(list)
    for p, j, c in zip(responses_p, responses_j, responses_c):
        by_person[p].append((j, c))
    b = [0.0] * n_items
    for it in range(n_iter):
        # precompute P(correct|theta_q, bj) per item per node (once per iter)
        p1 = [[0.0] * n_nodes for _ in range(n_items)]
        for j in range(n_items):
            bj = b[j]
            for q in range(n_nodes):
                p1[j][q] = 1.0 / (1.0 + math.exp(-(theta[q] - bj)))
        # E-step: PROBABILITY domain (no overflow)
        R = [[0.0] * n_nodes for _ in range(n_items)]
        C = [[0.0] * n_nodes for _ in range(n_items)]
        for p in range(n_persons):
            items = by_person.get(p)
            if not items:
                continue
            acc = list(w)  # P(theta_q) prior
            for (j, c) in items:
                pj = p1[j]
                if c == 1:
                    for q in range(n_nodes):
                        acc[q] *= pj[q]
                else:
                    for q in range(n_nodes):
                        acc[q] *= (1.0 - pj[q])
            tot = sum(acc)
            if tot <= 0:
                rp = list(w)
            else:
                rp = [acc[q] / tot for q in range(n_nodes)]
            for (j, c) in items:
                Rj = R[j]; Cj = C[j]
                for q in range(n_nodes):
                    Rj[q] += rp[q]
                    if c == 1:
                        Cj[q] += rp[q]
        # M-step: Newton on score equation (verified-correct R/C form)
        for j in range(n_items):
            S = sum(C[j]); bj = b[j]
            for _ in range(30):
                fval = 0.0; dfval = 0.0
                pj = p1[j]; Rj = R[j]
                for q in range(n_nodes):
                    pr = pj[q]
                    fval += Rj[q] * pr
                    dfval += Rj[q] * pr * (1.0 - pr)
                fval -= S; dfval = -dfval
                if abs(dfval) < 1e-12:
                    break
                step = fval / dfval
                if step > 1.0: step = 1.0
                elif step < -1.0: step = -1.0
                bj -= step
                if abs(step) < 1e-7:
                    break
            b[j] = bj
    return b

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

# synthetic
resp, tb = gen(15, 1000, 7)
b = fit_irt_1pl_fixed([r[0] for r in resp], [r[1] for r in resp], [r[2] for r in resp], 1000, 15)
print("SYNTH mean|b|=%.3f rho=%.3f" % (sum(abs(x) for x in b)/15, V.spearman_rho(tb, b)))
# stress: include extreme items (all-correct / all-incorrect)
resp2, tb2 = gen(40, 3000, 10)
b2 = fit_irt_1pl_fixed([r[0] for r in resp2], [r[1] for r in resp2], [r[2] for r in resp2], 3000, 40)
print("STRESS mean|b|=%.3f rho=%.3f" % (sum(abs(x) for x in b2)/40, V.spearman_rho(tb2, b2)))
