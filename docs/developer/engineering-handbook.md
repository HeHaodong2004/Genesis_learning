# Genesis 日常工程手册

这份手册供你实际修改 Genesis / `gnav` 时查阅。默认从独立工作台根目录操作，使用现有 `scripts/gnav-env.sh` 选择解释器与隔离 ROS 环境。研究约束以仓库最新 `STATUS_FOR_CLAUDE.md` 为准；学习练习不自动启动旧实验或改变冻结研究内容。

你的主线是具身学习研究系统。先按 [训练路线](learning-path.md) 完成包内近期实验；本手册中的 API、前端和容器部分作为后续交付工具查阅，不能据此推断它们已在本次实现。

## 一次改动的最短完整闭环

1. 写清用户可观察的问题与一个输入/输出例子。
2. 读入口、核心函数、现有测试，确认应该在哪一层修改。
3. 检查分支、源码位置、相关未提交改动，保留当前基线。
4. 先复现，再做最小改动；涉及行为错误时补回归测试。
5. 运行与改动对应的检查，阅读输出而非只看绿色标记。
6. 审查 diff，写清变化、验证与限制，让他人能够接手。

一个小 PR 最好只回答一个问题。修改错误提示时，不顺便更换配置框架、格式化整个研究库和调整算法。这样 review 能对照问题判断行为，未来回退也更容易。

## 每次开始工作的检查

```bash
pwd
git status --short
git branch --show-current
git log -1 --oneline
scripts/gnav-env.sh python developer/gnav_dev.py doctor
```

核对三件独立的事：你打开的是哪个目录，命令使用哪个 Python，实际加载的 `gnav` 来自哪里。只有三者符合预期，才开始调试。

`scripts/gnav-env.sh` 会清除 `PYTHONPATH` 与 `AMENT_PREFIX_PATH`，避免 ROS 2 Python 路径混入；默认使用 `genesis-research` conda 环境，并在未指定时选择 GPU 1。设置 `CUDA_VISIBLE_DEVICES=` 可以屏蔽可见 GPU，但不代表一条命令不会初始化 Genesis CPU 后端。是否初始化要看代码入口及 fixture。

## 看代码时从哪里进入

| 想知道什么 | 先看哪里 | 继续追踪 |
|---|---|---|
| 参数最后变成什么 | `configs/eval.yaml`、`configs/base.yaml` | `src/gnav/config.py` 的 `load_config`、`apply_overrides`、`_build` |
| 训练/评估如何启动 | `scripts/train.py`、`scripts/evaluate.py` | `src/gnav/experiment/` |
| run 如何记录身份 | `src/gnav/experiment/run.py` | `provenance`、`make_run_dir`、`MetricsLogger` |
| 机器人能看见什么 | `src/gnav/sim/env.py` | `OBS_KEYS`、`check_obs`、`privileged_state` 的边界 |
| 行为受哪些动力学限制 | `src/gnav/sim/dynamics.py`、`configs/profiles/` | 参数单位、延迟、速度与加速度限制 |
| 为什么跑测试会启仿真 | `tests/conftest.py` | session 级 `autouse=True` 的 `genesis_device` |
| 当前训练器是什么算法 | `src/gnav/experiment/train.py` | 文档明确为 test-grade recurrent A2C + GAE；审查 termination/truncation 简化 |
| 学习模块怎样流转 | `src/gnav/learning/interfaces.py`、`replay.py` | encoder、belief、policy/value、latent dynamics；first 与 privileged 的含义 |
| 当前研究能否继续运行 | `STATUS_FOR_CLAUDE.md` | 最新上下文、冻结内容、已关闭任务与原证据 |

不要从“所有代码”开始。先沿一个具体输入追到一个输出，再补模块之间的联系。

## 配置预检：把错误留在启动之前

```bash
scripts/gnav-env.sh python developer/gnav_dev.py config --config configs/eval.yaml backend=cpu env.n_envs=2
scripts/gnav-env.sh python developer/gnav_dev.py config --config configs/eval.yaml env.n_envs=0
```

