"""Shear-wave grid comparison at fixed Reynolds number and viscous time."""

import argparse
import json
from itertools import pairwise
from pathlib import Path

import numpy as np

from .cases import run_case


def study(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("choose an empty output directory")
    rows = []
    for ny in (16, 32, 64):
        speed = 0.02 * 32 / ny
        steps = 400 * ny**2 // 32**2
        report = run_case("shear-wave", output/f"n{ny}", ny=ny,
                          speed=speed, wave_steps=steps)
        rows.append({"ny": ny, "speed": speed, "steps": steps,
                     "reynolds": speed*ny/report["nu_input"],
                     "viscous_time": report["nu_input"]*steps/ny**2,
                     "relative_l2_error": report["profile_relative_l2_error"],
                     "nu_relative_error": report["nu_relative_error"],
                     "case_passed": report["passed"]})
    orders = [float(np.log(a["relative_l2_error"]/b["relative_l2_error"])/np.log(2))
              for a, b in pairwise(rows)]
    result = {"cases": rows, "observed_profile_orders": orders,
              "error_decreases": all(a["relative_l2_error"] > b["relative_l2_error"]
                                     for a, b in pairwise(rows))}
    (output/"study.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 3.5), constrained_layout=True)
    ax.loglog([r["ny"] for r in rows], [r["relative_l2_error"] for r in rows], "o-")
    ax.set(xlabel="Grid height N", ylabel="Relative L2 velocity error",
           title="Shear wave: fixed Re and viscous time")
    fig.savefig(output/"refinement.png", dpi=180)
    plt.close(fig)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("refinement-run"))
    args = parser.parse_args()
    try:
        result = study(args.output)
    except (ValueError, OSError, FloatingPointError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result["error_decreases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
