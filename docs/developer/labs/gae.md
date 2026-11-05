# Lab：亲手实现 termination / truncation 正确的 batched GAE

你已经做过 vectorization、reset、visibility、sweeps 和轻量 PPO micro-lab。这次把注意力放到训练目标的正确性：同样一批 reward，因为两个 mask 或一个 reset observation 用错，就会得到完全不同的 advantage。你的交付是一个能独立解释、用手算 oracle 验证的 GAE 函数，以及未来接回 Genesis collector 的数据契约。

本练习只使用标准库，运行时间为毫秒级；没有启动仿真、没有训练策略。通过它不代表已经实现 PPO 或取得研究性能提升。

## 从现有 Genesis 代码找真实接入点

读 [当前训练循环](../../../src/gnav/experiment/train.py) 的开头和 `for t in reversed(...)`。它自述为 test-grade recurrent **A2C + GAE**，明确把 truncation 当作 terminal。这是已有示例的简化，不是 PPO 实现。

再读 [NavEnv.step](../../../src/gnav/sim/env.py) 的 `auto_reset` 分支：默认在返回 observation 之前调用 `reset_done`，当前 `info` 不提供 `final_obs`。因此，仅把 GAE 的 `done` 改成 `terminated` 会让 truncation 的 bootstrap 读到下一 episode 的初始状态。你需要同时解决 collector 的真实 next observation 和 GAE 的两个 mask。

## 1. 先理解两个不同的问题

