"""Two-dimensional periodic Taylor-Green vortex with continuum reference fields."""

import argparse
import csv
import json
import math
import platform
from pathlib import Path

import numpy as np

from .solver import D2Q9


def reference(n, speed, nu, time):
    """Return ux, uy and weakly compressible pressure-consistent density."""
    y, x = np.indices((n, n), dtype=float) + 0.5
    k = 2*np.pi/n
    amplitude = speed*np.exp(-2*nu*k**2*time)
    ux = -amplitude*np.cos(k*x)*np.sin(k*y)
    uy = amplitude*np.sin(k*x)*np.cos(k*y)
    rho = 1 - 3*amplitude**2/4*(np.cos(2*k*x)+np.cos(2*k*y))
    return ux, uy, rho


def run(output, *, n=32, tau=0.8, speed=0.02, steps=200, every=10):
    if not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer >= 8")
    if not math.isfinite(speed) or not 0 < speed <= 0.05:
        raise ValueError("speed must be in (0, 0.05]")
    if not isinstance(steps, int) or steps < 40 or not isinstance(every, int) or every < 1:
        raise ValueError("steps must be >= 40 and every must be positive")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("choose an empty output directory")
    model = D2Q9(nx=n, ny=n, tau=tau)
    ux0, uy0, rho0 = reference(n, speed, model.nu, 0)
    model.initialize(ux0, uy0, rho0)
    output.mkdir(parents=True, exist_ok=True)
    mass0 = float(rho0.sum())
    denominator = float(np.sum(ux0**2+uy0**2))
    rows = []
    k = 2*np.pi/n
    for step in range(steps+1):
        if step % every == 0 or step == steps:
            rho, ux, uy = model.macroscopic()
            ref_x, ref_y, _ = reference(n, speed, model.nu, step)
            error = np.sqrt(np.sum((ux-ref_x)**2+(uy-ref_y)**2) /
                            np.sum(ref_x**2+ref_y**2))
            amplitude = speed*np.sum(ux*ux0+uy*uy0)/denominator
            energy_ref = n**2*speed**2/4*np.exp(-4*model.nu*k**2*step)
            rows.append({"step": step, **model.diagnostics(),
                         "relative_mass_drift": abs(float(rho.sum())/mass0-1),
                         "velocity_relative_l2_error": float(error),
                         "amplitude": float(amplitude),
                         "reference_amplitude": float(speed*np.exp(-2*model.nu*k**2*step)),
                         "reference_kinetic_energy": float(energy_ref)})
        if step < steps:
            model.step()
    fit = [r for r in rows if r["step"] >= 20 and r["amplitude"] > 0]
    if len(fit) < 3:
        raise ValueError("provide at least three saved samples from step 20 onward")
    slope, _ = np.polyfit([r["step"] for r in fit], np.log([r["amplitude"] for r in fit]), 1)
    fitted_nu = float(-slope/(2*k**2))
    final = rows[-1]
    energy_error = abs(final["kinetic_energy"]/final["reference_kinetic_energy"]-1)
    criteria = {"velocity": final["velocity_relative_l2_error"] < 0.01,
                "energy": energy_error < 0.02,
                "viscosity": abs(fitted_nu/model.nu-1) < 0.01,
                "mass": max(r["relative_mass_drift"] for r in rows) < 1e-10,
                "low_mach": max(r["mach_max"] for r in rows) < 0.1}
    report = {"case": "taylor-green", "n": n, "steps": steps, "nu_input": model.nu,
              "nu_fitted": fitted_nu, "nu_relative_error": abs(fitted_nu/model.nu-1),
              "velocity_relative_l2_error": final["velocity_relative_l2_error"],
              "kinetic_energy_relative_error": energy_error,
              "max_sampled_relative_mass_drift": max(r["relative_mass_drift"] for r in rows),
              "fit_start_step": fit[0]["step"], "fit_end_step": fit[-1]["step"],
              "criteria": criteria, "passed": all(criteria.values())}
    config = {"n": n, "tau": tau, "speed": speed, "steps": steps, "every": every,
              "python": platform.python_version(), "numpy": np.__version__}
    for name, data in (("config.json", config), ("report.json", report)):
        (output/name).write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    with (output/"history.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    np.savez_compressed(output/"fields.npz", rho=rho, ux=ux, uy=uy,
                        reference_ux=ref_x, reference_uy=ref_y)
    plot(output, ux, uy, ref_x, ref_y, rows, n)
    return report


def plot(output, ux, uy, ref_x, ref_y, rows, n):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), constrained_layout=True)
    y, x = np.indices((n, n), dtype=float) + 0.5
    magnitude = np.hypot(ux, uy)
    im = axes[0].imshow(magnitude, origin="lower", extent=(0, n, 0, n), cmap="viridis")
    stride = max(1, n//12)
    axes[0].quiver(x[::stride, ::stride], y[::stride, ::stride],
                   ux[::stride, ::stride], uy[::stride, ::stride], color="white")
    axes[0].set(title="Computed velocity", xlabel="x", ylabel="y")
    fig.colorbar(im, ax=axes[0], label="Speed", shrink=0.8)
    error = np.hypot(ux-ref_x, uy-ref_y)
    im = axes[1].imshow(error, origin="lower", extent=(0, n, 0, n), cmap="magma")
    axes[1].set(title="Velocity error magnitude", xlabel="x", ylabel="y")
    fig.colorbar(im, ax=axes[1], shrink=0.8)
    axes[2].semilogy([r["step"] for r in rows],
                     [r["reference_kinetic_energy"] for r in rows], label="Analytical")
    axes[2].semilogy([r["step"] for r in rows], [r["kinetic_energy"] for r in rows],
                     "o", ms=3, label="LBM")
    axes[2].set(title="Kinetic energy decay", xlabel="Time step", ylabel="Kinetic energy")
    axes[2].legend()
    fig.savefig(output/"comparison.png", dpi=180)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("taylor-green-run"))
    parser.add_argument("--n", type=int, default=32)
    parser.add_argument("--tau", type=float, default=0.8)
    parser.add_argument("--speed", type=float, default=0.02)
    parser.add_argument("--steps", type=int, default=200)
    args = vars(parser.parse_args(argv))
    try:
        report = run(**args)
    except (ValueError, OSError, FloatingPointError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
