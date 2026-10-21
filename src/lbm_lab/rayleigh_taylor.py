"""Exploratory low-Atwood Cahn-Hilliard/Boussinesq-LBM Rayleigh-Taylor experiment."""

import argparse
import csv
import json
import math
import platform
from pathlib import Path

import numpy as np

from .solver import D2Q9


def laplacian(a):
    """Periodic x, zero normal face gradient in y, unit grid spacing."""
    padded = np.pad(a, ((1, 1), (0, 0)), mode="edge")
    return np.roll(a, 1, axis=1)+np.roll(a, -1, axis=1)+padded[:-2]+padded[2:]-4*a


def gradient(a):
    padded = np.pad(a, ((1, 1), (0, 0)), mode="edge")
    return (np.roll(a, -1, axis=1)-np.roll(a, 1, axis=1))/2, (padded[2:]-padded[:-2])/2


def minmod(a, b):
    return np.where(a*b > 0, np.sign(a)*np.minimum(np.abs(a), np.abs(b)), 0)


def phase_rhs(phi, ux, uy, mobility, beta, kappa):
    """Conservative limited face advection plus chemical-potential diffusion."""
    right, left = np.roll(phi, -1, axis=1), np.roll(phi, 1, axis=1)
    sx = minmod(phi-left, right-phi)
    vx = (ux+np.roll(ux, -1, axis=1))/2
    flux_x = vx*np.where(vx >= 0, phi+sx/2, right-np.roll(sx, -1, axis=1)/2)
    padded = np.pad(phi, ((1, 1), (0, 0)), mode="edge")
    sy = minmod(phi-padded[:-2], padded[2:]-phi)
    vy = (uy[:-1]+uy[1:])/2
    flux_y = np.zeros((phi.shape[0]+1, phi.shape[1]))
    flux_y[1:-1] = vy*np.where(vy >= 0, phi[:-1]+sy[:-1]/2, phi[1:]-sy[1:]/2)
    mu = beta*(phi**3-phi)-kappa*laplacian(phi)
    return -(flux_x-np.roll(flux_x, 1, axis=1))-(flux_y[1:]-flux_y[:-1])+mobility*laplacian(mu)


def advance_phase(phi, ux, uy, mobility=2.0, beta=0.001, kappa=0.002):
    """One lattice time step using SSP-RK2; no clipping or mean correction."""
    first = phi+phase_rhs(phi, ux, uy, mobility, beta, kappa)
    return (phi+first+phase_rhs(first, ux, uy, mobility, beta, kappa))/2


def forces(phi, *, atwood, gravity, beta, kappa):
    mu = beta*(phi**3-phi)-kappa*laplacian(phi)
    gx, gy = gradient(mu)
    return -phi*gx, -phi*gy-atwood*gravity*phi


def interface_bounds(phi):
    lower, upper = phi[:-1], phi[1:]
    crossing = (lower*upper <= 0) & (lower != upper)
    yy, xx = np.nonzero(crossing)
    if not yy.size:
        return None, None
    heights = yy+0.5-lower[yy, xx]/(upper[yy, xx]-lower[yy, xx])
    return float(heights.min()), float(heights.max())


