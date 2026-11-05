# 练习：观测边界能否被反例击穿？

**问题**：策略表现很好，是否只是读到了部署时根本看不到的状态？你熟悉这个研究风险；本练习训练如何把它写成能自动失败的软件契约。

这是一份 30–60 分钟的纯 Python 小练习，不复制 Genesis 的完整传感器模型。这里 `rays(3), goal(2), proprio(2)` 是教学尺寸；真实 `gnav` 的尺寸和字段以 `src/gnav/sim/env.py` 的 `OBS_KEYS` 与 `check_obs` 为准，不可直接替换。

## 先预测

记真实状态为 s，合法传感器为 o=h(s)，策略为 a=π(o)。如果 h(s₁)=h(s₂)，一个无历史、确定性的合法策略必须给出相同动作。对有记忆的策略，需要整个合法观测与动作历史一致；单步观测相同不够。

写下三个预测：隐藏障碍坐标变化、合法测距变化、下一帧原地覆盖 buffer，各应如何影响已经构造的本帧策略输入？答案应分别是“不变”“允许变化”“不变”。这不是物理世界变化后传感器一定不变，而是用于隔离通道的软件干预。

## 你亲手实现

打开 `developer/labs/observation/starter.py`。只实现 `policy_input`，包括显式字段选择、尺寸和有限数值检查、独立数据副本。不要改测试来让它变绿。

```bash
# 故意失败，提示泄漏与buffer别名问题
LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest \
  developer.labs.observation.test_contract -v

# 修完同一个starter后重跑上式；参考答案的独立验证
scripts/gnav-env.sh python -m unittest developer.labs.observation.test_contract -v
```

我提供合成输入、测试和 `solution.py`；你实现数据边界，再自己增加一个“字段名称合法但值来自真值”的反例。后者不能单凭此处 allowlist 被识别：把隐藏坐标塞进 `proprio`，schema 仍可能通过。因此还需要检查传感器生产路径和信息来源。

## 接到真实工程

阅读 `src/gnav/sim/env.py` 中 `_compute_obs()`、`privileged_state()`、`step()`；画出 policy、critic、reward、evaluator 各拿到什么。允许训练 critic 使用特权信息与部署 actor 使用特权信息是不同的契约，不能用一个“完全不读真值”规则混为一谈。

下一项任务是在单独工作分支给实际 actor 输入加一次变形测试：固定合法观测与历史，只替换 oracle 辅助记录，actor 输出必须不变；再改变合法观测，确认测试不是靠输出常量蒙混过关。此包未替你修改训练器。

## 完成标准

全部 starter 测试通过；你能解释浅复制为何不够、schema 为何不是信息合法性证明，并能指出真实传感器生产和策略输入的代码位置。测试通过只证明这些有限软件干预，不能证明整个系统绝无泄漏。
