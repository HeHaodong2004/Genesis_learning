# 第一个可审查贡献：让实验比较先遵守数据契约

这节课把你熟悉的 episode、成功率、碰撞率，连到现代开发中每天会做的事：写清楚契约、复现问题、写回归测试、调试、做小修改、解释统计含义、交给别人审查。预计第一次需要 60–90 分钟；通过测试后，再用自己的话讲清楚为什么通过。

所有操作在新的 worktree 进行，运行代码只用 Python 标准库。练习没有启动 Genesis、没有训练模型，也没有修改原有研究结果。

```bash
cd /home/haodong/workspace/projects/genesis-developer-workbench
git branch --show-current
```

应看到 `codex/developer-workbench`。这里仍通过 `scripts/gnav-env.sh` 选择现有解释器并隔离 ROS 环境；练习模块不导入 `gnav`、Torch 或 Genesis。

## 1. 读真实代码，区分真实问题和教学故障

打开 [真实比较函数](../../src/gnav/experiment/evaluate.py)，找到 `paired_comparison`。它先按 `(env_id, episode_idx)` 建字典，再取 A、B 两组共同 episode，计算 **B − A**。当前函数已经正确使用这个方向，并过滤非有限差值。

真实问题是：同一组输入出现重复 episode ID 时，字典会用后面的行覆盖前面的行，调用者不知道发生了覆盖。当前 `n_paired` 记录共同 ID 数，却没有给出每个指标过滤非有限值后的有效样本数。这会让读结果的人难以判断各指标用了多少数据。

最小例子：A 同一 episode 的 `score` 先是 10、后是 100，B 为 13。悄悄覆盖后均值差会成为 −87；保留前行则是 +3。我们无法从这两行判断哪一个才正确，因此这节课选择 **发现重复就报错，让上游修复数据**，不代替研究者决定取第一行、最后一行或平均。

练习文件 [starter.py](../../developer/labs/paired_comparison/starter.py) 为了让你练习，还故意加入了方向颠倒、缺失值当 0、不区分有效样本的错误。它并不是生产函数的复制；不要把这些故意植入的错误写成对原仓库的 bug 指控。

## 2. 先写清“什么算正确”

本练习的契约如下。先看契约，再打开参考答案。

| 输入或输出 | 约定 |
|---|---|
| episode ID | `env_id`、`episode_idx` 都是非负整数，布尔值不算整数 |
| 重复 ID | A 或 B 中出现任何重复都报 `ValueError`，即使这个 ID 没有匹配上另一组 |
| 配对方式 | 按 ID 配对，输入行顺序不影响结果；只比较共同 ID |
| 差值方向 | 固定 `B − A`；A 为基线，B 为候选方案 |
| `n_paired` | 共同 episode ID 数，先于各指标缺失值过滤 |
| `unmatched_a/b` | 各组未在另一组找到的 ID 数 |
| 指标有效性 | 每个指标单独检查 A、B；缺失、`null`、字符串、布尔值、NaN、Infinity 均丢弃该指标的这一对；相减溢出也丢弃 |
| `n_valid / n_dropped` | 每个指标实际参与统计 / 被丢弃的配对数；两者之和等于 `n_paired` |
| `mean_diff` | 有效差值的算术平均；无有效样本时为 `None`，JSON 中为 `null` |
| `ci95` | 至少两对时，正态近似半宽 `1.96 × s / √n`，其中 `s` 是样本标准差；少于两对时为 `None` |
| 输入保护 | 函数不能修改传入的行 |

对成功率，正的 B−A 通常代表提高；对碰撞率，负的 B−A 通常代表降低。对 episode 长度，变短可能是更快到达，也可能是更早碰撞，要结合成功率等指标解释，不能只看正负。

`ci95` **不是上下界本身**。上下界是 `mean_diff ± ci95`。它是正态近似，不能保证任意样本量、相关结构、选择方式下都有 95% 覆盖率。小样本、同一环境的相关 episode、筛选后的结果和多重比较，都需要独立讨论统计设计。这里测试的只是实现是否遵守已约定公式。

原函数在不足两对时把标准误设为 0；本练习选择 `null` 来表达“不能估计”，属于**新的接口契约**。若未来迁回生产代码，必须说明兼容性、更新调用方和测试，不能悄悄修改指标定义、置信方法或历史表格。另一处 [analysis/stats.py](../../src/gnav/analysis/stats.py) 的 `paired_diff_ci(a, b)` 明确约定 A−B；不同 API 可以有不同契约，不能只凭函数名判断方向。

## 3. Red：运行一个必须失败的测试

只对这条命令选择 starter，不全局 `export`，防止以后把未完成练习混入常规检查：

```bash
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.paired_comparison.test_contract.PairedComparisonContract.test_duplicate_id_is_rejected_on_either_side_even_if_unmatched -v
```

预期退出码为 1，看到 `ValueError not raised`，A 和 B 两个子案例都失败。这个红色是练习的起点，不表示 Genesis 部署坏了。

再看方向错误，失败信息应显示期望 `3`，实际是 `-3`：

```bash
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.paired_comparison.test_contract.PairedComparisonContract.test_direction_is_b_minus_a -v
```

先用一句话记录：触发条件是什么、现在发生什么、应该发生什么。不要直接要求 AI “把测试变绿”；让它先解释失败原因和计划改动边界。

## 4. Debug：用数据验证你的理解

