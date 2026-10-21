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
function text(){return words[language];}
function translate(){
  document.documentElement.lang=language==="en"?"en":"zh-CN";
  document.querySelectorAll("[data-en]").forEach(el=>{el.textContent=el.dataset[language];});
  $("language").textContent=language==="en"?"中文":"English";
  const info=cases[$("case").value][language];
  $("description").textContent=info[0]; $("speed-label").textContent=info[1]; $("lesson").textContent=info[2];
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
  $("wave-section").hidden=c.case!=="shear-wave";
  $("explanation").textContent=c.case==="shear-wave"?t.wave:t.steady;
  if(result && c.case!=="shear-wave" && !result.converged) $("explanation").textContent=t.unfinished;
  if(result && c.case!=="shear-wave" && result.converged) $("explanation").textContent=t.settled;
  if(c.case==="shear-wave" && result){
    const points=result.history, times=points.map(p=>p.step), amps=points.map(p=>Math.log10(Math.max(p.amplitude,1e-300)));
    const exact=times.map(time=>Math.log10(c.speed)-sample.nu*(2*Math.PI/c.ny)**2*time/Math.LN10);
    chart($("decay"),times,[...amps,...exact],"Time step","log₁₀ amplitude",[
      {points:times.map((v,i)=>[v,exact[i]])},{dots:true,points:times.map((v,i)=>[v,amps[i]])}],260);
    $("explanation").textContent+=` ${t.viscosity}: ${result.fittedNu.toFixed(6)} (input ${sample.nu.toFixed(6)}).`;
  }
  $("checks").replaceChildren();
  if(result){
    const names={profile:t.profile,mass:t.mass,lowMach:t.lowMach,steady:t.steadyCheck,viscosity:t.viscosityCheck};
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
