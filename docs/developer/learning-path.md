# Genesis 研究开发者训练路线

这条路线按你补充的背景设计：ICL 机器人博士，已有数学、规划、最小模型与证伪思维，希望获得独立开展 frontier embodied AI 研究的能力，同时能够把研究系统交付给别人使用。主线是 **Genesis 物理与场景 → 合法 observation → RL 边界与 PPO → 表示、动力学与世界模型 → sim-to-real**。Git、调试、测试、CI 和交接贯穿每一步；API 与 React 是需要面向他人交付时的可选外层。

你已做过向量化、按环境 reset、可见性、compile、参数 sweep 与 PPO micro-labs，本路线不重复讲基础图搜索，也不要求重建 Falcon。当前导航仓库是可用的工程练习场，不预设它就是你未来论文方向。“自我理解”等兴趣暂时是问题线索，需要经过定义、反例、基线和已有工作比较，才能判断是否形成研究问题。

本材料中的未来任务不是已完成实验。现有源码与历史结果、今天的轻量教学实验、未来 Genesis 验证应分别记录。旧 micro-labs 的存在和用户完成情况，不等于本次重新验证了它们的训练或物理正确性。

## 从已有能力出发

| 已有研究经验 | 对应工程能力 | 现在增加的动作 |
|---|---|---|
| 控制变量、消融、重复实验 | 缩小故障范围，比较基线，判断回归 | 修改前保存一个能重现问题的最小输入 |
| 张量、传感器、动力学与规划 | 接口契约、数据边界、数值与物理检查 | 明确单位、时序、shape、信息来源与异常行为 |
| 数学推导和反例 | 独立 oracle、边界测试、证伪实现假设 | 为小规模情况写可手算答案，与向量化实现比较 |
| seed、配置和 checkpoint | 版本、数据与结果溯源 | 结果同时携带代码、配置、依赖和数据身份 |
| 论文假设与限制 | 设计取舍、评审与交接 | 说明为什么这样实现，以及验证没有覆盖什么 |

目标是让你能回答：这条学习曲线来自什么数据流？如果换一个 reset 时机、遮挡条件或动力学参数，哪些量应该改变，哪些应该保持？出现意外结果时，怎样分清 bug、数值误差、不可识别性和真正的新现象？

## 时间预算与学习协议

建议每周 4–6 小时：四天各 30–45 分钟，周末一次 2–3 小时。论文截止周可以减量，但保留一次独立实现或排错。12 周是一个可调整的课程节奏，不代表 72 小时足以掌握整个领域；某个边界没有理解就延长该周。

每个 lab 都留下同样的证据：

1. **预测**：运行前写下预期方向、边界和可能失败的条件。
2. **数学**：状态、观测、动作、目标、单位和必要的推导。
3. **核心实现**：你亲手完成决定实验含义的部分；脚手架由工具辅助。
4. **测试**：至少一个手算或独立 oracle、一个边界、一个故障反例。
5. **控制变量**：只改目标因素，其余条件及 seed 配对或清楚记录。
6. **基线**：说明没有新组件时应当怎样；加入故意错误的实现检查测试灵敏度。
7. **解释**：结果支持了什么、排除了什么、仍无法判断什么。
8. **参考解答**：完成预测与独立尝试后再看，比较假设而不只比较代码。

一次 45 分钟练习：5 分钟预测，10 分钟推导与读代码，20 分钟实现，10 分钟验证与记录。卡住超过 15 分钟，先缩小输入，再让 AI 给提示。每周提交给自己的不是阅读时长，而是一份差异、一份验证记录和三分钟解释。

## 第一天：确认实际运行的代码

在 `genesis-developer-workbench` 根目录执行：

```bash
pwd
git status --short
git branch --show-current
scripts/gnav-env.sh python developer/gnav_dev.py doctor
scripts/gnav-env.sh python developer/gnav_dev.py config --config configs/eval.yaml backend=cpu env.n_envs=2
```

