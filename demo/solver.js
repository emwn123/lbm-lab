/* D2Q9-BGK browser implementation. No network requests or third-party libraries. */
(function (root) {
  "use strict";
  // Self-contained so the UI can run it in a Blob worker, including from file://.
  function runBenchmark(config, progress = () => {}) {
    const {case: name, ny = 32, tau = 0.8, speed = 0.02} = config;
    const vortex = name === "taylor-green", nx = vortex ? ny : 8, size = nx * ny;
    if (!["poiseuille", "couette", "shear-wave", "taylor-green"].includes(name) ||
        !Number.isInteger(ny) || ny < 8 || ny > 64 ||
        !Number.isFinite(tau) || tau < 0.6 || tau > 1.2 ||
        !Number.isFinite(speed) || speed < 0.001 || speed > 0.05) {
      throw new Error("Unsupported case or parameters.");
    }
    const cx = [0,1,0,-1,0,1,-1,-1,1], cy = [0,0,1,0,-1,1,1,-1,-1];
    const weights = [4/9,1/9,1/9,1/9,1/9,1/36,1/36,1/36,1/36];
    const opposite = [0,3,4,1,2,7,8,5,6];
    const nu = (tau - 0.5) / 3, omega = 1 / tau;
    const walls = name === "poiseuille" || name === "couette", top = name === "couette" ? speed : 0;
    const force = name === "poiseuille" ? 8*nu*speed/(ny*ny) : 0;
    const waveSteps = config.waveSteps ?? Math.round((vortex?200:400)*ny*ny/1024);
    const maxSteps = config.maxSteps ?? 80000;
    if (!Number.isInteger(waveSteps) || waveSteps < 40 || waveSteps > 10000 ||
        !Number.isInteger(maxSteps) || maxSteps < 1 || maxSteps > 100000) {
      throw new Error("Step limits are outside the supported range.");
    }
    let f = new Float64Array(9*size), next = new Float64Array(9*size);
    const rho = new Float64Array(size), ux = new Float64Array(size), uy = new Float64Array(size);
    const basis = Array.from({length: ny}, (_, y) => Math.sin(2*Math.PI*(y+0.5)/ny));
    const initialX=new Float64Array(size),initialY=new Float64Array(size);
    let initialNorm=0;
    for (let p=0;p<size;p++) {
      const x=2*Math.PI*(p%nx+0.5)/nx,y=2*Math.PI*(Math.floor(p/nx)+0.5)/ny;
      const r=vortex?1-3*speed*speed/4*(Math.cos(2*x)+Math.cos(2*y)):1;
      const u = vortex?-speed*Math.cos(x)*Math.sin(y):(walls?0:speed*basis[Math.floor(p/nx)])-force/(2*r);
      const v = vortex?speed*Math.sin(x)*Math.cos(y):0;
      initialX[p]=u;initialY[p]=v;initialNorm+=u*u+v*v;
      for (let i=0;i<9;i++) {const dot=cx[i]*u+cy[i]*v;f[i*size+p] = weights[i]*r*(1+3*dot+4.5*dot*dot-1.5*(u*u+v*v));}
    }
    function macros() {
      let mass=0, mach=0, energy=0;
      for (let p=0;p<size;p++) {
        let r=0, mx=0, my=0;
        for (let i=0;i<9;i++) {const value=f[i*size+p]; r+=value; mx+=cx[i]*value; my+=cy[i]*value;}
        if (!(r>0) || !Number.isFinite(r)) throw new Error("Simulation became unstable. Reset and reduce speed.");
        rho[p]=r; ux[p]=(mx+force/2)/r; uy[p]=my/r;
        mass+=r; mach=Math.max(mach,Math.hypot(ux[p],uy[p])*Math.sqrt(3));
        energy+=0.5*r*(ux[p]*ux[p]+uy[p]*uy[p]);
      }
      return {mass,mach,energy};
    }
    function step() {
      // Collision and push streaming; every destination is assigned exactly once.
      for (let y=0;y<ny;y++) for (let x=0;x<nx;x++) {
        const p=y*nx+x, r=rho[p], u=ux[p], v=uy[p];
        for (let i=0;i<9;i++) {
          const dot=cx[i]*u+cy[i]*v;
          const eq=weights[i]*r*(1+3*dot+4.5*dot*dot-1.5*(u*u+v*v));
          const post=f[i*size+p]-omega*(f[i*size+p]-eq)+
            weights[i]*(1-omega/2)*force*(3*(cx[i]-u)+9*dot*cx[i]);
          const yy=y+cy[i];
          if (walls && (yy<0 || yy>=ny)) {
            next[opposite[i]*size+p]=post-6*weights[i]*r*cx[i]*(yy>=ny?top:0);
          } else {
            const dest=((yy+ny)%ny)*nx+(x+cx[i]+nx)%nx;
            next[i*size+dest]=post;
          }
        }
      }
      [f,next]=[next,f];
    }
    const first=macros(), initialMass=first.mass;
    let maxMassDrift=0, maxMach=first.mach, converged=false, residual=null;
    let previous=Float64Array.from(ux), last;
    const history=[];
    function sample(iteration) {
      const stats=macros(), profile=Array(ny).fill(0), reference=[];
      let amplitude=0, squared=0, norm=0;
      for (let y=0;y<ny;y++) {
        if(vortex) profile[y]=ux[y*nx];
        else for (let x=0;x<nx;x++) profile[y]+=ux[y*nx+x]/nx;
        const yy=y+0.5;
        reference[y]=name==="poiseuille"?force*yy*(ny-yy)/(2*nu):
          name==="couette"?speed*yy/ny:vortex?initialX[y*nx]*Math.exp(-2*nu*(2*Math.PI/ny)**2*iteration):speed*basis[y]*Math.exp(-nu*(2*Math.PI/ny)**2*iteration);
        amplitude+=2*profile[y]*basis[y]/ny;
        squared+=(profile[y]-reference[y])**2; norm+=reference[y]**2;
      }
      if(vortex){
        amplitude=0;squared=0;norm=0;
        const decay=Math.exp(-2*nu*(2*Math.PI/ny)**2*iteration);
        for(let p=0;p<size;p++){
          const rx=initialX[p]*decay,ry=initialY[p]*decay;
          squared+=(ux[p]-rx)**2+(uy[p]-ry)**2;norm+=rx*rx+ry*ry;
          amplitude+=speed*(ux[p]*initialX[p]+uy[p]*initialY[p])/initialNorm;
        }
      }
      const massDrift=Math.abs(stats.mass/initialMass-1);
      maxMassDrift=Math.max(maxMassDrift,massDrift); maxMach=Math.max(maxMach,stats.mach);
      const referenceEnergy=vortex?size*speed*speed/4*Math.exp(-4*nu*(2*Math.PI/ny)**2*iteration):null;
      const point={step:iteration, amplitude, massDrift, mach:stats.mach,energy:stats.energy,referenceEnergy};
      history.push(point);
      last={...point, profile, reference, error:Math.sqrt(squared/norm), residual,
        converged, nu, maxMassDrift, maxMach};
      if(vortex){last.ux=Array.from(ux);last.uy=Array.from(uy);last.rho=Array.from(rho);}
      progress(last);
    }
    sample(0);
    const limit=walls?maxSteps:waveSteps, interval=walls?100:10;
    let iteration=0;
    for (iteration=1;iteration<=limit;iteration++) {
      step(); macros();
      if (iteration%interval===0 || iteration===limit) {
        residual=0;
        for (let p=0;p<size;p++) residual=Math.max(residual,Math.abs(ux[p]-previous[p])/speed);
        previous.set(ux);
        converged=walls && residual<1e-8;
        sample(iteration);
        if (converged) break;
      }
    }
    let fittedNu=null;
    if (!walls) {
      const points=history.filter(p=>p.step>=20 && p.amplitude>0);
      if (points.length<3) throw new Error("Not enough wave samples to fit viscosity.");
      const meanT=points.reduce((s,p)=>s+p.step,0)/points.length;
      const meanLog=points.reduce((s,p)=>s+Math.log(p.amplitude),0)/points.length;
      let cov=0, variance=0;
      for (const p of points) {cov+=(p.step-meanT)*(Math.log(p.amplitude)-meanLog); variance+=(p.step-meanT)**2;}
      fittedNu=-cov/variance/((vortex?2:1)*(2*Math.PI/ny)**2);
    }
    const criteria={profile:last.error<(name==="couette"?1e-5:0.01),
      mass:maxMassDrift<1e-10, lowMach:maxMach<0.1};
    if (walls) criteria.steady=converged;
    else criteria.viscosity=Math.abs(fittedNu/nu-1)<0.01;
    if(vortex) criteria.energy=Math.abs(last.energy/last.referenceEnergy-1)<0.02;
    return {...last, config:{case:name,ny,nx,tau,speed,waveSteps,maxSteps},history,fittedNu,
      criteria,passed:Object.values(criteria).every(Boolean)};
  }
  const api={runBenchmark};
  if (typeof module!=="undefined" && module.exports) module.exports=api;
  else root.LBMDemo=api;
})(globalThis);
