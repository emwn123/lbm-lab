# Changelog

## 0.4.1

- Integrate a live Rayleigh–Taylor solver into the shared browser selector and Run experiment control.
- Add step-count and gravity controls, a live phase map, cancellation and completed-run JSON.
- Cross-check the JavaScript phase field against Python and document a 20000-step local run and wall-interaction limits.


## 0.4.0

- Add an exploratory low-Atwood Rayleigh-Taylor case coupling Cahn-Hilliard transport and Boussinesq LBM flow.
- Extend Guo forcing to finite spatial x/y force fields and test vertical-force momentum and phase conservation.
- Include a recorded 5000-step run, matched early-time controls, interface snapshots and diagnostics.
- Keep the experimental case separate from the four analytical benchmark checks.

- Add a direct online entry and a bilingual first-experiment guide.
- Add trial-feedback and bug-report forms, including feedback context.
- Link first-run help and feedback from the browser footer.

## 0.3.0

- Add a square-domain Taylor-Green vortex with full-field velocity and kinetic-energy checks.
- Add pressure-consistent initial density and verify JavaScript/Python agreement for both velocity components.
- Add a browser velocity map and four guided experiment cards in English and Chinese.
- Include Taylor-Green in `lbm-lab all` and add `--vortex-steps` for its duration.

## 0.2.0

- Add browser experiments with local computation, parameter controls, cancellation and JSON export.
- Cross-check the JavaScript D2Q9 implementation against Python.
- Add nine Poiseuille grid/relaxation-time cases at fixed Reynolds number, with measured convergence results.
- Include browser solver checks in CI and document GitHub Pages setup.

## 0.1.0

- Add a shared D2Q9-BGK solver with Guo forcing and horizontal wall boundaries.
- Add Poiseuille, Couette and periodic shear-wave cases with analytical references.
- Add a diffusive-scaling shear-wave refinement study.
- Add CSV/NPZ output, numerical reports, comparison figures and English/Chinese documentation.