先预测最后一条命令是否启动仿真，以及 `eval.n_episodes`、`backend`、`env.n_envs` 的值。预期：工作台只读取、合并和预检配置；episode 数是 32，两个覆盖值分别是 cpu 和 2。完整配置还包含 dataclass 默认值。

读三个真实文件：`scripts/gnav-env.sh`、`configs/eval.yaml`（及其父配置）、`src/gnav/config.py`。当天验收是解释“当前目录”“解释器”“实际导入的源码”三者的区别。共享 conda 环境的 editable 安装可能仍指向原仓库；工作台入口为当前进程选择当前 worktree 的 `src`，不重新安装共享环境。

## 第一周：把研究直觉连接到工程证据

| 日期 | 任务（30–60 分钟） | 验收 |
|---|---|---|
| 第 1 天 | 环境检查、配置追踪 | 解释源码、解释器与配置来源，确认没有启动仿真 |
| 第 2 天 | 对 `env.n_envs=0` 预测错误，追踪预检，再试合法输入 | 区分 YAML 语法、类型与领域规则；解释退出码 |
| 第 3 天 | 在 `apply_overrides` 设断点，跟踪 `env.n_envs=2` | 解释 `parts`、`node`、deepcopy 的作用，定位第一次偏离预期的位置 |
| 第 4 天 | 做配对比较教学 lab，自己实现核心计算 | 区分配对差值和未配对均值；能说明有效样本与缺失记录 |
| 第 5 天 | 读 GAE lab 的预测题与 starter，不急着看参考实现 | 手算一个 termination 和 truncation 的不同 target，写出反例 |

