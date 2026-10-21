"""Poiseuille refinement and BGK relaxation-time sensitivity at fixed Reynolds number."""

import argparse
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np

from .cases import run_case


def study(output, grids=(12, 24, 48), taus=(0.7, 0.8, 1.0)):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("choose an empty output directory")
    rows, groups = [], []
    for tau in taus:
        group = []
        nu = (tau - 0.5)/3
        for ny in grids:
            speed = 3.2*nu/ny
            report = run_case("poiseuille", output/f"tau-{tau:g}-n{ny}",
                              ny=ny, tau=tau, speed=speed,
                              max_steps=math.ceil(2.5*ny**2/nu),
                              steady_tolerance=1e-10)
            row = {"tau": tau, "ny": ny, "nu": nu, "speed": speed,
                   "reynolds": speed*ny/nu,
                   "relative_l2_error": report["profile_relative_l2_error"],
                   "steady_converged": report["steady_converged"],
                   "steps": report["steps"], "case_passed": report["passed"]}
            rows.append(row)
            group.append(row)
        orders = [float(np.log(a["relative_l2_error"]/b["relative_l2_error"]) /
                        np.log(b["ny"]/a["ny"])) for a, b in pairwise(group)]
        groups.append({"tau": tau, "observed_orders": orders,
                       "error_decreases": all(a["relative_l2_error"] > b["relative_l2_error"]
                                              for a, b in pairwise(group))})
    result = {"reynolds": 3.2, "cases": rows, "groups": groups,
              "all_steady": all(r["steady_converged"] for r in rows),
              "all_errors_decrease": all(g["error_decreases"] for g in groups)}
    (output/"study.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for tau in taus:
        subset = [r for r in rows if r["tau"] == tau]
        ax.loglog([r["ny"] for r in subset], [r["relative_l2_error"] for r in subset],
                  "o-", label=f"tau = {tau:g}")
    ax.set(xlabel="Channel height N", ylabel="Relative L2 velocity error",
           title="Poiseuille flow, Re = 3.2")
    ax.legend()
    fig.savefig(output/"channel-refinement.png", dpi=180)
    plt.close(fig)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("channel-study-run"))
    args = parser.parse_args()
    try:
        result = study(args.output)
    except (ValueError, OSError, FloatingPointError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result["all_steady"] and result["all_errors_decrease"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