第二条是故意设置的非法输入练习，应当看到明确错误并得到非零退出码。Bash 中紧接着执行 `echo $?` 查看上一条退出码；中间不要先运行其他命令。

理解三层检查：YAML 能否解析；字段名与类型是否合适；数值对这个应用是否有意义。例如 `0` 是合法整数，但 0 个并行环境通常没有运行意义。预检通过只说明检查覆盖的规则成立，不证明仿真稳定、算法正确或科学结论有效。

原配置入口已对未知 dataclass 字段报错。工作台提供外围预检和更适合开发的反馈；它不替换历史科研模型。若遇到配置被拒绝，先看字段与规则，再判断是输入错误还是校验规则过严，不要直接绕过错误。

配置 hash 标识解析后的配置内容；它不是一次实验的全部身份。同一配置可能配合不同代码、依赖或数据。记录结果时还需要代码版本、dirty 状态、环境与数据信息。

## Git：用差异而不是记忆管理变更

| 概念 | 在这里的意义 |
|---|---|
| 工作区 working tree | 当前目录中的真实文件；未保存的编辑器内容还不在磁盘上 |
| 暂存区 index | 下一次提交将包含的快照选择 |
| 提交 commit | 带父关系的版本快照；commit 本身不会上传 |
| 分支 branch | 指向提交的可移动名字；不是复制了一套完整历史 |
| worktree | 同一仓库的另一个工作目录，通常对应另一个分支 |
| 远端 remote | 另一个仓库的位置；push 才会向其发送提交 |

日常先看 `git diff --stat`，再看 `git diff -- 路径`。暂存后用 `git diff --cached` 看真正将提交的内容。注意：普通 `git diff` 不显示新建、未跟踪文件的内容，必须同时看 `git status --short` 并打开这些文件。

本次已有独立 worktree，不必再创建。以后在获准的新任务中，可以从确定的起点创建，例如：

```bash
git worktree list
git worktree add -b practice/run-summary ../gnav-run-summary HEAD
```

