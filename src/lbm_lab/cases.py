"""Run channel, shear-wave and Taylor-Green benchmarks against analytical solutions."""

import argparse
import csv
import json
import math
import platform
from pathlib import Path

import numpy as np

from .solver import D2Q9


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_case(name, output, *, ny=32, nx=8, tau=0.8, speed=0.02,
             max_steps=20000, wave_steps=400, check_every=100, steady_tolerance=1e-8):
    if name not in ("poiseuille", "couette", "shear-wave"):
        raise ValueError("unknown case")
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 4 for n in (nx, ny)):
        raise ValueError("nx and ny must be integers >= 4")
    if not math.isfinite(speed) or not 0 < speed <= 0.05:
        raise ValueError("speed must be in (0, 0.05] for these low-Mach benchmarks")
    if any(not isinstance(n, int) or n < 1 for n in (max_steps, wave_steps, check_every)):
        raise ValueError("step counts and check interval must be positive integers")
    if not math.isfinite(steady_tolerance) or not 0 < steady_tolerance < 1:
        raise ValueError("steady tolerance must be in (0, 1)")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output is not empty: {output}")
    nu = (tau - 0.5) / 3
    force = 8*nu*speed/ny**2 if name == "poiseuille" else 0.0
    model = D2Q9(nx, ny, tau, walls=name != "shear-wave",
                  top_speed=speed if name == "couette" else 0, force_x=force)
    output.mkdir(parents=True, exist_ok=True)
    y = np.arange(ny) + 0.5
    k = 2*np.pi/ny
    basis = np.sin(k*y)
    if name == "shear-wave":
        model.initialize(ux=speed*basis[:, None])
    initial_mass = model.diagnostics()["mass"]
    rows = []

    def record(step):
        _rho, ux, _uy = model.macroscopic()
        row = {"step": step, **model.diagnostics()}
        row["relative_mass_drift"] = abs(row["mass"] / initial_mass - 1)
        row["amplitude"] = float(2*np.mean(ux.mean(axis=1)*basis))
        rows.append(row)
        return ux

    previous = record(0)
    converged, residual = False, None
    stop = wave_steps if name == "shear-wave" else max_steps
    for step in range(1, stop + 1):
        model.step()
        interval = min(check_every, 10) if name == "shear-wave" else check_every
        if step % interval == 0 or step == stop:
            ux = record(step)
            residual = float(np.max(np.abs(ux-previous)) / speed)
            previous = ux.copy()
            if name != "shear-wave" and residual < steady_tolerance:
                converged = True
                break
    rho, ux, uy = model.macroscopic()
    measured = ux.mean(axis=1)
    if name == "poiseuille":
        reference = force*y*(ny-y)/(2*nu)
    elif name == "couette":
        reference = speed*y/ny
    else:
        reference = speed*basis*np.exp(-nu*k**2*step)
    error = float(np.linalg.norm(measured-reference) / np.linalg.norm(reference))
    report = {"case": name, "steps": step, "nu_input": nu,
              "profile_relative_l2_error": error, "last_checkpoint_velocity_change": residual,
              "steady_converged": converged if name != "shear-wave" else None,
              "max_sampled_relative_mass_drift": max(r["relative_mass_drift"] for r in rows),
              "max_sampled_mach": max(r["mach_max"] for r in rows),
              "final": model.diagnostics()}
    # Predeclared acceptance thresholds for these low-Mach teaching cases.
    criteria = {"profile_error": error < (0.01 if name != "couette" else 1e-5),
                "mass": report["max_sampled_relative_mass_drift"] < 1e-10,
                "low_mach": report["max_sampled_mach"] < 0.1}
    if name == "shear-wave":
        fit_rows = [r for r in rows if 20 <= r["step"] <= step and r["amplitude"] > 0]
        if len(fit_rows) < 3:
            raise ValueError("shear wave needs at least three samples after step 20")
        slope, intercept = np.polyfit([r["step"] for r in fit_rows],
                                      np.log([r["amplitude"] for r in fit_rows]), 1)
        fitted_nu = float(-slope/k**2)
        report.update({"nu_fitted": fitted_nu, "nu_relative_error": abs(fitted_nu/nu-1),
                       "fit_start_step": fit_rows[0]["step"],
                       "fit_end_step": fit_rows[-1]["step"],
                       "fit_log_intercept": float(intercept)})
        criteria["viscosity"] = report["nu_relative_error"] < 0.01
    else:
        criteria["steady"] = converged
    report["criteria"] = criteria
    report["passed"] = all(criteria.values())
    configuration = {"case": name, "ny": ny, "nx": nx, "tau": tau, "speed": speed,
                     "force_density_x": force, "max_steps": max_steps,
                     "wave_steps": wave_steps, "check_every": check_every,
                     "steady_tolerance": steady_tolerance,
                     "python": platform.python_version(), "numpy": np.__version__}
    _json(output / "config.json", configuration)
    _json(output / "report.json", report)
    np.savez_compressed(output / "fields.npz", rho=rho, ux=ux, uy=uy, y=y,
                        reference_ux=reference)
    with (output / "history.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output / "profile.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["y", "ux_lbm", "ux_reference", "difference"])
        writer.writerows(zip(y, measured, reference, measured-reference))
    _plot(output, name, y, measured, reference, rows, nu, k, speed)
    return report


