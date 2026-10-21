import tempfile
import unittest
from pathlib import Path

import numpy as np

from lbm_lab.cases import run_case
from lbm_lab.solver import D2Q9, C, equilibrium


class SolverTests(unittest.TestCase):
    def test_equilibrium_moments(self):
        rho = np.full((4, 8), 1.1)
        f = equilibrium(rho, np.full_like(rho, 0.03), np.full_like(rho, -0.02))
        np.testing.assert_allclose(f.sum(axis=0), rho, atol=1e-14)
        np.testing.assert_allclose(np.einsum("i,iyx->yx", C[:, 0], f), rho*0.03, atol=1e-14)
        np.testing.assert_allclose(np.einsum("i,iyx->yx", C[:, 1], f), rho*(-0.02), atol=1e-14)

    def test_uniform_periodic_velocity(self):
        model = D2Q9()
        model.initialize(0.02, -0.01)
        for _ in range(10):
            model.step()
        rho, ux, uy = model.macroscopic()
        np.testing.assert_allclose(rho, 1, atol=1e-13)
        np.testing.assert_allclose(ux, 0.02, atol=1e-13)
        np.testing.assert_allclose(uy, -0.01, atol=1e-13)

    def test_force_momentum_increment(self):
        model = D2Q9(force_x=1e-5)
        self.assertAlmostEqual(model.macroscopic()[1].mean(), 0, places=14)
        for _ in range(20):
            model.step()
        self.assertAlmostEqual(model.macroscopic()[1].mean(), 20e-5, places=13)

    def test_periodic_mass(self):
        model = D2Q9()
        rng = np.random.default_rng(3)
        model.initialize(rng.normal(0, 0.001, (24, 8)), 0)
        mass = model.f.sum()
        for _ in range(50):
            model.step()
        self.assertAlmostEqual(model.f.sum(), mass, places=10)

    def test_bad_parameters(self):
        for params in ({"tau": 0.5}, {"ny": 2}, {"tau": np.nan}, {"top_speed": 0.1}):
            with self.assertRaises(ValueError):
                D2Q9(**params)

    def test_analytical_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ("poiseuille", "couette", "shear-wave"):
                with self.subTest(case=name):
                    report = run_case(name, Path(temp)/name,
                                      ny=24 if name == "shear-wave" else 12, wave_steps=100,
                                      max_steps=6000)
                    self.assertTrue(report["passed"], report)
                    self.assertLess(report["profile_relative_l2_error"], 0.01)
                    self.assertLess(report["max_sampled_relative_mass_drift"], 1e-10)
                    self.assertLess(report["final"]["uy_max_abs"], 1e-10)
                    if name != "shear-wave":
                        self.assertTrue(report["steady_converged"])
                    else:
                        self.assertLess(report["nu_relative_error"], 0.01)
                    self.assertTrue((Path(temp)/name/"comparison.png").exists())

    def test_unfinished_case_is_not_passed(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run_case("couette", Path(temp)/"short", max_steps=1)
            self.assertFalse(report["steady_converged"])
            self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()
