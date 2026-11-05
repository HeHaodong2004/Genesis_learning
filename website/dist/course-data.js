window.COURSE_DATA = {
  "lessons": [
    {
      "id": "setup",
      "title": "01 · 建立可信的开发入口",
      "subtitle": "先知道自己在运行哪份代码，再开始修改它。",
      "minutes": 45,
      "question": "同一个命令为什么可能运行到另一份工作树的代码？",
      "prerequisites": [
        "会使用终端和基本Python；不需要重新学机器人几何。",
        "准备Git、Python 3.11或3.12；已有Genesis环境优先沿用。"
      ],
      "docPath": "docs/developer/setup.md",
      "steps": [
        {
          "id": "clone",
          "title": "拿到一份可追踪的学习副本",
          "kind": "run",
          "body": "在你希望保存项目的位置打开终端，执行一次下面的命令。若已经克隆，直接进入现有 Genesis_learning 目录，不要重复clone。后续命令都从仓库根目录执行。网站不会连接你的终端或自动执行命令；把命令复制到本机终端。",
          "command": "git clone https://github.com/HeHaodong2004/Genesis_learning.git\ncd Genesis_learning\ngit status --short\ngit branch --show-current",
          "file": "",
          "expected": "新克隆通常显示main，git status没有输出。已有学习改动则应显示实际改动，不能为了让它干净而删除自己的文件。",
          "prompt": "我正在Genesis_learning课程第1章。请帮我解释仓库、分支和工作树三个概念，结合我粘贴的pwd、git status及分支输出，确认后续命令应该在哪个目录执行。不要让我清除未提交学习改动。"
        },
        {
          "id": "existing-env",
          "title": "路径A：沿用已有Genesis环境",
          "kind": "run",
          "body": "如果你在已经部署好Genesis的工作站上，选择此路径。默认环境位于 ~/miniforge3/envs/genesis-research；若你的环境在别处，只替换这个路径。执行后跳过下一步的“路径B”。不要因为要学习现代开发就升级Torch、驱动或重新安装Genesis。",
          "command": "export GNAV_ENV_PREFIX=\"$HOME/miniforge3/envs/genesis-research\"\nmake doctor",
          "file": "developer/gnav_dev.py",
          "expected": "ok为true；python.executable来自你的科研环境；gnav_source指向当前克隆目录的src/gnav。doctor只读元数据，不证明GPU或仿真健康。",
          "prompt": "我选择已有Genesis环境，正在运行make doctor。请根据下面的输出辨认解释器路径与gnav源码路径，解释二者为何不同；若失败，先定位路径/依赖原因，不要建议重装CUDA或替换工作环境。"
        },
        {
          "id": "light-env",
          "title": "路径B：新机器先运行轻量练习",
          "kind": "run",
          "body": "如果没有现成科研环境，选择此路径；已有环境且已完成路径A则跳过。本步骤只在当前目录新建 .venv 并安装PyYAML，不安装Torch/Genesis。将GNAV_ENV_PREFIX设为该环境后，后续同样可以使用scripts/gnav-env.sh。此变量只影响当前终端；新开终端要重新设置。物理章仍需要真正的Genesis环境。",
          "command": "python3.11 -m venv .venv\n.venv/bin/python -m pip install -r developer/requirements-ci.txt\nexport GNAV_ENV_PREFIX=\"$PWD/.venv\"\nmake doctor",
          "file": "",
          "expected": "可将python3.11换成python3.12。doctor的轻量检查应通过；缺少Torch/Genesis的提示在本路径是预期状态。若没有Python3.11/3.12，先安装其中一个，不要用旧版Python勉强通过。",
          "prompt": "我使用新机器的轻量.venv，环境只应该有Python3.11/3.12和PyYAML。请区分make doctor中的必需依赖失败与仿真依赖缺失提示，告诉我哪些课程现在能做、物理章还缺什么。不要把“元数据通过”说成GPU已经验证。"
        },
        {
          "id": "gate",
          "title": "运行开发门禁，理解绿灯的范围",
          "kind": "verify",
          "body": "选择好A或B其中一个环境后，运行整个轻量检查。它包括开发工具和四套参考解的测试，不会启动Genesis。原仓库tests/conftest.py会自动初始化仿真，所以本包有独立developer测试入口。记录你实际看到的测试数量与版本。",
          "command": "make check",
          "file": "",
          "expected": "当前交付包含44个工具测试和56个参考练习测试，共100个。全部通过说明参考实现满足这些契约，不表示你的starter已实现，也不表示整套研究结论得到验证。",
          "prompt": "我在运行make check。请先读失败测试名称和第一条异常，区分环境问题、参考代码问题、或我自己的修改。解释这些检查覆盖和不覆盖什么；不要把100项测试通过泛化成完整机器人系统可靠。"
        },
        {
          "id": "config-predict",
          "title": "预测一次配置覆盖和一次错误输入",
          "kind": "predict",
          "body": "先读load_config与apply_overrides，预测两条命令的行为：env.n_envs=2应该改哪个层级？env.n_envs=0为什么应在启动仿真之前被拒绝？第二条是故意无效输入，用于确认失败路径。配置检查器在外围加预检，原训练脚本尚未自动使用它。",
          "command": "scripts/gnav-env.sh python developer/gnav_dev.py config --config configs/eval.yaml backend=cpu env.n_envs=2\nscripts/gnav-env.sh python developer/gnav_dev.py config --config configs/eval.yaml env.n_envs=0 --json",
          "file": "src/gnav/config.py",
          "expected": "第一条输出resolved config，backend=cpu、n_envs=2；第二条输出结构化错误并退出2。退出2在这个无效输入案例中是正确结果。",
          "prompt": "请用我自己的预测和下面两次配置输出，带我跟踪YAML继承、命令行覆盖和预检的执行顺序。重点解释dataclass类型注解为何不自动完成运行时验证；先让我指出被修改的字段，不直接替我总结。"
        },
        {
          "id": "debug",
          "title": "亲手停一次断点",
          "kind": "implement",
          "body": "在VS Code打开仓库；选择同一个Python解释器。在developer/gnav_dev.py调用配置解析的位置，或src/gnav/config.py的apply_overrides设置断点。选择“Genesis: debug config (no simulation)”按F5，查看ov、parts、node以及最后的n_envs。没有GUI时可使用下面的pdb入口；在(Pdb)中用b src/gnav/config.py:209设断点，再用c、n、p观察。",
          "command": "scripts/gnav-env.sh python -m pdb developer/gnav_dev.py config --config configs/eval.yaml backend=cpu env.n_envs=2",
          "file": "src/gnav/config.py",
          "expected": "你能看到覆盖参数如何逐层进入字典，而不是只看到终端最终JSON。调试器会等待输入，不是卡死；用q退出。",
          "prompt": "我在配置加载断点处停住了。请根据我贴出的局部变量和代码行，每次只问我下一行会改变什么，然后核对我的预测。不要跳过单步观察直接给完整答案。"
        },
        {
          "id": "setup-reflect",
          "title": "留下第一份可交接记录",
          "kind": "reflect",
          "body": "写下：所选环境路径、实际gnav源码路径、成功命令、故意失败命令及其原因。解释为什么editable安装可能指向原仓库，以及为什么只在shell设置PYTHONPATH在本项目会被wrapper清掉。通过本章后，保留当前终端环境变量并进入第2章。",
          "command": "git status --short",
          "file": "",
          "expected": "你能不看答案区分“解释器来自哪里”和“代码来自哪里”，并说明make check没有运行GPU。完成A或B一条路径即可，不要求把两种环境都装一遍。",
          "prompt": "请对我这段环境与导入路径解释做一次口试：给我一个“命令运行成功但导入错工作树”的情景，让我说出诊断步骤。不要评价工具数量，检查我是否能解释实际执行路径。"
        }
      ],
      "gates": [
        "完成环境路径A或B之一，并能解释doctor输出。",
        "make check通过；记录测试范围，而非只记住绿灯。",
        "完成一次配置断点观察，并解释一次预期失败。"
      ]
    },
    {
      "id": "paired",
      "title": "02 · 让实验比较先遵守数据契约",
      "subtitle": "从一个重复episode开始，完成red → debug → green → review。",
      "minutes": 90,
      "question": "为什么一个看似合理的均值，可能只是字典悄悄覆盖了数据？",
      "prerequisites": [
        "完成环境章。",
        "理解episode、均值、样本标准差；不需要启动仿真。"
      ],
      "docPath": "docs/developer/first-contribution.md",
      "steps": [
        {
          "id": "paired-contract",
          "title": "阅读契约，辨认真实问题和教学故障",
          "kind": "read",
          "body": "生产比较函数固定计算B−A并过滤非有限差值；真实缺口是重复(env_id,episode_idx)会被字典覆盖，以及没有逐指标有效样本数。这里的starter还故意植入方向颠倒、缺失值当0等错误，它不是生产代码的原样复制。先读测试：重复ID必须报错，即使没有匹配；缺失/布尔/字符串/NaN/Inf只丢弃该指标的该对。",
          "command": "",
          "file": "developer/labs/paired_comparison/test_contract.py",
          "expected": "能口述n_paired与每个指标n_valid的区别；不能把教学故障写成原仓库已经存在的全部bug。",
          "prompt": "我在配对评估lab，契约是按episode ID配对、B−A、拒绝重复、逐指标过滤。请帮我从测试提取输入输出契约，尤其区分n_paired与n_valid。先问我一个可能被字典覆盖的例子，不直接贴solution。"
        },
        {
          "id": "paired-predict",
          "title": "先用三行数据预测后果",
          "kind": "predict",
          "body": "A中同一ID先记录score=10、后记录100，B中该ID为13。先写：取首行差值是多少？取末行是多少？为什么“自动挑一个”不是工程修复？再算差值为−2和−4时的均值与正态近似半宽。少于两对时，无法估计样本方差，应输出null，而不是冒充测得零不确定性。",
          "command": "",
          "file": "",
          "expected": "首行B−A为+3，末行为−87；两对差值均值−3，半宽1.96。这个正态近似不保证小样本或任意分布的95%覆盖。",
          "prompt": "请核对我的手算，不要先给答案。我会解释重复ID应拒绝而不是平均的理由，以及1.96*s/sqrt(n)的含义。请指出我是否把“缺少不确定性估计”和“估计的不确定性为零”混淆了。"
        },
        {
          "id": "paired-red",
          "title": "显式选择starter，观察失败",
          "kind": "run",
          "body": "执行学生版本测试。初始失败是设计好的学习状态：先定位重复ID测试，再看方向、缺失值和样本数。不要运行默认参考测试后就宣布自己修好了。把第一条失败的输入、期望和实际输出记下来。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.paired_comparison.test_contract -v",
          "file": "developer/labs/paired_comparison/starter.py",
          "expected": "尚未修改的starter会有失败/错误，退出非零。若初始全绿，先检查是否真的加了LAB_IMPLEMENTATION=starter。",
          "prompt": "我运行了显式starter测试，下面是失败日志与我的starter。请只选择第一个有诊断价值的失败，帮我构造最小复现，先给一个提示；不要重写整个函数或让我修改断言迎合代码。"
        },
        {
          "id": "paired-implement",
          "title": "只实现一个小函数",
          "kind": "implement",
          "body": "修改paired_comparison：先验证ID且拒绝重复，再建立索引并按共同ID配对；对每个指标分别检查两侧值与差值；计算B−A、n_valid/n_dropped、mean_diff和ci95。无有效样本或少于两对的不确定性用None。不得修改传入对象，不要导入solution。按一种失败修一处的节奏进行。",
          "command": "",
          "file": "developer/labs/paired_comparison/starter.py",
          "expected": "你的实现满足行为契约即可，不必与参考答案逐字相同。每次改动能说出它守住了哪一条数据假设。",
          "prompt": "我正在实现paired_comparison。请审查我贴出的局部修改是否违反契约：拒绝重复、逐指标有效性、B−A、None语义、不改输入。先指出最小问题和一个能击穿它的输入，不直接替我完成所有分支。"
        },
        {
          "id": "paired-green",
          "title": "验证自己的实现与合成例子",
          "kind": "verify",
          "body": "先运行显式starter全测试，再运行学生版本演示。参考解只用于最终比对理解；默认make check的绿灯仍不替代这两条命令。演示数据是合成教学输入，不是某次机器人实验结果。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.paired_comparison.test_contract -v\nscripts/gnav-env.sh python -m developer.labs.paired_comparison.run --implementation starter",
          "file": "developer/labs/paired_comparison/solution.py",
          "expected": "13个学生版本测试通过。合成样例共同ID为3；length有效2对，B−A=-3，正态近似半宽1.96。",
          "prompt": "下面是我完成后的starter、测试和演示结果。请核对实现与契约是否一致，并让我解释为什么共同3对但length只用2对。不要因为13个测试通过就断言所有统计比较都可靠。"
        },
        {
          "id": "paired-review",
          "title": "提交一份别人能审查的解释",
          "kind": "reflect",
          "body": "查看只涉及starter的diff，写三句话：具体输入触发什么问题；修改后怎样处理；哪些情况还未验证。自己再加一个不同顺序或未匹配重复ID的案例。不要直接把教学函数替换到历史结果生成器，因为字段和小样本区间契约有所变化。",
          "command": "git diff -- developer/labs/paired_comparison/starter.py\ngit status --short",
          "file": "",
          "expected": "你能解释diff里的每一处行为改变，并能设计原例子之外的一个边界案例。",
          "prompt": "请把我这段配对评估修改说明当作PR review：问题是否具体、证据是否充分、有没有悄悄改统计定义？给我一个新边界输入检验理解，先不要告诉我期望结果。"
        }
      ],
      "gates": [
        "显式starter的13个测试通过，而非仅参考解通过。",
        "能解释重复ID、样本计数、差值方向和null区间语义。",
        "保留一份最小复现、修复diff与自行设计的边界案例。"
      ]
    },
    {
      "id": "physics",
      "title": "03 · 把Genesis当作可检验的仪器",
      "subtitle": "用解析解测量误差，再讨论真实接触。",
      "minutes": 90,
      "question": "时间步变小后误差变小，究竟验证了什么，又没有验证什么？",
      "prerequisites": [
        "完成环境章；可辨认位置、速度、积分步长。",
        "物理运行要求已经验证的Genesis/Torch环境；轻量.venv不满足。"
      ],
      "docPath": "docs/developer/labs/physics.md",
      "steps": [
        {
          "id": "physics-predict",
          "title": "先写连续解与离散解",
          "kind": "predict",
          "body": "场景是z0=2m、v0=0、g=−9.81m/s²、T=.2s的无接触自由落体。先手算v(T)=gT、z(T)=z0+gT²/2。再推导v[k+1]=v[k]+g*dt、z[k+1]=z[k]+v[k+1]*dt，得到z[n]=z0+g*dt²*n*(n+1)/2。保持T不变，预测dt=.02与.01的误差和比值，暂不打开已保存报告。",
          "command": "",
          "file": "developer/labs/physics_predictions.json",
          "expected": "误差公式为g*T*dt/2；步长减半时绝对误差约减半。你能解释这是半隐式位置更新的有限步长效应。",
          "prompt": "请检查我自由落体连续解与半隐式Euler离散解的推导。先让我指出固定的是T还是步数，再核对误差阶。不要把一次近似二倍误差比直接叫成普遍收敛证明。"
        },
        {
          "id": "physics-read",
          "title": "把每个API对应到实验部件",
          "kind": "read",
          "body": "阅读physics_probe.py：初始化一次Genesis；创建无接触球体；build两个批环境；对每个dt步进固定物理时间；读取末位置与速度；只重置env0，检查env1未改变。它故意逐步拷数据到CPU方便诊断，所以总耗时不是吞吐benchmark。报告包含源码与预测文件hash并拒绝覆盖旧文件。",
          "command": "",
          "file": "developer/physics_probe.py",
          "expected": "你能找到每个预测对应的测量和判据；能指出场景中没有地面，也没有传感器、策略或接触验证。",
          "prompt": "我在读physics_probe.py。请让我逐段对应“假设、干预、测量、判据”，特别检查固定物理时间、batch维度和subset reset。每次只解释我指出的一段，别隐藏在新封装里。"
        },
        {
          "id": "physics-env",
          "title": "回到科研环境并查看资源",
          "kind": "run",
          "body": "如果前面用了轻量.venv，此处必须切回已有Genesis环境。下方是原工作站的默认路径，环境不同请替换。doctor不会替你验证GPU；nvidia-smi用于确认物理GPU1是否有空闲资源。没有Genesis环境时先完成本章推导和代码阅读，实际测量保持未验收，不要将参考报告当作自己运行的结果。",
          "command": "export GNAV_ENV_PREFIX=\"$HOME/miniforge3/envs/genesis-research\"\nmake doctor\nnvidia-smi",
          "file": "",
          "expected": "科研环境中应有Genesis/Torch。确认物理GPU1占用后再跑GPU步骤。两张24GB卡不是单个48GB池。",
          "prompt": "我准备运行物理仪器，下面是doctor和nvidia-smi。请确认当前是否仍是轻量venv、哪些信息只能证明依赖存在、GPU1是否适合这个小实验。不要升级我的工作环境，也不要把cuda:0误当物理GPU0。"
        },
        {
          "id": "physics-cpu",
          "title": "先运行CPU仪器",
          "kind": "run",
          "body": "从仓库根目录显式运行CPU探针。它会生成新的JSON证据而不渲染窗口。首次运行可能编译内核；输出文件已存在时会拒绝覆盖，请换一个新文件名，不要删除旧证据。",
          "command": "CUDA_VISIBLE_DEVICES= scripts/gnav-env.sh python developer/physics_probe.py --backend cpu --output developer/evidence/my-physics-cpu.json",
          "file": "",
          "expected": "ok=true；两种dt各项判据通过；误差比接近2（既有验证约2.0000243）。精确浮点和耗时可因环境变化，不应为匹配旧数字改判据。",
          "prompt": "我跑了CPU自由落体，下面是输出和我的解析预测。请先比较哪个具体检查不同，再区分代码、时间步、单位、版本或数值问题；不要为了通过而放宽误差阈值。"
        },
        {
          "id": "physics-gpu",
          "title": "再测GPU，核对设备映射",
          "kind": "run",
          "body": "确认GPU1空闲后运行同一小场景。CUDA_VISIBLE_DEVICES=1会把物理GPU1映射成进程内cuda:0。记录后端、版本、hash与轨迹；CPU/GPU相同场景通过只支持这里的有限检查，不证明所有物理工况等价。",
          "command": "CUDA_VISIBLE_DEVICES=1 scripts/gnav-env.sh python developer/physics_probe.py --backend gpu --output developer/evidence/my-physics-gpu.json",
          "file": "",
          "expected": "后端应为CUDA，进程设备可能显示cuda:0；各项检查通过。总耗时含初始化和编译，不能用它排名稳态CPU/GPU速度。",
          "prompt": "请比较我贴出的CPU/GPU报告，明确哪些检查相同、哪些差异合理。解释物理GPU1为何报告cuda:0，并质疑我是否把含编译的总用时当成吞吐性能结论。"
        },
        {
          "id": "physics-intervene",
          "title": "亲手做一次能推翻错误解释的修改",
          "kind": "implement",
          "body": "创建独立的学习副本，选一种干预并先预测：只reset位置、不reset速度；或将substeps改成2；或保持步数而不是物理时间相同。只改一个因素，用新报告路径保存。另写一个独立analyze_freefall函数从轨迹重算误差，别直接相信报告的ok。修改副本之后，在命令中换成副本路径。",
          "command": "cp developer/physics_probe.py developer/physics_probe_student.py",
          "file": "developer/physics_probe.py",
          "expected": "只重置位置应暴露残留速度；改变内部步长需要重新推导误差；固定步数会改变T。把观察与原预测并排保存，即使预测错了也不擦掉。",
          "prompt": "我选择的干预是……，运行前预测是……。请评审这个干预是否只改一个因素、我的判据能否区分两种解释。只给最小实验建议，不帮我增加复杂场景。"
        },
        {
          "id": "physics-limit",
          "title": "给结论划定边界",
          "kind": "reflect",
          "body": "写四行结论：这次验证的场景和后端；连续与离散模型差异；reset故障的机制；尚未验证的接触/执行器/传感器。下一项真实机器人检查可以是力矩饱和、阻尼或接触穿透，只选一个。原教学probe保持不变，自己的扩展代码与报告单独存放。",
          "command": "",
          "file": "",
          "expected": "你能说明自由落体通过不代表真实机器人可靠，也能提出一个带参考和判据的后续检查。",
          "prompt": "请像论文审稿人一样检查我的四行物理验证结论：是否把有限场景外推过头、是否区分模型误差与实现误差、下一项实验是否可以证伪。不要用动画效果代替证据。"
        }
      ],
      "gates": [
        "运行前完成连续/离散手算，并保留预测。",
        "在具备相应环境时，生成自己的CPU/GPU新报告；缺环境的测量不标完成。",
        "完成一个单因素干预与独立轨迹分析，解释结果的适用范围。"
      ]
    },
    {
      "id": "observation",
      "title": "04 · 把观测边界写成测试",
      "subtitle": "合法字段只是起点，信息来源仍需检查。",
      "minutes": 60,
      "question": "两个世界给出完全相同的合法观测时，策略还能区分它们吗？",
      "prerequisites": [
        "理解合法观测与oracle真值的区别。",
        "使用任一路径的轻量Python环境即可，不需要Genesis。"
      ],
      "docPath": "docs/developer/labs/observation.md",
      "steps": [
        {
          "id": "obs-predict",
          "title": "先写一个不变性预测",
          "kind": "predict",
          "body": "设合法观测o=h(s)，无历史确定性策略a=π(o)。若两个真实状态的合法观测相同，动作应相同。有记忆策略则要求整个合法历史一致，不是只看当前帧。预测三种干预：只改隐藏障碍坐标；改变合法测距；下一帧原地覆盖传感器buffer。它们应如何影响已经构造的本帧输入？",
          "command": "",
          "file": "",
          "expected": "隐藏字段不应影响输入；合法测距变化允许影响；未来buffer覆盖不应改掉已存的本帧输入。这是软件通道干预，不是说物理世界变化后传感器自然不变。",
          "prompt": "请核对我对三个观测干预的预测，并区分单步无记忆策略与recurrent策略的不变性条件。先问我“固定了什么”，不要把schema测试说成信息来源合法性的完整证明。"
        },
        {
          "id": "obs-contract",
          "title": "阅读教学尺寸与数据契约",
          "kind": "read",
          "body": "本lab只允许rays(3)、goal(2)、proprio(2)，保留有限数值，rays非负，输出独立数据。它是教学尺寸；真实gnav的OBS_KEYS和传感器尺寸不同，不能直接替换。额外的privileged_obstacle_xy、episode_seed等字段不进入策略。",
          "command": "",
          "file": "developer/labs/observation/test_contract.py",
          "expected": "知道输入字段、尺寸、数值条件和复制语义；不会误以为这里实现了完整Genesis传感器。",
          "prompt": "请根据这份测试帮我提炼policy_input的精确契约。我会先解释允许字段、尺寸、有限值与复制语义，请指出遗漏，不要直接给出参考实现。"
        },
        {
          "id": "obs-red",
          "title": "让泄漏与别名问题显现",
          "kind": "run",
          "body": "starter目前返回dict(sensor_packet)，它会携带额外字段，而且浅复制后内部list仍共享。显式运行starter测试，分别找到allowlist、不变性与buffer别名失败。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.observation.test_contract -v",
          "file": "developer/labs/observation/starter.py",
          "expected": "初始有多个失败；不是环境坏了。浅复制不会让嵌套list成为独立快照。",
          "prompt": "下面是观测边界starter测试失败。请用一个很小的Python对象例子引导我解释浅复制为什么仍共享内部list；先让我预测修改前后对象，不直接把deepcopy当万能答案。"
        },
        {
          "id": "obs-implement",
          "title": "实现边界而不擦除有用信号",
          "kind": "implement",
          "body": "只改policy_input：明确选字段、验证形状与数值、生成独立且适合保存的值。允许忽略额外调试字段，但不接受缺失必需传感器。既要让隐藏字段变化不起作用，也要让合法传感器变化被保留；返回常量虽然不泄漏，却没实现可用观测。",
          "command": "",
          "file": "developer/labs/observation/starter.py",
          "expected": "输入不被修改；输出不受后续buffer写入影响；非法值被明确拒绝。",
          "prompt": "我写了policy_input，请检查它是否用返回常量或过度过滤“蒙混过关”。给我一个合法传感器改变应该保留的案例，再给一个缺失字段或NaN案例，让我先说明期望。"
        },
        {
          "id": "obs-green",
          "title": "验证学生实现，再阅读参考",
          "kind": "verify",
          "body": "用完全相同的显式starter命令复测。通过之后才打开solution，比较你的取舍。参考使用不可变tuple保存数值；你可以有不同实现，但行为必须满足契约。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.observation.test_contract -v",
          "file": "developer/labs/observation/solution.py",
          "expected": "7个学生版本测试通过；你能逐一解释隐藏字段、合法变化、buffer别名这三类测试的目的。",
          "prompt": "我的7个starter测试已通过。请不要只祝贺我，给一个“字段名合法、值却来自隐藏真值”的反例，检查我能否解释当前测试为何检测不到。"
        },
        {
          "id": "obs-source",
          "title": "回到真实信息流，写下一条集成契约",
          "kind": "reflect",
          "body": "在真实src/gnav/sim/env.py中定位_compute_obs、privileged_state与step，再画actor、critic、reward、evaluator各可读取什么。训练critic允许特权信息和部署actor允许特权信息是两件事。若把隐藏坐标伪装成proprio，字段检查可能仍通过；还需审查生产路径。",
          "command": "rg -n \"OBS_KEYS|def _compute_obs|def privileged_state|def step\" src/gnav/sim/env.py",
          "file": "",
          "expected": "形成一张信息流图和一个针对实际actor的干预测试设计。此处尚未修改或验证真实训练collector。若未安装rg，用编辑器搜索同样方法名。",
          "prompt": "请审查我的actor/critic/reward/evaluator信息流图。指出最容易发生语义泄漏的一条边，并帮我设计只改变oracle记录、固定合法历史的测试。不要把所有训练特权信息一律判错。"
        }
      ],
      "gates": [
        "显式starter的7个测试通过。",
        "能解释不变性、合法信号保留和buffer复制。",
        "能举出schema通过仍泄漏的反例，并定位真实传感器生产路径。"
      ]
    },
    {
      "id": "gae",
      "title": "05 · 写对GAE的两个边界",
      "subtitle": "同样的reward，两个mask用错就会训练完全不同的目标。",
      "minutes": 120,
      "question": "为什么时间截断需要保留bootstrap，却必须切断下一集的advantage？",
      "prerequisites": [
        "能读嵌套list形状[T,B]；理解V(s)与折扣因子γ。",
        "本章不训练PPO，也不运行Genesis。"
      ],
      "docPath": "docs/developer/labs/gae.md",
      "steps": [
        {
          "id": "gae-model",
          "title": "区分任务终止、采样截断与rollout尾部",
          "kind": "read",
          "body": "terminated是任务终止；truncated是任务之外的截断。如果时间上限本来属于任务目标，则需按有限时域建模，不能见timeout就bootstrap。这里δ=r+γ*(1−terminated)*V(true_next_obs)−V(obs)；A=δ+γλ*(1−(terminated OR truncated))*A_next。前一mask决定是否还有后继价值，后一mask阻止不同episode残差相连。",
          "command": "",
          "file": "developer/labs/gae/contract.py",
          "expected": "能分别回答“状态之后还有任务价值吗”和“下一行还属于同一episode吗”。rollout chunk结束本身不是terminal。",
          "prompt": "我在GAE lab。请用一个时间截断但任务可继续的例子，检验我对bootstrap mask与trace mask的理解。先让我写公式；不要把done作为统一答案，也不要把所有time limit都等同外部截断。"
        },
        {
          "id": "gae-hand",
          "title": "手算四个单步案例",
          "kind": "predict",
          "body": "取r=2、V=1、true next V=10、γ=.9、λ=.8。分别预测继续但rollout结束、terminated、truncated，以及truncated却误用reset V=100时的delta/advantage/return。再看cases.py的两个episode样例：把后一集reward改成一百万，前一集advantage能否变化？",
          "command": "",
          "file": "developer/labs/gae/cases.py",
          "expected": "先写自己的答案。核对时单步advantage应分别为10、1、10、91；正确两集优势为[3.572,2.6,50]。后一集奖励不应回流前一集。",
          "prompt": "下面是我的四种GAE手算和理由。请逐行核对bootstrap与trace，而不是只比较终态数字。若我得到91，请让我定位这个有限但错误的next_value从哪里来。"
        },
        {
          "id": "gae-red",
          "title": "把两个错误分开暴露",
          "kind": "run",
          "body": "先运行只针对bootstrap的测试，再运行只针对trace的测试。初始两者都失败。一次只修一种错误，观察另一种仍失败的证据；这比同时改一堆代码后只看均值更有诊断价值。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.gae.test_contract.GAEContract.test_termination_removes_bootstrap_but_truncation_preserves_it -v\nLAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.gae.test_contract.GAEContract.test_truncation_stops_trace_into_next_episode -v",
          "file": "developer/labs/gae/starter.py",
          "expected": "初始第一项截断A=1而应10；第二项trace为[102,100]而应[2,100]。都应退出1，修好对应语义后才应变绿。",
          "prompt": "这是我分别运行两个GAE边界测试的结果。请帮我只分析一个mask的错误，指出当前那一行为什么错；我修完后再讨论另一项。不要一次贴完整compute_gae。"
        },
        {
          "id": "gae-implement",
          "title": "实现逆序递推与padding",
          "kind": "implement",
          "body": "修改compute_gae。每个batch列独立，从末尾逆序；padding行不读数值、输出0并清carry；terminal不读取next_value；先算delta，再按term|trunc决定是否接carry；returns=A+V。不要写0*NaN来“屏蔽”终止值。检查输入和输出有限性，不在这里做advantage normalization。",
          "command": "",
          "file": "developer/labs/gae/starter.py",
          "expected": "对有效的[T,B]数据保持批列独立；valid只支持每列尾部padding，不悄悄接跨内部缺失步。",
          "prompt": "请审查我的GAE循环，仅检查四点：真实next value、两个mask、padding、每列carry。请用一个terminal next_value=NaN或异步batch边界击穿错误，而不是替我重新组织整个文件。"
        },
        {
          "id": "gae-green",
          "title": "用学生实现核对手算oracle",
          "kind": "verify",
          "body": "运行显式starter全测试与演示。若只运行默认测试，实际上用的是solution，不是你的修改。通过后再读参考代码解释每个条件分支；你没有因此完成PPO。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.gae.test_contract -v\nscripts/gnav-env.sh python -m developer.labs.gae.run --implementation starter",
          "file": "developer/labs/gae/solution.py",
          "expected": "17个学生版本测试通过。两集advantages=[3.572,2.6,50]，returns=[5.572,5.6,100]；γ或λ端点与padding案例也通过。",
          "prompt": "我的GAE starter通过17个测试，下面是演示输出。请给我一个新的两环境异步终止案例，让我手算一列并预测另一列是否受影响；不要把测试通过说成训练性能已提升。"
        },
        {
          "id": "gae-collector",
          "title": "找到真实训练器里尚未解决的接口问题",
          "kind": "read",
          "body": "当前src/gnav/experiment/train.py是test-grade recurrent A2C，不是PPO；它简化地把truncation当terminal。NavEnv.step默认auto_reset后才返回obs，当前info没有final_obs。因此只把GAE的done换成terminated，仍可能把新episode初始obs当旧episode后继。接入时必须在reset前保存真实next_obs与本episode的recurrent state。",
          "command": "",
          "file": "src/gnav/experiment/train.py",
          "expected": "你能画出step(auto_reset=False)→评true_next_obs→保存term/trunc→reset_done的顺序，并说明recurrent hidden state不能提前重置或推进两次。这是待实现的集成设计。",
          "prompt": "请审查我给Genesis recurrent collector画的数据流：true_next_obs、next_value、hidden state、prev-action和first mask何时更新？不要假设自定义NavEnv有Gymnasium的final_obs键，先依据我贴出的代码。"
        },
        {
          "id": "gae-next",
          "title": "给Torch移植写验收而非直接开长训练",
          "kind": "reflect",
          "body": "下一步你可以把列表实现移植为Torch：时间逆序、batch向量化；target放在no_grad/detach边界，只对valid样本归一化与算loss。先用CPU float64对手算oracle，再讨论GPU float32容差。PPO的old_log_prob、ratio、clip、minibatch/epoch、KL仍是后续单独任务。",
          "command": "",
          "file": "",
          "expected": "交付一页Torch移植验收计划和一个reset V=100、true next V=10的collector stub案例。未实现的PPO不标记完成。",
          "prompt": "请评审我的Torch GAE移植计划，重点检查梯度边界、valid样本、NaN屏蔽和float32容差。给我一个必须先写的collector集成测试，不要直接为我搭建完整PPO框架。"
        }
      ],
      "gates": [
        "显式starter17个测试通过，并能手算两个episode。",
        "能解释截断bootstrap保留、trace切断及reset观测污染。",
        "明确当前A2C与未来PPO的界线，并写出collector集成验收。"
      ]
    },
    {
      "id": "identification",
      "title": "06 · 检验数据是否足以辨识动力学",
      "subtitle": "训练误差很小，仍可能完全没有学会如何响应新动作。",
      "minutes": 120,
      "question": "两个模型解释了同一份数据，什么动作能区分它们？",
      "prerequisites": [
        "能解2×2线性方程并理解最小二乘。",
        "已完成配对评估；不要求使用GPU或Genesis。"
      ],
      "docPath": "docs/developer/labs/identification.md",
      "steps": [
        {
          "id": "id-predict",
          "title": "先构造一个不能被数据区分的模型对",
          "kind": "predict",
          "body": "合成系统v[t+1]=a*v[t]+b*u[t]+w[t]，观测z[t]=v[t]+e[t]。先令噪声为零，真值a=.75,b=.5。预测v0=0,u=0；v0=1,u=0；v0=2,u=1三种情况。第三种里(.75,.5)与(.5,1)为何都维持v=2？再预测将初态改为0后，恒定输入是否仍一定不可辨识。",
          "command": "",
          "file": "",
          "expected": "零状态零输入不给任何参数信息；零输入衰减可约束a但不能辨识b；稳态恒定输入的两列共线。恒定输入有瞬态时可以满秩，不能把例子写成普遍定理。",
          "prompt": "请核对我对三种输入/初态的辨识预测。用“哪些不同(a,b)仍解释相同观测”来追问我，不要先用哲学自我意识语言，也不要把恒定输入一概说成无信息。"
        },
        {
          "id": "id-math",
          "title": "推导五个累加量与秩判据",
          "kind": "read",
          "body": "构造X[t]=[z[t],u[t]]，y[t]=z[t+1]；手写Svv、Suu、Svu、Svy、Suy与2×2正规方程。D=Svv*Suu−Svu²，a=(Svy*Suu−Suy*Svu)/D，b=(Suy*Svv−Svy*Svu)/D。不要给D偷偷加epsilon：秩不足要明确报告。条件数报告的是cond(X)=sqrt(λmax/λmin)，不是cond(XᵀX)。",
          "command": "",
          "file": "developer/labs/identification/test_contract.py",
          "expected": "能用states=[0,1,.5]、inputs=[1,0]手算a=.5,b=1。知道identifiable只表示该有限数据和数值阈值下的估计条件，不证明全局结构可辨识。",
          "prompt": "我推导了2×2 OLS和条件数，请检查我的时间索引、五个累加量、cond(X)与cond(XᵀX)区别。若秩不足，先让我解释为什么不该给行列式加epsilon掩盖问题。"
        },
        {
          "id": "id-red",
          "title": "运行未完成的估计器",
          "kind": "run",
          "body": "starter的fit_dynamics还抛出NotImplementedError。先运行它的测试，把第一个手算oracle作为实现起点。common.py提供输入检查、MSE与合成数据；核心估计由你完成。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.identification.test_contract -v",
          "file": "developer/labs/identification/starter.py",
          "expected": "初始会失败/报未实现，属于预期红测试。不要改成导入solution来“完成”练习。",
          "prompt": "我开始实现系统辨识starter，下面是第一条失败。请从states=[0,1,.5], inputs=[1,0]引导我定位时间索引，先实现最小正确案例，然后再增加秩与异常输入处理。"
        },
        {
          "id": "id-implement",
          "title": "实现估计器并处理数值尺度",
          "kind": "implement",
          "body": "只改fit_dynamics：验证N+1个状态和N个输入；计算Gram与右端项；按相对特征值阈值判断数值rank；满秩求a/b与原单位MSE，否则返回None与identifiable=false。参考实现会用共同尺度归一化X和y，避免仅因1e-100或1e154单位尺度而误报缺激励。真正列共线不能靠共同缩放消除。",
          "command": "",
          "file": "developer/labs/identification/starter.py",
          "expected": "返回n_samples、rank、rank_tolerance、condition_x、identifiable、a、b、train_one_step_mse。原单位MSE与数值rank语义清楚；不是通用生产线性代数求解器。",
          "prompt": "请检查我的OLS实现，尤其数值rank、共同尺度归一化、系数不变与MSE恢复原单位。请用一个良态但极小尺度的正交例子检验，避免把浮点下溢误叫成科学不可辨识。"
        },
        {
          "id": "id-green",
          "title": "先验收学生实现，再运行受控比较",
          "kind": "verify",
          "body": "先让显式starter测试变绿，再执行同一学生实现的实验。比较恒定+1与固定seed的±1输入，保持相同样本数128、输入能量128、初态2；相同噪声级别复用相同draws；holdout使用独立输入seed和初态−.3。查看rank、cond、训练一步MSE和holdout rollout，而不是只看训练曲线。",
          "command": "LAB_IMPLEMENTATION=starter scripts/gnav-env.sh python -m unittest developer.labs.identification.test_contract -v\nscripts/gnav-env.sh python -m developer.labs.identification.run --implementation starter",
          "file": "developer/labs/identification/run.py",
          "expected": "19个学生版本测试通过。无噪声稳态恒定组rank1，丰富组恢复参数。默认过程噪声例子训练MSE均约.00085，而holdout rollout约.01558对.00196；这是固定种子合成观察，不是跨任务定律。",
          "prompt": "下面是我两组输入的实验结果。请让我先解释控制了哪些变量、没控制哪些变量，再比较rank/condition、one-step与rollout误差。检查我是否用holdout挑了模型或把一个seed泛化成普遍结论。"
        },
        {
          "id": "id-noise",
          "title": "加入测量噪声，挑战OLS假设",
          "kind": "run",
          "body": "先预测，再给观测添加标准差.2的测量噪声。z[t+1]=a*z[t]+b*u[t]+(w[t]+e[t+1]−a*e[t])，回归输入与误差共享e[t]，所以即便X满秩，OLS也不自动恢复真参数。隐藏状态只用于合成评分，真实机器人通常没有这个oracle。",
          "command": "scripts/gnav-env.sh python -m developer.labs.identification.run --implementation starter --measurement-noise 0.2",
          "file": "developer/labs/identification/common.py",
          "expected": "输出应为合法JSON。参数与holdout表现会变化；能说明errors-in-variables机制，不把“更多数据”当作修复错误统计假设的万能办法。",
          "prompt": "我增加了测量噪声。请让我从z=v+e推导回归残差，检查Cov(z_t,residual_t)为何通常非零，再解释满秩、低MSE和参数一致性是不同命题。不要声称这个实验证明了机器人自我意识。"
        },
        {
          "id": "id-report",
          "title": "写一份保留反例的科学结论",
          "kind": "reflect",
          "body": "完成后再读solution和参考结果。报告一个你被证据修正的预测，区分实现错误、输入信息不足、模型假设不匹配。设计下一项最小实验：例如提前固定三种输入，用训练阶段条件数选设计，再用独立种子评价；不能用同一个holdout既挑选又宣称泛化。",
          "command": "",
          "file": "developer/labs/identification/solution.py",
          "expected": "能展示两个模型在同一训练轨迹零误差但新输入下不同，并保留“恒定输入有瞬态也可满秩”的反例。",
          "prompt": "请审查我的辨识结论和下一轮实验计划：是否把数值rank当结构定理、是否重复使用holdout、是否解释输入变化的机制。只指出能被明确实验推翻的表述，帮我缩小一个最有价值的下一步。"
        }
      ],
      "gates": [
        "显式starter的19个测试通过，包括极端共同尺度。",
        "给出低训练误差但holdout不同的反例，区分拟合与辨识。",
        "解释测量噪声的误差相关，并保留预测、控制条件与限制。"
      ]
    },
    {
      "id": "capstone",
      "title": "07 · 把一次练习交付成可复现研究工作",
      "subtitle": "让另一个人只看你的记录也能判断发生了什么。",
      "minutes": 90,
      "question": "没有你在旁边解释，别人能复现并质疑你的结论吗？",
      "prerequisites": [
        "完成至少一套starter，最好完成前六章。",
        "准备自己的预测、代码改动、实际命令和输出；不要补写成完美故事。"
      ],
      "docPath": "docs/developer/engineering-handbook.md",
      "steps": [
        {
          "id": "cap-scope",
          "title": "选一个已经完成的最小问题",
          "kind": "read",
          "body": "只选前面一个问题做交付：重复ID导致错误比较、reset观测污染GAE、输入缺激励、或时间步误差。写清现象、最小模型、竞争解释和验收。不要一次把PPO、world model、Web前端与真实机器人全部装进一个PR。本包提供近期底座；完整PPO/world model仍是未来作业。",
          "command": "",
          "file": "",
          "expected": "问题能用三句话说明，且有一条会失败的反例。你的工作不是“把课程跑完”，而是让这个小结论可被别人检查。",
          "prompt": "请帮我压缩这次交付的范围。我会给出现象、两个解释和当前代码，请判断哪个最小实验能区分它们，不要替我扩成新博士课题或大系统。"
        },
        {
          "id": "cap-evidence",
          "title": "区分学生验收、工程门禁与物理证据",
          "kind": "verify",
          "body": "对你选择的lab显式运行starter测试，保存原始输出；再运行make check确认参考工具未被破坏。若包含物理实验，另外引用新报告、版本、源hash和预测hash。默认100项测试不能替代学生版本，更不能替代论文结论。",
          "command": "make check\ngit status --short\ngit diff --stat",
          "file": "",
          "expected": "参考门禁100项通过；你另有对应starter的通过证据。未运行的GPU、GUI、真实机器人或后期算法明确写“未验证”。",
          "prompt": "下面是我保存的测试与运行证据。请检查每一条结论是否有相同范围的证据，特别警惕用参考解绿灯替代学生实现、用物理probe替代传感器/接触验证。"
        },
        {
          "id": "cap-record",
          "title": "写实验卡和中文交接",
          "kind": "implement",
          "body": "在自己的新文件中按模板记录：运行前预测、控制变量、基线、seeds、命令、版本、实际结果、负结果和下一项区分实验。不要改写原预测以迎合结果。交接中写明工作树、改动文件、可执行下一步和未覆盖范围。",
          "command": "git diff -- developer/labs\ngit status --short",
          "file": "",
          "expected": "另一个人能找到源码、输入、命令、实际输出及不确定性，不需要读取你与AI的整段聊天。",
          "prompt": "请作为接手的研究工程师读我的实验卡：哪些信息足够直接执行，哪些仍靠猜？请优先找缺少输入、seed、环境、判据或数据路径的地方，不做空泛润色。"
        },
        {
          "id": "cap-independent",
          "title": "做一次无参考答案的理解验收",
          "kind": "predict",
          "body": "关掉solution，自己改一个新输入或引入一个故障，先预测再运行。让同学或另一个AI只问问题：为什么这个测试会失败？如果换一个物理/统计假设，还能得出原结论吗？自己的方案不需要和参考代码长得一样，但必须能解释。",
          "command": "",
          "file": "",
          "expected": "能独立复现、解释改动、处理新边界、说明未验证范围。四项各自打0/1，用于发现薄弱项，不是能力认证。",
          "prompt": "请对我做一次不泄露答案的口试。我会贴自己的实现与解释，请给一个没在原演示出现的输入，让我先预测；之后再检查理由，不要立即展示参考解。"
        },
        {
          "id": "cap-review",
          "title": "整理一个小改动供他人评审",
          "kind": "reflect",
          "body": "查看diff，只选择本次问题必需的代码、测试和文档。写PR草稿：具体触发、修改后行为、验证命令、实际结果、契约变化、回退办法。原科学结果与冻结记录不随教学改动重写。提交或推送前理解每个文件；本网站不会替你执行Git写操作。",
          "command": "git diff --check\ngit diff --stat",
          "file": "",
          "expected": "没有无关格式化、大结果文件或环境变更混入；对统计定义/接口的变化有明确说明。",
          "prompt": "请审查我的PR草稿与diff摘要：问题和行为是否具体、是否存在无关改动、测试是否对应行为、是否悄悄改变科学或数据契约？不要替我自动提交或推送。"
        },
        {
          "id": "cap-next",
          "title": "选下一个能力缺口，而不是追逐框架",
          "kind": "reflect",
          "body": "按下方12周路线选一项下一任务。若算法目标不清，先做真实问题访谈与文献机制对照；若物理边界不清，先补执行器或传感器验证；若target正确性还不清，不开长训练。API/前端是需要给别人使用时的交付支线。三年研究目标需要真实实验、原论文、同行反馈与你自己的判断持续更新。",
          "command": "",
          "file": "",
          "expected": "下一步有明确能力、亲手实现部分、输入、参考和可失败验收。不会把“自我建模”兴趣提前宣布为原创贡献或固定论文题目。",
          "prompt": "基于我已能独立完成的部分和仍解释不清的点，请建议一个两周内可验收的下一任务。每个建议必须写明我亲手实现什么、如何证伪、需要哪些外部反馈；不要列一堆新框架。"
        }
      ],
      "gates": [
        "交付一份能被他人复现的中文实验卡、代码diff和验证记录。",
        "通过一个未见输入/故障的解释验收。",
        "下一项任务有明确参考与边界，而不是继续堆工具。"
      ]
    }
  ],
  "files": {
    "developer/gnav_dev.py": "#!/usr/bin/env python3\n\"\"\"Read-only developer tools for gnav; never initialise Genesis or load a checkpoint.\n\nRun through scripts/gnav-env.sh. This entry point pins imports to its own worktree,\nso an editable installation of another checkout cannot silently win.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nimport dataclasses\nimport importlib.metadata\nimport importlib.util\nimport json\nimport math\nimport os\nfrom pathlib import Path\nimport subprocess\nimport sys\nimport types\nimport typing\n\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / \"src\"\nsys.path.insert(0, str(SRC))\nMAX_BYTES = 16 * 1024 * 1024\n\n\nclass PreflightError(ValueError):\n    \"\"\"An actionable input problem, shown without an implementation traceback.\"\"\"\n\n\ndef _git(*args: str) -> str | None:\n    try:\n        result = subprocess.run(\n            [\"git\", \"-C\", str(ROOT), *args], capture_output=True, text=True, timeout=5,\n            check=False,\n        )\n    except (OSError, subprocess.TimeoutExpired):\n        return None\n    return result.stdout.strip() if result.returncode == 0 else None\n\n\ndef doctor() -> dict:\n    \"\"\"Inspect package metadata without importing torch/genesis or probing a GPU.\"\"\"\n    dependencies = {}\n    for name in (\"PyYAML\", \"numpy\", \"torch\", \"genesis-world\", \"pytest\"):\n        try:\n            dependencies[name] = importlib.metadata.version(name)\n        except importlib.metadata.PackageNotFoundError:\n            dependencies[name] = None\n    spec = importlib.util.find_spec(\"gnav\")\n    actual = Path(spec.origin).resolve() if spec and spec.origin else None\n    expected = SRC / \"gnav\" / \"__init__.py\"\n    status = _git(\"status\", \"--porcelain\")\n    checks = {\n        \"python_supported\": (3, 11) <= sys.version_info[:2] < (3, 13),\n        \"source_is_this_worktree\": actual == expected,\n        \"yaml_available\": dependencies[\"PyYAML\"] is not None,\n    }\n    warnings = []\n    if any(dependencies[name] is None for name in (\"numpy\", \"torch\", \"genesis-world\")):\n        warnings.append(\"仿真依赖不完整；轻量开发检查仍可使用，未启动仿真。\")\n    if os.environ.get(\"PYTHONPATH\"):\n        warnings.append(\"PYTHONPATH 非空；建议经 scripts/gnav-env.sh 运行以隔离 ROS。\")\n    if status:\n        warnings.append(\"工作区有未提交变更；这是状态提示，不是错误。\")\n    return {\n        \"ok\": all(checks.values()), \"command\": \"doctor\", \"root\": str(ROOT),\n        \"python\": {\"executable\": sys.executable, \"version\": sys.version.split()[0]},\n        \"gnav_source\": str(actual) if actual else None,\n        \"git\": {\"branch\": _git(\"branch\", \"--show-current\"),\n                \"commit\": _git(\"rev-parse\", \"HEAD\"),\n                \"dirty\": bool(status) if status is not None else None},\n        \"dependencies\": dependencies, \"checks\": checks, \"warnings\": warnings,\n        \"scope\": \"仅检查元数据和导入路径；不代表 CUDA、渲染器或仿真健康检查通过。\",\n    }\n\n\ndef _read_text(path: Path) -> str:\n    try:\n        if not path.is_file():\n            raise PreflightError(f\"找不到普通文件：{path}\")\n        if path.stat().st_size > MAX_BYTES:\n            raise PreflightError(f\"文件超过轻量检查上限 16 MiB：{path}\")\n        return path.read_text(encoding=\"utf-8\")\n    except (OSError, UnicodeError) as exc:\n        raise PreflightError(f\"无法读取 {path}：{exc}\") from exc\n\n\ndef _yaml_module():\n    try:\n        import yaml\n    except ImportError as exc:\n        raise PreflightError(\"缺少 PyYAML；请使用 scripts/gnav-env.sh 及已配置的 Genesis 环境。\") from exc\n    return yaml\n\n\ndef _yaml_mapping(path: Path) -> dict:\n    yaml = _yaml_module()\n    try:\n        data = yaml.safe_load(_read_text(path))\n    except yaml.YAMLError as exc:\n        raise PreflightError(f\"YAML 无法解析：{path}：{exc}\") from exc\n    if data is None:\n        return {}\n    if not isinstance(data, dict):\n        raise PreflightError(f\"配置顶层必须是 mapping（键值表）：{path}\")\n    return data\n\n\ndef _load_tree(path: Path, stack: tuple[Path, ...] = ()) -> dict:\n    \"\"\"Match gnav inheritance semantics while rejecting cycles and wrong shapes.\"\"\"\n    from gnav.config import _deep_merge\n\n    path = path.resolve()\n    if path in stack:\n        raise PreflightError(\"配置继承循环：\" + \" -> \".join(p.name for p in (*stack, path)))\n    if len(stack) >= 32:\n        raise PreflightError(\"配置继承超过 32 层；请简化继承关系。\")\n    data = _yaml_mapping(path)\n    parents = data.pop(\"inherit\", []) or []\n    if not isinstance(parents, list) or any(not isinstance(p, str) for p in parents):\n        raise PreflightError(f\"inherit 必须是相对路径字符串列表：{path}\")\n    merged = {}\n    for parent in parents:\n        merged = _deep_merge(merged, _load_tree(path.parent / parent, (*stack, path)))\n    return _deep_merge(merged, data)\n\n\ndef _type_errors(value, expected, path: str = \"config\", depth: int = 0) -> list[str]:\n    \"\"\"Runtime-check dataclass annotations; dataclasses alone do not enforce types.\"\"\"\n    if depth > 40:\n        return [f\"{path}：嵌套超过 40 层（可能含 YAML alias 循环）\"]\n    if expected is typing.Any:\n        return []\n    origin, args = typing.get_origin(expected), typing.get_args(expected)\n    if origin in (typing.Union, types.UnionType):\n        if any(not _type_errors(value, option, path, depth + 1) for option in args):\n            return []\n        return [f\"{path}：应为 {expected}，实际为 {type(value).__name__}\"]\n    if dataclasses.is_dataclass(expected):\n        if not isinstance(value, dict):\n            return [f\"{path}：应为键值表，实际为 {type(value).__name__}\"]\n        hints = typing.get_type_hints(expected)\n        errors = []\n        for key, item in value.items():\n            if key not in hints:\n                errors.append(f\"{path}.{key}：未知配置字段\")\n            else:\n                errors.extend(_type_errors(item, hints[key], f\"{path}.{key}\", depth + 1))\n        return errors\n    if origin in (list, tuple):\n        if not isinstance(value, (list, tuple)) or (origin is list and not isinstance(value, list)):\n            return [f\"{path}：应为 {origin.__name__}\"]\n        if origin is tuple and len(args) != len(value):\n            return [f\"{path}：需要 {len(args)} 个元素，实际为 {len(value)}\"]\n        errors = []\n        for index, item in enumerate(value):\n            kind = args[0] if origin is list else args[index]\n            errors.extend(_type_errors(item, kind, f\"{path}[{index}]\", depth + 1))\n        return errors\n    if origin is dict:\n        if not isinstance(value, dict):\n            return [f\"{path}：应为键值表\"]\n        errors = []\n        for key, item in value.items():\n            errors.extend(_type_errors(key, args[0], f\"{path}.<key>\", depth + 1))\n            errors.extend(_type_errors(item, args[1], f\"{path}.{key}\", depth + 1))\n        return errors\n    valid = isinstance(value, expected)\n    if expected is int:\n        valid = type(value) is int\n    elif expected is float:\n        valid = type(value) in (int, float) and math.isfinite(value)\n    if valid:\n        return []\n    return [f\"{path}：应为 {getattr(expected, '__name__', expected)}，实际为 {type(value).__name__}\"]\n\n\ndef validate_config(cfg) -> list[str]:\n    \"\"\"Conservative preflight rules, separate from the frozen scientific code.\n\n    This catches common invalid inputs. It does not prove geometric feasibility,\n    checkpoint compatibility, physics stability, or completeness of custom profiles.\n    \"\"\"\n    d = cfg.to_dict()\n    errors = []\n\n    def get(path):\n        result = d\n        for part in path.split(\".\"):\n            result = result[part]\n        return result\n\n    def require(condition, message):\n        if not condition:\n            errors.append(message)\n\n    positive = (\n        \"env.n_envs\", \"env.sim_dt\", \"env.control_decimation\", \"env.max_episode_steps\",\n        \"env.arena_half_size\", \"env.wall_height\", \"env.goal_radius\", \"env.robot_mass\",\n        \"env.robot_max_force\", \"env.robot_max_torque\", \"env.sensors.rays_n\",\n        \"env.sensors.max_range\", \"env.mover.mass\", \"env.mover.max_force\",\n        \"model.latent_dim\", \"model.belief_dim\", \"model.hidden_dim\", \"train.iterations\",\n        \"train.rollout_len\", \"train.lr\", \"train.seq_len\", \"train.batch_size\",\n        \"train.replay_capacity\", \"train.checkpoint_every\", \"eval.n_episodes\",\n    )\n    nonnegative = (\n        \"seed\", \"eval_seed\", \"env.n_pillars\", \"env.n_occluders\", \"env.min_start_goal_dist\",\n        \"env.near_collision_clearance\", \"env.dynamics.delay_jitter\", \"env.dynamics.max_delay_steps\",\n        \"env.sensors.depth_noise_std\", \"env.sensors.rays_noise_std\",\n        \"env.sensors.proprio_noise_std\", \"env.sensors.goal_noise_std\",\n    )\n    for path in positive:\n        require(get(path) > 0, f\"{path} 必须 > 0\")\n    for path in nonnegative:\n        require(get(path) >= 0, f\"{path} 必须 >= 0\")\n    require(d[\"backend\"] in (\"cpu\", \"gpu\"), \"backend 必须是 cpu 或 gpu\")\n    require(bool(d[\"name\"].strip()), \"name 不能为空\")\n    require(bool(d[\"output_dir\"].strip()), \"output_dir 不能为空\")\n    require(0 <= d[\"train\"][\"gamma\"] <= 1, \"train.gamma 必须在 [0, 1] 内\")\n    require(0 <= d[\"env\"][\"dynamics\"][\"scale_range\"] < 1, \"env.dynamics.scale_range 必须在 [0, 1) 内\")\n    require(0 < get(\"env.sensors.depth_hfov_deg\") < 180,\n            \"env.sensors.depth_hfov_deg 必须在 (0, 180) 内\")\n    require(0 < get(\"env.sensors.rays_fov_deg\") <= 360,\n            \"env.sensors.rays_fov_deg 必须在 (0, 360] 内\")\n    require(all(n > 0 for n in d[\"env\"][\"sensors\"][\"depth_res\"]), \"env.sensors.depth_res 每个分辨率必须 > 0\")\n    for path in (\"env.mover.speed_range\", \"env.mover.path_length_range\"):\n        lo, hi = get(path)\n        require(0 <= lo <= hi, f\"{path} 需要 0 <= 下界 <= 上界\")\n    dynamics = d[\"env\"][\"dynamics\"]\n    profiles, probs = dynamics[\"profiles\"], dynamics[\"profile_probs\"]\n    require(bool(profiles), \"env.dynamics.profiles 不能为空\")\n    for profile in profiles:\n        require(profile in (\"agile\", \"heavy\") or profile in dynamics[\"custom_profiles\"],\n                f\"env.dynamics.profiles：未知动力学 profile {profile!r}\")\n    if probs is not None:\n        require(len(probs) == len(profiles), \"env.dynamics.profile_probs 长度必须匹配 profiles\")\n        require(all(p >= 0 for p in probs), \"env.dynamics.profile_probs 概率不能为负\")\n        require(math.isclose(sum(probs), 1.0, rel_tol=1e-7, abs_tol=1e-7),\n                \"env.dynamics.profile_probs 总和必须为 1\")\n    return errors\n\n\ndef _check_json_config(data) -> None:\n    \"\"\"Also check untyped dictionaries before dataclass copying or JSON output.\"\"\"\n    try:\n        json.dumps(data, allow_nan=False)\n    except (ValueError, TypeError, OverflowError, RecursionError) as exc:\n        raise PreflightError(\n            f\"配置必须是可序列化的 JSON 数据，数值须有限且不能有循环引用：{exc}\"\n        ) from exc\n\n\ndef resolve_config(path: Path, overrides: list[str] | None = None) -> dict:\n    _yaml_module()\n    from gnav import config as config_module\n\n    if Path(config_module.__file__).resolve() != SRC / \"gnav\" / \"config.py\":\n        raise PreflightError(\"gnav.config 来自其他工作树；请重新启动 Python 并使用本入口。\")\n    data = _load_tree(path)\n    for override in overrides or []:\n        if \"=\" not in override or any(not p for p in override.split(\"=\", 1)[0].split(\".\")):\n            raise PreflightError(f\"覆盖参数必须为 section.key=value：{override}\")\n    try:\n        data = config_module.apply_overrides(data, overrides or [])\n    except (ValueError, TypeError, AttributeError, _yaml_module().YAMLError) as exc:\n        raise PreflightError(f\"无法应用覆盖参数：{exc}\") from exc\n    errors = _type_errors(data, config_module.ExperimentConfig)\n    if errors:\n        raise PreflightError(\"配置类型检查失败：\\n\" + \"\\n\".join(errors[:30]))\n    # Bare dict fields can contain values outside their dataclass type annotations.\n    # Check before asdict/deepcopy, which would recurse forever on a YAML alias cycle.\n    _check_json_config(data)\n    cfg = config_module.config_from_dict(data)\n    resolved = cfg.to_dict()\n    _check_json_config(resolved)\n    errors = validate_config(cfg)\n    if errors:\n        raise PreflightError(\"配置预检失败：\\n\" + \"\\n\".join(errors[:30]))\n    return {\n        \"ok\": True, \"command\": \"config\", \"input\": str(path.resolve()),\n        \"source\": str(Path(config_module.__file__).resolve()),\n        \"digest\": cfg.digest(), \"config\": resolved,\n        \"scope\": \"类型和常见参数预检通过；未创建环境、运行实验或验证科研结论。\",\n    }\n\n\ndef _json_loads(text: str):\n    def reject_constant(value):\n        raise ValueError(f\"非标准 JSON 数值 {value}\")\n\n    def finite_float(value):\n        number = float(value)\n        if not math.isfinite(number):\n            raise ValueError(f\"JSON 数值超出有限浮点范围：{value}\")\n        return number\n\n    return json.loads(text, parse_constant=reject_constant, parse_float=finite_float)\n\n\ndef inspect_run(path: Path) -> dict:\n    \"\"\"Inspect ordinary metadata only, never pickle/PT/NPZ or executable code.\"\"\"\n    if not path.is_dir():\n        raise PreflightError(f\"run 目录不存在：{path}\")\n    report = {\n        \"ok\": True, \"command\": \"inspect-run\", \"path\": str(path.resolve()),\n        \"files\": {}, \"errors\": [],\n        \"scope\": \"只读元数据检查；文件齐全不等于实验完成、结果可信或可复现。\",\n    }\n    for name in (\"config.yaml\", \"provenance.json\", \"metrics.json\", \"metrics.jsonl\"):\n        file = path / name\n        if not file.exists():\n            report[\"files\"][name] = {\"present\": False}\n            if name in (\"config.yaml\", \"provenance.json\"):\n                report[\"errors\"].append(f\"缺少 {name}\")\n            continue\n        entry = {\"present\": True}\n        report[\"files\"][name] = entry\n        try:\n            if name == \"config.yaml\":\n                result = resolve_config(file)\n                entry.update({\"valid\": True, \"digest\": result[\"digest\"],\n                              \"experiment_name\": result[\"config\"][\"name\"]})\n            elif name == \"metrics.jsonl\":\n                count = 0\n                keys = set()\n                for line_number, line in enumerate(_read_text(file).splitlines(), 1):\n                    if not line.strip():\n                        continue\n                    try:\n                        record = _json_loads(line)\n                        if not isinstance(record, dict):\n                            raise ValueError(\"每条记录必须是对象\")\n                    except (ValueError, TypeError) as exc:\n                        raise PreflightError(f\"第 {line_number} 行：{exc}\") from exc\n                    count += 1\n                    keys.update(record)\n                if count == 0:\n                    raise PreflightError(\"metrics.jsonl 没有记录\")\n                entry.update({\"valid\": True, \"records\": count, \"keys\": sorted(keys)})\n            else:\n                data = _json_loads(_read_text(file))\n                if not isinstance(data, dict):\n                    raise PreflightError(\"顶层必须是 JSON 对象\")\n                entry.update({\"valid\": True, \"keys\": sorted(data)})\n                if name == \"provenance.json\":\n                    entry[\"summary\"] = {key: data[key] for key in (\n                        \"python\", \"torch\", \"torch_cuda\", \"genesis\", \"git_commit\", \"git_dirty\", \"time\", \"synthetic\"\n                    ) if key in data}\n                else:\n                    entry[\"summary\"] = {key: data[key] for key in (\n                        \"policy\", \"n_episodes\", \"eval_seed\", \"config_digest\", \"synthetic\"\n                    ) if key in data}\n        except (PreflightError, ValueError, TypeError, RecursionError) as exc:\n            entry.update({\"valid\": False, \"error\": str(exc)})\n            report[\"errors\"].append(f\"{name}：{exc}\")\n    if not any(report[\"files\"][name][\"present\"] for name in (\"metrics.json\", \"metrics.jsonl\")):\n        report[\"errors\"].append(\"缺少 metrics.json 或 metrics.jsonl；可能尚未开始记录指标\")\n    metrics = report[\"files\"][\"metrics.json\"]\n    config = report[\"files\"][\"config.yaml\"]\n    stored_digest = metrics.get(\"summary\", {}).get(\"config_digest\")\n    if stored_digest is not None and config.get(\"valid\") and stored_digest != config[\"digest\"]:\n        report[\"errors\"].append(\"metrics.json 的 config_digest 与 config.yaml 不匹配\")\n    report[\"ok\"] = not report[\"errors\"]\n    return report\n\n\ndef parser() -> argparse.ArgumentParser:\n    p = argparse.ArgumentParser(description=\"Genesis 开发工作台：轻量预检，不启动仿真、不修改文件。\")\n    sub = p.add_subparsers(dest=\"command\", required=True)\n    doctor_parser = sub.add_parser(\"doctor\", help=\"检查解释器、包元数据与真实导入路径\")\n    doctor_parser.add_argument(\"--json\", action=\"store_true\", help=\"输出可供脚本读取的 JSON\")\n    cfg = sub.add_parser(\"config\", help=\"解析真实配置、覆盖参数并做类型/常见参数预检\")\n    cfg.add_argument(\"--config\", default=\"configs/eval.yaml\", metavar=\"PATH\")\n    cfg.add_argument(\"--json\", action=\"store_true\")\n    cfg.add_argument(\"overrides\", nargs=\"*\", metavar=\"key=value\")\n    run = sub.add_parser(\"inspect-run\", help=\"只读检查已有 run 的元数据\")\n    run.add_argument(\"path\", type=Path)\n    run.add_argument(\"--json\", action=\"store_true\")\n    return p\n\n\ndef main(argv: list[str] | None = None) -> int:\n    args = parser().parse_args(argv)\n    try:\n        if args.command == \"doctor\":\n            report = doctor()\n        elif args.command == \"config\":\n            report = resolve_config(Path(args.config), args.overrides)\n        else:\n            report = inspect_run(args.path)\n    except (PreflightError, RecursionError) as exc:\n        report = {\"ok\": False, \"command\": args.command, \"error\": str(exc)}\n    if args.json:\n        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))\n    elif not report[\"ok\"]:\n        print(\"检查未通过：\", file=sys.stderr)\n        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), file=sys.stderr)\n    else:\n        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))\n    return 0 if report[\"ok\"] else 2\n\n\nif __name__ == \"__main__\":\n    raise SystemExit(main())\n",
    "developer/labs/paired_comparison/starter.py": "\"\"\"Intentionally faulty exercise. Edit this file to satisfy test_contract.py.\n\nThis is not copied production code: direction and missing-value bugs are seeded\nfor practice. The production function already uses B-A and filters non-finite\ndifferences. Its duplicate-ID overwrite is the real motivation for this lab.\n\"\"\"\n\nimport math\nimport statistics\n\n\ndef paired_comparison(rows_a, rows_b, keys=(\"success\", \"collided\", \"length\")):\n    # TODO 1: Define and enforce ID validity; reject duplicates before indexing.\n    indexed_a = {(row[\"env_id\"], row[\"episode_idx\"]): row for row in rows_a}\n    indexed_b = {(row[\"env_id\"], row[\"episode_idx\"]): row for row in rows_b}\n    common = sorted(indexed_a.keys() & indexed_b.keys())\n    result = {\n        \"direction\": \"b - a\",\n        \"n_paired\": len(common),\n        \"unmatched_a\": len(indexed_a.keys() - indexed_b.keys()),\n        \"unmatched_b\": len(indexed_b.keys() - indexed_a.keys()),\n        \"metrics\": {},\n    }\n    for key in keys:\n        # TODO 2: Match the declared sign; handle unavailable values per metric.\n        differences = [indexed_a[i].get(key, 0) - indexed_b[i].get(key, 0) for i in common]\n        n_valid = len(differences)\n        # TODO 3: Distinguish unavailable uncertainty from a measured zero width.\n        half_width = 0.0\n        if n_valid >= 2:\n            half_width = 1.96 * statistics.stdev(differences) / math.sqrt(n_valid)\n        result[\"metrics\"][key] = {\n            \"mean_diff\": statistics.mean(differences) if n_valid else 0.0,\n            \"ci95\": half_width,\n            \"n_valid\": n_valid,\n            \"n_dropped\": 0,\n        }\n    return result\n",
    "developer/labs/paired_comparison/solution.py": "\"\"\"Reference implementation for the lab, not a replacement for gnav statistics.\n\nThe difference is always B minus A. Every metric independently excludes missing,\nnon-numeric, non-finite, or overflowing differences. ``ci95`` is the half-width\n1.96 * sample standard deviation / sqrt(n), or None when fewer than two valid\npairs exist. It is a normal approximation, not a coverage guarantee.\n\"\"\"\n\nfrom collections.abc import Mapping, Sequence\nimport math\nfrom numbers import Real\nimport statistics\nfrom typing import Any\n\n\ndef _index(rows: Sequence[Mapping[str, Any]], label: str) -> dict:\n    indexed = {}\n    for position, row in enumerate(rows):\n        if not isinstance(row, Mapping):\n            raise ValueError(f\"{label} row {position}: expected an object\")\n        try:\n            identity = (row[\"env_id\"], row[\"episode_idx\"])\n        except KeyError as error:\n            raise ValueError(f\"{label} row {position}: missing episode ID\") from error\n        if any(type(value) is not int or value < 0 for value in identity):\n            raise ValueError(f\"{label} row {position}: episode IDs must be nonnegative integers\")\n        if identity in indexed:\n            raise ValueError(f\"{label}: duplicate episode ID {identity}\")\n        indexed[identity] = row\n    return indexed\n\n\ndef _finite_number(value: Any) -> bool:\n    if isinstance(value, bool) or not isinstance(value, Real):\n        return False\n    try:\n        return math.isfinite(value)\n    except (OverflowError, TypeError, ValueError):\n        return False\n\n\ndef paired_comparison(rows_a, rows_b, keys=(\"success\", \"collided\", \"length\")):\n    \"\"\"Compare unique episodes by ID, reporting metric-specific valid pair counts.\"\"\"\n    keys = tuple(keys)\n    if any(not isinstance(key, str) or not key for key in keys):\n        raise ValueError(\"metric keys must be nonempty strings\")\n    if len(set(keys)) != len(keys):\n        raise ValueError(\"metric keys must be unique\")\n    indexed_a, indexed_b = _index(rows_a, \"A\"), _index(rows_b, \"B\")\n    common = sorted(indexed_a.keys() & indexed_b.keys())\n    result = {\n        \"direction\": \"b - a\",\n        \"n_paired\": len(common),\n        \"unmatched_a\": len(indexed_a.keys() - indexed_b.keys()),\n        \"unmatched_b\": len(indexed_b.keys() - indexed_a.keys()),\n        \"metrics\": {},\n    }\n    for key in keys:\n        differences = []\n        for identity in common:\n            a, b = indexed_a[identity].get(key), indexed_b[identity].get(key)\n            if not (_finite_number(a) and _finite_number(b)):\n                continue\n            difference = float(b) - float(a)\n            if math.isfinite(difference):\n                differences.append(difference)\n        n_valid = len(differences)\n        ci95 = None\n        if n_valid >= 2:\n            ci95 = 1.96 * (statistics.stdev(differences) / math.sqrt(n_valid))\n            if not math.isfinite(ci95):\n                raise ValueError(f\"{key}: confidence half-width exceeds finite numeric range\")\n        result[\"metrics\"][key] = {\n            \"mean_diff\": statistics.mean(differences) if n_valid else None,\n            \"ci95\": ci95,\n            \"n_valid\": n_valid,\n            \"n_dropped\": len(common) - n_valid,\n        }\n    return result\n",
    "developer/labs/paired_comparison/test_contract.py": "\"\"\"Default: reference solution. LAB_IMPLEMENTATION=starter opts into the red lab.\"\"\"\n\nimport copy\nimport importlib\nimport json\nimport math\nimport os\nfrom pathlib import Path\nimport unittest\n\nIMPLEMENTATION = os.environ.get(\"LAB_IMPLEMENTATION\", \"solution\")\nif IMPLEMENTATION not in {\"starter\", \"solution\"}:\n    raise ValueError(\"LAB_IMPLEMENTATION must be starter or solution\")\ncompare = importlib.import_module(f\"developer.labs.paired_comparison.{IMPLEMENTATION}\").paired_comparison\n\n\ndef row(episode, **metrics):\n    return {\"env_id\": 0, \"episode_idx\": episode, **metrics}\n\n\nclass PairedComparisonContract(unittest.TestCase):\n    def test_direction_is_b_minus_a(self):\n        result = compare([row(0, score=10)], [row(0, score=13)], [\"score\"])\n        self.assertEqual(result[\"direction\"], \"b - a\")\n        self.assertEqual(result[\"metrics\"][\"score\"][\"mean_diff\"], 3)\n\n    def test_duplicate_id_is_rejected_on_either_side_even_if_unmatched(self):\n        duplicate = [row(5, score=1), row(5, score=8)]\n        for a, b, label in ((duplicate, [row(0)], \"A\"), ([row(0)], duplicate, \"B\")):\n            with self.subTest(side=label):\n                with self.assertRaisesRegex(ValueError, f\"{label}.*duplicate\"):\n                    compare(a, b, [\"score\"])\n\n    def test_match_by_id_not_input_position(self):\n        a = [row(0, score=10), row(1, score=20), row(2, score=1000)]\n        b = [row(1, score=24), row(0, score=12), row(3, score=10000)]\n        result = compare(a, b, [\"score\"])\n        self.assertEqual(result[\"n_paired\"], 2)\n        self.assertEqual((result[\"unmatched_a\"], result[\"unmatched_b\"]), (1, 1))\n        self.assertEqual(result[\"metrics\"][\"score\"][\"mean_diff\"], 3)\n        self.assertAlmostEqual(result[\"metrics\"][\"score\"][\"ci95\"], 1.96)\n\n    def test_metric_specific_valid_counts_and_normal_half_width(self):\n        a = [row(0, score=10, length=10), row(1, score=20, length=20), row(2, score=30)]\n        b = [row(0, score=12, length=8), row(1, score=24, length=16), row(2, score=36, length=7)]\n        result = compare(a, b, [\"score\", \"length\"])\n        self.assertEqual(result[\"n_paired\"], 3)\n        score, length = result[\"metrics\"][\"score\"], result[\"metrics\"][\"length\"]\n        self.assertEqual((score[\"n_valid\"], length[\"n_valid\"], length[\"n_dropped\"]), (3, 2, 1))\n        self.assertEqual((score[\"mean_diff\"], length[\"mean_diff\"]), (4, -3))\n        self.assertAlmostEqual(score[\"ci95\"], 1.96 * 2 / math.sqrt(3))\n        self.assertAlmostEqual(length[\"ci95\"], 1.96)\n\n    def test_invalid_and_nonfinite_metric_values_are_excluded(self):\n        invalid = [None, \"3\", True, float(\"nan\"), float(\"inf\"), float(\"-inf\")]\n        for value in invalid:\n            for side in (\"A\", \"B\"):\n                with self.subTest(value=repr(value), side=side):\n                    a = [row(0, score=2), row(1, score=value if side == \"A\" else 2)]\n                    b = [row(0, score=5), row(1, score=value if side == \"B\" else 5)]\n                    metric = compare(a, b, [\"score\"])[\"metrics\"][\"score\"]\n                    self.assertEqual((metric[\"mean_diff\"], metric[\"n_valid\"], metric[\"n_dropped\"]), (3, 1, 1))\n                    self.assertIsNone(metric[\"ci95\"])\n\n    def test_overflowing_difference_is_excluded(self):\n        metric = compare([row(0, score=-1e308)], [row(0, score=1e308)], [\"score\"])[\"metrics\"][\"score\"]\n        self.assertEqual((metric[\"n_valid\"], metric[\"n_dropped\"]), (0, 1))\n        self.assertIsNone(metric[\"mean_diff\"])\n\n    def test_no_match_or_no_valid_value_is_json_safe(self):\n        for a, b in (([row(0)], [row(1)]), ([row(0)], [row(0)]), ([], [])):\n            with self.subTest(a=a, b=b):\n                result = compare(a, b, [\"score\"])\n                self.assertIsNone(result[\"metrics\"][\"score\"][\"mean_diff\"])\n                self.assertIsNone(result[\"metrics\"][\"score\"][\"ci95\"])\n                json.dumps(result, allow_nan=False)\n\n    def test_single_pair_has_no_estimated_uncertainty(self):\n        metric = compare([row(0, score=2)], [row(0, score=5)], [\"score\"])[\"metrics\"][\"score\"]\n        self.assertEqual(metric[\"n_valid\"], 1)\n        self.assertIsNone(metric[\"ci95\"])\n\n    def test_constant_differences_have_zero_width(self):\n        metric = compare([row(0, score=2), row(1, score=5)], [row(0, score=5), row(1, score=8)], [\"score\"])[\"metrics\"][\"score\"]\n        self.assertEqual((metric[\"mean_diff\"], metric[\"ci95\"]), (3, 0))\n\n    def test_input_is_not_modified(self):\n        a, b = [row(0, score=2)], [row(0, score=5)]\n        before = copy.deepcopy((a, b))\n        compare(a, b, [\"score\"])\n        self.assertEqual((a, b), before)\n\n    def test_ids_must_be_nonnegative_integers(self):\n        bad_rows = [{\"env_id\": 0}, {\"env_id\": True, \"episode_idx\": 0}, {\"env_id\": 0, \"episode_idx\": -1}, {\"env_id\": 0.0, \"episode_idx\": 0}]\n        for bad in bad_rows:\n            with self.subTest(row=bad):\n                with self.assertRaises(ValueError):\n                    compare([bad], [], [\"score\"])\n\n    def test_metric_keys_have_an_unambiguous_contract(self):\n        for keys in ([\"score\", \"score\"], [\"\"], [None]):\n            with self.subTest(keys=keys):\n                with self.assertRaises(ValueError):\n                    compare([], [], keys)\n\n    def test_synthetic_fixture_is_explicit_and_reproducible(self):\n        fixture = json.loads((Path(__file__).parent / \"fixtures\" / \"synthetic.json\").read_text(encoding=\"utf-8\"))\n        result = compare(fixture[\"a\"], fixture[\"b\"], fixture[\"keys\"])\n        self.assertEqual(result[\"n_paired\"], 3)\n        self.assertEqual((result[\"unmatched_a\"], result[\"unmatched_b\"]), (1, 1))\n        self.assertAlmostEqual(result[\"metrics\"][\"success\"][\"mean_diff\"], 2 / 3)\n        self.assertAlmostEqual(result[\"metrics\"][\"collided\"][\"mean_diff\"], -1 / 3)\n        self.assertEqual(result[\"metrics\"][\"length\"][\"n_valid\"], 2)\n        self.assertEqual(result[\"metrics\"][\"length\"][\"mean_diff\"], -3)\n        json.dumps(result, allow_nan=False)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n",
    "developer/labs/gae/starter.py": "\"\"\"Intentionally wrong masks. Implement compute_gae yourself; checks are provided.\"\"\"\n\nfrom .contract import validate\n\n\ndef compute_gae(rewards, values, next_values, terminated, truncated, *, gamma=0.99, lam=0.95, valid=None):\n    time_steps, batch_size, valid = validate(\n        rewards, values, next_values, terminated, truncated, valid, gamma, lam\n    )\n    deltas = [[0.0] * batch_size for _ in range(time_steps)]\n    advantages = [[0.0] * batch_size for _ in range(time_steps)]\n    returns = [[0.0] * batch_size for _ in range(time_steps)]\n    for batch in range(batch_size):\n        carry = 0.0\n        for time in reversed(range(time_steps)):\n            if not valid[time][batch]:\n                carry = 0.0\n                continue\n            value = float(values[time][batch])\n            # TODO: Which boundary removes the value bootstrap?\n            done = terminated[time][batch] or truncated[time][batch]\n            bootstrap = 0.0 if done else float(next_values[time][batch])\n            delta = float(rewards[time][batch]) + gamma * bootstrap - value\n            # TODO: Which boundary prevents the NEXT episode's advantage leaking?\n            tail = 0.0 if terminated[time][batch] else carry\n            carry = delta + gamma * lam * tail\n            deltas[time][batch] = delta\n            advantages[time][batch] = carry\n            returns[time][batch] = carry + value\n    return {\"deltas\": deltas, \"advantages\": advantages, \"returns\": returns}\n",
    "developer/labs/gae/solution.py": "\"\"\"Reference GAE with separate bootstrap and trace masks, standard library only.\"\"\"\n\nfrom .contract import finite_number, validate\n\n\ndef compute_gae(rewards, values, next_values, terminated, truncated, *, gamma=0.99, lam=0.95, valid=None):\n    \"\"\"Return deltas, advantages, returns as time-major [T, B] float lists.\n\n    next_values[t][b] is V of this transition's TRUE next observation, before\n    reset, evaluated with the same frozen critic. It is not generally values[t+1].\n    Trailing padding emits zeros and is not a training sample. This function\n    neither normalizes advantages nor carries a trace across rollout chunks.\n    \"\"\"\n    time_steps, batch_size, valid = validate(\n        rewards, values, next_values, terminated, truncated, valid, gamma, lam\n    )\n    deltas = [[0.0] * batch_size for _ in range(time_steps)]\n    advantages = [[0.0] * batch_size for _ in range(time_steps)]\n    returns = [[0.0] * batch_size for _ in range(time_steps)]\n    for batch in range(batch_size):\n        carry = 0.0\n        for time in reversed(range(time_steps)):\n            if not valid[time][batch]:\n                carry = 0.0\n                continue\n            value = float(values[time][batch])\n            bootstrap = 0.0 if terminated[time][batch] else float(next_values[time][batch])\n            delta = float(rewards[time][batch]) + gamma * bootstrap - value\n            tail = 0.0 if (terminated[time][batch] or truncated[time][batch]) else carry\n            carry = delta + gamma * lam * tail\n            deltas[time][batch] = finite_number(delta, f\"delta[{time}][{batch}]\")\n            advantages[time][batch] = finite_number(carry, f\"advantage[{time}][{batch}]\")\n            returns[time][batch] = finite_number(carry + value, f\"return[{time}][{batch}]\")\n    return {\"deltas\": deltas, \"advantages\": advantages, \"returns\": returns}\n",
    "developer/labs/gae/test_contract.py": "\"\"\"Boundary oracles for GAE; select the unfinished exercise explicitly via env.\"\"\"\n\nimport copy\nimport importlib\nimport json\nimport os\nimport unittest\n\nfrom .cases import one_step_case, reset_boundary_case\n\nIMPLEMENTATION = os.environ.get(\"LAB_IMPLEMENTATION\", \"solution\")\nif IMPLEMENTATION not in {\"starter\", \"solution\"}:\n    raise ValueError(\"LAB_IMPLEMENTATION must be starter or solution\")\ncompute_gae = importlib.import_module(f\"developer.labs.gae.{IMPLEMENTATION}\").compute_gae\n\n\nclass GAEContract(unittest.TestCase):\n    def assertMatrixAlmostEqual(self, actual, expected):\n        self.assertEqual(len(actual), len(expected))\n        for actual_row, expected_row in zip(actual, expected):\n            self.assertEqual(len(actual_row), len(expected_row))\n            for a, b in zip(actual_row, expected_row):\n                self.assertAlmostEqual(a, b, places=10)\n\n    def test_termination_removes_bootstrap_but_truncation_preserves_it(self):\n        # r=2, V=1, gamma=.9, V(next)=10: terminal delta=1, trunc delta=10.\n        terminal = compute_gae(**one_step_case(terminated=True))\n        truncated = compute_gae(**one_step_case(truncated=True))\n        self.assertEqual(terminal[\"advantages\"], [[1.0]])\n        self.assertEqual(truncated[\"advantages\"], [[10.0]])\n        self.assertEqual(truncated[\"returns\"], [[11.0]])\n\n    def test_truncation_stops_trace_into_next_episode(self):\n        # gamma=lambda=1, V=0: no bootstrap contribution, isolating trace masking.\n        result = compute_gae([[2], [100]], [[0], [0]], [[0], [None]],\n                             [[False], [True]], [[True], [False]], gamma=1, lam=1)\n        self.assertEqual(result[\"advantages\"], [[2.0], [100.0]])\n\n    def test_hand_calculated_two_episode_oracle(self):\n        # delta=(1+.9*3-2, 2+.9*4-3, 100-50)=(1.7,2.6,50).\n        # A1=2.6, A0=1.7+.72*2.6=3.572; A2=50 is a separate episode.\n        result = compute_gae(**reset_boundary_case())\n        self.assertMatrixAlmostEqual(result[\"deltas\"], [[1.7], [2.6], [50]])\n        self.assertMatrixAlmostEqual(result[\"advantages\"], [[3.572], [2.6], [50]])\n        self.assertMatrixAlmostEqual(result[\"returns\"], [[5.572], [5.6], [100]])\n\n    def test_new_episode_reward_cannot_change_previous_episode_advantage(self):\n        case = reset_boundary_case()\n        before = compute_gae(**case)\n        case[\"rewards\"][2][0] = 1000000\n        after = compute_gae(**case)\n        self.assertEqual(before[\"advantages\"][:2], after[\"advantages\"][:2])\n        self.assertNotEqual(before[\"advantages\"][2], after[\"advantages\"][2])\n\n    def test_batch_columns_do_not_leak_across_different_boundaries(self):\n        # Column 0 terminates at t0; column 1 continues until t1 termination.\n        result = compute_gae([[1, 10], [2, 20]], [[0, 0], [0, 0]], [[None, 0], [None, None]],\n                             [[True, False], [True, True]], [[False, False], [False, False]],\n                             gamma=1, lam=1)\n        self.assertEqual(result[\"advantages\"], [[1.0, 30.0], [2.0, 20.0]])\n\n    def test_rollout_end_bootstraps_without_inventing_a_terminal_state(self):\n        result = compute_gae(**one_step_case())\n        self.assertEqual(result[\"advantages\"], [[10.0]])\n        self.assertEqual(result[\"returns\"], [[11.0]])\n\n    def test_lambda_zero_equals_one_step_td_and_gamma_zero_equals_reward_minus_value(self):\n        case = reset_boundary_case()\n        case[\"lam\"] = 0\n        result = compute_gae(**case)\n        self.assertMatrixAlmostEqual(result[\"advantages\"], [[1.7], [2.6], [50]])\n        case[\"gamma\"] = 0\n        result = compute_gae(**case)\n        self.assertEqual(result[\"advantages\"], [[-1.0], [-1.0], [50.0]])\n        self.assertEqual(result[\"returns\"], case[\"rewards\"])\n\n    def test_gamma_and_lambda_one_match_hand_summed_bootstrapped_return(self):\n        result = compute_gae([[2], [3]], [[1], [4]], [[4], [5]],\n                             [[False], [False]], [[False], [False]], gamma=1, lam=1)\n        # G1=3+5=8, G0=2+3+5=10; subtract V=(1,4) => A=(9,4).\n        self.assertEqual(result[\"advantages\"], [[9.0], [4.0]])\n        self.assertEqual(result[\"returns\"], [[10.0], [8.0]])\n\n    def test_trailing_padding_is_ignored_and_cannot_contaminate_valid_cells(self):\n        result = compute_gae([[2, 10], [float(\"nan\"), 20], [None, None]],\n                             [[1, 0], [None, 0], [None, None]],\n                             [[4, 0], [None, None], [None, None]],\n                             [[False, False], [False, True], [False, False]],\n                             [[False, False], [False, False], [False, False]],\n                             gamma=1, lam=1, valid=[[True, True], [False, True], [False, False]])\n        self.assertEqual(result[\"advantages\"], [[5.0, 30.0], [0.0, 20.0], [0.0, 0.0]])\n        self.assertEqual(result[\"returns\"], [[6.0, 30.0], [0.0, 20.0], [0.0, 0.0]])\n        json.dumps(result, allow_nan=False)\n\n    def test_interior_padding_is_rejected(self):\n        case = reset_boundary_case()\n        case[\"valid\"] = [[True], [False], [True]]\n        with self.assertRaisesRegex(ValueError, \"prefix\"):\n            compute_gae(**case)\n\n    def test_all_padding_column_emits_only_zeros(self):\n        result = compute_gae([[None]], [[None]], [[None]], [[False]], [[False]], valid=[[False]])\n        self.assertEqual(result, {\"deltas\": [[0.0]], \"advantages\": [[0.0]], \"returns\": [[0.0]]})\n\n    def test_terminal_next_value_is_unused_even_when_nan_or_flags_both_true(self):\n        for value in (None, float(\"nan\")):\n            case = one_step_case(terminated=True, truncated=True, next_value=value)\n            self.assertEqual(compute_gae(**case)[\"advantages\"], [[1.0]])\n\n    def test_valid_numeric_inputs_must_be_finite(self):\n        for field in (\"rewards\", \"values\", \"next_values\"):\n            for value in (None, True, \"1\", float(\"nan\"), float(\"inf\")):\n                with self.subTest(field=field, value=repr(value)):\n                    case = one_step_case(truncated=True)\n                    case[field][0][0] = value\n                    with self.assertRaisesRegex(ValueError, \"finite\"):\n                        compute_gae(**case)\n\n    def test_nonfinite_computed_result_is_rejected(self):\n        case = one_step_case(next_value=1e308)\n        case[\"rewards\"] = [[1e308]]\n        case[\"values\"] = [[0.0]]\n        case[\"gamma\"] = 1\n        with self.assertRaisesRegex(ValueError, \"finite\"):\n            compute_gae(**case)\n\n    def test_rectangular_shape_and_boolean_masks_are_enforced(self):\n        for field, bad in ((\"values\", []), (\"next_values\", [[1, 2]]),\n                           (\"rewards\", [[1], []]), (\"terminated\", [[1]]), (\"valid\", [[0]])):\n            with self.subTest(field=field):\n                case = one_step_case()\n                case[field] = bad\n                with self.assertRaises(ValueError):\n                    compute_gae(**case)\n        with self.assertRaises(ValueError):\n            compute_gae([], [], [], [], [])\n        with self.assertRaises(ValueError):\n            compute_gae([[]], [[]], [[]], [[]], [[]])\n\n    def test_gamma_lambda_range_and_input_immutability(self):\n        for field in (\"gamma\", \"lam\"):\n            for value in (-0.1, 1.1, True, float(\"nan\")):\n                with self.subTest(field=field, value=repr(value)):\n                    case = one_step_case()\n                    case[field] = value\n                    with self.assertRaises(ValueError):\n                        compute_gae(**case)\n        case = reset_boundary_case()\n        before = copy.deepcopy(case)\n        compute_gae(**case)\n        self.assertEqual(case, before)\n\n    def test_using_reset_observation_is_a_detectable_collection_error(self):\n        actual_next = compute_gae(**one_step_case(truncated=True, next_value=10))\n        reset_next = compute_gae(**one_step_case(truncated=True, next_value=100))\n        self.assertEqual(actual_next[\"advantages\"], [[10.0]])\n        self.assertEqual(reset_next[\"advantages\"], [[91.0]])\n        # The GAE function cannot know that the finite value 100 came from reset.\n        self.assertEqual(reset_next[\"advantages\"][0][0] - actual_next[\"advantages\"][0][0], 81)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n",
    "developer/labs/gae/cases.py": "\"\"\"Hand-selected transition data, not simulator output or training evidence.\"\"\"\n\n\ndef reset_boundary_case():\n    \"\"\"Episode 1 truncates at t=1; t=2 belongs to a new episode and terminates.\"\"\"\n    return {\n        \"rewards\": [[1.0], [2.0], [100.0]],\n        \"values\": [[2.0], [3.0], [50.0]],\n        \"next_values\": [[3.0], [4.0], [None]],\n        \"terminated\": [[False], [False], [True]],\n        \"truncated\": [[False], [True], [False]],\n        \"gamma\": 0.9,\n        \"lam\": 0.8,\n    }\n\n\ndef one_step_case(*, terminated=False, truncated=False, next_value=10.0):\n    return {\n        \"rewards\": [[2.0]], \"values\": [[1.0]], \"next_values\": [[next_value]],\n        \"terminated\": [[terminated]], \"truncated\": [[truncated]],\n        \"gamma\": 0.9, \"lam\": 0.8,\n    }\n",
    "developer/labs/gae/contract.py": "\"\"\"Input checks shared by the exercise and answer, leaving the GAE work to you.\"\"\"\n\nimport math\nfrom numbers import Real\n\n\ndef finite_number(value, name):\n    if isinstance(value, bool) or not isinstance(value, Real):\n        raise ValueError(f\"{name} must be a finite number\")\n    try:\n        result = float(value)\n    except (OverflowError, ValueError) as error:\n        raise ValueError(f\"{name} must be a finite number\") from error\n    if not math.isfinite(result):\n        raise ValueError(f\"{name} must be a finite number\")\n    return result\n\n\ndef validate(rewards, values, next_values, terminated, truncated, valid, gamma, lam):\n    for name, value in ((\"gamma\", gamma), (\"lam\", lam)):\n        number = finite_number(value, name)\n        if not 0 <= number <= 1:\n            raise ValueError(f\"{name} must lie in [0, 1]\")\n    if not isinstance(rewards, (list, tuple)) or not rewards:\n        raise ValueError(\"expected nonempty time-major [T, B] rewards\")\n    if not isinstance(rewards[0], (list, tuple)) or not rewards[0]:\n        raise ValueError(\"expected nonempty batch dimension B\")\n    time_steps, batch_size = len(rewards), len(rewards[0])\n    if valid is None:\n        valid = [[True] * batch_size for _ in range(time_steps)]\n    matrices = {\"rewards\": rewards, \"values\": values, \"next_values\": next_values,\n                \"terminated\": terminated, \"truncated\": truncated, \"valid\": valid}\n    for name, matrix in matrices.items():\n        if not isinstance(matrix, (list, tuple)) or len(matrix) != time_steps:\n            raise ValueError(f\"{name}: expected shape [{time_steps}, {batch_size}]\")\n        if any(not isinstance(row, (list, tuple)) or len(row) != batch_size for row in matrix):\n            raise ValueError(f\"{name}: expected shape [{time_steps}, {batch_size}]\")\n    for name, mask in ((\"terminated\", terminated), (\"truncated\", truncated), (\"valid\", valid)):\n        if any(type(cell) is not bool for row in mask for cell in row):\n            raise ValueError(f\"{name} must contain bool cells, not 0/1 numbers\")\n    for batch in range(batch_size):\n        padding_seen = False\n        for time in range(time_steps):\n            if not valid[time][batch]:\n                padding_seen = True\n                continue\n            if padding_seen:\n                raise ValueError(\"valid must be a prefix per environment; interior padding is ambiguous\")\n            for name, matrix in ((\"rewards\", rewards), (\"values\", values)):\n                finite_number(matrix[time][batch], f\"{name}[{time}][{batch}]\")\n            # True terminal states do not bootstrap. Their unused next value may\n            # be None/NaN; never implement this by multiplying NaN by zero.\n            if not terminated[time][batch]:\n                finite_number(next_values[time][batch], f\"next_values[{time}][{batch}]\")\n    return time_steps, batch_size, valid\n",
    "developer/labs/identification/starter.py": "\"\"\"Implement the estimator after writing predictions in your learning log.\n\nUse common.validate_data and common.mse; do not import solution. The contract is\ndefined in test_contract.py and docs/developer/labs/identification.md.\n\"\"\"\n\nfrom .common import validate_data\n\n\ndef fit_dynamics(states, inputs, *, rank_tolerance=1e-12):\n    states, inputs = validate_data(states, inputs)\n    # TODO 1: Build X rows [states[t], inputs[t]], y[t] = states[t+1].\n    # TODO 2: Compute the five sums and the numerical rank/condition of X.\n    # TODO 3: Return no unique a/b for rank < 2 (do not hide it with epsilon).\n    # TODO 4: Solve the 2x2 normal equations and return training one-step MSE.\n    raise NotImplementedError(\"Implement fit_dynamics after recording your predictions\")\n",
    "developer/labs/identification/solution.py": "\"\"\"Two-parameter OLS reference for teaching, not a production linear solver.\n\nNo regularisation or hidden pseudoinverse: rank-deficient data return no unique\nparameter estimate. Numerical rank is relative to the largest Gram eigenvalue.\n\"\"\"\n\nimport math\n\nfrom .common import mse, validate_data\n\n\ndef fit_dynamics(states, inputs, *, rank_tolerance=1e-12):\n    states, inputs = validate_data(states, inputs)\n    if type(rank_tolerance) not in (float, int) or not 0 < rank_tolerance < 1:\n        raise ValueError(\"rank_tolerance must lie in (0, 1)\")\n    original_x, original_y, original_inputs = states[:-1], states[1:], inputs\n    # A common scale preserves both OLS coefficients and cond(X). Base it on\n    # the design, not y: a large target must not make every design entry tiny.\n    # This prevents the Gram determinant from overflowing/underflowing when a\n    # well-conditioned dataset is merely expressed in very large/small units.\n    scale = max(max(map(abs, original_x)), max(map(abs, inputs))) or 1.0\n    x = [v / scale for v in original_x]\n    inputs = [u / scale for u in inputs]\n    y = [target / scale for target in original_y]\n    if not all(math.isfinite(target) for target in y):\n        raise ValueError(\"Target/design dynamic range exceeds floating-point limits; check units\")\n    xx = math.fsum(v * v for v in x)\n    uu = math.fsum(u * u for u in inputs)\n    xu = math.fsum(v * u for v, u in zip(x, inputs))\n    xy = math.fsum(v * target for v, target in zip(x, y))\n    uy = math.fsum(u * target for u, target in zip(inputs, y))\n    if not all(math.isfinite(number) for number in (xx, uu, xu, xy, uy)):\n        raise ValueError(\"Normal-equation values overflowed; rescale data\")\n    largest = (xx + uu + math.hypot(xx - uu, 2 * xu)) / 2\n    # Equivalent to xx*uu-xu*xu, with less cancellation near collinearity.\n    determinant = xx * math.fsum((u - (xu / xx) * v) ** 2 for v, u in zip(x, inputs)) if xx else 0.0\n    smallest = determinant / largest if largest else 0.0\n    rank = 0 if largest == 0 else (2 if smallest > rank_tolerance * largest else 1)\n    result = {\n        \"n_samples\": len(inputs), \"rank\": rank,\n        \"rank_tolerance\": rank_tolerance,\n        \"condition_x\": math.sqrt(largest / smallest) if rank == 2 else None,\n        \"identifiable\": rank == 2, \"a\": None, \"b\": None, \"train_one_step_mse\": None,\n    }\n    if rank != 2:\n        return result\n    a = (xy * uu - uy * xu) / determinant\n    b = (uy * xx - xy * xu) / determinant\n    if not all(math.isfinite(number) for number in (a, b)):\n        raise ValueError(\"Estimate overflowed; rescale data or improve excitation\")\n    result.update(a=a, b=b, train_one_step_mse=mse(\n        [a * v + b * u for v, u in zip(original_x, original_inputs)], original_y,\n    ))\n    return result\n",
    "developer/labs/identification/common.py": "\"\"\"Data generation and evaluation, kept separate from the learner's estimator.\"\"\"\n\nimport math\nimport random\n\n\ndef finite_vector(values, name):\n    values = list(values)\n    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):\n        raise ValueError(f\"{name} must contain finite numbers, not booleans\")\n    return [float(value) for value in values]\n\n\ndef validate_data(states, inputs):\n    states = finite_vector(states, \"states\")\n    inputs = finite_vector(inputs, \"inputs\")\n    if not inputs or len(states) != len(inputs) + 1:\n        raise ValueError(\"Need N >= 1 inputs and N+1 states\")\n    return states, inputs\n\n\ndef mse(predictions, targets):\n    predictions = finite_vector(predictions, \"predictions\")\n    targets = finite_vector(targets, \"targets\")\n    if not targets or len(predictions) != len(targets):\n        raise ValueError(\"MSE needs equally sized nonempty sequences\")\n    return math.fsum((pred - target) ** 2 for pred, target in zip(predictions, targets)) / len(targets)\n\n\ndef rich_inputs(n, seed):\n    rng = random.Random(seed)\n    return [rng.choice((-1.0, 1.0)) for _ in range(n)]\n\n\ndef simulate(a, b, inputs, *, initial_state=0.0, process_noise_std=0.0,\n             measurement_noise_std=0.0, process_seed=0, measurement_seed=1):\n    \"\"\"v[t+1] = a*v[t] + b*u[t] + w[t]; z[t] = v[t] + e[t].\"\"\"\n    a, b, initial_state, process_noise_std, measurement_noise_std = finite_vector(\n        [a, b, initial_state, process_noise_std, measurement_noise_std], \"parameters\"\n    )\n    if process_noise_std < 0 or measurement_noise_std < 0:\n        raise ValueError(\"Noise standard deviations must be nonnegative\")\n    inputs = finite_vector(inputs, \"inputs\")\n    if not inputs:\n        raise ValueError(\"Need at least one input\")\n    process_rng, measurement_rng = random.Random(process_seed), random.Random(measurement_seed)\n    states = [initial_state]\n    for action in inputs:\n        state = a * states[-1] + b * action + process_rng.gauss(0.0, process_noise_std)\n        if not math.isfinite(state):\n            raise ValueError(\"Trajectory overflowed; reduce horizon or parameter magnitude\")\n        states.append(state)\n    observations = [v + measurement_rng.gauss(0.0, measurement_noise_std) for v in states]\n    return {\"states\": states, \"observations\": observations, \"inputs\": inputs}\n\n\ndef evaluate(a, b, trajectory):\n    \"\"\"One-step uses each observed state; rollout only uses the first observation.\"\"\"\n    observed, inputs = validate_data(trajectory[\"observations\"], trajectory[\"inputs\"])\n    one_step = [a * state + b * action for state, action in zip(observed[:-1], inputs)]\n    rollout = [observed[0]]\n    for action in inputs:\n        rollout.append(a * rollout[-1] + b * action)\n    return {\n        \"one_step_observed_mse\": mse(one_step, observed[1:]),\n        \"rollout_observed_mse\": mse(rollout[1:], observed[1:]),\n        \"rollout_latent_mse\": mse(rollout[1:], trajectory[\"states\"][1:]),\n    }\n",
    "developer/labs/identification/run.py": "\"\"\"Controlled synthetic input-design comparison; no training on holdout data.\"\"\"\n\nimport argparse\nimport importlib\nimport json\nimport math\n\nfrom .common import evaluate, rich_inputs, simulate\n\n\ndef experiment(implementation=\"solution\", *, horizon=128, process_noise=0.03, measurement_noise=0.0):\n    if type(horizon) is not int or not 4 <= horizon <= 10000:\n        raise ValueError(\"horizon must be an integer in [4, 10000]\")\n    for value in (process_noise, measurement_noise):\n        if not math.isfinite(value) or value < 0:\n            raise ValueError(\"noise must be finite and nonnegative\")\n    if implementation not in (\"starter\", \"solution\"):\n        raise ValueError(\"implementation must be starter or solution\")\n    fit = importlib.import_module(f\"developer.labs.identification.{implementation}\").fit_dynamics\n    a, b, initial_state = 0.75, 0.5, 2.0\n    actions = {\"constant\": [1.0] * horizon, \"rich\": rich_inputs(horizon, seed=2026)}\n    report = {\n        \"synthetic\": True, \"purpose\": \"教学：输入设计与有限数据可辨识；不是新科研成果或自我意识证据\",\n        \"implementation\": implementation,\n        \"controls\": {\n            \"true_a\": a, \"true_b\": b, \"horizon\": horizon, \"train_initial_state\": initial_state,\n            \"input_energy_each\": float(horizon), \"input_max_abs_each\": 1.0,\n            \"rich_train_input_seed\": 2026, \"train_process_seed\": 101, \"train_measurement_seed\": 102,\n            \"holdout_input_seed\": 2027, \"holdout_process_seed\": 201, \"holdout_measurement_seed\": 202,\n            \"holdout_initial_state\": -0.3,\n            \"noise_note\": \"同一噪声级别内两个训练组复用相同噪声draws；holdout独立于训练且两组共享。\",\n            \"measurement_noise_std\": measurement_noise,\n            \"rank_note\": \"rank来自本次有限设计矩阵的数值阈值；不等于所有实验下的结构可辨识性。\",\n        },\n        \"comparisons\": [],\n    }\n    for process_std in dict.fromkeys((0.0, process_noise)):\n        holdout = simulate(a, b, rich_inputs(horizon, seed=2027), initial_state=-0.3,\n                           process_noise_std=process_std, measurement_noise_std=measurement_noise,\n                           process_seed=201, measurement_seed=202)\n        comparison = {\"process_noise_std\": process_std, \"fits\": {}}\n        for label, inputs in actions.items():\n            training = simulate(a, b, inputs, initial_state=initial_state,\n                                process_noise_std=process_std, measurement_noise_std=measurement_noise,\n                                process_seed=101, measurement_seed=102)\n            estimate = fit(training[\"observations\"], inputs)\n            if estimate[\"identifiable\"]:\n                estimate[\"parameter_l2_error\"] = math.hypot(estimate[\"a\"] - a, estimate[\"b\"] - b)\n                estimate[\"holdout\"] = evaluate(estimate[\"a\"], estimate[\"b\"], holdout)\n            else:\n                estimate[\"parameter_l2_error\"] = None\n                estimate[\"holdout\"] = None\n                estimate[\"reason\"] = \"按声明数值阈值不输出唯一稳定估计；condition_x=null表示数值秩不足或未定义，不等于证明精确矩阵无唯一解。\"\n            comparison[\"fits\"][label] = estimate\n        report[\"comparisons\"].append(comparison)\n    # Constructive witness: two different models agree on a constant equilibrium\n    # trajectory, but disagree under the same independent, noiseless input sequence.\n    equilibrium = simulate(a, b, actions[\"constant\"], initial_state=initial_state)\n    probe = simulate(a, b, rich_inputs(horizon, seed=2027), initial_state=-0.3)\n    report[\"nonidentifiability_witness\"] = [\n        {\"candidate_a\": candidate_a, \"candidate_b\": candidate_b,\n         \"train\": evaluate(candidate_a, candidate_b, equilibrium),\n         \"holdout\": evaluate(candidate_a, candidate_b, probe)}\n        for candidate_a, candidate_b in ((0.75, 0.5), (0.5, 1.0))\n    ]\n    return report\n\n\ndef main():\n    parser = argparse.ArgumentParser(description=__doc__)\n    parser.add_argument(\"--implementation\", choices=(\"starter\", \"solution\"), default=\"solution\")\n    parser.add_argument(\"--horizon\", type=int, default=128)\n    parser.add_argument(\"--process-noise\", type=float, default=0.03)\n    parser.add_argument(\"--measurement-noise\", type=float, default=0.0)\n    args = parser.parse_args()\n    try:\n        report = experiment(args.implementation, horizon=args.horizon,\n                            process_noise=args.process_noise, measurement_noise=args.measurement_noise)\n        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))\n    except (ValueError, NotImplementedError, OverflowError) as exc:\n        parser.exit(2, f\"Identification lab failed: {exc}\\n\")\n\n\nif __name__ == \"__main__\":\n    main()\n",
    "developer/labs/identification/test_contract.py": "\"\"\"Default solution is green; LAB_IMPLEMENTATION=starter selects the exercise.\"\"\"\n\nimport copy\nimport importlib\nimport json\nimport math\nimport os\nimport unittest\n\nfrom .common import evaluate, rich_inputs, simulate\nfrom .run import experiment\n\nIMPLEMENTATION = os.environ.get(\"LAB_IMPLEMENTATION\", \"solution\")\nif IMPLEMENTATION not in (\"starter\", \"solution\"):\n    raise ValueError(\"LAB_IMPLEMENTATION must be starter or solution\")\nfit = importlib.import_module(f\"developer.labs.identification.{IMPLEMENTATION}\").fit_dynamics\n\n\nclass IdentificationContract(unittest.TestCase):\n    def test_hand_calculation_with_orthogonal_rows(self):\n        # Rows [0,1], [1,0], targets [1,0.5]: a=0.5, b=1.\n        result = fit([0, 1, 0.5], [1, 0])\n        self.assertTrue(result[\"identifiable\"])\n        self.assertEqual(result[\"rank\"], 2)\n        self.assertAlmostEqual(result[\"a\"], 0.5)\n        self.assertAlmostEqual(result[\"b\"], 1)\n        self.assertAlmostEqual(result[\"condition_x\"], 1)\n        self.assertAlmostEqual(result[\"train_one_step_mse\"], 0)\n\n    def test_hand_calculation_with_nonorthogonal_rows(self):\n        # 2=a+b, 0=2a-b; catches swapped targets and wrong determinant.\n        result = fit([1, 2, 0], [1, -1])\n        self.assertAlmostEqual(result[\"a\"], 2 / 3)\n        self.assertAlmostEqual(result[\"b\"], 4 / 3)\n\n    def test_no_motion_and_no_input_gives_rank_zero(self):\n        result = fit([0] * 9, [0] * 8)\n        self.assertEqual(result[\"rank\"], 0)\n        self.assertFalse(result[\"identifiable\"])\n        for key in (\"a\", \"b\", \"condition_x\", \"train_one_step_mse\"):\n            self.assertIsNone(result[key])\n        json.dumps(result, allow_nan=False)\n\n    def test_free_decay_cannot_identify_input_gain(self):\n        data = simulate(0.75, 0.5, [0] * 16, initial_state=1)\n        result = fit(data[\"states\"], data[\"inputs\"])\n        self.assertEqual(result[\"rank\"], 1)\n        self.assertFalse(result[\"identifiable\"])\n\n    def test_nonzero_collinear_columns_cannot_identify_two_parameters(self):\n        states, inputs = [1.0], []\n        for _ in range(8):\n            inputs.append(2 * states[-1])\n            states.append(0.75 * states[-1] + 0.5 * inputs[-1])\n        result = fit(states, inputs)\n        self.assertEqual(result[\"rank\"], 1)\n        self.assertIsNone(result[\"a\"])\n        self.assertIsNone(result[\"b\"])\n\n    def test_constant_equilibrium_data_are_rank_deficient(self):\n        result = fit([2] * 129, [1] * 128)\n        self.assertEqual(result[\"rank\"], 1)\n        self.assertFalse(result[\"identifiable\"])\n\n    def test_constant_input_with_transient_can_have_full_rank(self):\n        data = simulate(0.75, 0.5, [1] * 128, initial_state=0)\n        result = fit(data[\"states\"], data[\"inputs\"])\n        self.assertEqual(result[\"rank\"], 2)\n        self.assertAlmostEqual(result[\"a\"], 0.75, places=10)\n        self.assertAlmostEqual(result[\"b\"], 0.5, places=10)\n\n    def test_rich_noiseless_trajectory_recovers_parameters(self):\n        for a, b in ((0.75, 0.5), (0.2, 1.2), (-0.3, 0.4)):\n            with self.subTest(a=a, b=b):\n                data = simulate(a, b, rich_inputs(128, 2026), initial_state=2)\n                result = fit(data[\"states\"], data[\"inputs\"])\n                self.assertEqual(result[\"rank\"], 2)\n                self.assertAlmostEqual(result[\"a\"], a, places=11)\n                self.assertAlmostEqual(result[\"b\"], b, places=11)\n                self.assertLess(result[\"train_one_step_mse\"], 1e-24)\n\n    def test_process_noise_recovery_on_prespecified_seed(self):\n        data = simulate(0.75, 0.5, rich_inputs(512, 2026), initial_state=2,\n                        process_noise_std=0.03, process_seed=101)\n        result = fit(data[\"states\"], data[\"inputs\"])\n        self.assertLess(abs(result[\"a\"] - 0.75), 0.02)\n        self.assertLess(abs(result[\"b\"] - 0.5), 0.02)\n        self.assertGreater(result[\"train_one_step_mse\"], 0)\n\n    def test_unexcited_models_can_fit_training_and_disagree_on_holdout(self):\n        training = simulate(0.75, 0.5, [1] * 64, initial_state=2)\n        holdout = simulate(0.75, 0.5, rich_inputs(64, 2027), initial_state=-0.3)\n        self.assertEqual(evaluate(0.5, 1.0, training)[\"one_step_observed_mse\"], 0)\n        self.assertEqual(evaluate(0.75, 0.5, training)[\"one_step_observed_mse\"], 0)\n        self.assertGreater(evaluate(0.5, 1.0, holdout)[\"rollout_observed_mse\"], 0.01)\n        self.assertEqual(evaluate(0.75, 0.5, holdout)[\"rollout_observed_mse\"], 0)\n        self.assertFalse(fit(training[\"states\"], training[\"inputs\"])[\"identifiable\"])\n\n    def test_holdout_rollout_does_not_use_later_observed_states(self):\n        # True y=[1,2,3], a=1,b=1, initial=0, u=1. Replace middle observation\n        # with 20: one-step feedback changes, free-running predictions remain 1,2,3.\n        original = {\"states\": [0, 1, 2, 3], \"observations\": [0, 1, 2, 3], \"inputs\": [1, 1, 1]}\n        changed = copy.deepcopy(original)\n        changed[\"observations\"][2] = 20\n        self.assertEqual(evaluate(1, 1, changed)[\"rollout_latent_mse\"], 0)\n        self.assertGreater(evaluate(1, 1, changed)[\"one_step_observed_mse\"], 0)\n\n    def test_condition_number_is_of_design_not_gram(self):\n        # X=[0,2; 1,0] => singular values 2,1. States need not follow model.\n        result = fit([0, 1, 1], [2, 0])\n        self.assertAlmostEqual(result[\"condition_x\"], 2)\n\n    def test_uniform_extreme_scales_preserve_orthogonal_oracle(self):\n        # X = scale * I with the two rows reversed: cond(X)=1, a=.5,b=1.\n        # The unscaled determinant is scale**4 and exceeds float range at\n        # either end, although the regression itself is perfectly conditioned.\n        for scale in (1e-100, 1e154):\n            with self.subTest(scale=scale):\n                result = fit([0, scale, 0.5 * scale], [scale, 0])\n                self.assertEqual(result[\"rank\"], 2)\n                self.assertTrue(result[\"identifiable\"])\n                self.assertAlmostEqual(result[\"condition_x\"], 1)\n                self.assertAlmostEqual(result[\"a\"], 0.5)\n                self.assertAlmostEqual(result[\"b\"], 1)\n                self.assertEqual(result[\"train_one_step_mse\"], 0)\n\n    def test_reported_mse_keeps_original_units_after_scaling(self):\n        # X=[[0,1],[1,0],[1,1]], y=[1,1,0] gives a=b=1/3 and MSE=4/9.\n        # Multiplying all data by 10 preserves a,b and multiplies MSE by 100.\n        result = fit([0, 10, 10, 0], [10, 0, 10])\n        self.assertAlmostEqual(result[\"a\"], 1 / 3)\n        self.assertAlmostEqual(result[\"b\"], 1 / 3)\n        self.assertAlmostEqual(result[\"train_one_step_mse\"], 400 / 9)\n\n    def test_nearly_collinear_data_respect_declared_rank_tolerance(self):\n        result = fit([2, 2 + 1e-10, 2 - 1e-10], [1, 1])\n        self.assertEqual(result[\"rank\"], 1)\n\n    def test_invalid_data_are_rejected(self):\n        for states, inputs in (([], []), ([0, 1], [1, 2]), ([0, True], [1]),\n                               ([0, float(\"nan\")], [1]), ([0, 1], [float(\"inf\")])):\n            with self.subTest(states=states, inputs=inputs), self.assertRaises(ValueError):\n                fit(states, inputs)\n\n    def test_input_sequences_are_unchanged(self):\n        states, inputs = [0, 1, 0.5], [1, 0]\n        before = copy.deepcopy((states, inputs))\n        fit(states, inputs)\n        self.assertEqual((states, inputs), before)\n\n    def test_reference_experiment_is_reproducible_and_json_safe(self):\n        first = experiment(IMPLEMENTATION)\n        second = experiment(IMPLEMENTATION)\n        self.assertEqual(first, second)\n        self.assertTrue(first[\"synthetic\"])\n        self.assertEqual(first[\"controls\"][\"input_energy_each\"], 128)\n        self.assertEqual(first[\"comparisons\"][0][\"fits\"][\"constant\"][\"rank\"], 1)\n        self.assertEqual(first[\"comparisons\"][0][\"fits\"][\"rich\"][\"rank\"], 2)\n        json.dumps(first, allow_nan=False)\n\n    def test_measurement_noise_is_explicitly_separate(self):\n        clean = simulate(0.75, 0.5, rich_inputs(16, 2026), process_noise_std=0)\n        noisy = simulate(0.75, 0.5, clean[\"inputs\"], process_noise_std=0, measurement_noise_std=0.2)\n        self.assertEqual(clean[\"states\"], noisy[\"states\"])\n        self.assertNotEqual(clean[\"observations\"], noisy[\"observations\"])\n        self.assertEqual(fit(noisy[\"observations\"], noisy[\"inputs\"])[\"rank\"], 2)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n",
    "developer/labs/observation/starter.py": "\"\"\"Deliberately faulty: implement the policy_input contract yourself.\"\"\"\n\n\ndef policy_input(sensor_packet):\n    # TODO: explicit field selection, shape/range checks, independent values.\n    return dict(sensor_packet)\n",
    "developer/labs/observation/solution.py": "\"\"\"Reference: accept only declared sensor fields, return independent immutable values.\"\"\"\nimport math\n\nSHAPES = {\"rays\": 3, \"goal\": 2, \"proprio\": 2}\n\n\ndef policy_input(sensor_packet):\n    result = {}\n    for name, size in SHAPES.items():\n        values = sensor_packet.get(name)\n        if not isinstance(values, (list, tuple)) or len(values) != size:\n            raise ValueError(f\"{name}: expected {size} readings\")\n        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):\n            raise ValueError(f\"{name}: expected finite numbers\")\n        result[name] = tuple(float(v) for v in values)\n    if any(v < 0 for v in result[\"rays\"]):\n        raise ValueError(\"rays: range cannot be negative\")\n    return result\n",
    "developer/labs/observation/test_contract.py": "import copy\nimport importlib\nimport os\nimport unittest\n\nimplementation = os.environ.get(\"LAB_IMPLEMENTATION\", \"solution\")\nif implementation not in {\"solution\", \"starter\"}:\n    raise ValueError(\"LAB_IMPLEMENTATION must be solution or starter\")\npolicy_input = importlib.import_module(f\"developer.labs.observation.{implementation}\").policy_input\n\n\ndef packet():\n    return {\"rays\": [1., 2., 3.], \"goal\": [4., 0.5], \"proprio\": [0.2, 0.1],\n            \"privileged_obstacle_xy\": [100., 200.], \"episode_seed\": 42}\n\n\nclass ObservationContract(unittest.TestCase):\n    def test_allowlist(self):\n        self.assertEqual(set(policy_input(packet())), {\"rays\", \"goal\", \"proprio\"})\n\n    def test_hidden_world_changes_do_not_change_input(self):\n        a, b = packet(), packet()\n        b[\"privileged_obstacle_xy\"] = [-999., 999.]\n        b[\"episode_seed\"] = 999\n        self.assertEqual(policy_input(a), policy_input(b))\n\n    def test_sensor_change_is_not_erased(self):\n        a, b = packet(), packet()\n        b[\"rays\"][0] = 0.2\n        self.assertNotEqual(policy_input(a), policy_input(b))\n\n    def test_no_buffer_alias_to_future_observation(self):\n        data = packet()\n        output = policy_input(data)\n        data[\"rays\"][0] = 900.\n        self.assertEqual(output[\"rays\"][0], 1.)\n\n    def test_bad_shape_or_missing_sensor(self):\n        for value in (None, [], [1., 2.], \"123\"):\n            with self.subTest(value=value), self.assertRaises(ValueError):\n                policy_input({**packet(), \"rays\": value})\n\n    def test_nonfinite_boolean_and_negative_range(self):\n        for value in (float(\"nan\"), float(\"inf\"), True, -1.):\n            with self.subTest(value=value), self.assertRaises(ValueError):\n                policy_input({**packet(), \"rays\": [value, 2., 3.]})\n\n    def test_does_not_mutate_sensor_input(self):\n        data = packet()\n        before = copy.deepcopy(data)\n        policy_input(data)\n        self.assertEqual(data, before)\n",
    "developer/physics_probe.py": "\"\"\"Bounded Genesis instrument: freefall, discretisation, and subset reset.\n\nNot part of the default lightweight test gate. Run explicitly with --backend.\nWrites only the explicitly supplied new report file (exclusive creation).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport argparse\nfrom datetime import datetime, timezone\nimport hashlib\nimport json\nfrom pathlib import Path\nimport sys\nimport time\n\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / \"src\"))\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description=__doc__)\n    parser.add_argument(\"--backend\", choices=[\"cpu\", \"gpu\"], required=True)\n    parser.add_argument(\"--output\", type=Path, required=True)\n    args = parser.parse_args()\n    if args.output.exists():\n        parser.error(\"output already exists; choose a new path to preserve previous evidence\")\n\n    from gnav.runtime import init_genesis\n    import genesis as gs\n    import torch\n\n    start = time.perf_counter()\n    init_genesis(args.backend, seed=0)\n    device = gs.device\n    results = []\n    for dt in (0.02, 0.01):\n        scene = gs.Scene(\n            sim_options=gs.options.SimOptions(dt=dt, substeps=1, gravity=(0, 0, -9.81)),\n            rigid_options=gs.options.RigidOptions(integrator=gs.integrator.Euler),\n            show_viewer=False,\n        )\n        ball = scene.add_entity(gs.morphs.Sphere(radius=0.1, pos=(0, 0, 2.0)))\n        scene.build(n_envs=2)\n        n = round(0.2 / dt)\n        trajectory = []\n        for step in range(n):\n            scene.step()\n            trajectory.append({\"t\": (step + 1) * dt, \"z\": ball.get_pos()[:, 2].cpu().tolist(),\n                               \"vz\": ball.get_vel()[:, 2].cpu().tolist()})\n        z = ball.get_pos()[:, 2].clone()\n        vz = ball.get_vel()[:, 2].clone()\n        continuous_z = 2.0 - 0.5 * 9.81 * (n * dt) ** 2\n        discrete_z = 2.0 - 9.81 * dt ** 2 * n * (n + 1) / 2\n        other_pos = ball.get_pos()[1].clone()\n        other_vel = ball.get_vel()[1].clone()\n        ball.set_pos(torch.tensor([[0.0, 0.0, 2.0]], device=device), envs_idx=[0])\n        ball.set_dofs_velocity(torch.zeros((1, 6), device=device), envs_idx=[0])\n        checks = {\n            \"velocity_matches_analytic\": bool(torch.all(torch.abs(vz + 9.81 * n * dt) < 2e-4)),\n            \"position_matches_discrete_euler\": bool(torch.all(torch.abs(z - discrete_z) < 2e-4)),\n            \"unselected_position_unchanged\": bool(torch.equal(other_pos, ball.get_pos()[1])),\n            \"unselected_velocity_unchanged\": bool(torch.equal(other_vel, ball.get_vel()[1])),\n            \"selected_position_reset\": bool(torch.allclose(ball.get_pos()[0], torch.tensor([0., 0., 2.], device=device))),\n            \"selected_velocity_reset\": bool(torch.allclose(ball.get_vel()[0], torch.zeros(3, device=device))),\n        }\n        results.append({\"dt\": dt, \"steps\": n, \"trajectory\": trajectory,\n                        \"continuous_z\": continuous_z, \"discrete_z\": discrete_z,\n                        \"continuous_error\": float((z - continuous_z).abs().max()), \"checks\": checks})\n        scene.destroy()\n\n    ratio = results[0][\"continuous_error\"] / results[1][\"continuous_error\"]\n    passed = all(all(r[\"checks\"].values()) for r in results) and 1.8 < ratio < 2.2\n    predictions = ROOT / \"developer/labs/physics_predictions.json\"\n    report = {\n        \"ok\": passed, \"kind\": \"educational_genesis_freefall_probe\",\n        \"created_utc\": datetime.now(timezone.utc).isoformat(),\n        \"python\": sys.version.split()[0], \"genesis\": gs.__version__, \"torch\": torch.__version__,\n        \"backend\": gs.backend.name, \"device\": str(device),\n        \"source_sha256\": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),\n        \"predictions_sha256\": hashlib.sha256(predictions.read_bytes()).hexdigest(),\n        \"results\": results, \"coarse_to_fine_error_ratio\": ratio,\n        \"elapsed_s_including_init_and_compilation\": time.perf_counter() - start,\n        \"scope\": \"Freefall and subset reset only; no contacts, sensors, policy, throughput or real-robot claim.\",\n    }\n    args.output.parent.mkdir(parents=True, exist_ok=True)\n    with args.output.open(\"x\", encoding=\"utf-8\") as stream:\n        json.dump(report, stream, indent=2, allow_nan=False)\n        stream.write(\"\\n\")\n    print(json.dumps({k: v for k, v in report.items() if k != \"results\"}, indent=2))\n    return 0 if passed else 1\n\n\nif __name__ == \"__main__\":\n    raise SystemExit(main())\n",
    "developer/labs/physics_predictions.json": "{\n  \"status\": \"predictions written before execution; educational validation, not research preregistration\",\n  \"model\": \"A sphere in gravity with no contact, Euler integrator, no initial velocity\",\n  \"parameters\": {\"gravity_z\": -9.81, \"initial_z\": 2.0, \"duration_s\": 0.2, \"substeps\": 1, \"n_envs\": 2},\n  \"predictions\": [\n    \"Final vertical velocity is g*T within 2e-4 m/s at dt=0.02 and dt=0.01.\",\n    \"Semi-implicit Euler position is z0+g*dt^2*n*(n+1)/2 within 2e-4 m.\",\n    \"Absolute error against continuous freefall is approximately halved when dt is halved at fixed duration (ratio in [1.8,2.2]).\",\n    \"Resetting only env0 position and velocity leaves env1 state unchanged before the next step.\"\n  ],\n  \"limitations\": [\"No contact, sensors, actuator, controller or learned policy is validated.\", \"No throughput claim: this deliberately tiny instrument performs host reads for diagnostics.\", \"A passed check only covers this scene, backend, installed version and finite precision.\"]\n}\n",
    "src/gnav/config.py": "\"\"\"Typed experiment configuration.\n\nYAML files may inherit from other files via a top-level ``inherit: [relative/path.yaml, ...]`` list (merged in\norder, later files win), and any field can be overridden from the command line with ``section.key=value`` (the\nvalue is parsed as YAML). The resolved config is saved verbatim next to every run so the run can be reproduced.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport copy\nimport dataclasses\nimport hashlib\nimport json\nimport os\nfrom dataclasses import dataclass, field\nfrom typing import Any\n\nimport yaml\n\n\n@dataclass\nclass RandomizationConfig:\n    # Each source draws from its own seed stream, so disabling one never changes what the others produce.\n    robot_init: bool = True\n    goal: bool = True\n    obstacles: bool = True\n    mover: bool = True\n    dynamics: bool = False\n    obs_noise: bool = False\n\n\n@dataclass\nclass SensorConfig:\n    depth_enabled: bool = True\n    depth_res: tuple[int, int] = (64, 16)  # (width, height)\n    depth_hfov_deg: float = 90.0\n    rays_enabled: bool = True\n    rays_n: int = 31\n    rays_fov_deg: float = 90.0\n    max_range: float = 6.0\n    mount_height: float = 0.20  # above base centre: 0.10 m above hull top, so rays never cross the hull\n    depth_noise_std: float = 0.02  # metres, applied when randomization.obs_noise\n    rays_noise_std: float = 0.02\n    proprio_noise_std: float = 0.02\n    goal_noise_std: float = 0.02\n\n\n@dataclass\nclass DynamicsConfig:\n    profiles: list[str] = field(default_factory=lambda: [\"agile\"])\n    profile_probs: list[float] | None = None  # None -> uniform\n    scale_range: float = 0.2  # +-20% multiplicative when randomization.dynamics\n    delay_jitter: int = 1  # +-1 control step when randomization.dynamics\n    max_delay_steps: int = 4\n    custom_profiles: dict[str, dict] = field(default_factory=dict)  # name -> DynamicsProfile fields\n\n\n@dataclass\nclass MoverConfig:\n    enabled: bool = True\n    speed_range: tuple[float, float] = (0.3, 0.9)\n    path_length_range: tuple[float, float] = (2.0, 4.0)\n    mass: float = 30.0\n    max_force: float = 150.0\n\n\n@dataclass\nclass EnvConfig:\n    n_envs: int = 16\n    sim_dt: float = 0.02\n    control_decimation: int = 5  # control period = sim_dt * decimation = 0.1 s\n    max_episode_steps: int = 300  # control steps (30 s)\n    arena_half_size: float = 4.0\n    wall_height: float = 2.0\n    goal_radius: float = 0.35\n    min_start_goal_dist: float = 4.0\n    terminate_on_collision: bool = True\n    near_collision_clearance: float = 0.15\n    robot_mass: float = 10.0\n    robot_max_force: float = 150.0  # N; servo force limit (contacts can stop the robot)\n    robot_max_torque: float = 20.0\n    servo_kv_lin: float = 600.0\n    servo_kv_ang: float = 30.0\n    n_pillars: int = 3\n    n_occluders: int = 2\n    reward_progress: float = 1.0\n    reward_success: float = 10.0\n    reward_collision: float = 5.0\n    reward_time: float = 0.01\n    sensors: SensorConfig = field(default_factory=SensorConfig)\n    dynamics: DynamicsConfig = field(default_factory=DynamicsConfig)\n    mover: MoverConfig = field(default_factory=MoverConfig)\n    randomization: RandomizationConfig = field(default_factory=RandomizationConfig)\n\n\n@dataclass\nclass ModelConfig:\n    latent_dim: int = 64\n    belief_dim: int = 128\n    hidden_dim: int = 128\n\n\n@dataclass\nclass TrainConfig:\n    iterations: int = 20\n    rollout_len: int = 32\n    lr: float = 3e-4\n    gamma: float = 0.99\n    entropy_coef: float = 0.01\n    value_coef: float = 0.5\n    model_coef: float = 1.0\n    seq_len: int = 16\n    batch_size: int = 32\n    replay_capacity: int = 20000\n    checkpoint_every: int = 10\n\n\n@dataclass\nclass EvalConfig:\n    n_episodes: int = 16\n    policy: str = \"reactive\"  # reactive | random | checkpoint\n    checkpoint: str | None = None\n    record_trajectories: bool = True\n    deterministic: bool = True\n\n\n@dataclass\nclass ExperimentConfig:\n    name: str = \"default\"\n    seed: int = 0\n    eval_seed: int = 10_000  # disjoint seed space from training\n    backend: str = \"gpu\"  # gpu | cpu\n    output_dir: str = \"runs\"\n    env: EnvConfig = field(default_factory=EnvConfig)\n    model: ModelConfig = field(default_factory=ModelConfig)\n    train: TrainConfig = field(default_factory=TrainConfig)\n    eval: EvalConfig = field(default_factory=EvalConfig)\n\n    def to_dict(self) -> dict:\n        return _to_plain(dataclasses.asdict(self))\n\n    def digest(self) -> str:\n        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:12]\n\n\n# ------------------------------------------------------------------------------------------------ loading\n\n\ndef _to_plain(x):\n    if isinstance(x, dict):\n        return {k: _to_plain(v) for k, v in x.items()}\n    if isinstance(x, (list, tuple)):\n        return [_to_plain(v) for v in x]\n    return x\n\n\ndef _deep_merge(base: dict, over: dict) -> dict:\n    out = copy.deepcopy(base)\n    for k, v in over.items():\n        if isinstance(v, dict) and isinstance(out.get(k), dict) and k != \"custom_profiles\":\n            out[k] = _deep_merge(out[k], v)\n        else:\n            out[k] = copy.deepcopy(v)\n    return out\n\n\ndef _load_yaml_tree(path: str) -> dict:\n    with open(path) as f:\n        data = yaml.safe_load(f) or {}\n    parents = data.pop(\"inherit\", []) or []\n    merged: dict = {}\n    for p in parents:\n        merged = _deep_merge(merged, _load_yaml_tree(os.path.join(os.path.dirname(path), p)))\n    return _deep_merge(merged, data)\n\n\ndef _build(cls, data: dict):\n    if not dataclasses.is_dataclass(cls):\n        return data\n    kwargs = {}\n    known = {f.name: f for f in dataclasses.fields(cls)}\n    for k, v in data.items():\n        if k not in known:\n            raise KeyError(f\"Unknown config key '{k}' for {cls.__name__}\")\n        ftype = known[k].type\n        sub = _DATACLASS_FIELDS.get((cls.__name__, k))\n        if sub is not None and isinstance(v, dict):\n            kwargs[k] = _build(sub, v)\n        elif isinstance(v, list) and isinstance(ftype, str) and ftype.startswith(\"tuple\"):\n            kwargs[k] = tuple(v)\n        else:\n            kwargs[k] = v\n    return cls(**kwargs)\n\n\n_DATACLASS_FIELDS = {\n    (\"ExperimentConfig\", \"env\"): EnvConfig,\n    (\"ExperimentConfig\", \"model\"): ModelConfig,\n    (\"ExperimentConfig\", \"train\"): TrainConfig,\n    (\"ExperimentConfig\", \"eval\"): EvalConfig,\n    (\"EnvConfig\", \"sensors\"): SensorConfig,\n    (\"EnvConfig\", \"dynamics\"): DynamicsConfig,\n    (\"EnvConfig\", \"mover\"): MoverConfig,\n    (\"EnvConfig\", \"randomization\"): RandomizationConfig,\n}\n\n\ndef apply_overrides(data: dict, overrides: list[str]) -> dict:\n    data = copy.deepcopy(data)\n    for ov in overrides or []:\n        if \"=\" not in ov:\n            raise ValueError(f\"Override must be key=value, got '{ov}'\")\n        key, val = ov.split(\"=\", 1)\n        node = data\n        parts = key.split(\".\")\n        for p in parts[:-1]:\n            node = node.setdefault(p, {})\n        node[parts[-1]] = yaml.safe_load(val)\n    return data\n\n\ndef load_config(path: str | None = None, overrides: list[str] | None = None) -> ExperimentConfig:\n    data = _load_yaml_tree(path) if path else {}\n    data = apply_overrides(data, overrides or [])\n    return _build(ExperimentConfig, data)\n\n\ndef config_from_dict(data: dict) -> ExperimentConfig:\n    return _build(ExperimentConfig, data)\n\n\ndef save_config(cfg: ExperimentConfig, path: str):\n    with open(path, \"w\") as f:\n        yaml.safe_dump(cfg.to_dict(), f, sort_keys=False)\n",
    "src/gnav/experiment/train.py": "\"\"\"Reference training loop: recurrent A2C (GAE) + latent-dynamics auxiliary loss from sequence replay.\n\nTest-grade by design. Its job is to exercise the full data flow (env -> encoder -> belief -> policy/value,\nreplay -> latent dynamics, checkpoints, metrics) reproducibly, not to be a strong learner. Truncated episodes are\ntreated as terminal; a stronger learner should bootstrap them.\"\"\"\n\nfrom __future__ import annotations\n\nimport os\nimport time\n\nimport torch\n\nfrom ..config import ExperimentConfig\nfrom ..learning.replay import SequenceReplay\nfrom ..runtime import init_genesis, seed_everything\nfrom .policies import build_agent\nfrom .run import MetricsLogger, make_run_dir, save_checkpoint\n\nEP_KEYS = (\"success\", \"collided\", \"spl\", \"return\", \"length\", \"min_clearance\", \"mover_visible_frac\")\n\n\ndef train(cfg: ExperimentConfig, run_dir: str | None = None) -> str:\n    init_genesis(cfg.backend, seed=cfg.seed)\n    seed_everything(cfg.seed)\n    torch.backends.cudnn.deterministic = True\n    torch.backends.cudnn.benchmark = False\n    from ..sim.env import NavEnv\n\n    run_dir = make_run_dir(cfg, \"train\", run_dir)\n    log = MetricsLogger(os.path.join(run_dir, \"metrics.jsonl\"))\n    env = NavEnv(cfg.env, seed=cfg.seed)\n    dev = env.device\n    tc = cfg.train\n    agent = build_agent(cfg, env.obs_shapes).to(dev)\n    opt = torch.optim.Adam(agent.parameters(), lr=tc.lr)\n    replay = SequenceReplay(tc.replay_capacity, env.B, env.obs_shapes, 2, dev)\n    gen = torch.Generator(device=dev).manual_seed(cfg.seed)\n\n    obs = env.reset()\n    state = agent.initial_state(env.B, dev)\n    first = torch.ones(env.B, dtype=torch.bool, device=dev)\n    env_steps = 0\n    for it in range(1, tc.iterations + 1):\n        t0 = time.time()\n        h0 = {k: v.detach() for k, v in state.items()}\n        roll = {\"obs\": [], \"first\": [], \"u\": [], \"r\": [], \"done\": []}\n        ep_acc = {k: torch.zeros((), device=dev) for k in EP_KEYS}\n        n_ep = torch.zeros((), device=dev)\n        for _ in range(tc.rollout_len):\n            with torch.no_grad():\n                b, _, h = agent.step(obs, state, first)\n                dist = agent.policy(b)\n                u = _sample(dist, gen)\n                a = torch.tanh(u)\n            obs2, r, term, trunc, info = env.step(a)\n            done = term | trunc\n            roll[\"obs\"].append(obs)\n            roll[\"first\"].append(first)\n            roll[\"u\"].append(u)\n            roll[\"r\"].append(r)\n            roll[\"done\"].append(done)\n            replay.add(obs, a, r, first)\n            ep = info[\"episode\"]\n            n_ep += done.sum()\n            for k in EP_KEYS:\n                ep_acc[k] += (ep[k] * done).sum()\n            state = {\"h\": h, \"prev_action\": a}\n            first = done\n            obs = obs2\n        env_steps += tc.rollout_len * env.B\n\n        # ---- actor-critic update (BPTT over the rollout from the detached initial state)\n        st = h0\n        logps, ents, vals = [], [], []\n        for t in range(tc.rollout_len):\n            b, _, h = agent.step(roll[\"obs\"][t], st, roll[\"first\"][t])\n            d = agent.policy(b)\n            logps.append(d.log_prob(roll[\"u\"][t]))\n            ents.append(d.entropy())\n            vals.append(agent.value(b))\n            st = {\"h\": h, \"prev_action\": torch.tanh(roll[\"u\"][t])}\n        with torch.no_grad():\n            b_last, _, _ = agent.step(obs, st, first)\n            v_last = agent.value(b_last)\n        vals_t = torch.stack(vals)\n        adv = torch.zeros_like(vals_t)\n        gae = torch.zeros(env.B, device=dev)\n        lam = 0.95\n        for t in reversed(range(tc.rollout_len)):\n            nd = (~roll[\"done\"][t]).float()\n            v_next = v_last if t == tc.rollout_len - 1 else vals_t[t + 1].detach()\n            delta = roll[\"r\"][t] + tc.gamma * v_next * nd - vals_t[t].detach()\n            gae = delta + tc.gamma * lam * nd * gae\n            adv[t] = gae\n        ret = adv + vals_t.detach()\n        adv_n = (adv - adv.mean()) / (adv.std() + 1e-8)\n        pi_loss = -(torch.stack(logps) * adv_n).mean()\n        v_loss = 0.5 * ((vals_t - ret) ** 2).mean()\n        ent = torch.stack(ents).mean()\n\n        # ---- latent dynamics loss: predict e_{t+1} from (b_t, a_t) on replayed sequences\n        m_loss = torch.zeros((), device=dev)\n        if replay.size >= tc.seq_len:\n            seq = replay.sample(tc.batch_size, tc.seq_len, gen)\n            L = tc.seq_len\n            hs = agent.belief.initial_state(tc.batch_size, dev)\n            pa = torch.zeros(tc.batch_size, 2, device=dev)\n            preds, targets, masks = [], [], []\n            embeds = [agent.encoder({k: v[t] for k, v in seq[\"obs\"].items()}) for t in range(L)]\n            for t in range(L - 1):\n                bt, hs = agent.belief(embeds[t], pa, hs, seq[\"first\"][t])\n                preds.append(agent.dynamics(bt, seq[\"action\"][t]))\n                targets.append(embeds[t + 1].detach())\n                masks.append((~seq[\"first\"][t + 1]).float())\n                pa = seq[\"action\"][t]\n            mk = torch.stack(masks)\n            m_loss = (((torch.stack(preds) - torch.stack(targets)) ** 2).mean(-1) * mk).sum() / mk.sum().clamp_min(1)\n\n        loss = pi_loss + tc.value_coef * v_loss - tc.entropy_coef * ent + tc.model_coef * m_loss\n        opt.zero_grad(set_to_none=True)\n        loss.backward()\n        torch.nn.utils.clip_grad_norm_(agent.parameters(), 1.0)\n        opt.step()\n        state = {k: v.detach() for k, v in state.items()}\n\n        n = max(int(n_ep.item()), 1)  # one sync per iteration (logging)\n        log.log(\n            iteration=it, env_steps=env_steps, loss=loss.item(), pi_loss=pi_loss.item(), v_loss=v_loss.item(),\n            entropy=ent.item(), model_loss=m_loss.item(), episodes=int(n_ep.item()),\n            **{f\"ep_{k}\": float(ep_acc[k]) / n for k in EP_KEYS},\n            sps=round(tc.rollout_len * env.B / (time.time() - t0), 1),\n        )\n        if it % tc.checkpoint_every == 0 or it == tc.iterations:\n            save_checkpoint(os.path.join(run_dir, \"checkpoints\", f\"iter_{it:06d}.pt\"), cfg=cfg, agent=agent,\n                            optimizer=opt, iteration=it, extra={\"env_steps\": env_steps})\n    log.close()\n    return run_dir\n\n\ndef _sample(dist, gen):\n    \"\"\"Sample a (diagonal) Normal with an explicit generator for reproducibility.\"\"\"\n    base = dist.base_dist\n    eps = torch.randn(base.loc.shape, device=base.loc.device, generator=gen)\n    return base.loc + base.scale * eps\n"
  },
  "roadmap": [
    {
      "title": "第1–3周 · 建立可验证的实验边界",
      "body": "完成本网站的工程、物理、观测和GAE基础。保留已做的GPU micro-labs能力，不重复入门测速；新增一个执行器或传感器的解析/受控验证。每次先预测、再测量、再解释偏差。",
      "deliverable": "可复现的开发环境、自己的starter实现、物理测量卡、信息流图和一份同行可运行的交接。"
    },
    {
      "title": "第4–6周 · 自己实现并诊断PPO",
      "body": "先把GAE移植到Torch并验证collector边界，再逐项实现old log-prob、ratio、clip surrogate、minibatch/epoch、value更新与日志。先用微小可控任务，之后才接Genesis短训练。当前仓库A2C不能直接被称为PPO。",
      "deliverable": "算法单测、手算与Torch对照、短训练成本、固定seed与独立评估、至少一个失败机制诊断。此阶段为后续作业。"
    },
    {
      "title": "第7–9周 · 辨识、预测模型与决策相关表示",
      "body": "从输入是否足够辨识开始，再比较一步预测与多步rollout。为学习表示设下游决策指标与简单基线，分离过程噪声、测量噪声和模型失配；不把小训练loss当理解或原创性证明。",
      "deliverable": "独立holdout、多seed、分布变化/反例、简单显式模型基线、对信息损失与任务影响的解释。此阶段为后续作业。"
    },
    {
      "title": "第10–12周 · 整合成可复现研究系统",
      "body": "将仿真、合法观测、学习、评估和证据串起来。选择一个可获得的真实平台问题，先核实传感器与约束；定义sim-to-real差异的最小实验。确有分享需求时再加API/前端，保持研究问题开放。",
      "deliverable": "一页架构、实验报告、运行预算、复现说明、真实使用或同行反馈，以及明确尚未解决的科学问题。真机/完整world model尚未由本包实现。"
    }
  ]
};
