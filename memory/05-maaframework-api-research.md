# MaaFramework Python API 调研（基于 M9A 源码）

## 核心架构：Agent Server 模式

M9A 不直接创建 Controller/Resource/Tasker。MaaPiCli（GUI）是主进程，Python agent 是子进程，通过 socket 通信。

```python
from maa.agent.agent_server import AgentServer
from maa.tasker import Tasker

import custom  # 触发所有装饰器注册

Tasker.set_log_dir("./debug")
socket_id = sys.argv[-1]
AgentServer.start_up(socket_id)
AgentServer.join()
AgentServer.shut_down()
```

## 核心 API

| 类 | 核心方法 |
|---|---|
| `AgentServer` | `.start_up(socket_id)`, `.join()`, `.shut_down()`, `@.custom_action()`, `@.custom_recognition()`, `@.tasker_sink()` |
| `Context` | `.run_task(entry, override)`, `.run_recognition(name, img, override)`, `.override_pipeline(dict)`, `.override_next(node, list)`, `.tasker` |
| `Controller` | `.post_screencap().wait().get()`, `.post_click(x,y).wait()`, `.post_swipe(x1,y1,x2,y2,dur).wait()`, `.cached_image` |
| `Tasker` | `.controller`, `.post_stop()`, `.stopping` |

## 自定义组件注册

```python
@AgentServer.custom_action("MyAction")
class MyAction(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        # context.run_task() 执行子任务
        # context.tasker.controller.post_click() 直接操控
        return CustomAction.RunResult(success=True)

@AgentServer.custom_recognition("MyReco")
class MyReco(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        reco = context.run_recognition("SomeNode", argv.image)
        if reco and reco.hit:
            return [x, y, w, h]  # 返回坐标 = 成功
        return None  # 返回 None = 失败

@AgentServer.tasker_sink()
class MySink(TaskerEventSink):
    def on_tasker_task(self, tasker, noti_type, detail):
        # 事件回调（任务开始/结束/错误）
        pass
```

## Override 机制

贯穿 MaaFramework 的核心模式：

```python
# 禁用节点
context.override_pipeline({"NodeName": {"enabled": False}})
# 修改 next 列表
context.override_next("CurrentNode", ["NewTarget"])
# 运行任务时局部覆盖参数
context.run_task("Entry", {"Entry": {"template": [...], "next": [...]}})
# 识别时局部覆盖
context.run_recognition("Node", img, {"Node": {"recognition": {"param": {...}}}})
```

## Pipeline JSON 格式

```json
{
    "NodeName": {
        "recognition": { "type": "TemplateMatch", "param": { "template": "x.png", "roi": [x,y,w,h] } },
        "action": { "type": "Click|Custom", "param": { "custom_action": "MyAction" } },
        "next": ["NormalNode", "[JumpBack]InterruptHandler"],
        "post_delay": 3000,
        "timeout": 60000,
        "post_wait_freezes": { "time": 500 },
        "enabled": true
    }
}
```

`[JumpBack]` 前缀 = 中断处理节点，执行后跳回继续匹配。

## Win32 后台配置（interface.json）

```json
{
    "type": "Win32",
    "win32": {
        "class_regex": "UnityWndClass",
        "window_regex": "GameTitle.*",
        "screencap": "PrintWindow",
        "mouse": "SendMessageWithCursorPos",
        "keyboard": "SendMessageWithCursorPos"
    }
}
```

## 资源路径叠加

多路径后者覆盖前者，用于多服务器/多语言支持：
```json
"resource": [
    { "name": "官服", "path": ["./resource/base"] },
    { "name": "B服", "path": ["./resource/base", "./resource/bilibili"] }
]
```

## 依赖

MaaFramework Python 包名: `MaaFw` (PyPI)
M9A 的 requirements: `MaaFw>=v5.9.2`
包含: Python 绑定 + C++ DLL (~24.6MB wheel)
依赖: numpy, strenum, maaagentbinary

## 架构决策

- **不用** AgentServer / MaaPiCli — 我们自己做主进程
- **直接创建** Win32Controller + Resource + Tasker
- MaaFw 是库，不是框架。GUI/调度/生命周期全由我们控制
- 战斗和导航绕过 MaaFw 管线，直接用 screenshot/click/key_press
- GameSession 是对 MaaFw 的唯一封装点
