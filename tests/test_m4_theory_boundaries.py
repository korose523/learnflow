import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


def test_single_factor_optimal_weights_are_not_reliability_weights():
    rho = np.array([.25, .81]); q = np.sqrt(rho)
    V = np.outer(q, q) + np.diag(1 - rho)
    beta = np.linalg.solve(V, q)
    error_weights = q / (1 - rho)
    np.testing.assert_allclose(beta / beta.sum(), error_weights / error_weights.sum())
    assert not np.allclose(beta / beta.sum(), rho / rho.sum())
    assert not np.allclose(np.linalg.solve(np.eye(2), q), error_weights)


def test_covariance_objective_matches_cauchy_schwarz_bound():
    rng = np.random.default_rng(77); a = rng.normal(size=(4, 4))
    V = a @ a.T + np.eye(4); q = rng.normal(size=4)
    optimum = np.linalg.solve(V, q)
    bound = q @ optimum
    candidates = rng.normal(size=(100, 4))
    values = (candidates @ q) ** 2 / np.einsum('ij,jk,ik->i', candidates, V, candidates)
    assert np.all(values <= bound + 1e-12)
    np.testing.assert_allclose((optimum @ q) ** 2 / (optimum @ V @ optimum), bound)


def test_fractional_bt_recovers_centered_scores_not_raw_shift():
    u = np.array([3., 4., 6., 8.]); i, j = np.triu_indices(4, 1)
    p = expit(u[i] - u[j])
    def objective(x):
        d = np.r_[x, -sum(x)]; difference = d[i] - d[j]
        return np.sum(np.logaddexp(0, difference) - p * difference)
    result = minimize(objective, np.zeros(3), method="BFGS", options={"gtol": 1e-9})
    fitted = np.r_[result.x, -sum(result.x)]
    np.testing.assert_allclose(fitted, u - u.mean(), atol=1e-5)
    assert not np.allclose(fitted, u)


def test_noisy_validity_target_attenuates_latent_correlation():
    # v=t+eta, Var(t)=1, Cov(c,eta)=0, Var(c)=1.
    latent_correlation = .8
    eta_variance = 3.
    validity_correlation = latent_correlation / np.sqrt(1 + eta_variance)
    assert validity_correlation == .4
    assert validity_correlation != latent_correlation
