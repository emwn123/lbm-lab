import tempfile
import unittest
from pathlib import Path

import numpy as np

from lbm_lab.rayleigh_taylor import advance_phase, forces, laplacian, phase_rhs, simulate
from lbm_lab.solver import D2Q9


class RayleighTaylorTests(unittest.TestCase):
    def test_vertical_force_increment(self):
        model = D2Q9(force_y=-1e-5)
        self.assertAlmostEqual(model.macroscopic()[2].mean(), 0, places=14)
        for _ in range(20):
            model.step()
        self.assertAlmostEqual(model.macroscopic()[2].mean(), -20e-5, places=13)

    def test_variable_force_increment(self):
        model = D2Q9(nx=8, ny=8)
        force = np.broadcast_to(np.linspace(-1e-5, 1e-5, 8)[:, None], (8, 8))
        model.set_force(0, force)
        model.initialize()
        initial = model.f.sum()
        model.step()
        self.assertAlmostEqual(model.f.sum(), initial, places=12)
        self.assertTrue(np.isfinite(model.macroscopic()[2]).all())

    def test_phase_conservation(self):
        rng = np.random.default_rng(5)
        phi = rng.uniform(-0.1, 0.1, (16, 16))
        ux, uy = rng.normal(0, 0.01, (2, 16, 16))
        rhs = phase_rhs(phi, ux, uy, 2, 0.001, 0.002)
        self.assertAlmostEqual(rhs.sum(), 0, places=13)
        updated = advance_phase(phi, ux, uy)
        self.assertAlmostEqual(updated.sum(), phi.sum(), places=13)
        self.assertAlmostEqual(laplacian(phi).sum(), 0, places=13)

    def test_uniform_phase_and_buoyancy_direction(self):
        phi = np.ones((16, 16))
        np.testing.assert_allclose(advance_phase(phi, phi*0, phi*0), phi)
        fx, fy = forces(phi, atwood=0.05, gravity=0.0004, beta=0.001, kappa=0.002)
        np.testing.assert_allclose(fx, 0)
        np.testing.assert_allclose(fy, -2e-5)

    def test_short_coupled_run(self):
        with tempfile.TemporaryDirectory() as temp:
            report = simulate(Path(temp)/"rt", nx=16, ny=32, steps=30, every=10,
                              amplitude=0.5, make_animation=False)
            self.assertIsNone(report["failure"])
            self.assertEqual(report["completed_steps"], 30)
            self.assertLess(report["max_sampled_phase_mean_drift"], 1e-12)
            self.assertLess(report["max_sampled_relative_mass_drift"], 1e-10)


if __name__ == "__main__":
    unittest.main()
