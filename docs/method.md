# Numerical method

## D2Q9

Populations `f[i,y,x]` represent nine velocities: rest, four axis directions and four diagonals. Weights are 4/9, 1/9 and 1/36 respectively. The isothermal sound speed squared is 1/3. The second-order equilibrium is

```text
f_eq_i = w_i rho [1 + 3 c_i·u + 4.5 (c_i·u)² - 1.5 u·u].
```

BGK collision uses omega = 1/tau. The kinematic viscosity is `(tau-0.5)/3` in lattice units. The model approximates weakly compressible isothermal flow at low Mach number.

## Force and velocity

For a constant x-directed force density F, the Guo source used here is

```text
S_i = w_i (1-omega/2) [3(c_ix-u_x) + 9(c_i·u)c_ix] F.
f_post_i = f_i - omega (f_i-f_eq_i) + S_i.
rho u_x = sum_i c_ix f_i + F/2.
```

F is force per lattice volume. Reference density is one; the continuum reference for Poiseuille flow uses this density. Initial populations use a raw x-momentum offset of -F/2 so the initial corrected velocity is zero.

## Streaming and walls

Post-collision populations are pushed to neighbouring nodes. x is periodic in every case. The shear wave is also periodic in y. Wall cases replace the y-wrapped populations with halfway bounce-back values at the same fluid node.

The lower wall is stationary. At the upper wall, incoming direction i is reconstructed as

```text
f_i = f_post_opposite(i) + 6 w_i rho c_ix U_wall.
```

There are N fluid nodes across the channel, with coordinates `y=j+0.5` and walls at 0 and H=N. Using H=N-1 would compare against the wrong geometry. The wall density in the correction is the pre-collision local density.

## Reference solutions

Poiseuille flow is driven by `F=8 nu U/H²`. With unit reference density,

```text
u_x(y) = F y(H-y)/(2 nu).
```

Here U denotes the continuum peak, not the maximum at a sampled node. Couette flow uses

```text
u_x(y) = U_wall y/H.
```

The periodic shear wave has k=2pi/N and

```text
u_x(y,t) = A sin(ky) exp(-nu k² t), u_y=0.
```

The amplitude is obtained by projection `2 mean_y[u_x sin(ky)]`. Fitting log amplitude versus time from step 20 onward gives `nu_fit=-slope/k²`. Equilibrium initialization produces a short kinetic startup transient, which still affects the final profile error. The fitted intercept is free. This is an incompressible continuum reference, not an exact discrete-LBM solution.

## Acceptance checks

Relative profile error is `norm(u_lbm-u_ref)/norm(u_ref)`, using the x-averaged profile. Poiseuille and shear-wave tolerances are 1%; Couette tolerance is 1e-5. Relative sampled mass drift must be below 1e-10, and sampled Mach number below 0.1. Wall cases additionally require a velocity change below 1e-8 over the last checkpoint interval, normalized by U. Shear-wave fitted viscosity must differ by less than 1% from the input.

These tolerances are teaching/regression checks, not universal accuracy guarantees. Histories contain sampled diagnostics, not every time step. The shared solver tests mass conservation and force-induced momentum independently of these case checks. BGK bounce-back can exhibit a grid- and relaxation-dependent channel slip error; the reference profile is not adjusted to hide that error.

## Refinement scaling

The wave study keeps tau=0.8, nx=8 and `U*N/nu=6.4`. As N doubles, U halves and the step count quadruples. The dimensionless time `nu*t/N²=0.0390625` is fixed. This is diffusive scaling: temporal and spatial resolution change together. The observed order therefore describes this refinement path, not an independent temporal convergence test. x refinement is unnecessary for the imposed x-independent solution; it does not validate general x-dependent flows.

## References

- Guo, Zheng and Shi (2002), *Discrete lattice effects on the forcing term in the lattice Boltzmann method*, Phys. Rev. E 65, 046308. [DOI](https://doi.org/10.1103/PhysRevE.65.046308).
- Zou and He (1997), *On pressure and velocity boundary conditions for the lattice Boltzmann BGK model*, Physics of Fluids 9, 1591–1598. [Preprint](https://arxiv.org/abs/comp-gas/9611001). Background on halfway bounce-back; this code uses periodic x and has no pressure inlet/outlet implementation.
- [waLBerla boundary-condition tutorial](https://www.walberla.net/doxygen/tutorial_lbm06.html) for further boundary-condition examples.

The implementation is written for this project; these references describe methods and related benchmarks.
