# 文档重审记录 (2026-04-04 第二轮)

## 背景

第一轮文档由错误的模型生成，存在过度工程化问题。第二轮用 Opus 1M 重审。

## 保留的核心决策

- 产品定位：混合渐进式，先深空之眼再多游戏
- 三大核心能力：后台运行、定时任务、跨游戏编排
- 技术路线：MaaFramework + Python
- 初始游戏：深空之眼

## 重写的文档

### coding-standards.md
- 删除：CQRS、Event Sourcing、六边形架构、手写缓存/对象池、健康检查、Result 单子
- 改为：Python 异常处理、loguru 直接用、ruff 替代 black+isort+flake8
- 降低：覆盖率要求 80% → 核心模块 70%
- 保留：严格类型、Protocol 接口、构造函数 DI、模块依赖方向

### product-specification.md
- 删除：与编码标准重复的技术约束章节（占原文一半）
- 新增：深空之眼具体功能描述、场景复杂度分析
- 新增：三层任务架构 + 战斗引擎 + 导航引擎
- 精简：去掉产品规格中不该有的实现细节

### 删除的文件
- `maaframework-architecture.md` — 基于猜测的 API 设计，等研究真实 API 再写
- `infrastructure-design.md` — 过时的初始基础设施规格
- `phase1-background-engine.md` — 纯 Python 实现计划，已被 MaaFramework 方案替代
- `infrastructure-setup.md` — 过时的基础设施搭建计划
- `maaframework-integration.md` — 基于猜测 API 的集成计划

## 当前待办

1. **研究 MaaFramework 真实 Python API** — 看 M9A 代码怎么用的
2. 基于真实 API 设计架构
3. 写实施计划
4. 开始编码
