# Lab：动作怎样帮助你辨识自身动力学？

这个实验让你亲手完成一个可证伪的闭环：**提出预测 → 选择输入 → 收集数据 → 实现估计器 → 在新输入上检验 → 修正解释**。这里的闭环是研究工作流程；程序使用预先固定的开环输入，还没有实现根据估计结果在线挑选动作的主动学习策略。

它与 Genesis 的关系是：在你决定让机器人学习跨动力学表示之前，先检查数据是否足以区分不同动力学。这个 lab 只使用 Python 标准库的合成一维系统，不运行 Genesis、不修改现有科学代码，也不是新的科研贡献或自我意识证据。预留约 90–120 分钟；更重要的交付是你的原始预测和被证据修正的判断。

## 1. 先预测，暂时别看参考结果

复制 [预测模板](../../../developer/labs/identification/PREDICTIONS.template.md) 到你的个人学习记录，填写日期、当前分支和原始预测。学习记录属于你自己的新文件；不要改写历史研究预注册。

模型为

\[
v_{t+1}=a v_t+b u_t+w_t,\qquad z_t=v_t+e_t.
\]

`v` 是一维状态，`u` 是控制输入，`a` 是上一步状态保留系数，`b` 是输入增益。我们人为选定真实值 `a=0.75, b=0.5`；第一轮 `w=e=0`，所以观测 `z=v`。这些参数没有直接标定到某个真实机器人，也没有定义物理采样周期。

运行前回答：

1. `v0=0, u=0` 时，增加一万条数据能区分 `a` 和 `b` 吗？
2. `v0=1, u=0` 的衰减轨迹能告诉你哪个参数？
3. `v0=2, u=1` 时，为什么 `(a,b)=(0.75,0.5)` 和 `(0.5,1.0)` 都可能完全拟合？
4. 把上题初态改为 `v0=0`，恒定输入是否仍然一定不可辨识？
5. 固定同样的样本数和输入能量，改成正负交替变化的输入，你预计矩阵的秩和条件数怎样改变？
6. 训练误差都很低的两个模型，在新输入上的误差是否必须相近？

为每题写“预测、理由、什么观察会推翻我”。不要只填“可能更好”。

## 2. 你要实现的最小数学核心

给出 `N+1` 个观测状态和 `N` 个输入，构造

\[
X_t=[z_t,u_t],\quad y_t=z_{t+1},\quad
\hat\theta=\arg\min_{[a,b]^T}\|X\theta-y\|_2^2.
\]

定义五个累加量：

\[
S_{vv}=\sum z_t^2,\quad S_{uu}=\sum u_t^2,\quad
S_{vu}=\sum z_tu_t,\quad S_{vy}=\sum z_ty_t,\quad S_{uy}=\sum u_ty_t.
\]

当设计矩阵有两条独立列时，正规方程给出

\[
D=S_{vv}S_{uu}-S_{vu}^2,\qquad
\hat a=\frac{S_{vy}S_{uu}-S_{uy}S_{vu}}{D},\quad
\hat b=\frac{S_{uy}S_{vv}-S_{vy}S_{vu}}{D}.
\]

**不要用 `D += 1e-8` 掩盖秩不足。** 那会悄悄换成另一个问题，而且输出一组数字不等于参数已经被数据区分。对本实验，秩不足应返回 `a=null, b=null, identifiable=false`。`identifiable` 这个字段的精确定义是“按本次数值阈值，有限数据上的双参数 OLS 解唯一”，不是对系统全局结构可辨识性的证明。

设 `G=XᵀX` 的特征值为 `λmax ≥ λmin ≥ 0`，那么 `condition_x = sqrt(λmax / λmin)`。报告的是 **X 的条件数**，不是 G 的条件数；后者是前者的平方。参考实现将 `λmin <= 1e-12 × λmax` 视为数值秩不足。此时 JSON 用 `null` 表示未报告条件数：精确秩不足时可视为无限/未定义；仅被阈值判为数值秩不足时，精确条件数仍可能有限，不能据此证明不存在唯一数学解。不同列的相对尺度与单位会影响条件数，因此这里只在固定单位、同一模型内比较。