`terminated` 表示任务定义中的终止，如成功或失败；`truncated` 表示任务之外的采样截断。对于后者，任务本身可能继续，所以价值目标仍应使用截断处的后继状态价值。一个时间上限如果本来就是任务目标的一部分，则是另一个建模选择：应按有限时域任务处理，并考虑把剩余时间纳入 observation，而不是见到 timeout 一律 bootstrap。[Gymnasium 的时间限制说明](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)、[Pardo 等，Time Limits in Reinforcement Learning](https://arxiv.org/abs/1712.00378)。

GAE 把一步 TD residual 的序列按 `γλ` 衰减求和，权衡偏差和方差。[Schulman 等，Generalized Advantage Estimation](https://arxiv.org/abs/1506.02438)。本练习按当前采样段写成：

```text
bootstrap_mask[t,b] = 1 - terminated[t,b]
trace_mask[t,b]     = 1 - (terminated[t,b] OR truncated[t,b])

δ[t,b] = r[t,b] + γ × bootstrap_mask[t,b] × V(true_next_obs[t,b]) - V(obs[t,b])
A[t,b] = δ[t,b] + γλ × trace_mask[t,b] × A[t+1,b]
return_target[t,b] = A[t,b] + V(obs[t,b])
```

`bootstrap_mask` 回答“这个任务在该状态之后是否还有价值”；`trace_mask` 回答“下一行 residual 还是不是同一个采样 episode”。截断时，第一个答案是有，第二个答案是否。因此不能把这两个 mask 合并。

最后一行采样后初始化 `A[T,b]=0`，但该行若没有终止仍用真实 `next_value` bootstrap。rollout chunk 结束不等于环境 terminal，也不需要伪造一个 truncation 标签。这是有限采样段上的 GAE 估计，未假定你知道 chunk 以外的 TD residual。

## 2. 写预测表，暂时不要看 solution

使用 `r=2, V(obs)=1, V(true_next_obs)=10, γ=.9, λ=.8`，单步序列。先在自己的笔记填空：

| 情况 | bootstrap mask | trace mask | δ / A | return target |
|---|---:|---:|---:|---:|
| 普通继续，但 rollout 正好结束 | ? | ? | ? | ? |
| 真正 terminated | ? | ? | ? | ? |
| 外部 truncated | ? | ? | ? | ? |
| truncated，但误用 reset 后 V=100 | ? | ? | ? | ? |

再预测这个时间序列，形状 `[T=3, B=1]`：

| t | episode | r | V(obs) | V(true next obs) | terminated | truncated |
|---|---|---:|---:|---:|---|---|
| 0 | 第一个 | 1 | 2 | 3 | false | false |
| 1 | 第一个 | 2 | 3 | 4 | false | true |
| 2 | 第二个 | 100 | 50 | 不使用 | true | false |

请回答：把 t=2 的 reward 从 100 改成 1,000,000，t=0、t=1 的 advantage 能不能改变？如果能变，具体是哪条递推把不同 episode 连在了一起？

## 3. 你要实现的函数与输入契约

编辑 [starter.py](../../../developer/labs/gae/starter.py) 中的 `compute_gae`。输入检查已放在 [contract.py](../../../developer/labs/gae/contract.py)，可以调用；你的核心任务是自己写两种 mask、逆序递推和 padding 分支。建议先把 starter 的循环删掉，用上面的预测从空白重写，然后再对照参考实现。

```python
compute_gae(rewards, values, next_values, terminated, truncated,
            gamma=0.99, lam=0.95, valid=None)
# 返回 {"deltas": [T,B], "advantages": [T,B], "returns": [T,B]}
```

| 契约 | 为什么要明确 |
|---|---|
| 输入是相同、非空、矩形的 `[T,B]` 嵌套 list/tuple，T 在前 | 防止误把环境维当时间维递推 |
| `terminated/truncated/valid` 单元必须是 bool | 避免随手传浮点概率或数字 mask |
| `next_values[t,b]` 来自这一次 transition 的真实后继 observation | reset 边界不能直接用 `values[t+1,b]` 代替 |
| 所有 values 来自同一轮冻结 critic | 不能边更新 critic，边用新旧估值构造同一批 target |
| 有效行的 reward、value 必须是有限数字；非 terminal 的 next_value 也必须有限 | NaN 不能被静默带入梯度；非有限计算结果也报错 |
| terminal 行的 next_value 不使用，可为 `None` 或 NaN | 显式条件分支；`0 × NaN` 仍然是 NaN |
| 同时 term/trunc 为 true 时，term 优先：不 bootstrap，且截断 trace | 避免输入歧义产生不稳定目标 |
| `gamma/lam` 是 `[0,1]` 的有限数 | 排除无意义的衰减参数；`gamma=0` 仍要求非 terminal next_value 合法 |
| `valid=False` 只允许每个环境列的尾部 padding | padding 行输出三个 0，也清空 trace；数值内容不读取，可以是 None/NaN |
| 不支持 valid 的 true→false→true 内部空洞 | 那可能是丢失 transition 或 next-step autoreset 的占位步，必须由 collector 明确处理，不能偷偷当连续轨迹 |
| 不修改输入，不做 advantage normalization | 保持纯函数便于验证；归一化必须只在有效训练样本上另做 |

某一列可以全部是 padding；这只是“这一列没有训练样本”，不能把那些输出的 0 放进 loss。尾部最后一个有效 transition 若仍在继续，应有自己的 true next value，不能因为下一格是 padding 就删掉 bootstrap。

## 4. Red：分别隔离两个错误

```bash
cd /home/haodong/workspace/projects/genesis-developer-workbench
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.gae.test_contract.GAEContract.test_termination_removes_bootstrap_but_truncation_preserves_it -v
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.gae.test_contract.GAEContract.test_truncation_stops_trace_into_next_episode -v
```

这两条命令初始都应失败，退出码 1。第一条预期 truncated advantage 为 10，starter 得 1；第二条把所有 value 设为 0、γ=λ=1，单独检验 trace：应为 `[2,100]`，starter 把两个 episode 接成 `[102,100]`。

不要同时猜两个 mask。先修第一个测试，再看第二个仍失败的原因。测试名应该描述你想守住的物理/数据语义，而不只是“函数输出没变化”。

## 5. Debug 与 Green：做出自己的实现

每个环境列单独逆序循环，初始化该列 `carry=0`。每一行先处理 padding，再选择 bootstrap，然后算 delta；最后根据 episode 边界选择是否把 carry 接进来。赋值 return target 时保持 `A+V`，并验证输出有限。

在编辑器给 `delta`、`carry` 两行设断点，运行上面的小测试；或直接用标准库调试器：

```bash
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m pdb -m unittest \
  developer.labs.gae.test_contract.GAEContract.test_hand_calculated_two_episode_oracle
```

在 `(Pdb)` 用 `b developer/labs/gae/starter.py:25`、`c`、`p time`、`p batch`、`p carry` 观察边界。文件改动后把断点移到 bootstrap 赋值附近。只看终态均值容易掩盖错；你要逐行看到 t=1 截断时 next value 被保留，而 t=2 的 carry 被挡住。

```bash
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.gae.test_contract -v
scripts/gnav-env.sh python -m developer.labs.gae.run --implementation starter
```

完成标准：显式 starter 的 **17 个测试通过**；你能手算两集样例，并解释为什么换第二集 reward 不影响第一集。若卡住，打开 [参考 solution](../../../developer/labs/gae/solution.py)；不要把默认绿当作自己的练习完成。

参考验证命令（未设置环境变量时默认也使用 solution）：

```bash
LAB_IMPLEMENTATION=solution scripts/gnav-env.sh python -m unittest developer.labs.gae.test_contract -v
scripts/gnav-env.sh python -m developer.labs.gae.run --implementation solution
```

## 6. 手算 oracle 与受控反例

完成预测和实现后再核对：

| 单步情况 | bootstrap mask | trace mask | δ / A | return target |
|---|---:|---:|---:|---:|
| 普通继续、rollout 截止 | 1 | 1 | 10 | 11 |
| terminated | 0 | 0 | 1 | 2 |
| truncated | 1 | 0 | 10 | 11 |
| truncated 误用 reset V=100 | 1 | 0 | 91 | 92 |

两集样例有 `γλ=.72`：

```text
δ2 = 100 - 50 = 50              A2 = 50
δ1 = 2 + .9×4 - 3 = 2.6        A1 = 2.6（这里截断，不能 +.72×50）
δ0 = 1 + .9×3 - 2 = 1.7        A0 = 1.7 + .72×2.6 = 3.572
return targets = [5.572, 5.6, 100]
```

只删除截断 bootstrap、但正确切断 trace，会得到 `A1=-1`、`A0=.98`。保留正确 bootstrap、但错误延续 trace，则得到 `A1=38.6`、`A0=29.492`。starter 同时有两个错误，所以它最初得到 `A1=35`、`A0=26.9`。这三个模式是调试线索，不是训练效果数据。

额外挑战：把 `lam` 设为 0，advantage 必须等于每行 delta；把 gamma 设为 0，return target 必须等于当前 reward；γ=λ=1 时，用两步手算的 bootstrapped return 复核；把某列的 terminal 移到另一个时间，另一列的结果必须不变。以上都有独立例子进入测试，不只是让 solution 自己和自己比较。

## 7. Collector：final observation 为什么会让 mask 修复失效

Gymnasium 的 Same-Step autoreset 会返回 reset observation，原 episode 的 final observation 放到 info；官方当前例子用 `info["final_obs"]`，旧版本出现过 `final_observation`。Next-Step 模式在下一次 step 才 reset，会有不代表真实动作转移的 reset 占位步。查看实际版本、wrapper 和 `metadata["autoreset_mode"]`，不要混用模式；Next-Step 占位步应从轨迹中剔除或由另一个明确支持内部空洞的 buffer 处理。[Farama 官方 autoreset 说明](https://farama.org/Vector-Autoreset-Mode)、[Gymnasium VectorEnv API](https://gymnasium.farama.org/api/vector/)。

假设截断时真正后继 observation 的价值为 10，reset 初始 observation 的价值为 100，reward=2、当前 V=1。正确 GAE 算 10，误传 reset 值就算 91。**这两个值都是有限数、形状也正确，GAE 函数无法从数字上知道 100 来错地方了**；这必须由 collector 集成测试守住。

你的自定义 NavEnv 当前没有 Gymnasium 的 `final_obs` 键。下一次接入时可先采用明确顺序：

```text
true_next_obs, reward, term, trunc, info = env.step(action, auto_reset=False)
用当前冻结 critic 对 true_next_obs 评值，保存 next_values
把 term、trunc 分别存进 rollout，不能只存 done
obs_for_next_action = env.reset_done(term | trunc, true_next_obs)
```

这段是接入设计，不是已验证的训练补丁。当前 agent 是 recurrent：评 final observation 时必须使用本 episode 的历史 belief/hidden state 与当前 action，不能先把 `first=True` 的 reset hidden state 用进去。完成 final value 计算后，下一 episode 才用新的 reset observation 和 episode-start mask；不要为了 bootstrap 多走一次 policy state 导致 hidden state 被推进两次。若 observation 字典可能复用内存，存储时 clone 所需张量，先用 collector stub 证明数据未被 reset 覆盖。

## 8. 下一步：你亲手把它接向 PPO

先交付一个独立 Torch 移植，而不是立刻开长训练：保留 `[T,B]` 接口，按时间逆序、按 B 向量化；使旧 value、next value 和 return target 都在 `no_grad` / detach 边界内，policy gradient 不通过 advantage target 回传。用本节列表 oracle 与 Torch CPU float64 逐元素对比，再选 float32 合理容差。终止处若允许 next value 的 NaN，先用条件选择安全值，不要写 `(~terminated) * next_value`。只对 valid 样本归一化 advantage、计算 loss 和组成 minibatch。

然后写一个可控 collector stub：截断前给定 value=10，reset 后给定 value=100；明确断言送进 GAE 的是 10，且换新 episode 的 reward 不影响旧 episode target。再为 recurrent hidden-state 与 prev-action 的 reset 边界加案例。这个阶段仍不需要 Genesis GPU。

最后才计划真正 PPO：固定一轮 rollout 的 `old_log_prob` 与 critic target，验证 ratio、clip surrogate、minibatch/epoch、KL 与梯度范数记录，以及 episode 与 buffer 边界处理。当前研究代码是 A2C；你需要设计并审查 PPO 更新，而不是把一个文件改名成 PPO。若迁入真实训练，先记录任务 time-limit 语义、对比旧新 target 的受控差异，再安排固定 seed 的短 smoke run；训练性能结论还需要独立评估。

你本次可交付的证据包括：自己的预测表；starter 通过的测试输出；一个“修第一个 mask 后第二个测试仍红”的调试记录；collector 数据流图；Torch 移植及与手算样例的逐元素比较计划。这些展示的是你能主动实现并判断 robot learning 系统的正确性。
