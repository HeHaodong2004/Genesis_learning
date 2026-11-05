# 环境、工作树与断点调试

## 先认清四个东西

| 名称 | 这里的实例 | 为什么要区分 |
| --- | --- | --- |
| 仓库 | Genesis 的 Git 历史 | 存放代码与版本 |
| 工作树 | `genesis-developer-workbench/` | 这次实际编辑的文件 |
| Python 环境 | `~/miniforge3/envs/genesis-research/` | 提供解释器和依赖 |
| 运行产物 | `runs/某次运行/` | 数据与证据，不是程序源码 |

两个工作树可以共享解释器，却不能假定解释器会自动导入当前目录的源码。现有环境安装的 editable `gnav` 指向原仓库。工作台 CLI 在进程内把自己所在工作树的 `src/` 放到导入路径首部；这只对该进程生效。原科研脚本没有因此被自动修复或迁移。

## 五分钟环境检查

```bash
pwd
git branch --show-current
git status --short
make doctor
make config
```

原机工作树的分支是 `codex/developer-workbench`；从 GitHub 新克隆的默认分支是 `main`。代码来源应指向你当前目录下的 `src/gnav`（新克隆通常是 `Genesis_learning/src/gnav`），与 `doctor` 的 root 一致。如果失败，先保留第一条错误和退出码，别先重装 CUDA。`scripts/gnav-env.sh` 会清掉 ROS 的 `PYTHONPATH` 和 `AMENT_PREFIX_PATH`，所以单纯在外面设置 `PYTHONPATH` 不能解决这里的工作树问题。

`doctor` 读取依赖版本元数据，不加载 Torch/Genesis、不测试 GPU。缺少可选编辑器工具与“仿真环境坏了”不是同一个诊断。

## 配置 VS Code

1. 从本工作树执行 `code .`。如果 GUI 不可用，终端命令仍可使用。
2. 需要时安装仓库建议的 Python、Python Debugger、Pylance 扩展。
3. 命令面板运行 `Python: Select Interpreter`，选择 Genesis 环境中的 Python。已有工作区选择可能覆盖 `defaultInterpreterPath`，因此以界面实际选择和 `doctor` 输出核对。
4. 打开 `developer/gnav_dev.py`，找到处理 `config` 子命令的函数。在调用配置加载或检查处设置断点。
5. 在“运行和调试”选择 **Genesis: debug config (no simulation)**，按 F5。
6. 暂停后观察配置路径和 overrides，单步进入 `src/gnav/config.py`，观察 `env.n_envs` 从 YAML 值变成 2。
7. 使用调试控制台观察 `sys.executable`、`sys.path[0]`。这是观察，不要在调试控制台启动训练。

调试配置用进程级环境隔离 ROS，并隐藏 GPU。它不会运行 `gnav-env.sh`，因为调试器直接启动选定 Python；因此正确选择解释器很重要。F5 的图形交互需在你的 VS Code 中完成；本次终端验证不能替代你的 GUI 验收。

[VS Code 官方调试文档](https://code.visualstudio.com/docs/python/debugging)说明 `debugpy` 启动配置；[Python 设置参考](https://code.visualstudio.com/docs/python/settings-reference)说明解释器与测试发现设置。这里将测试发现限定为 `developer/tests`，保留原科研测试的独立运行方式。

## 各层测试分别回答什么

| 命令 | 回答的问题 | 不回答的问题 |
| --- | --- | --- |
| `make doctor` | 当前进程在用哪份代码和环境 | GPU 是否能运行 |
| `make test` | CLI 的错误输入和正常输入是否符合契约 | 物理仿真是否可信 |
| `make lab` | 教学参考实现是否符合练习契约 | 原生产统计函数是否已修复 |
| `make check` | 上述开发单测、参考练习、语法与配置样例是否通过 | 全仓库质量、GUI、远端 CI、科研结论 |
| 原仓库的仿真测试 | 特定后端的物理/接口行为 | 没测过的模型、工况与科学命题 |

如果要检查 CPU 仿真，请先回到项目当前执行计划确认范围、输出目录、资源和已有任务。新开发者的第一天不需要运行全仓库测试或历史实验脚本。

## 日常开发循环

```bash
git status --short
# 写下本次的输入、输出与验收条件，再编辑一个小范围改动
make test
git diff --stat
git diff -- path/to/changed-file
make check
```

新增文件在提交前是 untracked，普通 `git diff` 不显示它们。先用编辑器查看，或 `git diff --no-index /dev/null 新文件` 查看；这个命令有差异时退出 1 是正常行为。只有理解变更后才选择暂存与提交，不要用 `git add .` 将研究数据混入工程改动。

## CI 的位置

`.github/workflows/developer-check.yml` 给出轻量 GitHub Actions 门禁：只安装 PyYAML，在 Python 3.11/3.12 跑开发检查，不安装仿真依赖。它在你将文件纳入受评审分支并创建相应 PR 后才可能运行；这里没有推送，也没有证明 GitHub 账户、权限或分支保护已配置。

本地 `make check` 使用现有环境；云端最小依赖环境用于暴露对本机安装状态的意外依赖。两者应运行同一个 `developer/check.py`。当你增加新依赖，要同时解释必要性并更新最小依赖文件，不能只让“自己的电脑能跑”。

## 历史环境记录不是可迁移锁文件

`environment/requirements.lock.txt` 是原工作站的历史环境记录，包含本机 `file:///home/conda/...` 来源，不能直接当作新机器的可迁移安装清单。轻量训练使用根目录README给出的venv命令和 `developer/requirements-ci.txt`；已有Genesis环境不需要重装。物理环境迁移是单独任务，应先核对平台、驱动和可用包版本。
