# Genesis 现代机器人研究者训练包

**从这里开始。** 这是围绕现有 Genesis 研究代码制作的中文开发工作台和主动练习包。它保留你的数学与规划基础，补上现代开发、仿真验证、学习算法实现与实验交付。无需重新安装 Genesis，也不需要持续订阅 AI 才能运行这些本地文件。

## 网页学习入口

打开 [Genesis 研究者工坊](https://genesis-robotics-learning.hehaodong2004.chatgpt.site)，从第 1 章开始。网站已发布，默认仅站点所有者可访问，需要登录对应账号。

7 章、46 个步骤带你依次完成环境与调试、配对评估、Genesis 物理验证、观测边界、GAE、系统辨识和独立交付。每步有命令、预期现象、源码和验收问题；遇到不懂的代码，可以复制带上下文的问题给其他 AI。命令在本机终端执行。进度和笔记保存在当前浏览器，请定期导出 JSON 备份。

网站源码完整保存在 [website/](website/README.md)，无需 API key 或在线 AI 订阅。在线托管与本地文件是两回事；若在线入口不可用，克隆后可直接启动本地网站：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory website/dist
```

然后打开 `http://127.0.0.1:8765`。执行代码之外，每章还要求你预测、修改关键实现并解释结果，完成标记是自评记录。

## 从 GitHub 下载后开始

```bash
git clone https://github.com/HeHaodong2004/Genesis_learning.git
cd Genesis_learning
make doctor
make check
```

以上命令适用于已有 `genesis-research` 环境的工作站。全新机器先只跑轻量练习：

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r developer/requirements-ci.txt
.venv/bin/python developer/check.py
```

也可使用 Python 3.12。此轻量环境不安装 Genesis/Torch，不能运行物理探针；物理练习使用你已经验证的科研环境。克隆目录里的原 `scripts/train.py` 等用于跟读，单独执行前须核对实际导入路径；工作台入口已显式选择本目录源码。

## 在原工作站上开始

```bash
cd /home/haodong/workspace/projects/genesis-developer-workbench
make doctor
make check
code START_HERE.md
```

这台机器已经有相应 Python 环境。GitHub 下载版进入自己的克隆目录即可；环境位置不同请设置 `GNAV_ENV_PREFIX`。新机器没有环境时，先读 [环境说明](docs/developer/setup.md)，轻量练习只需要 Python 3.11/3.12 和 PyYAML，物理仪器另需已安装 Genesis/Torch。不要在还没核实环境时运行历史安装脚本。

1. 看 `doctor` 中的解释器和 `gnav_source`，用自己的话解释“环境”和“工作树”的区别。
2. 看 `check`，理解它验证开发工具和参考解，**不是证明你已经会做，也不是全仓库科学验证**。
3. 打开 [第一个贡献](docs/developer/first-contribution.md)，先写预测，再修改 starter。今天只做这一项。

## 按顺序跟练（约两周，可按实际掌握程度放慢）

| 顺序 | 任务与入口 | 必须亲手交付 | 可以前进的条件 |
| --- | --- | --- | --- |
| 1 / 第1天 | [环境与断点](docs/developer/setup.md) | 找到当前源码；在配置加载处停一次断点 | 能解释覆盖参数的实际执行路径 |
| 2 / 第2–3天 | [配对评估](docs/developer/first-contribution.md) | 修 starter、自己加边界用例、PR草稿 | 能解释重复ID、有效样本与差值方向 |
| 3 / 第4–5天 | [Genesis物理验证](docs/developer/labs/physics.md) | 独立计算轨迹误差；位置重置故障 | 能区分连续模型、离散误差、仿真实测 |
| 4 / 第6天 | [观测边界](docs/developer/labs/observation.md) | 修输入接口、画信息流、构造反例 | 能说明schema为什么不能保证无泄漏 |
| 5 / 第7–9天 | [GAE](docs/developer/labs/gae.md) | 手算优势；实现两个不同的mask | 能解释truncation bootstrap和reset污染 |
| 6 / 第10–12天 | [辨识](docs/developer/labs/identification.md) | 实现2×2最小二乘；比较激励/holdout | 能给出低训练误差但参数不可辨识的反例 |
| 7 / 第13–14天 | [工程手册](docs/developer/engineering-handbook.md) | 给同学复现；写一次失败诊断和交接 | 对方能按记录重现，不靠你的口头补充 |

日程是建议，不是效率承诺。每项至少留一页自己的预测、实现、结果和反思。参考答案已提供，但先对 starter 实现；默认测试绿只说明参考实现通过。各教程给出显式 `LAB_IMPLEMENTATION=starter` 命令，未完成时失败是预期行为。

## 后续能力主线

读 [12周与三年路线](docs/developer/learning-path.md)。之后逐步做：真实执行器/传感器验证 → 自己的PPO → 跨seed评估 → 预测模型/表示 → 闭环控制 → 一次受控sim-to-real研究。后期项目是有验收标准的作业，不是假装已经实现的完整课程。你可以随博士方向变化更换平台和题目，保留这条验证方法。

已有 `src/gnav/experiment/train.py` 是参考 recurrent A2C，不是完整PPO。旧GPU micro-labs的性能数字也不作为本包的验证结果。这里不会替你重建Falcon、宣布自我建模的原创性或预定博士课题。

## 怎么知道自己真的会了

关掉参考答案，给自己一个新输入或故障。你应能先预测、定位代码、写一个能失败的测试、实现修复、解释结果和未覆盖范围。能够运行命令只是第一步。真正研究独立性还需要原论文、真实实验、外部问题反馈和同行质疑；路线里会把它们安排成具体交付。

## 工作台入口

- [工具与文档索引](docs/developer/README.md)
- [实际验证与边界](docs/developer/VALIDATION.md)
- [中文交接](docs/developer/HANDOFF_ZH.md)
- [每日记录模板](docs/developer/templates/daily-log.md)
- [交接与AI任务模板](docs/developer/templates/handoff.md)
- [可选：API/前端产品支线](docs/developer/product-brief.md)

默认检查不启动GPU。物理实验显式执行并写新报告。原工作环境、科研结果和预注册文件保持原状。训练包与长期论文研究分别管理，避免一次学习改动悄悄改写旧结论。

## GitHub 教学快照说明

本仓库是独立训练包：保留跟读所需的原始源码、配置与入口，不包含原项目Git历史、研究结果、历史诊断模型、完整科研测试/实验目录或个人记忆。请运行 `make check` 而非把它当成原研究仓库的完整复现。原研究状态 `STATUS_FOR_CLAUDE.md` 只在原工作区读取。已有源码来自本机Genesis研究库基线 `181c8f6`，用于本人的学习与开发。
