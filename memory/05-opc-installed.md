# OPC 安装记录 (2026-04-04)

## 什么是 OPC

**OPC ("One Person Company")** — Claude Code skill，模拟多角色软件团队。
- 仓库：https://github.com/iamtouchskyer/opc
- 版本：0.4.1
- 许可：MIT

## 核心能力

- 11 个内置角色：PM、Designer、3 种用户角色、Frontend/Backend/DevOps、Security、Tester、Compliance
- 6 种任务模式：Review、Analysis、Build、Brainstorm、Plan、Full Pipeline
- 对抗式质量控制：做工作的 agent ≠ 评审的 agent
- 纯 Markdown 实现，零运行时依赖

## 安装方式

```bash
npm install -g @touchskyer/opc
```

文件安装到 `~/.claude/skills/opc/`：
- `skill.md` — 主编排 skill（~14KB）
- `replay.md` — 查看历史报告
- `pipeline/` — 7 个 prompt 模板
- `roles/` — 11 个角色定义

## 使用方式

在 Claude Code 中直接用 `/opc` 命令：

```
/opc review the changes in this PR
/opc analyze why the API is slow
/opc implement the migration plan
/opc what are our options for auth?
/opc -i review the payment flow       # 交互模式
/opc replay                            # 查看历史报告
```

## 与现有工具的关系

- **superpowers** — 已安装的 brainstorming/TDD/planning 工作流
- **OPC** — 多角色并行评审和分析，补充 superpowers 的单角色视角
- 两者互补：superpowers 管流程，OPC 管多角色质量把关

## 适用场景（对本项目）

- MaaFramework 集成方案评审 → `/opc review`
- Combat Engine 架构分析 → `/opc analyze`
- 新功能实现 → `/opc build`
- 技术选型讨论 → `/opc brainstorm`
