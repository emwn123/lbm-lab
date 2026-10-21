// Run with: node tests/browser-check.cjs
const assert = require("node:assert/strict");
const {runBenchmark} = require("../demo/solver.js");
for (const name of ["poiseuille", "couette", "shear-wave"]) {
  const result = runBenchmark({case:name,ny:24,tau:0.8,speed:0.02,waveSteps:100});
  assert.ok(result.passed, JSON.stringify(result.criteria));
  assert.ok(result.maxMassDrift < 1e-10);
  if (name !== "shear-wave") assert.ok(result.converged);
}
const coarse = runBenchmark({case:"shear-wave",ny:16,tau:0.8,speed:0.04,waveSteps:100});
assert.equal(coarse.criteria.profile,false);
assert.equal(coarse.passed,false);
const short = runBenchmark({case:"couette",ny:24,tau:0.8,speed:0.02,maxSteps:1});
assert.equal(short.converged,false);
assert.equal(short.passed,false);
assert.throws(()=>runBenchmark({case:"poiseuille",ny:0}), /Unsupported/);
console.log("Browser solver: three benchmarks, coarse-grid failure, incomplete run and invalid input passed.");