可以在编辑器给 `starter.py` 的字典推导打断点，也可以使用内置调试器：

```bash
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m pdb -m unittest \
  developer.labs.paired_comparison.test_contract.PairedComparisonContract.test_direction_is_b_minus_a
```

在 `(Pdb)` 输入：

```text
b developer/labs/paired_comparison/starter.py:14
c
p rows_a
p rows_b
n
p indexed_a
n
p indexed_b
q
```

这组命令的目的：检查输入是否真的进入你以为的函数，然后看按 ID 建出的对象。在你修改文件后，断点行号可能变化；将断点移到 `indexed_a` 那行即可。

## 5. Green：只修改 starter，逐步通过契约测试

编辑 [starter.py](../../developer/labs/paired_comparison/starter.py)，保留公开函数签名和输出字段。可以提取小的辅助函数；无需新框架。

1. 在写入索引前检查 ID，发现重复时给出 A/B 标签与 ID。先让重复测试通过。
2. 修正差值方向；按指标分别过滤缺失、非数字、非有限值，记录有效数量。
3. 明确零个和一个有效配对的输出，避免 `NaN` 流进 JSON，也避免把无法估计的区间标成 0。
4. 跑完整练习套件，确认没有为了修一个案例破坏另一个。

```bash
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.paired_comparison.test_contract -v
```

完成后应为 `Ran 13 tests`、`OK`。测试包含重复 ID、错位顺序、每指标有效数、非有限输入、溢出、空集合、单样本、常量差值、输入不变和合成样例。

## 6. 用明确的 synthetic 数据验收

[synthetic.json](../../developer/labs/paired_comparison/fixtures/synthetic.json) 是手工编写的教学数据，**不是 Genesis 实验结果**。它有三个共同 episode，A/B 各有一个未匹配 episode，第三个 episode 的 A 长度缺失。

```bash
scripts/gnav-env.sh python -m developer.labs.paired_comparison.run --implementation starter
```

修复后输出应包含：

| 结果 | 预期 |
|---|---:|
| `n_paired` | 3 |
| `unmatched_a`、`unmatched_b` | 各 1 |
| 成功率 B−A 均值 | 2/3 |
| 碰撞率 B−A 均值 | −1/3 |
| 长度 B−A 均值 | −3 |
| 长度 `n_valid`、`n_dropped` | 2、1 |
| 长度 `ci95` 半宽 | 1.96 |

长度的两个有效差值是 −2、−4，均值 −3，样本标准差 √2，标准误 1，所以半宽 1.96。你应能独立复算这个数。

## 7. 参考答案与默认检查

卡住时先读 [测试](../../developer/labs/paired_comparison/test_contract.py) 的输入输出，再看 [solution.py](../../developer/labs/paired_comparison/solution.py)。它不是唯一可行解法。

```bash
LAB_IMPLEMENTATION=solution scripts/gnav-env.sh python -m unittest \
  developer.labs.paired_comparison.test_contract -v
scripts/gnav-env.sh python -m developer.labs.paired_comparison.run --implementation solution
```

未设置 `LAB_IMPLEMENTATION` 时，测试默认选择参考答案，所以未完成的 starter 不会让日常检查变红。**默认检查绿不代表你完成练习**；完成证据是显式选择 `starter` 的全部测试通过，并能解释每个字段。

这两个实现不导入生产科学模块。参考答案通过，证明此练习契约被满足，不代表原生产函数已经修复，也不替代完整研究回归测试。

## 8. Review：把修改变成别人能评审的贡献

查看自己的改动，避免改到科学模块、预注册或结果文件：

```bash
git status --short
git diff -- developer/labs/paired_comparison/starter.py
```

初次交付时整个 `developer/` 可能尚未被 Git 跟踪，此时 `git diff` 不会显示未跟踪文件，这是 Git 的正常行为。可以直接比较 starter 与参考实现：

```bash
diff -u developer/labs/paired_comparison/starter.py developer/labs/paired_comparison/solution.py
```

`diff` 不同返回 1，表示文件不同，不是测试失败。你的答案也不需要逐字等同参考答案。不要为了查看差异而执行 `git add .` 或提交整份研究输出。

写一段 PR 描述草稿，例如：

> 合成 episode 比较遇到重复 ID 时，原教学实现会覆盖数据；现在会报告输入侧和冲突 ID。指标按 B−A 计算，并分别报告有效配对数；不足两对时不输出区间估计。本次仅修改独立教学实现，未改变 gnav 科学代码或历史结果。验证：starter 的 13 个契约测试通过，合成样例长度差为 −3、有效配对 2。

请只在实际得到对应结果后写“通过”。暂时不用提交或 push；这里的目标是准备可审查的改动。

请审查者回答四件事：重复数据会不会静默丢失；方向和样本数是否可解释；异常值是否被明确计数；新统计契约是否会误导旧调用方。下一次真正集成到 `gnav`，从这个评审结果再设计小范围、向后兼容的改动与回归测试。

最后，不看答案回答：为什么不能直接用 `zip(rows_a, rows_b)` 配对？为什么 `n_paired=3` 不等于每个指标都有三个有效样本？为什么 `ci95=null` 和 `ci95=0` 含义不同？为什么运行原 `tests/` 可能初始化 Genesis，而这个练习不会？答得出来，比记住一串工具名更接近成熟开发者的日常能力。
