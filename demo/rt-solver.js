/* Conservative CH / Boussinesq D2Q9 experiment. Lattice units throughout. */
(function(root){
  "use strict";
  function runRayleighTaylor(config, progress=()=>{}){
    const nx=config.nx??64,ny=2*nx,tau=config.tau??0.65,steps=config.steps??10000;
    const atwood=config.atwood??0.05,gravity=config.gravity??0.0004,amplitude=config.amplitude??2;
    if(!Number.isInteger(nx)||nx<16||nx>64||!Number.isInteger(steps)||steps<1||steps>30000||
       !Number.isFinite(tau)||tau<0.6||tau>1.2||!Number.isFinite(atwood)||atwood<=0||atwood>0.1||
       !Number.isFinite(gravity)||gravity<0||gravity>0.001||!Number.isFinite(amplitude)||amplitude<0||amplitude>=ny/8)
      throw new Error("Unsupported RT parameters.");
    const size=nx*ny,beta=.001,kappa=.002,mobility=2,omega=1/tau;
    const cx=[0,1,0,-1,0,1,-1,-1,1],cy=[0,0,1,0,-1,1,1,-1,-1];
    const w=[4/9,1/9,1/9,1/9,1/9,1/36,1/36,1/36,1/36],opp=[0,3,4,1,2,7,8,5,6];
    const east=new Int32Array(size),west=new Int32Array(size),north=new Int32Array(size),south=new Int32Array(size);
    for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
      const p=y*nx+x;east[p]=y*nx+(x+1)%nx;west[p]=y*nx+(x+nx-1)%nx;
      north[p]=Math.min(y+1,ny-1)*nx+x;south[p]=Math.max(y-1,0)*nx+x;
    }
    let phi=new Float64Array(size),f=new Float64Array(9*size),next=new Float64Array(9*size);
    const rho=new Float64Array(size),ux=new Float64Array(size),uy=new Float64Array(size),fx=new Float64Array(size),fy=new Float64Array(size);
    const mu=new Float64Array(size),sx=new Float64Array(size),sy=new Float64Array(size),fluxX=new Float64Array(size),fluxY=new Float64Array(size);
    const first=new Float64Array(size),rhs=new Float64Array(size),updated=new Float64Array(size);
    function chemical(a){for(let p=0;p<size;p++)mu[p]=beta*(a[p]**3-a[p])-kappa*(a[east[p]]+a[west[p]]+a[north[p]]+a[south[p]]-4*a[p]);}
    function forces(){chemical(phi);for(let p=0;p<size;p++){
      fx[p]=-phi[p]*(mu[east[p]]-mu[west[p]])/2;
      fy[p]=-phi[p]*(mu[north[p]]-mu[south[p]])/2-atwood*gravity*phi[p];
    }}
    const minmod=(a,b)=>a*b>0?Math.sign(a)*Math.min(Math.abs(a),Math.abs(b)):0;
    function phaseRhs(a){
      chemical(a);
      for(let p=0;p<size;p++){sx[p]=minmod(a[p]-a[west[p]],a[east[p]]-a[p]);sy[p]=minmod(a[p]-a[south[p]],a[north[p]]-a[p]);}
      for(let p=0;p<size;p++){
        const e=east[p],n=north[p],vx=(ux[p]+ux[e])/2,vy=(uy[p]+uy[n])/2;
        fluxX[p]=vx*(vx>=0?a[p]+sx[p]/2:a[e]-sx[e]/2);
        fluxY[p]=n===p?0:vy*(vy>=0?a[p]+sy[p]/2:a[n]-sy[n]/2);
      }
      for(let p=0;p<size;p++)rhs[p]=-(fluxX[p]-fluxX[west[p]])-(fluxY[p]-(south[p]===p?0:fluxY[south[p]]))+
        mobility*(mu[east[p]]+mu[west[p]]+mu[north[p]]+mu[south[p]]-4*mu[p]);
    }
    function macros(){
      let mass=0,mach=0;
      for(let p=0;p<size;p++){
        let r=0,mx=0,my=0;
        for(let i=0;i<9;i++){const v=f[i*size+p];r+=v;mx+=cx[i]*v;my+=cy[i]*v;}
        if(!(r>0)||!Number.isFinite(r))throw new Error("RT density guard exceeded.");
        rho[p]=r;ux[p]=(mx+fx[p]/2)/r;uy[p]=(my+fy[p]/2)/r;
        mass+=r;mach=Math.max(mach,Math.hypot(ux[p],uy[p])*Math.sqrt(3));
      }
      return {mass,mach};
    }
    for(let y=0;y<ny;y++)for(let x=0;x<nx;x++)phi[y*nx+x]=Math.tanh((y+.5-ny/2-amplitude*Math.cos(2*Math.PI*(x+.5)/nx))/Math.sqrt(2*kappa/beta));
    forces();
    const meanForce=new Float64Array(ny),pressure=new Float64Array(ny);
    for(let y=0;y<ny;y++)for(let x=0;x<nx;x++)meanForce[y]+=fy[y*nx+x]/nx;
    for(let y=1;y<ny;y++)pressure[y]=pressure[y-1]+(meanForce[y]+meanForce[y-1])/2;
    const pressureMean=pressure.reduce((a,b)=>a+b,0)/ny;
    for(let p=0;p<size;p++){
      const r=1+3*(pressure[Math.floor(p/nx)]-pressureMean),u=-fx[p]/(2*r),v=-fy[p]/(2*r);
      for(let i=0;i<9;i++){const dot=cx[i]*u+cy[i]*v;f[i*size+p]=w[i]*r*(1+3*dot+4.5*dot*dot-1.5*(u*u+v*v));}
    }
    const mass0=macros().mass,phase0=phi.reduce((a,b)=>a+b,0),history=[];
    let maxMassDrift=0,maxMach=0,maxPhaseDrift=0,last;
    function sample(step){
      const stats=macros();let sum=0,lo=Infinity,hi=-Infinity;
      for(let p=0;p<size;p++){
        sum+=phi[p];const n=north[p];
        if(n!==p&&phi[p]*phi[n]<=0&&phi[p]!==phi[n]){const height=Math.floor(p/nx)+.5-phi[p]/(phi[n]-phi[p]);lo=Math.min(lo,height);hi=Math.max(hi,height);}
      }
      maxMassDrift=Math.max(maxMassDrift,Math.abs(stats.mass/mass0-1));maxMach=Math.max(maxMach,stats.mach);
      maxPhaseDrift=Math.max(maxPhaseDrift,Math.abs(sum-phase0)/size);
      const point={step,massDrift:Math.abs(stats.mass/mass0-1),mach:stats.mach,phaseMeanDrift:Math.abs(sum-phase0)/size,interfaceLow:Number.isFinite(lo)?lo:null,interfaceHigh:Number.isFinite(hi)?hi:null};
      history.push(point);last={...point,phi:Array.from(phi),maxMassDrift,maxMach,maxPhaseDrift,nx,ny};progress(last);
    }
    sample(0);
    for(let t=1;t<=steps;t++){
      macros();
      for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
        const p=y*nx+x,r=rho[p],u=ux[p],v=uy[p];
        for(let i=0;i<9;i++){
          const dot=cx[i]*u+cy[i]*v,eq=w[i]*r*(1+3*dot+4.5*dot*dot-1.5*(u*u+v*v));
          const post=f[i*size+p]-omega*(f[i*size+p]-eq)+w[i]*(1-omega/2)*(3*((cx[i]-u)*fx[p]+(cy[i]-v)*fy[p])+9*dot*(cx[i]*fx[p]+cy[i]*fy[p]));
          const yy=y+cy[i];
          if(yy<0||yy>=ny)next[opp[i]*size+p]=post;
          else next[i*size+yy*nx+(x+cx[i]+nx)%nx]=post;
        }
      }
      [f,next]=[next,f];macros();phaseRhs(phi);
      for(let p=0;p<size;p++)first[p]=phi[p]+rhs[p];
      phaseRhs(first);
      for(let p=0;p<size;p++){
        updated[p]=(phi[p]+first[p]+rhs[p])/2;
        if(!Number.isFinite(updated[p])||Math.abs(updated[p])>1.5)throw new Error(`RT phase guard exceeded at step ${t}. Reduce gravity or duration.`);
      }
      phi.set(updated);forces();
      const stats=macros();maxMach=Math.max(maxMach,stats.mach);maxMassDrift=Math.max(maxMassDrift,Math.abs(stats.mass/mass0-1));
      if(stats.mach>.15)throw new Error(`RT Mach guard exceeded at step ${t}. Reduce gravity or duration.`);
      if(t%100===0||t===steps)sample(t);
    }
    return {...last,history,config:{case:"rayleigh-taylor",nx,ny,tau,steps,atwood,gravity,amplitude,beta,kappa,mobility},
      validationStatus:"Exploratory Boussinesq experiment; no quantitative benchmark pass claimed"};
  }
  if(typeof module!=="undefined"&&module.exports)module.exports={runRayleighTaylor};else root.RTDemo={runRayleighTaylor};
})(globalThis);

