# Genesis 开发工作台：从研究代码到可交付产品

你的近期主线是独立构建和验证 Genesis / 机器人学习研究系统，同时发展端到端交付能力。这套工作台以现有 `gnav` 仓库为起点，帮助你练习：提出可失败的预测 → 找代码 → 写用例 → 实现核心 → 调试 → 控制实验 → 写清楚证据。API、数据库、前端与部署是可选的产品交付扩展，不占据机器人学习主线。

## 回来后的第一件事（10 分钟）

在这台机器的终端执行：

```bash
cd /home/haodong/workspace/projects/genesis-developer-workbench
make doctor
make check
code .
```

在 VS Code 打开本文件，用 Markdown 预览阅读。`make doctor` 应显示当前工作树的代码路径；`make check` 验证的是轻量开发工具和教学参考实现，不代表仿真或研究结论通过验证。命令使用已存在的 Genesis Python 环境，不需要重新安装 Genesis。

如果机器上的环境不在默认目录：

```bash
GNAV_ENV_PREFIX=/你的环境路径 make doctor
```

VS Code 另外执行 `Python: Select Interpreter` 选择同一解释器；这里的默认设置按这台 Linux 机器配置。推荐扩展只是建议安装，尚未替你安装。先看 [环境与调试](setup.md)，再按以下顺序进行。

## 学习入口

| 你现在想做什么 | 打开哪里 | 应留下的证据 |
| --- | --- | --- |
| 理解工作台与原仓库的关系 | [环境与调试](setup.md) | 解释器、分支、代码来源路径 |
| 第一次亲手修一个问题 | [第一个贡献](first-contribution.md) | 一个失败用例、修复、通过结果、PR 草稿 |
| 检验仿真物理与时间离散 | [Genesis 物理仪器](labs/physics.md) | 手算、CPU/GPU轨迹、误差解释 |
| 隔离部署观测与特权信息 | [观测边界](labs/observation.md) | 反例与数据来源图 |
| 理解终止、截断和 advantage | [GAE 实战](labs/gae.md) | 手算oracle与自己的实现 |
| 判断参数是否真的被辨识 | [系统辨识](labs/identification.md) | 激励、rank、holdout与反例 |
| 学会日常开发的判断方式 | [工程手册](engineering-handbook.md) | 每次改动的复现步骤与验收条件 |
| 安排接下来的 12 周与三年 | [成长路线](learning-path.md) | 每周可演示的作品，而非课程观看量 |
| 可选：将研究工具交付给他人 | [产品实践计划](product-brief.md) | 用户任务、接口契约、纵向切片 |
| 交给下一个 AI / 未来的自己 | [开发交接模板](templates/handoff.md) | 当前状态、已验证证据、下一步 |

## 三个直接可用的动作

```bash
# 1. 查看当前解释器、代码来源和依赖元数据
make doctor

# 2. 在启动仿真前检查配置；这里只读配置
scripts/gnav-env.sh python developer/gnav_dev.py config \
  --config configs/eval.yaml backend=cpu env.n_envs=2

# 3. 检查已有运行产物；PATH 换成某个真实 run 目录
scripts/gnav-env.sh python developer/gnav_dev.py inspect-run PATH --json
```

配置检查器是新增的外围工具。原训练脚本尚未自动调用它，因此“此处通过”不是训练正确的证明。这里不把原 `tests/` 当日常入口，因为其共享 fixture 会自动初始化 Genesis。

## 本次工作的边界

起点是 `phase-a2` 的 `181c8f6`，交付位于独立分支 `codex/developer-workbench` 和这个独立工作树。原仓库、Claude 的研究分支、已有部署与科学结果不需要迁移。原仓库还有一个用户未跟踪文件，本工作台不复制或覆盖它。新增内容尚未合并或推送；GitHub workflow 是可审阅的配置，不代表云端 CI 已运行。

这套工作台的首要验收不是“会使用多少工具”，而是你能不用 AI 代答地解释：这次改了什么，为什么有效，证据是什么，以及哪些情况仍然不知道。
