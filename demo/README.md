# Interactive experiments

Open `index.html` in a current desktop browser. The page uses local scripts and a Blob Web Worker; it needs no Python installation, API key or external libraries. If local file execution is restricted by your browser, serve the repository with `python -m http.server 8000 --bind 127.0.0.1` and open `http://localhost:8000/demo/`. Browser interaction was checked over local HTTP; direct file execution was not verified in the test environment.

Choose a flow, set the number of y-nodes, relaxation time and speed, then run. Parameters stay fixed during a run. Stop cancels the worker; a cancelled run cannot be downloaded as a completed benchmark. JSON downloads contain parameters, profiles, sampled history and acceptance checks.

The browser uses a separate JavaScript implementation of the same D2Q9 equations and boundaries. Tests compare its velocity fields with the Python solver at the same step. It is not a Python or WebAssembly wrapper. Node.js is used only to test this implementation; visitors do not need Node.js.

## Run limits

- The first three cases use nx=8. Taylor-Green uses a square N × N grid. Available sizes are 16, 24, 32 and 48.
- Relaxation time ranges from 0.6 to 1.2, and speed from 0.005 to 0.04.
- Wall cases stop at a normalized velocity change below 1e-8 over 100 steps, or at 80000 steps. The latter may be insufficient on a fine grid at low viscosity; incomplete runs are reported separately.
- Shear-wave duration is `round(400*N²/32²)`, so viscous time is fixed when varying N at fixed tau. Speed is not automatically rescaled when N changes; match Reynolds number yourself or use the Python refinement command.
- During a wall run, the plotted analytical curve is the steady solution. Startup flow is expected to differ from it.
- The viscosity fit uses sampled amplitudes from step 20 onward. Final-profile error includes startup effects.
- The same mass, Mach, velocity-error and viscosity tolerances as the Python benchmarks are used. Small grids can miss these criteria.

## GitHub Pages

After pushing the files, a repository administrator can enable Pages under **Settings → Pages → Build and deployment → Deploy from a branch**, selecting **main** and **/(root)**. The root `index.html` redirects to this directory. Wait for GitHub's Pages deployment to complete, then use the URL shown in Settings. A repository push alone does not confirm that Pages is enabled or deployed.

## Tests

```sh
node tests/browser-check.cjs
python -m unittest discover -s tests -v
```

The cross-language Python tests require Node.js. They are skipped locally if Node is unavailable; CI installs Node explicitly. The parity check covers 100 steps of each flow, including both velocity components of Taylor-Green. It does not substitute for the analytical benchmark checks.

## Taylor-Green and guided activities

Taylor-Green duration is `round(200*N²/32²)`. Its initial density follows the analytical pressure. Acceptance uses the full 2D velocity error (<1%), kinetic-energy error (<2%), fitted viscosity (<1%), mass and Mach checks. The displayed profile is only the x=0.5 slice. Colors use a fixed initial-amplitude scale; arrows rescale per frame. JSON includes final 2D fields flattened in row-major [y,x] order. Four activity cards load starting configurations and offer prediction prompts with expandable expected behavior. See [the experiment guide](../docs/EXPERIMENTS.md).

## Live Rayleigh–Taylor

Choose Rayleigh–Taylor in the same selector, then Run experiment. It computes a conservative Cahn–Hilliard phase field coupled to Boussinesq D2Q9 flow, entirely in the browser worker. The default is 64 × 128, tau=0.65, A=0.05 and 10000 steps. The RT controls replace benchmark speed/tau controls with step count and gravity. Results show phase-mean drift, fluid mass drift, maximum Mach and the live phase field, without analytical error or a benchmark pass badge.

The 5000-step Python animation farther down the page remains a reference, separate from the live calculation. Stop and completed-run JSON download work through the shared controls. See [model and limits](../examples/RAYLEIGH_TAYLOR.md), including the consequences of walls and changing the wavelength.
