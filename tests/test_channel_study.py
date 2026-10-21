import tempfile
import unittest
from pathlib import Path

from lbm_lab.channel_study import study


class ChannelStudyTests(unittest.TestCase):
    def test_matched_reynolds_and_decreasing_error(self):
        with tempfile.TemporaryDirectory() as temp:
            result = study(Path(temp)/"channel", grids=(8, 16), taus=(0.8,))
            self.assertTrue(result["all_steady"])
            self.assertTrue(result["all_errors_decrease"])
            for row in result["cases"]:
                self.assertAlmostEqual(row["reynolds"], 3.2)
            order = result["groups"][0]["observed_orders"][0]
            self.assertGreater(order, 1.8)
            self.assertLess(order, 2.2)


if __name__ == "__main__":
    unittest.main()