def simulate(output, *, nx=64, ny=128, steps=5000, every=250, tau=0.65,
             atwood=0.05, gravity=0.0004, amplitude=2.0, mobility=2.0,
             beta=0.001, kappa=0.002, make_animation=True):
    if any(not isinstance(n, int) or n < 16 for n in (nx, ny)):
        raise ValueError("nx and ny must be integers >= 16")
    if not isinstance(steps, int) or steps < 1 or not isinstance(every, int) or every < 1:
        raise ValueError("steps and every must be positive integers")
    if not math.isfinite(atwood) or not 0 < atwood <= 0.1:
        raise ValueError("Boussinesq demo supports 0 < Atwood <= 0.1")
    if not math.isfinite(gravity) or gravity < 0 or not math.isfinite(amplitude) or not 0 <= amplitude < ny/8:
        raise ValueError("gravity must be nonnegative and amplitude in [0, ny/8)")
    for value in (mobility, beta, kappa):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("phase parameters must be finite and positive")
    if mobility*(8*beta+64*kappa) > 1:
        raise ValueError("phase diffusion is too stiff for this explicit step")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("choose an empty output directory")
    model = D2Q9(nx=nx, ny=ny, tau=tau, walls=True)
    y, x = np.indices((ny, nx), dtype=float)+0.5
    height = ny/2+amplitude*np.cos(2*np.pi*x/nx)
    phi = np.tanh((y-height)/math.sqrt(2*kappa/beta))
    fx, fy = forces(phi, atwood=atwood, gravity=gravity, beta=beta, kappa=kappa)
    model.set_force(fx, fy)
    # Support the horizontal-mean initial force with approximate hydrostatic pressure.
    mean_force = fy.mean(axis=1)
    pressure = np.zeros(ny)
    pressure[1:] = np.cumsum((mean_force[1:]+mean_force[:-1])/2)
    rho0 = np.broadcast_to((1+3*(pressure-pressure.mean()))[:, None], phi.shape)
    model.initialize(rho=rho0)
    phase0, mass0 = float(phi.sum()), float(rho0.sum())
    output.mkdir(parents=True, exist_ok=True)
    history, snapshots, times = [], [], []
    failure = None

    def record(step):
        low, high = interface_bounds(phi)
        row = {"step": step, **model.diagnostics(), "phase_sum": float(phi.sum()),
               "phase_mean_drift": abs(float(phi.sum())-phase0)/(nx*ny),
               "relative_mass_drift": abs(model.diagnostics()["mass"]/mass0-1),
               "phi_min": float(phi.min()), "phi_max": float(phi.max()),
               "interface_low": low, "interface_high": high}
        history.append(row)
        snapshots.append(phi.copy())
        times.append(step)

    record(0)
    completed = 0
    for step in range(1, steps+1):
        try:
            model.step()
            _rho, ux, uy = model.macroscopic()
            with np.errstate(over="raise", invalid="raise"):
                phi = advance_phase(phi, ux, uy, mobility, beta, kappa)
            if not np.isfinite(phi).all() or np.max(np.abs(phi)) > 1.5:
                raise FloatingPointError("phase field exceeded numerical guard")
            model.set_force(*forces(phi, atwood=atwood, gravity=gravity, beta=beta, kappa=kappa))
            if model.diagnostics()["mach_max"] > 0.15:
                raise FloatingPointError("Mach guard exceeded; reduce gravity or run duration")
            completed = step
            if step % every == 0 or step == steps:
                record(step)
        except FloatingPointError as exc:
            failure = f"Step {step}: {exc}"
            break
    config = {"nx": nx, "ny": ny, "steps": steps, "every": every, "tau": tau,
              "atwood": atwood, "gravity": gravity, "amplitude": amplitude,
              "mobility": mobility, "beta": beta, "kappa": kappa,
              "model": "Boussinesq CH / D2Q9-BGK, exploratory",
              "python": platform.python_version(), "numpy": np.__version__}
    report = {"completed_steps": completed, "requested_steps": steps, "failure": failure,
              "max_sampled_phase_mean_drift": max(r["phase_mean_drift"] for r in history),
              "max_sampled_relative_mass_drift": max(r["relative_mass_drift"] for r in history),
              "max_sampled_mach": max(r["mach_max"] for r in history),
              "initial_interface_low": history[0]["interface_low"],
              "initial_interface_high": history[0]["interface_high"],
              "last_saved_interface_low": history[-1]["interface_low"],
              "last_saved_interface_high": history[-1]["interface_high"],
              "last_saved_step": history[-1]["step"],
              "validation_status": "exploratory demonstration; no benchmark pass claimed"}
    for name, data in (("config.json", config), ("report.json", report)):
        (output/name).write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    with (output/"history.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    np.savez_compressed(output/"snapshots.npz", phi=np.array(snapshots), time=np.array(times))
    plot(output, snapshots, times, history, nx, ny, make_animation)
    return report


def plot(output, snapshots, times, history, nx, ny, make_animation):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    indices = np.unique(np.linspace(0, len(times)-1, min(4, len(times)), dtype=int))
    fig, axes = plt.subplots(1, len(indices), figsize=(3*len(indices), 5),
                             squeeze=False, constrained_layout=True)
    for ax, index in zip(axes[0], indices):
        im = ax.imshow(snapshots[index], origin="lower", extent=(0, nx, 0, ny),
                       cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set(title=f"t = {times[index]}", xlabel="x", ylabel="y")
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Phase: -1 light, +1 heavy", shrink=0.8)
    fig.savefig(output/"interface.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.3), constrained_layout=True)
    t = [r["step"] for r in history]
    axes[0].plot(t, [r["interface_high"] for r in history], label="Highest phi=0 crossing")
    axes[0].plot(t, [r["interface_low"] for r in history], label="Lowest phi=0 crossing")
    axes[0].set(xlabel="Time step", ylabel="Interface height")
    axes[0].legend(fontsize=8)
    axes[1].plot(t, [r["phase_mean_drift"] for r in history], label="Mean phase drift")
    axes[1].plot(t, [r["relative_mass_drift"] for r in history], label="Relative fluid mass drift")
    axes[1].set(xlabel="Time step", ylabel="Absolute drift")
    axes[1].legend(fontsize=8)
    fig.savefig(output/"diagnostics.png", dpi=150)
    plt.close(fig)
    if make_animation:
        from PIL import Image, ImageDraw
        frames = []
        cmap = plt.get_cmap("RdBu_r")
        for field, time in zip(snapshots, times):
            rgb = (cmap(np.clip((field+1)/2, 0, 1))[::-1, :, :3]*255).astype("uint8")
            image = Image.fromarray(rgb).resize((nx*4, ny*4), resample=Image.Resampling.NEAREST)
            frame = Image.new("RGB", (nx*4, ny*4+40), "white")
            frame.paste(image, (0, 40))
            draw = ImageDraw.Draw(frame)
            draw.text((8, 3), f"RT demo | t={time}", fill="black")
            draw.text((8, 20), "red: heavy | blue: light", fill="black")
            frames.append(frame)
        frames[0].save(output/"evolution.gif", save_all=True, append_images=frames[1:],
                       duration=180, loop=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("rayleigh-taylor-run"))
    for name, default in (("nx", 64), ("ny", 128), ("steps", 5000), ("every", 250)):
        parser.add_argument(f"--{name}", type=int, default=default)
    for name, default in (("gravity", 0.0004), ("atwood", 0.05), ("amplitude", 2.0)):
        parser.add_argument(f"--{name}", type=float, default=default)
    args = vars(parser.parse_args())
    try:
        report = simulate(**args)
    except (ValueError, OSError, FloatingPointError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 1 if report["failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
