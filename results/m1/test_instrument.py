import sys, os, random, math, zlib
from collections import defaultdict
sys.path.insert(0, "E:/learnflow/results/m1")

def fit_irt_1pl_scaled_DEBUG(responses_p, responses_j, responses_c, n_persons, n_items,
                             n_iter=60, n_nodes=21, lo=-5.0, hi=5.0, debug=False):
    theta = [lo + (hi - lo) * i / (n_nodes - 1) for i in range(n_nodes)]
    raw = [math.exp(-0.5 * t * t) for t in theta]
    sw = sum(raw); w = [r / sw for r in raw]
    by_person = defaultdict(list)
    for p, j, c in zip(responses_p, responses_j, responses_c):
        by_person[p].append((j, c))
    b = [0.0] * n_items
    for it in range(n_iter):
        p1 = [[0.0] * n_nodes for _ in range(n_items)]
        lp1 = [[0.0] * n_nodes for _ in range(n_items)]
        lm1 = [[0.0] * n_nodes for _ in range(n_items)]
        for j in range(n_items):
            bj = b[j]
            for q in range(n_nodes):
                x = theta[q] - bj
                pr = 1.0 / (1.0 + math.exp(-x))
                p1[j][q] = pr
                lp1[j][q] = -math.log1p(math.exp(-x))
                lm1[j][q] = -math.log1p(math.exp(x))
        R = [[0.0] * n_nodes for _ in range(n_items)]
        C = [[0.0] * n_nodes for _ in range(n_items)]
        for p in range(n_persons):
            items = by_person.get(p)
            if not items: continue
            ll = [math.log(wq) for wq in w]
            for (j, c) in items:
                pj = lp1[j]; mj = lm1[j]
                if c == 1:
                    for q in range(n_nodes): ll[q] += pj[q]
                else:
                    for q in range(n_nodes): ll[q] += mj[q]
            m = max(ll)
            L = [math.exp(ll[q] - m) for q in range(n_nodes)]
            tot = sum(L)
            rp = [L[q] / tot for q in range(n_nodes)]
            for (j, c) in items:
                Rj = R[j]; Cj = C[j]
                for q in range(n_nodes):
                    Rj[q] += rp[q]
                    if c == 1: Cj[q] += rp[q]
        for j in range(n_items):
            S = sum(C[j])
            bj = b[j]
            for _ in range(25):
                fval = 0.0; dfval = 0.0
                Rj = R[j]; Cj = C[j]
                for q in range(n_nodes):
                    pr = p1[j][q]
                    fval += Rj[q] * pr
                    dfval += Rj[q] * pr * (1.0 - pr)
                fval -= S
                dfval = -dfval
                if abs(dfval) < 1e-12: break
                step = fval / dfval
                if step > 2.0: step = 2.0
                elif step < -2.0: step = -2.0
                bj -= step
                if abs(step) < 1e-6: break
            b[j] = bj
        if debug and it % 5 == 0:
            mb = sum(b)/len(b)
            print(f"  it={it} mean(b)={mb:.3f} max|b|={max(abs(x) for x in b):.2f}")
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

resp, tb = gen(15, 1000, 7)
print("true mean|b|", round(sum(abs(x) for x in tb)/15,3))
print("DEBUG trace of fit_irt_1pl_scaled:")
b = fit_irt_1pl_scaled_DEBUG([r[0] for r in resp],[r[1] for r in resp],[r[2] for r in resp],1000,15,debug=True)
print("final b", [round(x,2) for x in b])
