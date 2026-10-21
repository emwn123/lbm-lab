import tempfile
import unittest
from pathlib import Path

import numpy as np

from lbm_lab.solver import D2Q9
from lbm_lab.taylor_green import reference, run


class TaylorGreenTests(unittest.TestCase):
    def test_reference_decay_and_energy(self):
        n, speed, nu, time = 32, 0.02, 0.1, 100
        ux0, uy0, rho = reference(n, speed, nu, 0)
        ux, uy, _ = reference(n, speed, nu, time)
        decay = np.exp(-2*nu*(2*np.pi/n)**2*time)
        np.testing.assert_allclose(ux, ux0*decay, atol=1e-15)
        np.testing.assert_allclose(uy, uy0*decay, atol=1e-15)
        self.assertAlmostEqual(np.sum(0.5*(ux**2+uy**2)), n*n*speed*speed/4*decay**2)
        self.assertAlmostEqual(rho.mean(), 1)
        self.assertGreater(ux0.std(axis=1).max(), 0.001)
        self.assertGreater(uy0.std(axis=0).max(), 0.001)

    def test_variable_density_initialization(self):
        model = D2Q9(nx=16, ny=16, force_x=1e-5)
        ux, uy, rho = reference(16, 0.02, model.nu, 0)
        model.initialize(ux, uy, rho)
        actual_rho, actual_ux, actual_uy = model.macroscopic()
        np.testing.assert_allclose(actual_rho, rho, atol=1e-14)
        np.testing.assert_allclose(actual_ux, ux, atol=1e-14)
        np.testing.assert_allclose(actual_uy, uy, atol=1e-14)
        with self.assertRaises(ValueError):
            model.initialize(rho=0)

    def test_default_case(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run(Path(temp)/"vortex")
            self.assertTrue(report["passed"], report)
            self.assertLess(report["velocity_relative_l2_error"], 0.01)
            self.assertLess(report["kinetic_energy_relative_error"], 0.02)


if __name__ == "__main__":
    unittest.main()
