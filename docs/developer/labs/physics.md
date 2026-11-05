# 练习：Genesis 真的在计算我写下的动力学吗？

已有 GPU micro-labs 之后，下一步是建立一台可检验的物理测量仪器。本练习用不接触地面的自由落体，刻意排除策略、碰撞和复杂资产，把时间离散与批环境状态操作单独暴露出来。

## 先推导，再运行

设 z₀=2 m、v₀=0、g=-9.81 m/s²、T=0.2 s。连续模型：

```text
v(T) = gT
z(T) = z₀ + gT²/2
```

显式速度更新、半隐式位置更新：

```text
v[k+1] = v[k] + g Δt
z[k+1] = z[k] + v[k+1] Δt
z[n] = z₀ + g Δt² n(n+1)/2
z[n] - z(T) = g T Δt/2
```

预测在固定 T 下 Δt 减半，位置离散误差约减半，速度应与解析解接近。先自己算出两个末位置，再看 `developer/labs/physics_predictions.json`。那份文件在本次测量前写入；它是教学预测，不冒称正式科研预注册。

## 可执行仪器

```bash
# 先看GPU占用；此处只用物理GPU1
nvidia-smi
CUDA_VISIBLE_DEVICES=1 scripts/gnav-env.sh python developer/physics_probe.py \
  --backend gpu --output developer/evidence/my-physics-gpu.json

# CPU独立进程；现有文件不会被覆盖，换一个新路径可重新测量
CUDA_VISIBLE_DEVICES= scripts/gnav-env.sh python developer/physics_probe.py \
  --backend cpu --output developer/evidence/my-physics-cpu.json
```

代码只构建两个各含球体的批环境，分别用 Δt=.02/.01，记录轨迹，并只重置 env0 的位置和速度。无需图形界面。第一次运行可能包含内核编译；程序总用时不是稳态吞吐。`CUDA_VISIBLE_DEVICES=1` 会把物理 GPU1 映射为进程的 `cuda:0`，报告中的 `cuda:0` 不表示抢用了显示卡。

默认 `make check` 不运行本仪器。代码中的 Genesis 初始化、场景、实体、build、step、get/set 状态全部可直接读到，没有封装在大框架内。报告包含源代码及预测文件 SHA256，避免改了脚本却引用旧结果。

## 你来完成的部分

1. 不看公式答案，手推并写一个独立的 `analyze_freefall(trajectory, dt)`，从保存的 JSON 重建两个误差；不要直接信报告中的 `ok`。
2. 在自己的副本把 n 改成固定步数而非固定 T。预测为什么此时不能直接把两份末位置误差比解释为收敛阶，再验证。
3. 故意只 reset 位置不 reset 速度，增加一个测试：下一步不应带着上一回合末速度继续下落。解释为什么 reset 不是单纯把画面上的球挪回去。
4. 把 `substeps` 设为 2。保持宏观 dt 和 T 不变，重新推导内部步长对离散误差的影响；生成新证据路径，保留旧报告。
5. 最后才加入地面。自由落体公式在接触后不再适用；设计新的穿透深度、静止残差、能量和时间步检查，明确容许误差来源。此扩展尚未由本包验证。

## 这次检查证明什么

它只检验所选版本、后端、两种时间步、无接触球体和子环境 reset 的有限行为。不能据此宣称碰撞模型、相机、执行器、真实机器人或学习策略可信。真正的机器人验证应逐项扩展：惯性、阻尼、关节限位、力矩饱和、接触、传感器时序，每次保留一个可以失败的参考。

接口依据：[Genesis 场景入门](https://genesis-world.readthedocs.io/en/latest/user_guide/getting_started/hello_genesis.html)、[并行环境与子集操作](https://genesis-world.readthedocs.io/en/latest/user_guide/getting_started/parallel_simulation.html)。实际执行以本机已安装的 1.4.5 为准，不要求你更新到文档的未来版本。
