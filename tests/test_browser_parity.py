"""Cross-check the independent JavaScript solver against Python using Node.js."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

import numpy as np

from lbm_lab.solver import D2Q9
from lbm_lab.taylor_green import reference

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js is needed for browser/Python parity tests")
class BrowserParityTests(unittest.TestCase):
    def test_same_discrete_evolution(self):
        for name in ("poiseuille", "couette", "shear-wave", "taylor-green"):
            with self.subTest(case=name):
                config = {"case": name, "ny": 16, "tau": 0.8, "speed": 0.02,
                          "maxSteps": 100, "waveSteps": 100}
                script = ("const {runBenchmark}=require('./demo/solver.js');"
                          "console.log(JSON.stringify(runBenchmark(JSON.parse(process.argv[1]))));")
                completed = subprocess.run(["node", "-e", script, json.dumps(config)], cwd=ROOT,
                                           capture_output=True, text=True, check=True)
                browser = json.loads(completed.stdout)
                nu = 0.1
                model = D2Q9(nx=16 if name == "taylor-green" else 8,
                              ny=16, tau=0.8, walls=name in ("poiseuille", "couette"),
                              top_speed=0.02 if name == "couette" else 0,
                              force_x=8*nu*0.02/16**2 if name == "poiseuille" else 0)
                if name == "shear-wave":
                    model.initialize(0.02*np.sin(2*np.pi*(np.arange(16)+0.5)/16)[:, None])
                elif name == "taylor-green":
                    ux0, uy0, rho0 = reference(16, 0.02, nu, 0)
                    model.initialize(ux0, uy0, rho0)
                for _ in range(100):
                    model.step()
                if name == "taylor-green":
                    np.testing.assert_allclose(np.array(browser["ux"]).reshape(16, 16),
                                               model.macroscopic()[1], atol=2e-13, rtol=1e-10)
                    np.testing.assert_allclose(np.array(browser["uy"]).reshape(16, 16),
                                               model.macroscopic()[2], atol=2e-13, rtol=1e-10)
                else:
                    np.testing.assert_allclose(browser["profile"], model.macroscopic()[1].mean(axis=1),
                                               atol=2e-13, rtol=1e-10)


if __name__ == "__main__":
    unittest.main()
