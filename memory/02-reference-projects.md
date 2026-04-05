# 参考项目研究

## 已 clone 的参考仓库

均位于 `.references/` 目录下（shallow clone）。

---

## 1. M9A (重返未来1999) — 深度调研 (2026/04/04)

- **仓库**: `.references/M9A/`
- **语言**: Python 3.11+
- **核心框架**: MaaFramework v5.9.2 (pip: `maafw==v5.9.2`)
- **架构模式**: Agent Server 模式 + 声明式 JSON 管线
- **图像识别**: OpenCV 模板匹配 + OCR + 颜色匹配（MaaFramework 内置）
- **输入模拟**: ADB (安卓) / Win32 SendMessage (PC) / PlayCover (iOS)
- **任务定义**: JSON 节点图（Node = 识别条件 + 动作 + 后继列表）
- **平台**: Win/Linux/macOS/iOS

### 核心架构: Agent Server 模式
- M9A **不自己创建** Controller/Resource/Tasker
- MaaPiCli（GUI）是主进程，负责连接设备和加载资源
- M9A 的 `agent/main.py` 是被 MaaPiCli 作为**子进程**启动
- 通过 `socket_id` 参数通信: `AgentServer.start_up(socket_id)`
- `import custom` 触发所有装饰器注册

### MaaFramework Python API 核心类
| 类 | 模块 | 核心方法 |
|---|---|---|
| `AgentServer` | `maa.agent.agent_server` | `.start_up()`, `.join()`, `.shut_down()`, `@.custom_action()`, `@.custom_recognition()`, `@.tasker_sink()` |
| `Context` | `maa.context` | `.run_task()`, `.run_recognition()`, `.override_pipeline()`, `.override_next()`, `.get_node_object()`, `.tasker` |
| `Tasker` | `maa.tasker` | `.set_log_dir()`, `.controller`, `.post_stop()`, `.stopping`, `.get_task_detail()` |
| `Controller` | via `tasker.controller` | `.post_screencap().wait().get()`, `.post_click(x,y).wait()`, `.post_swipe()`, `.cached_image` |
| `CustomAction` | `maa.custom_action` | `.run(context, argv) → RunResult` |
| `CustomRecognition` | `maa.custom_recognition` | `.analyze(context, argv) → AnalyzeResult\|None` |
| `TaskerEventSink` | `maa.tasker` | `.on_tasker_task(tasker, noti_type, detail)` |

### Pipeline JSON 节点格式
```json
{
  "NodeName": {
    "recognition": {"type": "TemplateMatch|OCR|ColorMatch|And|Or|Custom", "param": {...}},
    "action": {"type": "Click|Swipe|StartApp|StopApp|DoNothing|Custom", "param": {...}},
    "next": ["NextNode", "[JumpBack]InterruptNode"],
    "post_delay": 3000, "timeout": 60000, "max_hit": 5,
    "post_wait_freezes": {"time": 500, "target": [x,y,w,h]},
    "enabled": true
  }
}
```

### 关键设计模式
- **`[JumpBack]` 中断机制**: next 中以此前缀的节点是 interrupt，命中后跳回继续
- **Override 贯穿一切**: interface.json 选项 → context.override_pipeline() → run_task(entry, override)
- **`attach` 字段**: 自定义数据，不被框架解析，通过 `context.get_node_object().attach` 读取
- **异步 Future 链**: `post_xxx() → .wait() → .get()`
- **多资源路径叠加**: 后面路径覆盖前面 (base + bilibili)

### 关键文件
- 入口: `agent/main.py` (AgentServer 模式)
- 管线定义: `assets/resource/base/pipeline/*.json` (27个)
- 自定义识别: `agent/custom/reco/` (6个文件, 10+个类)
- 自定义动作: `agent/custom/action/` (9个文件, 20+个类)
- 事件回调: `agent/custom/sink/aspect_ratio.py`
- 接口声明: `assets/interface.json` (controller/resource/agent/task/option)
- 任务定义: `assets/resource/tasks/*.json` (import 到 interface.json)
- 依赖: `requirements.txt` (maafw==v5.9.2)

---

## 2. ok-wuthering-waves (鸣潮)

- **仓库**: `.references/ok-wuthering-waves/`
- **语言**: Python 3.12
- **核心框架**: ok-script (作者自研)
- **架构模式**: Python OOP 类继承
- **图像识别**: OpenCV + YOLO v8 (ONNX) + ppocr
- **输入模拟**: PostMessage (后台) / pydirectinput (前台)
- **GUI**: PySide6 + Fluent Design
- **平台**: 仅 Windows

### 关键设计
- **YOLO 目标检测**: 训练模型识别掉落物，比模板匹配更鲁棒
- **角色工厂 (CharFactory)**: 自动识别队伍，加载 44 个角色各自的技能循环
- **冻结时间计算**: 精确考虑动画锁对冷却时间的影响
- **后台运行**: PostMessage 不抢焦点
- **任务分类**: OneTimeTask (一次性) + TriggerTask (持续监控)

### 关键文件
- 入口: `main.py`
- 配置: `config.py`
- 任务基类: `src/task/BaseWWTask.py`, `src/task/BaseCombatTask.py`
- 角色系统: `src/char/BaseChar.py`, `src/char/CharFactory.py`
- YOLO 检测: `src/OnnxYolo8Detect.py`
- 标签枚举: `src/Labels.py` (300+ 模板)

---

## 3. BetterGI Scripts (原神)

