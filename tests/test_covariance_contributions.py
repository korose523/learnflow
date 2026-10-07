import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('instability',ROOT/'results/code/m1_instability.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def test_orthogonal_equal_variance_does_not_imply_nominal_weights():
    z=np.array([[-1.,-1.],[-1.,1.],[1.,-1.],[1.,1.]])
    w=np.array([.25,.75]);pi=M.eff_weights(z,w)
    np.testing.assert_allclose(pi,w*w/np.sum(w*w))
    assert not np.allclose(pi,w)
    np.testing.assert_allclose(pi.sum(),1.)


def test_shared_increasing_transform_preserves_link_and_covariance():
    rng=np.random.default_rng(42);x=rng.normal(size=(30,2));cal=rng.normal(size=(40,2));w=np.array([.25,.75])
    transformed=x.copy();transcal=cal.copy();transformed[:,0]=np.exp(x[:,0]);transcal[:,0]=np.exp(cal[:,0])
    np.testing.assert_allclose(M.logit_metric_pi(x,cal,w),M.logit_metric_pi(transformed,transcal,w),atol=1e-14)


def test_clipping_creates_ties_and_falls_outside_strict_invariance():
    x=np.array([0.,1.]);cal=np.array([-2.,.5,2.])
    original=M.ecdf_logit(x,cal)
    clipped=M.ecdf_logit(M.logit_minmax(x,x),M.logit_minmax(cal,x))
    assert not np.allclose(original,clipped)