def _plot(output, name, y, measured, reference, rows, nu, k, speed):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7), constrained_layout=True)
    axes[0].plot(reference, y, "-", label="Analytical")
    axes[0].plot(measured, y, "o", ms=3, label="LBM")
    axes[0].set(xlabel="Velocity ux (lattice units)", ylabel="y (lattice units)", title=name)
    axes[0].legend()
    axes[0].xaxis.set_major_locator(MaxNLocator(5))
    if name == "shear-wave":
        time = np.array([r["step"] for r in rows])
        axes[1].semilogy(time, [r["amplitude"] for r in rows], "o", ms=3, label="LBM")
        axes[1].semilogy(time, speed*np.exp(-nu*k**2*time), "-", label="Analytical")
        axes[1].set(xlabel="Time step", ylabel="Wave amplitude", title="Viscous decay")
        axes[1].legend()
    else:
        axes[1].plot(y, measured-reference, "o-")
        axes[1].set(xlabel="y (lattice units)", ylabel="LBM - analytical velocity",
                    title="Profile error")
        axes[1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0), useOffset=False)
    fig.savefig(output / "comparison.png", dpi=180)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["all", "poiseuille", "couette", "shear-wave", "taylor-green"])
    parser.add_argument("--output", type=Path, default=Path("runs"))
    parser.add_argument("--ny", type=int, default=32)
    parser.add_argument("--nx", type=int, default=8)
    parser.add_argument("--tau", type=float, default=0.8)
    parser.add_argument("--speed", type=float, default=0.02)
    parser.add_argument("--max-steps", type=int, default=20000)
    parser.add_argument("--wave-steps", type=int, default=400)
    parser.add_argument("--vortex-steps", type=int, default=200)
    args = vars(parser.parse_args(argv))
    case, output = args.pop("case"), args.pop("output")
    vortex_steps = args.pop("vortex_steps")
    try:
        if output.exists() and any(output.iterdir()):
            raise ValueError("choose an empty output directory")
        names = ("poiseuille", "couette", "shear-wave", "taylor-green") if case == "all" else (case,)
        reports = {}
        for name in names:
            if name == "taylor-green":
                from .taylor_green import run
                reports[name] = run(output/name, n=args["ny"], tau=args["tau"],
                                     speed=args["speed"], steps=vortex_steps)
            else:
                reports[name] = run_case(name, output/name, **args)
        _json(output / "summary.json", reports)
    except (ValueError, OSError, FloatingPointError) as exc:
        parser.error(str(exc))
    print(json.dumps(reports, indent=2))
    return 0 if all(r["passed"] for r in reports.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
