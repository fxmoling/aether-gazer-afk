# CLAUDE.md - Project Configuration

## Memory System

项目记忆存储在 `memory/` 目录下（项目根目录），每个文件为 `.md` 格式。

**强制规则**:
- **每次开启新会话**，必须加载 `memory/` 下的所有 `.md` 文件
- **每次有代码改动**，必须将变更摘要记入 memory
- **每次有结构变化**（新增模块、重构、文件重组等），必须更新 memory
- **每次有讨论结论**（技术选型、设计决策、问题解决等），必须记入 memory
- 文件按编号排序，用数字前缀 `01-`, `02-`, ... 组织
- 内容应简洁、结构化，便于快速回顾

**当前 memory 文件**:
- `01-project-overview.md` — 项目目标与合规要求
- `02-reference-projects.md` — 四个参考项目（MAA、M9A、ok-ww、BetterGI）的详细研究
- `03-tech-comparison.md` — 技术方案对比与选型建议
- `06-ui-mapping-paradigm.md` — UI 坐标验证方法论 + 已验证坐标 + 战斗流程
- `08-code-architecture.md` — 9层架构设计 + 实施进度
- `09-code-review-lessons.md` — 代码审查教训（7条规则 + 未来审查清单）

## 文档体系

项目采用**文档先行**开发方式，严格遵循以下规则：

**强制文档加载规则**:
- **每次会话启动**，必须按以下顺序加载所有文档：
  1. `docs/` 目录下的所有 `.md` 文件（requirements、architecture、api、development、deployment、compliance、coding-standards）
  2. 关键目录的 `README.md`（根目录、src/、tests/、assets/等）
  3. `memory/` 下的所有历史记录
  4. `docs/plans/` 下的当前计划文件

**文档先行开发流程**:
1. **准备阶段** — 查阅现有文档（docs/、memory/）
2. **设计阶段** — 在文档中记录设计决策和变更计划
3. **实现阶段** — 严格按文档进行代码实现
4. **验证阶段** — 实现后必须review并更新所有相关文档

**文档维护强制要求**:
- 任何代码变更前必须先查阅和更新相关文档
- 实现完成后必须review文档确保与代码同步
- 新增目录必须同时创建标准 `README.md`
- 重要设计决策必须记录到对应文档中
- 每次有代码改动、结构变化、讨论结论时，必须更新 memory

**编码前强制检查清单**:
1. **必须阅读** `docs/coding-standards.md` - 企业级代码规范与最佳实践
2. **严格遵循** 类型系统、错误处理、异步编程等技术标准
3. **强制执行** Result模式、Protocol接口、依赖注入等架构模式
4. **确保通过** mypy --strict、pytest覆盖率>80%、所有质量检查工具
5. **代码审查** 性能优化、安全性、监控等非功能性要求

**目录规范**:
每个目录都必须有 `README.md`，包含：目录职责、文件组织规范、接口说明、使用示例、注意事项。

## Web Search

Claude Code's built-in `WebSearch` and `WebFetch` tools are **not functional** in this environment (blocked by network restrictions).

**Workaround**: Use `curl` via `Bash` tool to fetch web content directly. For search, use:
```bash
curl -sL "https://www.bing.com/search?q=your+query" 2>&1
```
Or use the GitHub API via `curl` or `gh` CLI for GitHub-related lookups.

## Development Environment

The following tools are available globally on this system:

| Tool    | Version   | Path                                      |
|---------|-----------|-------------------------------------------|
| Python  | 3.11.8    | `C:\Program Files\Python311\python.exe`   |
| pip     | 24.0      | `C:\Program Files\Python311\Scripts\pip.exe` |
| uv      | 0.11.2    | `C:\Program Files\Python311\Scripts\uv.exe` |
| Node.js | 22.16.0   | `C:\node22\node-v22.16.0-win-x64\node.exe` |
| npm     | 10.9.2    | `C:\node22\node-v22.16.0-win-x64\npm.cmd` |
| gh      | 2.67.0    | `C:\gh\bin\gh.exe`                        |

**Note**: `gh` was manually installed to `C:\gh\bin`. If `gh` is not found in a new shell session, ensure `C:\gh\bin` is in the system PATH.

## Plugins

- **superpowers** (v5.0.7) - Installed via `obra/superpowers-marketplace`. Provides agentic workflow skills (brainstorming, TDD, planning, code review, etc.)

## Platform Notes

- OS: Windows 11 Pro
- Shell: bash (Git Bash style via Claude Code)
- Use Unix-style paths in shell commands (forward slashes)
- The `winget` package manager is currently broken on this system; use direct downloads or `curl` for installing tools

## 分辨率与多分辨率适配 — 设计约束

**开发测试环境使用 1600×900（16:9），但不能假设所有用户都是此分辨率。**

用户的游戏窗口可能是：
- 不同分辨率：1920×1080、1280×720、2560×1440 等
- 不同宽高比：16:9、16:10、4:3、21:9 等
- 窗口化 vs 全屏，窗口大小可变

**强制设计规则**:
1. **坐标必须使用归一化比例**（0.0~1.0），不得硬编码像素坐标
2. **模板匹配必须考虑缩放**——模板和截图分辨率不一致时需要缩放对齐
3. **OCR 不受分辨率影响**（自带缩放），但 region 裁剪坐标仍需归一化
4. **UI 布局假设**：游戏 UI 元素的相对位置（比例）在不同分辨率下基本一致，但不同宽高比下布局可能有差异（如 4:3 下左右留黑边或 UI 重排）

**当前状态**:
- `DeviceAdapter.screenshot()` 已有自动缩放到设计分辨率的逻辑
- `src/` 代码中的坐标已部分迁移到 fractional coordinates（0.0~1.0）
- 模板匹配尚未处理多分辨率适配
- 需要在截图层或匹配层统一处理分辨率归一化

## UI 坐标定位 — 禁止规则

**禁止使用像素亮度/颜色扫描来定位 UI 元素坐标。** 这个方法已反复证明不可靠：
- 游戏 UI 背景颜色多变，亮度阈值无法泛化
- 角色模型、特效、动态背景会干扰扫描
- 结果经常误判，浪费大量调试时间

**必须使用的方法**:
1. **cv2.matchTemplate** — 模板匹配，用预裁剪的 UI 签名区域匹配
2. **目视缩略图 + 估算** — 从 800x450 缩略图目测坐标，乘以 2 换算到 1600x900
3. **cv2.findContours** — 轮廓检测，用于定位按钮/卡片等有明确边界的元素
4. **OCR (如需要)** — 文字识别定位
5. **交互式验证** — 点击后截图确认结果，每个坐标都必须实测验证

## 游戏交互 — 快捷键优先规则

**当 UI 元素旁边标注了快捷键提示时，优先使用键盘快捷键而非鼠标点击。**

原因：
- 键盘输入不会导致鼠标光标跳动，对后台操作更稳定
- 某些按钮点击不生效（如宿舍退出确认），但对应的快捷键可靠

注意事项：
- 快捷键标注通常在按钮的**下方或侧面**，不是按钮本身
- 必须理解快捷键对应的是哪个按钮，而不是点击快捷键文字所在的区域
- 常见模式：确定/购买 → Enter (0x0D)，取消/关闭 → ESC (0x1B)

