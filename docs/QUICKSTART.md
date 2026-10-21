# A two-minute tour

This is a short first experiment, not a prerequisite for using the Python solver. Run time depends on your device.

## 1. Open the lab

[Launch the browser experiments](https://emwn123.github.io/lbm-lab/demo/). No installation, login or API key is needed. Computation stays in your browser.

## 2. Start with a moving wall

Under **Try a guided experiment**, find **01 · Move the wall** and click **Set up this experiment**. This selects Couette flow at N=32, tau=0.8 and wall speed 0.02. Click **Run experiment**.

The upper plate moves and the lower plate is stationary. As the flow settles, the velocity approaches a straight line between the walls. Wait for **Checks passed** or **Checks not met**; an intermediate profile is not a steady result.

## 3. Read one result

Look at **Velocity error**, then the individual checks below the plot. The solid line is the analytical reference; dots are the computed LBM velocities. Small visual separation is not enough to establish accuracy, so the lab also reports a numerical error.

Change the wall speed to 0.04 and run again. Predict the change first. In this case the steady velocity doubles while the normalized shape remains linear. Use **Download results (JSON)** if you want to keep either run.

## 4. Try a vortex, or tell us what got in the way

The fourth activity loads **Taylor–Green** on a square grid. The arrows show circulation; the energy chart checks its viscous decay. Its error uses the full 2D velocity field, not just the displayed slice.

If something failed or was confusing, [share what happened](https://github.com/emwn123/lbm-lab/issues/new?template=trial-feedback.yml). A short report of an actual attempt is useful, including an attempt that did not work. Posting an issue requires a GitHub account; using the experiments does not. Do not include private data or credentials.

For equations and more activities, see the [experiment guide](EXPERIMENTS.md). For Python installation, see the [main README](../README.md#install-and-run).

## 中文入门

1. 打开 [在线实验室](https://emwn123.github.io/lbm-lab/demo/)，点击右上角 **中文**。无需安装、登录或 API Key。
2. 在“动手试一试”中找到第一张“移动壁面”卡，点击 **设置此实验**，再点击 **运行实验**。它会使用 Couette 流的默认配置。
3. 等待计算结束。上壁运动、下壁静止，稳态速度剖面应为直线。看数值误差和检查项，不要只凭两条曲线看起来重合就判断准确。
4. 将壁面速度从 0.02 改为 0.04，再运行一次。先预测变化：稳态速度会加倍，归一化后的剖面形状仍相同。可下载 JSON 保存结果。
5. 第四张卡可切换到二维涡旋，观察箭头和动能衰减。全场误差使用两个速度分量，切片只是辅助显示。

如果某一步不能运行或说明不清楚，可以 [记录实际试用情况](https://github.com/emwn123/lbm-lab/issues/new?template=trial-feedback.yml)。不需要写好评；失败和不理解的地方同样有用。提交 issue 需要 GitHub 账号，运行实验不需要。不要上传私有数据或账号凭据。
