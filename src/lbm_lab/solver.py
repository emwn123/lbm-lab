"""A small D2Q9 BGK solver in lattice units (dx = dt = rho_ref = 1)."""

import math

import numpy as np

C = np.array([(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1),
              (1, 1), (-1, 1), (-1, -1), (1, -1)])
W = np.array([4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36])
OPPOSITE = np.array([0, 3, 4, 1, 2, 7, 8, 5, 6])


def equilibrium(rho, ux, uy):
    """Second-order isothermal equilibrium; arrays have shape [y, x]."""
    cu = C[:, 0, None, None] * ux + C[:, 1, None, None] * uy
    return W[:, None, None] * rho * (1 + 3*cu + 4.5*cu**2 - 1.5*(ux**2 + uy**2))


class D2Q9:
    """Periodic x; periodic y or halfway bounce-back horizontal walls.

    Forces are force densities, not accelerations, and may vary in space. Physical velocity
    includes the half-force correction. All boundaries are grid aligned.
    """

    def __init__(self, nx=8, ny=24, tau=0.8, *, walls=False, top_speed=0.0,
                 force_x=0.0, force_y=0.0):
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 4 for n in (nx, ny)):
            raise ValueError("nx and ny must be integers >= 4")
        if not math.isfinite(tau) or tau <= 0.5:
            raise ValueError("tau must be finite and greater than 0.5")
        if not math.isfinite(top_speed):
            raise ValueError("wall speed must be finite")
        if top_speed and not walls:
            raise ValueError("moving wall requires walls=True")
        self.nx, self.ny, self.tau = nx, ny, tau
        self.nu = (tau - 0.5) / 3
        self.walls, self.top_speed = walls, top_speed
        self.set_force(force_x, force_y)
        self.initialize()

    def set_force(self, force_x=0.0, force_y=0.0):
        """Set finite force fields on the fluid grid, including scalar inputs."""
        shape = (self.ny, self.nx)
        fx = np.broadcast_to(np.asarray(force_x, dtype=float), shape)
        fy = np.broadcast_to(np.asarray(force_y, dtype=float), shape)
        if not np.isfinite(fx).all() or not np.isfinite(fy).all():
            raise ValueError("forces must be finite")
        self.force_x, self.force_y = fx.copy(), fy.copy()
        self._has_force = bool(np.any(fx) or np.any(fy))

    def initialize(self, ux=0.0, uy=0.0, rho=1.0):
        """Initialize density and the requested macroscopic velocity."""
        shape = (self.ny, self.nx)
        ux = np.broadcast_to(np.asarray(ux, dtype=float), shape)
        uy = np.broadcast_to(np.asarray(uy, dtype=float), shape)
        rho = np.broadcast_to(np.asarray(rho, dtype=float), shape)
        if not np.isfinite(ux).all() or not np.isfinite(uy).all():
            raise ValueError("initial velocity must be finite")
        if not np.isfinite(rho).all() or (rho <= 0).any():
            raise ValueError("initial density must be finite and positive")
        self.f = equilibrium(rho, ux - self.force_x/(2*rho), uy - self.force_y/(2*rho))

    def macroscopic(self):
        rho = self.f.sum(axis=0)
        if not np.isfinite(self.f).all() or (rho <= 0).any():
            raise FloatingPointError("invalid populations or density")
        momentum_x = np.einsum("i,iyx->yx", C[:, 0], self.f)
        momentum_y = np.einsum("i,iyx->yx", C[:, 1], self.f)
        return rho, (momentum_x + self.force_x/2) / rho, (momentum_y + self.force_y/2) / rho

    def step(self):
        rho, ux, uy = self.macroscopic()
        omega = 1 / self.tau
        post = self.f - omega * (self.f - equilibrium(rho, ux, uy))
        if self._has_force:
            cu = C[:, 0, None, None] * ux + C[:, 1, None, None] * uy
            source = W[:, None, None] * (1 - omega/2) * (
                3*((C[:, 0, None, None]-ux)*self.force_x +
                   (C[:, 1, None, None]-uy)*self.force_y) +
                9*cu*(C[:, 0, None, None]*self.force_x + C[:, 1, None, None]*self.force_y))
            post += source
        # Push streaming. Wrapped wall-crossing values are replaced below.
        for i, (cx, cy) in enumerate(C):
            self.f[i] = np.roll(post[i], shift=(int(cy), int(cx)), axis=(0, 1))
        if self.walls:
            for i, (cx, cy) in enumerate(C):
                if cy == 1:
                    self.f[i, 0] = post[OPPOSITE[i], 0]
                elif cy == -1:
                    self.f[i, -1] = (post[OPPOSITE[i], -1] +
                                     6*W[i]*rho[-1]*cx*self.top_speed)

    def diagnostics(self):
        rho, ux, uy = self.macroscopic()
        speed = np.hypot(ux, uy)
        return {"mass": float(rho.sum()), "rho_min": float(rho.min()),
                "rho_max": float(rho.max()), "mach_max": float(speed.max()*np.sqrt(3)),
                "kinetic_energy": float(np.sum(0.5*rho*speed**2)),
                "uy_max_abs": float(np.abs(uy).max())}