这条命令创建新分支和目录，不会自动带走当前未提交文件，也不会同步被忽略的 runs 或原始数据。多个 worktree 共享 Git 对象和分支信息；Python editable 安装属于另一套机制，不能靠 worktree 自动隔离。[Git 官方 worktree 文档](https://git-scm.com/docs/git-worktree)

遇到别人留下的未提交文件，先明确归属，不能为了“干净状态”删除。完成一项改动后，是否 commit、merge 或 push 按当前项目约定执行。不要把备份、强制回退、删除工作树混入例行检查命令。

## 调试：找第一次偏离预期的位置

以 `env.n_envs=2` 为例，在 `src/gnav/config.py` 的 `apply_overrides` 设断点。运行工作台的配置检查入口，观察 `ov`、`parts`、`node`、`val`。先预测下一行怎样改变对象，再单步验证。继续跟到 `_build`，观察 Python 数据如何成为配置对象。

如果断点不命中，按顺序确认：启动配置是否正确；入口是否真的调用此函数；打开文件是否为实际导入文件；解释器与工作目录是否匹配。反复重装扩展通常无法回答这些问题。

VS Code 的 Python 调试配置使用 `debugpy`；`cwd`、参数与解释器是可分别设置的。工作台的配置应与命令行入口对齐。[VS Code 官方调试文档](https://code.visualstudio.com/docs/python/debugging)

调试记录只需四项：输入、预期、第一次异常的变量/行、解释。它比几十行无目的 `print` 更容易复查。修复后删除临时调试输出，保留必要的诊断信息与回归测试。

## 测试：按问题选择验证层

| 层级 | 本项目例子 | 能说明什么 | 不能代替什么 |
|---|---|---|---|
| 解析/静态检查 | Python 语法、配置文件格式 | 文件可以被解释或解析 | 运行时行为 |
| 轻量行为测试 | `developer/tests/` 配置与 run 检查 | 输入边界、输出、错误处理 | Genesis 物理正确性 |
| 模块/数值测试 | 原仓库某个模型测试 | 指定模型与边界的数值行为 | 全部场景成立 |
| 集成测试 | 仿真、传感器、策略一起运行 | 模块连接与环境行为 | 科学假设的充分证据 |
| 实验验证 | 预先定义的比较、seed 和判据 | 注册范围内的研究问题 | 未测试区域、无限精度结论 |

开发工作台的轻量检查：

```bash
scripts/gnav-env.sh python -m unittest discover -s developer/tests -v
```

独立教学 lab 的测试入口为 `scripts/gnav-env.sh python -m unittest discover -s developer/labs -p 'test_*.py' -v`。按对应说明选学生 starter 或参考实现，保存选择信息；尚未完成 starter 的失败是预期练习状态。

它与原仓库 `tests/` 的 pytest 启动路径分开，避免轻量工具检查触发原有 Genesis 自动 fixture。pytest 的 fixture 用于建立测试所需上下文；自动 fixture 也可能引入隐含依赖，选择测试命令前要看它的作用域。[pytest 官方 fixture 说明](https://docs.pytest.org/en/stable/explanation/fixtures.html)

一个有用的回归测试应回答“哪个外部可观察错误不会再发生”。例如坏 JSON 应报告文件位置并返回错误，而非静默成功。测试内部私有函数被调用几次往往不如检查最终行为稳定。

更改文档错字或可逆的低影响布局时，不必额外编写形式化测试；检查链接、预览和差异即可。更改输入校验、文件读取、计算或状态行为时，选择能发现实际错误的验证。

## 实验结果的证据链

先用合成 fixture 练习读取：

```bash
scripts/gnav-env.sh python developer/gnav_dev.py inspect-run developer/fixtures/demo_run --json
```

此 fixture 是教学数据，不是新研究结果。再读取已有真实 run 前，先确认目录格式与可读性。工具能检查文件是否存在和格式是否可解释，但不能从一份 provenance 自动证明内容真实，也不能补齐缺失原始数据。

给一份结果写摘要时分开记录：

- **身份**：代码版本、dirty 状态、完整配置、seed、数据版本。
- **执行**：解释器与依赖、后端、实际命令、资源与时间。
- **结果**：指标定义、单位、样本数和数据位置。
- **限制**：缺失记录、未运行验证、已知数值误差、适用范围。

若目录缺少 `provenance.json`，结论是“缺少对应溯源文件”，不是“实验无效”或“实验通过”。如果使用的是合成数据，每次展示都明确标识。缺文件、无结果、值为 0 是三个不同状态。

## 引入新工具前作一次小决策

| 需求出现时 | 可以学习/引入 | 在当前 Genesis 中的约束 |
|---|---|---|
| 依赖难以重建 | 独立工具的依赖锁定、uv 或现有 conda 锁定流程 | 先在隔离副本验证；不原地升级既有 CUDA/Genesis 环境 |
| 每次修改重复手工检查 | 任务入口、CI | 首先自动化真正有价值的 CPU 检查；GPU验证单独说明 |
| 他人需要从程序查询结果 | 稳定 CLI JSON；必要时 HTTP API | 先定义数据契约与错误，训练启动和只读查询分开设计 |
| 需要多用户筛选和交互 | 前端与 API | 围绕一个真实使用流程实现，不同时学习所有框架 |
| 需要跨机器交付 CPU 服务 | 容器镜像 | 镜像可重建不等于 GPU 驱动兼容或科学结果可复现 |
| 单机已无法满足吞吐 | 调度、队列、分布式执行 | 先量化瓶颈、幂等和失败恢复，再增加部署复杂度 |

uv 项目使用 `pyproject.toml` 描述项目、环境与锁文件协同管理依赖。这个机制适合在独立工具中练习；是否迁移整个科研环境，需要以复现与兼容验证决定。[uv 官方项目结构](https://docs.astral.sh/uv/concepts/projects/layout/)

## AI 协作：把任务定义、判断和验收留在自己手中

一次有效委托包含：问题、输入例子、相关路径、限制、验收命令和期望交接。可以直接复用：

> 请先读 `README.md`、`STATUS_FOR_CLAUDE.md` 和相关代码。任务是解决〔具体用户问题〕；复现输入是〔输入〕，期望行为是〔行为〕。只改〔范围〕，保留当前未提交内容。请先解释原因和最小方案，再实现并运行对应检查。交付时写出差异、实际运行的验证与未覆盖部分。不要把合成数据或历史结果描述为本次运行结果。

请 AI review 时，再给它你的假设：“我认为错误来自配置覆盖，不来自仿真；请优先尝试反证。”这与研究中的独立验证相同，能减少两个人沿着同一错误方向加速。

文件型项目说明适合记录长期规则；交接记录适合记录当前状态；聊天记忆可能过时。发生冲突时，用最新有效指令、当前代码和可复现证据校准。重要事实写入可审阅的项目文档，并注明日期与来源。

## 故障排查表

| 现象 | 先检查 | 下一步 |
|---|---|---|
| 改了代码却不生效 | `doctor` 的源码路径、解释器和当前分支 | 确认入口使用当前 worktree；不要立刻重装共享包 |
| `ModuleNotFoundError` | 是否通过 wrapper、模块是否为该入口所需 | 区分缺依赖和路径错误；避免向系统 Python 随意安装 |
| 输入 `env.n_envs=0` 被拒绝 | 字段值及错误规则 | 使用有意义的正整数；若边界规则有争议，先写问题卡 |
| YAML 看起来对却类型错误 | 引号、缩进、布尔值、字段路径 | 查看解析结果；Python 类型注解本身不保证运行时校验 |
| 一个小测试开始加载仿真 | 测试目录与 `conftest.py` | 改用工作台轻量测试入口；原测试要按其运行约定处理 |
| 单元测试绿但真实运行失败 | 依赖、数据、设备、模块连接 | 增加针对失败边界的集成验证，不扩大单元测试的证明范围 |
| 结果目录有指标却缺版本 | 对应 provenance 和配置文件 | 明确报告证据缺失，查原始记录，不用当前版本冒充历史版本 |
| CI 文件已写但没有运行记录 | 是否配置远端及触发事件 | 本地记录标“本地”；远端验证等真实运行后再报告 |
| 测试偶发失败 | seed、时间/并发、共享目录、资源状态 | 保存失败输入与日志，稳定复现后再判断，不用盲目重跑掩盖 |

## 可复制的小 PR 描述

```text
问题：使用者在……输入下遇到……。
变化：现在……，错误时……。
验证：实际执行……，结果……；未执行……，原因……。
限制与恢复：适用于……；出现……时恢复到……。
```

评审时检查：是否解决问题；是否改变无关行为；是否能处理空值、坏输入和边界；测试是否证明目标行为；是否引入隐藏环境依赖；文档是否与实现一致。

## 术语速查

| 术语 | 在开发中怎样理解 |
|---|---|
| contract / 契约 | 调用者与实现共同遵守的输入、输出和失败约定 |
| invariant / 不变量 | 一个过程始终应成立的条件，例如不把缺失指标解释成零 |
| regression / 回归 | 原来可用的行为因改动而坏掉 |
| fixture / 测试夹具 | 为测试准备可控上下文、文件或数据的机制 |
| provenance / 溯源 | 一份结果由什么代码、配置、数据与环境产生 |
| idempotency / 幂等 | 重复相同操作不会造成额外的业务效果 |
| observability / 可观测性 | 用日志、指标和追踪理解系统实际发生了什么 |
| dependency lock / 依赖锁定 | 记录可重复解析的具体依赖选择；仍需验证平台条件 |
| CI / 持续集成 | 每次集成改动时自动执行约定检查并提供反馈 |
| artifact / 产物 | 可以保存、传递和检查的构建包、报告或运行输出 |
| ADR / 架构决策记录 | 简述问题、选择、备选与代价，方便以后理解为什么这样做 |
| rollback / 回退 | 恢复到已知状态的操作；应知道代码与数据分别如何处理 |

继续实战见 [12 周与三年学习路线](learning-path.md)。
