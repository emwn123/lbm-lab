# Guided experiments

Each activity starts with a prediction, changes one control, and ends with a quantitative check. Browser cards load a configuration but do not start a run automatically. Save a separate JSON or Python output for each experiment.

## 1. Move the wall

**Predict:** What happens to the Couette profile when wall speed doubles?

Use N=32, tau=0.8 and speeds 0.02 and 0.04. Wait for convergence in both runs. Compare both absolute velocity and u/U.

**Expected:** Velocity and slope double; the normalized profile remains y/H. This straight-wall result is not a general high-speed accuracy guarantee.

## 2. Resolve the walls

**Predict:** Do overlapping curves always mean negligible numerical error?

Compare Poiseuille at N=16 and N=32 with tau=0.8 and speed=0.02. Inspect the L2 errors. The browser keeps speed fixed, so Reynolds number changes. For a matched-Re study, use:

```sh
python -m lbm_lab.channel_study --output channel-study-run
```

**Expected:** Under the study conditions, steady profile error decreases approximately quadratically. Do not adjust the reference profile to hide the offset.

## 3. Change viscosity

**Predict:** Which shear wave decays faster at tau=0.8 versus tau=1.1?

Keep N=32 and amplitude=0.02. Compare amplitudes at the same time and fitted viscosity against input viscosity.

**Expected:** Viscosity doubles from 0.1 to 0.2. Since amplitude is A exp(-nu k² t), its continuum decay rate doubles. Coarse-grid numerical estimates need not be exact.

## 4. Follow the vortices

**Predict:** If vortex velocity amplitude halves, how much kinetic energy remains?

```sh
lbm-lab taylor-green --output vortex-run
```

Use N=32, tau=0.8 and amplitude=0.02. Inspect the map: both velocity components vary in x and y. The profile at x=0.5 is only a slice; the error uses the full vector field.

**Expected:** Velocity amplitude decays as exp(-2 nu k² t), kinetic energy as exp(-4 nu k² t). Half the amplitude gives one quarter of the energy in the continuum solution. Numerical energy is density weighted; its reference uses unit density.

Try the 16-node browser grid. Its shorter duration preserves nu*t/N² at fixed tau. Amplitude is not automatically rescaled, so this does not keep Reynolds number fixed.

## 中文实验单

1. **Couette：**预测上壁速度加倍后的变化，再运行 0.02 与 0.04；比较 u/U，而不只看绝对速度。
2. **Poiseuille：**比较 16 与 32 节点的误差。网页固定速度时 Reynolds 数改变，严格对照使用通道流研究命令。
3. **剪切波：**比较 tau=0.8 与 1.1。黏度加倍时，解析振幅衰减率加倍。
4. **Taylor-Green：**查看二维速度场和动能。速度振幅减半时，解析动能降为四分之一；剖面只是切片，误差须检查全场。

记录预测、参数、观察和误差。若结果与预期不同，保留原始输出，再检查时间、单位、边界和分辨率。