断点调试先核对入口、Python 与工作目录。VS Code 支持变量检查和逐步执行，Python 调试类型为 `debugpy`；若当前图形调试未配置，先完成文本追踪再补交互操作。[VS Code 官方 Python 调试文档](https://code.visualstudio.com/docs/python/debugging)

## 当前教学包如何使用

**本包实际提供的是近期训练底座：开发检查器、配对比较、GAE、动力学识别、observation 边界教学实验，以及 Genesis 物理探针与操作说明。** 后面 12 周中的完整 PPO 学习系统、学习表示、多步世界模型、真机迁移、API 与前端是未来作业，未在本包中全部实现。可以依照下面顺序独立开始；长程研究仍需论文、真实实验和同行反馈。

建议顺序：环境/配置检查 → 配对比较 → [物理探针](labs/physics.md) → [observation 边界](labs/observation.md) → [GAE](labs/gae.md) → [识别实验](labs/identification.md)。物理探针入口是 `developer/physics_probe.py`，按其说明查看参数与执行条件；这与无需启动仿真的纯教学 lab 分开。

先读各 lab 的任务与预测题，再按其说明选择 starter；普通运行可用于查看参考演示：

```bash
scripts/gnav-env.sh python -m developer.labs.paired_comparison.run
scripts/gnav-env.sh python -m developer.labs.gae.run
scripts/gnav-env.sh python -m developer.labs.identification.run
scripts/gnav-env.sh python -m unittest developer.labs.observation.test_contract -v
scripts/gnav-env.sh python -m unittest discover -s developer/labs -p 'test_*.py' -v
```

练习核心实现时，按各 lab 的说明设置 `LAB_IMPLEMENTATION=starter`，显式选择学生版本。starter 中尚未完成的函数和对应失败是学习状态，不能写成参考实现失败。每次运行应说明用的是哪一个版本。

这些轻量实验解决定义、边界和反例，不证明 Genesis 场景或学习算法的端到端表现。物理与 observation 练习按其独立说明操作；是否真正执行了 Genesis、使用了什么设备、覆盖了哪些边界，以运行记录为准。

## 前 12 周：形成一个可检查的具身学习研究系统

每周至少用一次上面的八项学习协议。下面表格中的“交付”指你未来完成的练习；涉及新仿真、研究家族或冻结内容时，继续遵守仓库当前约定。

| 周 | 核心问题与学生实现 | 预测/基线/反例 | 交付与验收 |
|---|---|---|---|
| 1 | 工作树、配置、调试与配对比较 | 同一配置的覆盖顺序；错误源码路径；配对与未配对对照 | 能用证据说明运行了什么，完成一个小差异与review |
| 2 | Genesis 场景与物理语义；编写最小解析 oracle | 自由落体或受限运动解析值；时间步改变；无意的瞬移/速度重置 | 一份单位、步长与误差报告；只验证选定场景，不泛化至所有接触 |
| 3 | 合法 observation 与历史状态边界 | 隐藏真值改变、合法可见信息不变时策略输入应不变；reset 后不带旧历史 | 亲手实现观测投影/历史更新；泄漏反例可被测试抓住 |
| 4 | GAE 的 bootstrap 与 trace 边界 | termination 不 bootstrap；外部 truncation 使用最终观测值；trace 不串入新 episode | 手算例子、独立实现、对错误 mask 的反例；解释 rollout cut 的处理 |
| 5 | 从数学到 PPO 更新 | ratio=1、clip 两侧、旧 log-prob 固定；错误重新计算 old-policy 概率 | 独立实现 clipped objective 与有限输入测试；与最简单策略梯度基线比较 |
| 6 | 一个最小端到端学习闭环 | 固定环境/奖励/数据预算；随机策略与简单可解释策略；错 reward/reset 对照 | 阅读并解释数据流，记录 learning curve、评估与失败案例，区分吞吐和学习效果 |
| 7 | 动力学识别：哪些参数可以从哪些输入恢复？ | 不充分激励、混淆参数、噪声与有限观测；已知动力学 oracle | 完成 identification lab，明确可识别量、不可识别量和所需干预 |
| 8 | 表示与记忆到底增加了什么？ | 无记忆、手工充分统计、学习 recurrent 表示；历史交换/时间打乱反例 | 预先定义一个依赖历史的任务，固定训练预算，报告控制与失败 |
| 9 | 一步模型与多步世界模型 | 一步误差小未必多步稳定；无动作输入模型、常数预测与真实转移基线 | 实现小规模 action-conditioned 模型；报告预测时域、误差增长与数据覆盖 |
| 10 | 学到的模型能支持什么决策？ | 预测指标改善不必然改善控制；真实模型、学习模型与无模型对照 | 定义一个可测决策用途，控制模型误差与策略变化；拒绝仅凭 latent 图宣称理解 |
| 11 | 跨动力学与 sim-to-real 的验证设计 | 已见范围插值、范围外外推、传感延迟与动力学失配分开 | 保留未见条件；设计验证/失败边界；真机尚未运行就明确写“迁移假设” |
| 12 | 研究问题审查与可交付系统 | 最强简单基线、负结果、替代解释、已有工作 | 同伴用文档重现最小验证；提交研究问题备忘录与工程交接，允许结论是“不值得继续” |

第 2 周先用小场景理解 Genesis 的初始化、实体、build 与 step 语义，再决定批量规模。官方示例帮助定位 API，但你的当前安装版本与本地测试决定可运行命令。[Genesis 官方入门](https://genesis-world.readthedocs.io/en/latest/user_guide/getting_started/hello_genesis.html)

第 4 周将 GAE 的数学定义与工程边界拆开学习。GAE 用折扣 TD 残差估计 advantage；实际实现还必须明确 episode 与 buffer 的切分。[GAE 原论文](https://arxiv.org/abs/1506.02438) 外部时间限制导致的 truncation 通常保留 bootstrap；MDP 中真实的有限时域终止属于另一种语义，不能看到“时间到”就机械套用同一个规则。[Gymnasium 官方时间限制说明](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)

第 5 周从固定旧策略数据理解 PPO 的多轮优化与 clipped surrogate，而不把每个 actor-critic 都称为 PPO。[PPO 原论文](https://arxiv.org/abs/1707.06347) 当前 `src/gnav/experiment/train.py` 明确标注为 test-grade recurrent A2C + GAE，并说明把 truncation 当 terminal 的简化；读它是审计练习，课程没有据此声称已实现成熟 PPO，也不静默改写历史训练行为。

第 8–10 周可沿 `src/gnav/learning/interfaces.py` 追踪 encoder → belief → policy/value 和 latent dynamics。注意接口名称不能证明语义：`LatentDynamics.imagine` 的默认实现是从同一个 belief 对每个 action 作一步预测，不能只凭方法名就当作递归多步 rollout。你应先写目标定义，再决定实现应该满足什么。

## 一个 lab 的研究笔记模板

```text
问题：
预测（运行前，含边界）：
数学定义 / shape / 单位 / 时序：
学生核心实现文件：
独立 oracle 和手算例子：
只改变的因素、保持固定的因素：
简单基线、故意错误基线、反例：
实际命令 / 代码版本 / 配置 / seed：
观察到的结果：
支持、反驳、仍无法区分的解释：
参考解答比较后的修正：
下一次最便宜且最有区分力的实验：
```

例如“有记忆策略更好”至少存在多种解释：任务确实需要历史；模型容量更大；训练预算不同；reset 泄漏；观测含隐藏真值；特定 seed 偶然更好。先定义怎样逐个排除，再扩大模型。

## 产品交付能力作为外层逐步加入

每四周可用一次 1–2 小时整理，让同伴使用你的研究系统。先交付稳定 CLI、配置、摘要和清晰失败信息；需要浏览器协作后，再添加一个小的只读 run 检查界面。

| 外层能力 | 具体用法 | 验收 |
|---|---|---|
| Python 类型与数据契约 | 为实验摘要声明单位、缺失值与版本 | 损坏记录有明确错误，缺指标不显示为 0 |
| FastAPI / Pydantic | 通过允许的 run ID 查询摘要 | 正常、404、非法参数有测试；不接受任意文件路径 |
| SQL | 储存 run 元数据和查询索引 | 重复导入可控，结果可追溯回原文件，备份可恢复 |
| TypeScript / React | 展示列表、详情、错误与证据缺失 | loading/empty/error/success 均可使用，类型与运行时校验分清 |
| CI / 容器 / 日志 | 让开发工具和展示服务可重建、可诊断 | 区分 CPU 检查与 GPU 集成验证；报告真实运行记录 |
| AI 摘要与评估 | 生成有字段出处的研究摘要 | 不编造结果、不把差异变成因果；与确定性模板比较事实、成本和延迟 |

这些是你的全栈 / AI 工程师能力储备，不替代当前研究主线，也不表示这些服务已在本次部署。FastAPI/Pydantic 用于接口与输入验证；TypeScript/React 用于类型表达和 UI 状态。[FastAPI 官方教程](https://fastapi.tiangolo.com/tutorial/)、[Pydantic 模型文档](https://docs.pydantic.dev/latest/concepts/models/)、[TypeScript 手册](https://www.typescriptlang.org/docs/handbook/intro.html)、[React 入门](https://react.dev/learn)

## 三年路线：以独立判断与真实责任升级

| 阶段 | 重心 | 应留下的证据 |
|---|---|---|
| 第 1–3 个月 | 研究数据流和工程边界 | 上述 labs；可以解释和调试一个最小具身学习系统；一份同伴可运行交接 |
| 第 4–6 个月 | 比较候选问题，缩小研究方向 | 2–3 份问题备忘录：定义、已有工作、简单基线、最小反例、否决条件；不预先承诺 novelty |
| 第 7–12 个月 | 一条方向形成可复核成果 | 经过独立检查的实验与负结果；稳定评估协议；同伴 review 和一次跨人复现 |
| 第 13–18 个月 | 一个关键方向形成深度 | 例如表示、识别、世界模型或迁移中的一个；能测量收益与限制，解释替代方案 |
| 第 19–24 个月 | 承担协作系统的使用责任 | 实习/合作/开源/实验室平台中的真实交付；用户反馈、故障恢复、版本与数据迁移记录 |
| 第 25–30 个月 | 研究贡献与工程能力分别呈现 | 论文/研究说明与系统演示；清楚区分本人贡献、团队贡献、已验证和未验证结论 |
| 第 31–36 个月 | 匹配目标团队并补差距 | 按当时岗位要求选择作品，练研究讨论、系统设计和独立编码；围绕反馈补关键短板 |

每半年整理一次：谁提出了问题、你做了什么判断、交付了什么、别人怎样使用、什么地方失败、你如何修正。科技公司岗位会变化，以申请时真实团队需求校准；扎实研究、可靠系统和清晰协作是可以持续积累的证据。

博士研究和工程交付可以共享系统，但评价要分开。研究贡献回答“获得了什么新知识”，工程交付回答“谁能可靠地使用它完成什么”。不要为了展示现代技术栈牺牲研究问题，也不要用论文方向代替维护和交接能力。

## 每四周一次自测

打分：0 = 不会；1 = 依提示完成；2 = 可独立完成；3 = 能解释并处理变化。每个分数附一个真实文件、差异或实验记录，没有证据就先不升级。

| 能力 | 自测题 |
|---|---|
| 环境与版本 | 在两个 worktree 中说明实际导入的源码，定位错用旧代码的问题 |
| 数据流 | 从 action、reward、term/trunc 到 buffer、advantage 和 loss，解释每一项时序 |
| 信息边界 | 构造隐藏真值变化而合法历史相同的例子，检查学习输入是否泄漏 |
| 数学与实现 | 手算一个边界，然后写出能打败故意错误实现的测试 |
| 实验判断 | 列出一个惊喜结果的三种替代解释，设计最便宜的区分实验 |
| 调试与测试 | 用断点找第一次偏离；解释轻量测试没有证明什么 |
| 设计与交付 | 半页说明接口、依赖、失败与恢复，让同伴独立运行 |
| AI 协作 | 审出 AI 的错误假设，独立解释最终代码与证据 |

第 4 周优先让环境、数据流、调试达到 2；第 12 周希望八项达到 2。达不到就重复对应边界练习，不靠增加框架数量补偿。

## 与 AI 协作：先帮助理解，再帮助实现

> 教练模式：我先写出这个边界的预测和数学定义。请给一个最小反例和两个分层提示，暂时不要给完整核心实现。

> 结对模式：这是我的实现和手算 oracle。请帮我检查 shape、时序、reset 和信息边界，并区分确定的 bug 与待验证的猜测。

> 评审模式：这是 diff 和实验记录。请优先寻找替代解释、控制变量缺失、错误 baseline 和证据不足，不要替我包装 novelty。

每周至少 30 分钟关闭自动补全，独立完成核心函数或排错，然后请 AI review。参考解答应该帮助你核对定义，不应跳过预测和失败过程。

## 学习资源按问题取用

每次只为当前卡点读一个官方页面，再用到真实代码。Git worktree 用于隔离不同任务目录；本机 Python 环境仍需单独确认。[Git 官方 worktree 文档](https://git-scm.com/docs/git-worktree)

未来给独立 CPU 工具采用 uv 时，先理解 `pyproject.toml`、项目环境和锁文件的关系，独立验证后再考虑迁移既有环境。[uv 官方项目结构](https://docs.astral.sh/uv/concepts/projects/layout/) CI 先覆盖无需 GPU 的工具；工作流存在不等于远端已通过。[GitHub 官方 Python CI 文档](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) 容器可封装应用和依赖，但不自动消除主机 GPU/驱动条件。[Docker 官方镜像说明](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/)

日常操作和故障排查见 [工程手册](engineering-handbook.md)。
