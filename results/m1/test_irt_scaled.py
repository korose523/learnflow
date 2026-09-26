import sys, os, random, math
sys.path.insert(0, "E:/learnflow/results/m1")
import run_criteria_fit as R
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

resp, tb = gen(15, 1000, 7)
b_slow = V.fit_irt_1pl(resp, 1000, 15, n_iter=200, n_nodes=21)
b_fast = R.fit_irt_1pl_scaled([r[0] for r in resp], [r[1] for r in resp], [r[2] for r in resp],
                              1000, 15, n_iter=60, n_nodes=21)
print("true  ", [round(x, 2) for x in tb])
print("slow  ", [round(x, 2) for x in b_slow])
print("fast  ", [round(x, 2) for x in b_fast])
print("mean|slow|", round(sum(abs(x) for x in b_slow)/15, 3))
print("mean|fast|", round(sum(abs(x) for x in b_fast)/15, 3))
rho_slow = V.spearman_rho(tb, b_slow)
rho_fast = V.spearman_rho(tb, b_fast)
print("rho(true,slow)", round(rho_slow, 3))
print("rho(true,fast)", round(rho_fast, 3))
