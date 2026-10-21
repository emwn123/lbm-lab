"use strict";
const $ = id => document.getElementById(id);
let language="en", worker=null, result=null, lastSample=null, activeConfig=null, phase="ready";
const words={en:{ready:"Ready to run",running:"Running",stopped:"Stopped · results incomplete",pass:"Checks passed",fail:"Checks not met",steady:"Steady reference; wait for convergence before comparing the final error.",wave:"The analytical wave decays at the same time shown above. Its duration scales with grid height squared.",viscosity:"Fitted viscosity",unfinished:"Time limit reached before convergence. Try a smaller grid or a larger relaxation time.",
  settled:"The velocity has converged. The curve shows the steady analytical solution at the fluid-node coordinates.",errors:"Numerical error",profile:"Profile",mass:"Mass",lowMach:"Low Mach",steadyCheck:"Steady",viscosityCheck:"Viscosity"},
zh:{ready:"准备就绪",running:"计算中",stopped:"已停止 · 结果不完整",pass:"检查通过",fail:"未达到检查要求",steady:"解析曲线为稳态参考；请在收敛后比较最终误差。",wave:"解析波与当前计算时刻一致；计算步数随节点数的平方缩放。",viscosity:"拟合黏度",unfinished:"达到计算上限，尚未收敛。可减小网格或增大松弛时间。",settled:"速度已收敛。参考曲线取自流体节点坐标上的稳态解析解。",errors:"计算出错",profile:"剖面",mass:"质量",lowMach:"低 Mach 数",steadyCheck:"稳态",viscosityCheck:"黏度"}};
const cases={
  poiseuille:{en:["A constant body force drives flow between two stationary walls.","Reference peak speed","Look for a parabolic profile. Increasing the grid resolution should reduce the halfway-wall error. The force is adjusted with viscosity and channel height to keep the requested continuum peak speed."],zh:["恒定体力驱动两静止平板之间的流动。","参考峰值速度","速度剖面应为抛物线。加密网格后，半格点反弹壁面的误差应减小。体力会随黏度和通道宽度调整，使解析峰值速度保持为指定值。"]},
  couette:{en:["The top wall moves; the bottom wall stays still.","Top-wall speed","The steady profile should be linear. The walls lie half a lattice spacing beyond the first and last fluid nodes, so the channel height is N, not N − 1."],zh:["上壁运动，下壁静止。","上壁速度","稳态速度剖面应为直线。壁面在首末流体节点之外半格点处，因此通道宽度为 N，而不是 N−1。"]},
  "shear-wave":{en:["A sinusoidal velocity decays in a fully periodic domain.","Initial wave amplitude","Viscosity controls the exponential decay rate. Compare the fitted viscosity with (tau − 0.5)/3. A coarse grid can conserve mass and still miss the profile-error criterion."],zh:["正弦速度波在全周期区域内逐渐衰减。","初始波振幅","黏度决定指数衰减率。可将拟合黏度与 (tau−0.5)/3 比较。粗网格即使质量守恒，也可能未达到剖面误差要求。"]}}
