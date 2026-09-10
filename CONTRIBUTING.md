# 贡献指南

感谢你关注 LearnFlow。这是一个**研究 artifact**：它既是一个可运行的 K12 自适应学习平台，
也是一组实证论文的可复现性底座。因此本项目的贡献标准在「软件质量」之外，**额外要求数字与证据的可核验性**。

---

## 三种参与方式

本项目明确区分三条通道，请按你的目的选择：

| 你想做的事 | 去哪里 |
|---|---|
| **报告缺陷 / 问题** | 开一个 Issue（Bug 报告），见 §报告问题 |
| **寻求使用支持** | 先查 [`README.md`](README.md) 与 `docs/`；仍无法解决则开 Issue（Support 标签） |
| **提交代码 / 文档改动** | 提 Pull Request，见 §贡献流程 |

---

## 报告问题

提交 Bug 报告时，请尽量包含：

1. **环境**：操作系统、Python 版本（`python -V`）、Node 版本（`node -v`）
2. **复现步骤**：最小可复现路径，能贴命令就贴命令
3. **期望行为 vs 实际行为**
4. **完整错误栈**（不要只截一行）
5. **相关日志**：后端 `uvicorn` 输出、浏览器控制台输出

> **重要**：请先确认问题不是已知环境陷阱。两个最常见的误报来源：
> - `PYTEST_DEBUG_TEMPROOT` 指向的目录**不存在** → 依赖 `tmp_path` 的用例批量抛 `FileNotFoundError`，
>   看起来像大规模回归，实为环境问题。请先创建该目录并重新运行。
> - 本机存在 HTTP 代理时会拦截 `localhost` 流量 → 健康检查失败。请对 localhost 绕过代理
>   （`curl --noproxy '*'`，或设置 `no_proxy=localhost,127.0.0.1`）。

---

## 贡献流程

```bash
# 1. Fork 并克隆
git clone https://github.com/<your-name>/learnflow.git
cd learnflow

# 2. 建分支（请用有意义的前缀）
git checkout -b fix/parent-daily-limit-persistence
#   feat/*  新功能    fix/* 缺陷    docs/* 文档    test/* 测试

# 3. 搭建环境（见 README「快速开始」）
```

### 提交前必须通过

**后端**（在 `learnflow-backend/`）：

```bash
# 全量测试必须零失败
PYTEST_DEBUG_TEMPROOT=<已存在的绝对路径>/pytest_tmp .venv/Scripts/python -m pytest tests/ -q

# 数字一致性门禁必须通过（exit 0）
.venv/Scripts/python scripts/verify_asset_numbers.py --doc-check --with-pytest
.venv/Scripts/python scripts/verify_counts.py
```

**前端**（在 `learnflow-frontend/`）：

```bash
npm run lint
npx tsc --noEmit
npm run build
```

### 提交信息

沿用仓库既有的约定式前缀：

```
feat(范围): 简短描述
fix(范围): 简短描述
docs: 简短描述
test: 简短描述
refactor(范围): 简短描述
```

示例：`fix(parent): 每日时长上限改为后端持久化，替代 localStorage`

---

## 贡献的硬性约束

本项目的核心工程约定是**数字诚信**：文档中出现的每一个头部计数，都必须能被代码复算。

1. **不得引入无法复算的数字。**
   若你的改动使某个计数发生变化（如新增机制、新增测试、新增端点），
   **必须同时更新** `scripts/verify_asset_numbers.py` 中登记的基线值，
   否则 `--doc-check` 会以退出码 1 失败。

2. **不得编造数据。**
   任何面向用户或面向研究的数值若来自真实数据，必须真的来自真实数据；
   无数据时应返回 `null` / 空集合并显式说明，而不是填一个「看起来合理」的常量。
   历史上本项目修复过多处此类缺陷（AI 分析层喂入伪造的活跃时段、每日限时的假持久化），
   这类问题一律视为**高优先级缺陷**。

3. **不得留下沉默的死代码。**
   新模块要么被运行时入口接线（暴露为端点/被服务调用），要么在
   `learnflow-backend/docs/research_tooling.md` 中**显式登记**为「离线分析工具，按设计不暴露」。

4. **不得提交敏感数据或凭据。**
   参见 `.gitignore` 与 README 的「数据边界」一节。特别是：
   `.env`、`artifacts/state/`、`artifacts/experiments.json`、`*.db` **绝不入库**。

5. **涉及人类被试的改动**须先说明伦理审查状态。本项目面向未成年人，
   任何收集、存储、导出未成年人数据的改动都需要额外审查。

---

## 代码风格

- **Python**：遵循项目现有结构。API 层只做参数解析与错误映射，领域逻辑放在 `app/services/`。
  新增端点请参照最新的独立 API 模块（`app/api/class_pet.py`）的认证与响应约定。
- **TypeScript / React**：函数组件 + Hooks；类型必须完整，`tsc --noEmit` 必须零错误。
- **文档**：中文，全角标点，表格保持对齐。

---

## 支持

- **使用问题 / 缺陷**：请开 Issue（这是首选通道，便于他人检索）
- **安全问题**：请**不要**公开开 Issue，直接私下联系维护者
- **维护者邮箱**：`<TODO: 补充维护者联系邮箱>`

---

## 许可证

向本项目贡献即表示你同意你的贡献以 [MIT 许可证](LICENSE) 发布。
