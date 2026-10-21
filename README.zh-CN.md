# LBM Flow Lab：基础流动教学与验证

用同一个 D2Q9-BGK 求解器运行四个基础算例，并与解析解比较。源码包含碰撞、迁移、Guo 力项，以及固定壁面和运动壁面的半格点反弹边界。

| 算例 | 现象 | 验证内容 |
|---|---|---|
| Poiseuille 通道流 | 两固定平板间的体力驱动流动 | 抛物线速度分布、力项、壁面位置 |
| Couette 剪切流 | 上壁运动、下壁静止 | 线性速度分布、运动壁面边界 |
| 剪切波衰减 | 周期域内正弦速度波逐渐衰减 | 黏性衰减率及松弛时间—黏度关系 |
| Taylor-Green 涡 | 正方形周期域内二维涡旋衰减 | 两个速度分量、两个空间方向及动能衰减 |

## 安装与运行

无需安装 Python 的交互入口：下载仓库后打开 `demo/index.html`。可调整网格、松弛时间与速度，运行四个算例、查看误差并下载 JSON。网页全部在本机计算；浏览器实现与 Python 求解器做交叉测试。[交互说明及 GitHub Pages 设置](demo/README.md)

需要 Python 3.11 或以上版本。在项目目录运行：

```powershell
py -m pip install -e .
lbm-lab all --output runs
```

单独运行：

```powershell
lbm-lab poiseuille --output channel-run
lbm-lab couette --output moving-wall-run
lbm-lab shear-wave --output wave-run
lbm-lab taylor-green --output vortex-run
```

每次使用新的输出目录。各案例保存解析解对照图、速度剖面 CSV、历史诊断 CSV、最终场 NPZ、配置与通过/失败报告。所有指定案例达到要求时，命令返回 0；有案例未通过则返回 1。

## 先看哪些结果

1. `comparison.png`：数值剖面是否与解析解一致；同时看右侧误差图，避免仅凭曲线重合判断。
2. `report.json`：检查相对 L2 误差、质量漂移、Mach 数，以及是否真正达到稳态。
3. 剪切波报告中的 `nu_fitted`：由振幅的指数衰减反算黏度，与输入黏度比较。

前三个算例的默认流体节点数为 nx=8、ny=32；Taylor-Green 使用 32×32 正方形网格，tau=0.8，对应格子黏度 0.1。所有量均为格子单位，dx=dt=1，参考密度为 1。壁面位于流体节点之外半格点处，通道宽度 H=ny；节点坐标为 y=j+0.5。

壁面算例从静止状态开始，每 100 步比较速度变化；变化量除以指定速度低于 1e-8 才判为稳态。达到最大步数仍不满足要求，会报告失败。剪切波按最终时刻的解析解比较，并从第 20 步以后拟合振幅衰减。

## 网格加密

```powershell
py -m lbm_lab.refinement --output refinement-run
```

剪切波使用 16、32、64 个节点；速度按 1/N 缩放，步数按 N² 缩放，保持 Reynolds 数和无量纲黏性时间一致。本次结果中误差约按二阶下降；16 节点的粗网格未达到 1% 误差要求，报告保留了这个结果。

参数表、公式与数值限制见 [英文说明](README.md) 和 [方法文档](docs/method.md)。已运行的结果见 [案例报告](examples/RESULTS.md)。这四个算例用于基础流动验证，不包含多相、热传递或复杂几何流动。

## 测试

新增 Poiseuille 网格与松弛时间对比：

```powershell
py -m lbm_lab.channel_study --output channel-study-run
```

九组算例固定 Reynolds 数，达到稳态后比较速度误差。参数与结果见 [收敛报告](examples/CHANNEL_STUDY.md)。

```powershell
py -m unittest discover -s tests -v
```

许可证为 MIT。

实验卡采用“先预测、再运行、后比较”的形式，可一键加载配置；完整实验单见 [EXPERIMENTS.md](docs/EXPERIMENTS.md)，二维涡旋的公式与结果见 [TAYLOR_GREEN.md](examples/TAYLOR_GREEN.md)。
