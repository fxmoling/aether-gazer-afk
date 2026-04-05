# GSD (Get Shit Done) 安装记录

## 安装信息
- **版本**: v1.32.0
- **安装日期**: 2026-04-04
- **安装方式**: `npx get-shit-done-cc@latest --claude --local`
- **安装位置**: `.claude/` (项目级 local)

## 安装内容
- 60 个 skills (slash commands) → `.claude/skills/gsd-*/`
- Hooks (context monitor, prompt guard, read guard, commit validation, etc.) → `.claude/hooks/`
- Agents → `.claude/agents/`
- Statusline → GSD statusline

## 配置说明
- GSD 安装时会覆盖项目级 `.claude/settings.json`，只保留 hooks + statusline
- 用户级核心配置（env, permissions, model 等）在 `~/.claude/settings.json`，不受影响
- 两层配置互不冲突：用户级管权限/模型，项目级管 GSD hooks

## 核心命令
| 命令 | 用途 |
|------|------|
| `/gsd-new-project` | 初始化新项目（问答→需求→路线图） |
| `/gsd-map-codebase` | 分析现有代码库 |
| `/gsd-discuss-phase N` | 讨论第N阶段实现细节 |
| `/gsd-plan-phase N` | 规划第N阶段任务 |
| `/gsd-execute-phase N` | 执行第N阶段（多 agent 并行） |
| `/gsd-verify-work N` | 验证第N阶段成果 |
| `/gsd-quick` | 快速任务（不需要完整规划） |
| `/gsd-next` | 自动检测并执行下一步 |
| `/gsd-autonomous` | 自主模式（最少人工干预） |

## 关键特性
- **Context rot 解决**: 每个 plan 在全新 context window 执行，避免上下文退化
- **Wave 并行执行**: 独立任务并行，依赖任务顺序执行
- **原子提交**: 每个 task 一个 commit
- **自动验证**: 内置验证步骤检查实现质量