;
Object.assign(words.en,{vortex:"The error uses both velocity components over the full 2D grid. The profile is a slice at x = 0.5; energy is density-weighted.",energy:"Energy",velocityField:"2D velocity",energyTitle:"Kinetic energy decay"});
Object.assign(words.zh,{vortex:"误差使用整个二维网格上的两个速度分量。剖面取 x=0.5 的切片；动能按密度加权。",energy:"动能",velocityField:"二维速度",energyTitle:"动能衰减"});
cases["taylor-green"]={en:["A square periodic domain contains four decaying vortices.","Initial velocity amplitude","Both velocity components vary in x and y. Compare the full velocity field and kinetic energy with the continuum reference. Pressure-consistent density reduces acoustic startup, but this remains a weakly compressible approximation."],zh:["正方形周期域内的四个涡旋逐渐衰减。","初始速度振幅","两个速度分量均随 x 和 y 变化。比较整个速度场和动能，而不只看剖面。初始密度与解析压力相匹配，但模型仍是弱可压缩近似。"]};
const activities=[
  {case:"couette",en:["01 · Move the wall","Run at speed 0.02, then 0.04. What changes in the steady profile?","The slope and velocity double; the profile stays linear."],zh:["01 · 移动壁面","分别使用速度 0.02 与 0.04。稳态速度剖面如何变化？","斜率与速度加倍，剖面仍为直线。"]},
  {case:"poiseuille",en:["02 · Resolve the walls","Compare N=16 and N=32. Check the error, not just the curve overlap.","For this straight channel, profile error is expected to decrease approximately as N⁻². Use the Python study to match Reynolds number."],zh:["02 · 加密壁面附近的网格","比较 N=16 与 N=32。除了曲线重合，还要查看误差。","该直通道的剖面误差预期约按 N⁻² 下降。严格匹配 Reynolds 数的对比可运行 Python 研究。"]},
  {case:"shear-wave",en:["03 · Change viscosity","At N=32, compare tau=0.8 and tau=1.1. Which wave decays faster?","The viscosity doubles from 0.1 to 0.2, so the continuum amplitude decay rate doubles."],zh:["03 · 改变黏度","N=32 时比较 tau=0.8 与 tau=1.1。哪个波衰减更快？","黏度从 0.1 加倍到 0.2，连续方程的振幅衰减率也加倍。"]},
  {case:"taylor-green",en:["04 · Follow the vortices","Inspect the velocity arrows and energy history. If velocity amplitude halves, what happens to kinetic energy?","Kinetic energy is quadratic in velocity, so it becomes one quarter. For this continuum solution, E(t) decays as exp(-4 nu k² t)."],zh:["04 · 跟踪涡旋","查看速度箭头与动能历史。速度振幅减半时，动能会怎样？","动能与速度平方成正比，因此降为四分之一。该解析解的动能按 exp(-4 nu k² t) 衰减。"]}
];
function renderActivities(){
  $("activity-cards").replaceChildren();
  for(const activity of activities){
    const content=activity[language], card=document.createElement("article");
    const heading=document.createElement("h3");heading.textContent=content[0];
    const task=document.createElement("p");task.textContent=content[1];
    const button=document.createElement("button");button.className="quiet";button.dataset.preset=activity.case;button.disabled=!!worker;
    button.textContent=language==="en"?"Set up this experiment":"设置此实验";
    button.addEventListener("click",()=>{if(worker)return;$("case").value=activity.case;$("ny").value="32";$("tau").value="0.8";$("speed").value="0.02";$("case").dispatchEvent(new Event("input"));$("run").focus();});
    const details=document.createElement("details"),summary=document.createElement("summary"),answer=document.createElement("p");
    summary.textContent=language==="en"?"Expected behavior":"预期结果";answer.textContent=content[2];details.append(summary,answer);
    card.append(heading,task,button,details);$("activity-cards").append(card);
  }
}
function text(){return words[language];}
function translate(){
  document.documentElement.lang=language==="en"?"en":"zh-CN";
  document.querySelectorAll("[data-en]").forEach(el=>{el.textContent=el.dataset[language];});
  $("language").textContent=language==="en"?"中文":"English";
  const info=cases[$("case").value][language];
  $("description").textContent=info[0]; $("speed-label").textContent=info[1]; $("lesson").textContent=info[2];
  const vortex=$("case").value==="taylor-green";
  $("geometry").textContent=vortex?(language==="en"?"Square N × N grid · periodic x and y · lattice units":"N×N 正方形网格 · x、y 周期边界 · 格子单位"):(language==="en"?"8 nodes along x · lattice units":"x 方向 8 个节点 · 格子单位");
  $("profile-title").textContent=vortex?(language==="en"?"Velocity slice at x = 0.5":"x=0.5 的速度切片"):(language==="en"?"Velocity profile":"速度剖面");
  $("decay-title").textContent=vortex?text().energyTitle:(language==="en"?"Amplitude decay":"振幅衰减");
  renderActivities();
  if(lastSample) render(lastSample); else {$("status").textContent=text().ready; drawEmpty();}
}
function config(){return {case:$("case").value,ny:Number($("ny").value),tau:Number($("tau").value),speed:Number($("speed").value)};}
function updateValues(){
  $("tau-value").textContent=Number($("tau").value).toFixed(2);
  $("nu-value").textContent=((Number($("tau").value)-.5)/3).toFixed(4);
  $("speed-value").textContent=Number($("speed").value).toFixed(3);
}
function setBusy(busy){
  ["case","ny","tau","speed","run"].forEach(id=>$(id).disabled=busy);
  $("stop").disabled=!busy; $("download").disabled=busy || !result;
  document.querySelectorAll("[data-preset]").forEach(el=>el.disabled=busy);
}
function chart(svg, xValues, yValues, xLabel, yLabel, series, height=330){
  const left=67, right=22, top=24, bottom=48, width=700;
  let xmin=Math.min(...xValues),xmax=Math.max(...xValues),ymin=Math.min(...yValues),ymax=Math.max(...yValues);
  if(xmin===xmax){xmin-=1;xmax+=1;} if(ymin===ymax){ymin-=1;ymax+=1;}
  const nonnegative=xmin>=0, pad=(xmax-xmin)*.07; xmin-=pad;xmax+=pad;
  if(nonnegative) xmin=Math.max(0,xmin);
  const xp=x=>left+(x-xmin)/(xmax-xmin)*(width-left-right);
  const yp=y=>height-bottom-(y-ymin)/(ymax-ymin)*(height-top-bottom);
  let markup="";
  const fmt=v=>Math.abs(v)>=1000?v.toExponential(1):Math.abs(v)<.001&&v!==0?v.toExponential(1):Number(v.toPrecision(3)).toString();
  for(let i=0;i<=4;i++){
    const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;
    markup+=`<line x1="${left}" y1="${yp(y)}" x2="${width-right}" y2="${yp(y)}" stroke="#e7eeeb"/><text x="${left-10}" y="${yp(y)+4}" text-anchor="end">${fmt(y)}</text><text x="${xp(x)}" y="${height-bottom+22}" text-anchor="middle">${fmt(x)}</text>`;
  }
  markup+=`<line x1="${left}" y1="${top}" x2="${left}" y2="${height-bottom}" stroke="#adbeba"/><line x1="${left}" y1="${height-bottom}" x2="${width-right}" y2="${height-bottom}" stroke="#adbeba"/>`;
  for(const s of series){
    if(s.dots) markup+=s.points.map(([x,y])=>`<circle cx="${xp(x)}" cy="${yp(y)}" r="3" fill="#c45f32"/>`).join("");
    else markup+=`<polyline points="${s.points.map(([x,y])=>`${xp(x)},${yp(y)}`).join(" ")}" fill="none" stroke="#176b69" stroke-width="2"/>`;
  }
  markup+=`<text x="${(left+width-right)/2}" y="${height-6}" text-anchor="middle">${xLabel}</text><text transform="translate(15 ${(top+height-bottom)/2}) rotate(-90)" text-anchor="middle">${yLabel}</text>`;
  svg.innerHTML=markup;
}
function drawEmpty(){
  chart($("profile"),[-.01,.02],[0,1],"uₓ · lattice units","y / H",[]);
  $("explanation").textContent=language==="en"?"Choose a case and run the experiment.":"选择算例后点击运行。";
  $("wave-section").hidden=true;
  $("field-section").hidden=true;
}
function drawField(sample){
  const canvas=$("field"),ctx=canvas.getContext("2d"),n=activeConfig.ny;
  const left=130,top=18,side=350,cell=side/n,max=activeConfig.speed;
  ctx.clearRect(0,0,700,420);
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){
    const p=y*n+x,v=Math.min(1,Math.hypot(sample.ux[p],sample.uy[p])/max);
    ctx.fillStyle=`rgb(${Math.round(25+205*v)},${Math.round(50+155*v)},${Math.round(85-35*v)})`;
    ctx.fillRect(left+x*cell,top+(n-1-y)*cell,cell+.5,cell+.5);
  }
  const scale=sample.ux.reduce((m,u,p)=>Math.max(m,Math.hypot(u,sample.uy[p])),1e-30);
  const stride=Math.max(1,Math.floor(n/8));ctx.strokeStyle="white";ctx.lineWidth=1.1;
  for(let y=Math.floor(stride/2);y<n;y+=stride)for(let x=Math.floor(stride/2);x<n;x+=stride){
    const p=y*n+x,px=left+(x+.5)*cell,py=top+(n-y-.5)*cell;
    const dx=sample.ux[p]/scale*15,dy=-sample.uy[p]/scale*15,angle=Math.atan2(dy,dx);
    ctx.beginPath();ctx.moveTo(px-dx/2,py-dy/2);ctx.lineTo(px+dx/2,py+dy/2);
    ctx.lineTo(px+dx/2-4*Math.cos(angle-.5),py+dy/2-4*Math.sin(angle-.5));ctx.moveTo(px+dx/2,py+dy/2);ctx.lineTo(px+dx/2-4*Math.cos(angle+.5),py+dy/2-4*Math.sin(angle+.5));ctx.stroke();
  }
  ctx.fillStyle="#536a72";ctx.font="12px system-ui";ctx.fillText("x / N",left+side/2-10,top+side+25);ctx.fillText("y / N",left-46,top+side/2);ctx.fillText("0",left-12,top+side+3);ctx.fillText("1",left-12,top+7);
  ctx.fillText(language==="en"?"Color: speed / initial amplitude (0 → 1); arrows rescaled each frame":"颜色：速度/初始振幅（0→1）；箭头逐帧缩放",80,410);
}
function render(sample){
  const c=activeConfig,t=text();
  $("step").textContent=`t = ${sample.step.toLocaleString()}`;
  $("error").textContent=(100*sample.error).toFixed(3)+"%";
  $("mass").textContent=sample.maxMassDrift.toExponential(1);
  $("mach").textContent=sample.maxMach.toFixed(4);
  $("status").textContent=phase==="running"?t.running:phase==="stopped"?t.stopped:result?(result.passed?t.pass:t.fail):t.ready;
  const y=sample.profile.map((_,i)=>(i+.5)/c.ny);
  chart($("profile"),[...sample.profile,...sample.reference],[0,1],"uₓ · lattice units","y / H",[
    {points:sample.reference.map((v,i)=>[v,y[i]])},{dots:true,points:sample.profile.map((v,i)=>[v,y[i]])}]);
  const vortex=c.case==="taylor-green",unsteady=vortex||c.case==="shear-wave";
  $("field-section").hidden=!vortex;if(vortex)drawField(sample);
  $("wave-section").hidden=!unsteady;
  $("explanation").textContent=c.case==="shear-wave"?t.wave:t.steady;
  if(result && !unsteady && !result.converged) $("explanation").textContent=t.unfinished;
  if(result && !unsteady && result.converged) $("explanation").textContent=t.settled;
  if(vortex)$("explanation").textContent=t.vortex;
  if(unsteady && result){
    const points=result.history, times=points.map(p=>p.step), amps=points.map(p=>Math.log10(Math.max(vortex?p.energy:p.amplitude,1e-300)));
    const exact=vortex?points.map(p=>Math.log10(p.referenceEnergy)):times.map(time=>Math.log10(c.speed)-sample.nu*(2*Math.PI/c.ny)**2*time/Math.LN10);
    chart($("decay"),times,[...amps,...exact],"Time step",vortex?"log₁₀ kinetic energy":"log₁₀ amplitude",[
      {points:times.map((v,i)=>[v,exact[i]])},{dots:true,points:times.map((v,i)=>[v,amps[i]])}],260);
    $("explanation").textContent+=` ${t.viscosity}: ${result.fittedNu.toFixed(6)} (input ${sample.nu.toFixed(6)}).`;
  }
  $("checks").replaceChildren();
  if(result){
    const names={profile:vortex?t.velocityField:t.profile,mass:t.mass,lowMach:t.lowMach,steady:t.steadyCheck,viscosity:t.viscosityCheck,energy:t.energy};
    for(const [key,passed] of Object.entries(result.criteria)){
      const item=document.createElement("span");item.className="check"+(passed?"":" fail");
      item.textContent=(passed?"✓ ":"× ")+names[key];$("checks").append(item);
    }
  }
}
$("run").addEventListener("click",()=>{
  result=null;lastSample=null;activeConfig=config();phase="running";setBusy(true);$("checks").replaceChildren();
  const code=`const runBenchmark=${LBMDemo.runBenchmark.toString()};self.onmessage=({data})=>{try{const result=runBenchmark(data,sample=>self.postMessage({type:'progress',sample}));self.postMessage({type:'done',result});}catch(error){self.postMessage({type:'error',message:error.message});}};`;
  const url=URL.createObjectURL(new Blob([code],{type:"application/javascript"}));
  worker=new Worker(url);URL.revokeObjectURL(url);
  worker.onmessage=({data})=>{
    if(data.type==="progress"){lastSample=data.sample;render(lastSample);}
    else if(data.type==="done"){result=data.result;lastSample=result;phase="done";worker.terminate();worker=null;setBusy(false);render(lastSample);}
    else fail(data.message);
  };
  worker.onerror=event=>fail(event.message||"Worker unavailable in this browser.");
  worker.postMessage(activeConfig);
});
function fail(message){if(worker)worker.terminate();worker=null;phase="stopped";setBusy(false);$("status").textContent=text().errors+": "+message;}
$("stop").addEventListener("click",()=>{if(worker)worker.terminate();worker=null;phase="stopped";setBusy(false);if(lastSample)render(lastSample);else $("status").textContent=text().stopped;});
$("language").addEventListener("click",()=>{language=language==="en"?"zh":"en";translate();});
for(const id of ["case","ny","tau","speed"]) $(id).addEventListener("input",()=>{
  updateValues(); result=null;lastSample=null;phase="ready";setBusy(false);
  $("error").textContent=$("mass").textContent=$("mach").textContent="—";$("step").textContent="t = 0";$("checks").replaceChildren();translate();
});
$("download").addEventListener("click",()=>{
  if(!result)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
  const link=document.createElement("a");link.href=url;link.download=`lbm-${result.config.case}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
updateValues();translate();