参考实现先用设计矩阵最大绝对元素对 `X` 和 `y` 作共同缩放，再计算正规方程；这不改变系数或 `cond(X)`，能避免仅因共同单位尺度为 `1e-100` 或 `1e154` 而把良态正交数据误报为不可辨识。报告的 MSE 仍按原始单位计算。该处理不是通用数值求解器：极端的相对动态范围、接近阈值的数据、预测或平方误差超出浮点范围仍需单独处理；不能用缩放消除真正的列共线性。

上述小公式用于看清楚问题；大规模或病态问题应该学习 QR/SVD 求解，避免显式构造正规方程放大数值误差。输入设计、数据矩阵的信息量和条件数的关系，可对照 [MIT System Identification：实验设计章节](https://underactuated.mit.edu/sysid.html)。更系统的推导见 [MIT 6.435 的最小二乘讲义](https://ocw.mit.edu/courses/6-435-system-identification-spring-2005/resources/lec5_6_435/)。

## 3. 先跑红测试，再亲手写核心

以下命令都从工作台仓库根目录执行。所有测试都是 CPU 上的微小合成数据，不导入 Torch 或 Genesis。

```bash
# starter 尚未实现，预期退出非零。这是教学的红测试。
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.identification.test_contract -v
```

只编辑 [starter.py](../../../developer/labs/identification/starter.py) 中的 `fit_dynamics`。可以复用 `common.validate_data` 和 `common.mse`，但先不要导入或复制 `solution.py`。实现顺序：

1. 用手算例 `[0,1,0.5]` 与输入 `[1,0]` 检查时间索引，得到 `a=0.5,b=1`。
2. 写五个累加量、秩与条件数；解释零输入与两列共线的区别。
3. 写满秩时的两参数解；写秩不足时的明确返回值。
4. 计算训练一步预测 MSE；处理长度不匹配、布尔值、NaN/Infinity。
5. 重跑同一条红测试命令，直到你的 starter 变绿。

函数返回值契约：

| 字段 | 含义 |
|---|---|
| `n_samples` | 输入/转移数量 N |
| `rank` | 数值秩 0、1 或 2 |
| `rank_tolerance` | 采用的 Gram 特征值相对阈值，默认 `1e-12` |
| `condition_x` | 满秩时 X 的条件数；否则 `None` |
| `identifiable` | 此数据和阈值下是否有唯一双参数 OLS 解 |
| `a`, `b` | 满秩时估计值；否则 `None` |
| `train_one_step_mse` | 满秩时一步预测 MSE；否则 `None` |

参考实现与测试在 [solution.py](../../../developer/labs/identification/solution.py) 和 [test_contract.py](../../../developer/labs/identification/test_contract.py)。默认测试使用参考实现，保持正常工程门禁为绿：

```bash
scripts/gnav-env.sh python -m unittest developer.labs.identification.test_contract -v
```

测试覆盖已知手算、无激励、非零共线、恒定输入的稳态与瞬态、参数恢复、独立 holdout、一步预测与自由 rollout 的区分。测试通过说明这些约定下实现正确，不证明任何真实机器人的动力学模型正确。

## 4. 做一个有控制条件的比较

实现后先运行自己的版本；需要核对时才跑参考版本：

```bash
scripts/gnav-env.sh python -m developer.labs.identification.run --implementation starter
scripts/gnav-env.sh python -m developer.labs.identification.run --implementation solution
```

固定条件如下：

| 项目 | 恒定输入组 | 丰富输入组 |
|---|---|---|
| 真实动力学 | `a=.75, b=.5` | 相同 |
| 训练初态 | `v0=2` | 相同 |
| 样本数 | 128 次转移 | 相同 |
| 输入 | 每步 `+1` | 固定 seed=2026 的随机 `±1` 序列 |
| 峰值 / 总平方输入 | `1 / 128` | 相同 |
| 过程噪声 | 先 0，再标准差 .03 | 同一噪声级别复用相同 draws，seed=101 |
| 测量噪声 | 默认 0 | 相同 |
| holdout | seed=2027 的丰富输入；初态 -.3；过程seed=201 | 完全相同的独立留出轨迹 |

这控制了输入能量，却没有控制总位移、任务奖励或安全性。它支持比较这一具体输入设计，不能推出随机激励在所有任务中最优。holdout 从未进入拟合，也没有根据 holdout 结果挑模型或挑种子。

输出中：

- `train_one_step_mse`：每一步都使用真实观测 `z_t` 预测 `z_{t+1}`。
- `holdout.one_step_observed_mse`：在新轨迹上做同样的一步预测。
- `holdout.rollout_observed_mse`：只在起点使用观测，随后把模型自己的预测递推下去。
- `holdout.rollout_latent_mse`：对合成系统可见的无测量噪声真实状态评分；真实机器人通常没有这份 oracle。

一步预测损失与递推仿真损失回答不同问题。MIT 课程也将这两类目标分开讨论。[Equation error vs simulation error](https://underactuated.mit.edu/sysid.html)

<details>
<summary>完成预测后再展开：本机参考运行的核对值</summary>

默认命令、128步、过程噪声标准差 `.03` 的一次固定种子运行：

| 训练输入 | rank(X) | cond(X) | 估计(a,b) | 训练一步MSE | holdout一步MSE | holdout rollout MSE |
|---|---:|---:|---|---:|---:|---:|
| 恒定 | 2 | 105.9005 | (.80210, .39891) | .0008563 | .0121476 | .0155770 |
| 丰富 | 2 | 1.1553 | (.75548, .49904) | .0008546 | .0008704 | .0019595 |

训练误差相近，但参数误差和留出误差不同。这里报告的是一个事先固定的合成例子，没有置信区间，不是跨任务或所有种子的统计结论。

无噪声时：恒定组保持 `v=2`，rank=1，返回无唯一估计；丰富组rank=2，参数恢复到浮点误差范围。输出还构造了两个模型：它们在稳态训练轨迹上的 MSE 都为零，而错误模型 `(a=.5,b=1)` 的留出 rollout MSE 约为 `.283136`。这直接反驳“训练误差为零就说明学会了动力学”。

**恒定输入不总是不可辨识。** 把恒定输入组的初态改成零，会出现瞬态，有限矩阵可以满秩；加入过程噪声也可能使状态变化并使数值秩升高。测试特意包含这两个反例，避免把一个受控例子误写成普遍定理。

</details>

## 5. 挑战你的模型假设

先写下预测，再把测量噪声加上去：

```bash
scripts/gnav-env.sh python -m developer.labs.identification.run \
  --implementation solution --measurement-noise 0.2
```

程序仍然只用观测 `z` 拟合；隐藏的真实状态只用于评分。若 `z_t=v_t+e_t`，代入可得

\[
z_{t+1}=a z_t+b u_t+\underbrace{w_t+e_{t+1}-a e_t}_{r_t}.
\]

即便测量噪声独立同分布，回归输入 `z_t` 与回归误差 `r_t` 也共享 `e_t`。在这里的独立零均值假设下，`Cov(z_t,r_t)=-a Var(e_t)`，通常不为零。这是 errors-in-variables 问题：增加数据、减小训练 MSE 或让 X 满秩，都不能单独保证普通最小二乘恢复真实参数。

默认仅有过程噪声时，当前状态不含未来独立创新，条件更适合这一估计形式；但有限长度动态数据仍不能被随意宣称“有限样本无偏”或“精确恢复”。若换成闭环控制、延迟、隐状态、传感器偏置、非线性饱和或时变参数，还需要重新分析模型与误差关系。进一步可读 [MIT 6.435 课程：输入设计、可辨识性、工具变量与闭环辨识](https://ocw.mit.edu/courses/6-435-system-identification-spring-2005/pages/lecture-notes/)。

## 6. 交付一份可以审查的结论

保留最初预测，在运行后另加结果：

1. 给出命令、分支、修改文件、测试输出，以及未根据结果更换的种子。
2. 解释一个你最初猜错的条件，并区分代码错误、数据不足、模型错误。
3. 用“两个模型同样解释已见数据，却对新动作给出不同预测”的证据说明下一次为什么要改变输入。
4. 指出当前脚本没有选择下一步输入、没有在线更新策略、没有解释语义或意识。
5. 提出下一轮**最小**扩展，例如先注册三个候选输入序列，用训练阶段条件数选一个，再在独立种子上比较参数误差；不要用同一 holdout 既选择又宣称泛化。

回到 Genesis 时，先讨论哪个状态可测、哪个参数希望区分、哪些动作在允许范围内、数据独立性和模型误差是什么。只有这些约定清楚后，再决定是否需要新的物理实验。这个 lab 本身不会触发已有研究分支的仿真或改变任何冻结结果。