- **仓库**: `.references/bettergi-scripts-list/`
- **类型**: BetterGI 引擎的脚本集合（非独立框架）
- **脚本语言**: JavaScript (复杂逻辑) + JSON (路径) + TXT (战斗)
- **引擎**: BetterGI (C# 编写，不在此仓库)

### 三种脚本格式
1. **Pathing JSON**: 地图路径 + 采集动作（4630+ 个）
2. **Combat TXT**: 战斗连招序列（极简 DSL）
3. **JS 脚本**: 完整编排（128 个），支持持久化/多账号

### 关键设计
- **分层脚本**: 不同复杂度任务用不同格式
- **引擎 API**: `captureGameRegion()`, `RecognitionObject.TemplateMatch()`, `genshin.tp()` 等
- **持久化状态**: JSON 文件记录上次完成进度
- **社区生态**: 大量社区贡献脚本

### 关键文件
- API 定义: `bettergi.d.ts` (3600+ 行 TypeScript 声明)
- 示例: `example/js/RecognitionDemo/main.js`
- 复杂脚本: `repo/js/AbundantOre/main.js`

---

## 4. MaaAssistantArknights (明日方舟) — 标杆项目

- **仓库**: `.references/MaaAssistantArknights/`
- **语言**: C++20 (核心引擎)，多语言绑定 (Python, Java, Rust, Go, TS, Dart)
- **构建**: CMake 3.28+
- **Star 数极高，口碑最好，架构最成熟**

### 核心依赖
- OpenCV (图像处理)
- PaddleOCR + FastDeploy (OCR)
- ONNX Runtime (模型推理)
- meojson (JSON 解析)

### 架构分层
```
MaaCore/
├── Assistant        # 主门面，线程编排 (call queue + msg queue + worker)
├── Controller/      # 输入/截图抽象层
│   ├── AdbController      # Android ADB
│   ├── MinitouchController # Minitouch 协议 (低延迟触控)
│   ├── MaatouchController  # 自研增强版 Minitouch
│   └── Win32Controller     # Windows 原生
├── Vision/          # 图像识别管线
│   ├── Matcher            # OpenCV 模板匹配
│   ├── FeatureMatcher     # SIFT/ORB 特征匹配
│   ├── OCRer              # PaddleOCR 封装
│   ├── Hasher             # 图像哈希
│   └── PipelineAnalyzer   # 多策略调度器
├── Task/            # 任务执行引擎
│   ├── ProcessTask        # FSM 状态机执行器
│   ├── PackageTask        # 复合任务容器
│   ├── InterfaceTask      # 用户对接层
│   └── 具体任务: Fight, Infrast, Recruit, Roguelike, Copilot...
├── Config/          # 资源与配置加载
│   ├── TaskData           # JSON 任务定义解析
│   └── TemplResource      # 模板图缓存
└── Utils/           # 日志、平台抽象
```

### 图像识别 — 多策略管线
1. **模板匹配** (主力): OpenCV matchTemplate，阈值默认 0.8，支持多模板回退
2. **特征匹配**: ORB/SIFT/AKAZE，处理旋转/缩放变化
3. **OCR**: PaddleOCR，支持中英文，ROI 约束
4. **颜色直方图** (HSVCount): 颜色元素检测
5. **图像哈希**: 快速相似度判断

### 任务定义 (JSON 声明式)
```json
{
  "MyTask": {
    "algorithm": "TemplMatch",
    "template": ["btn.png", "btn_alt.png"],
    "templThreshold": 0.85,
    "roi": [100, 200, 300, 400],
    "action": "ClickSelf",
    "next": ["TaskA", "TaskB"],
    "on_error_next": ["ErrorHandler"],
    "maxTimes": 10,
    "preDelay": 100,
    "postDelay": 500
  }
}
```

### 输入模拟 (优先级)
1. **Minitouch/Maatouch** — 二进制协议，5-10ms 延迟，贝塞尔曲线滑动
2. **ADB shell** — 回退方案，~100ms 延迟
3. **Win32 API** — PC 端 SendMessage/PostMessage
4. **ControlScaleProxy** — 1280x720 坐标自动缩放到实际分辨率

### 错误恢复机制
- 每任务可配 retry 次数 (默认 20)
- `on_error_next` 显式错误恢复路径
- 弹窗并行检测 + 自动关闭
- 断连自动重连 (5 次指数退避)
- 多模板回退: 模板A失败 → 模板B → 特征匹配 → OCR

### 插件系统
- 任务级插件: `StageDropsTaskPlugin` (上报企鹅物流)、`FightTimesTaskPlugin` 等
- 不修改核心代码即可扩展

### 成功要素总结
1. **多策略识别**: 不押注单一算法，模板+特征+OCR 互补
2. **JSON 声明式任务**: 非程序员可编写任务，引擎与逻辑分离
3. **异步资源加载**: 后台线程加载 JSON 和模板图，不阻塞启动
4. **跨平台抽象**: C++ 核心 + 平台插件，同一任务定义全平台通用
5. **社区集成**: 抄作业平台 (prts.plus)、企鹅物流数据上报
6. **回调驱动**: 所有操作异步，UI 从不阻塞
7. **模板缓存 + ROI**: 性能优化不增加复杂度

### 关键文件
- 主入口: `src/MaaCore/Assistant.h/cpp`
- 任务执行器: `src/MaaCore/Task/ProcessTask.cpp`
- 视觉识别: `src/MaaCore/Vision/Matcher.cpp`, `OCRer.cpp`, `FeatureMatcher.cpp`
- 控制器: `src/MaaCore/Controller/`
- 任务定义: `resource/tasks/*.json` (70+ 文件)
- 模板图片: `resource/template/`
