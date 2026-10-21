# Changelog

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
