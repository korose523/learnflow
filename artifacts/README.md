# 验证资产（artifacts/）

本目录保存**可复现性验证脚本**与**验证证据截图**。它们记录的是「文档与代码中的头部数字
是如何被实测的」，而不是运行时的业务产物。

> ⚠️ **数据边界**：本目录下的 `state/`、`experiments.json`、`*.db`、`*.log` 属于被试运行时
> 状态与本地环境产物，已在 `.gitignore` 中排除，**不得提交**。此处保留的仅为脚本与截图。

---

## 1. HTTP 层端到端验证

| 脚本 | 验证内容 |
|---|---|
| `e2e_api_v2.sh` | 在**同一次 shell 调用内**启动后端 → 用轮换后的种子口令登录 → 校验自陈测量层（`GET /instruments`、`POST /instruments/{code}/responses`、`GET /instruments/me/coverage`）→ 校验 LAI 仪表盘在提交前后 `coverage.weight_basis` 与 `control.measured` 的变化 → 校验错误路径（越界 400 / 未知量表 404 / 未授权 401）→ 回归既有端点（leaderboard、parent children） |
| `e2e_coverage.sh` | 在**全新数据库**上验证 LAI 覆盖度的递进：0.55（仅行为代理）→ 0.80（+行为控制）→ 1.00（+功能影响），并确认未测维度始终不被当作「健康」计分 |

**为什么必须「同一次 shell 调用内」**：后台进程组会在工具调用结束时被回收，跨调用启动的
`uvicorn` 会变成不可达（`curl` 退出码 7 / HTTP `000`）。因此这两个脚本把
「启动 → 健康检查 → 验证 → 收尾」写在同一个脚本里。

## 2. 浏览器层端到端验证（真实 Chromium）

| 脚本 | 验证内容 |
|---|---|
| `run_login_e2e.sh` | 登录页口令解耦后，开发模式快捷登录仍可用；提交后落到 `/student` 且无控制台错误 |
| `run_lai_card.sh` | 在**全新数据库**上渲染 `/student`，断言 LAI 卡片的覆盖度披露：未测维度显示「名义权重 N% · 不计入」，不显示分数、不显示风险标记；已测维度权重已归一化；控制台零错误 |

**为什么需要真实浏览器**：`tsc`、`eslint`、`vite build` 与单元测试**全部通过**的情况下，
本项目历史上仍出现过页面级崩溃（`Promise.allSettled` 解构错误导致学生仪表盘恒显示
「无法加载」，且不产生任何 console error）。只有真实浏览器读取渲染后的正文才能暴露此类缺陷。

### 运行前置

1. **Playwright Chromium**：脚本会在 `%LOCALAPPDATA%/ms-playwright` 下自动查找
   `chromium-*/chrome-win64/chrome.exe`。若不存在，先执行
   `npx playwright install chromium`。
2. **`playwright-core`**：脚本通过 `NODE_PATH` 指向一个安装了 `playwright-core` 的
   `node_modules`。若你的环境不是这样，请改为在脚本同目录 `npm i playwright-core` 并调整
   `NODE_PATH`。
3. **端口**：后端固定 `8000`，前端固定 `5173`（`vite.config.ts` 将 `/api` 代理到 8000）。
   若端口被占用，请先释放。
4. **脚本中的绝对路径**：`PY`、`PATH`、`NODE_PATH` 三处指向本仓库作者的机器布局，
   **在别的机器上运行前需要按你的环境修改**。这是脚本唯一不可移植的部分。
5. **代理**：本机 `http_proxy` 会拦截 localhost 流量，脚本内统一使用
   `curl --noproxy '*'` 并设置 `no_proxy=localhost,127.0.0.1`。若你的环境无代理可忽略。

## 3. 证据截图（`e2e_screenshots/`）

| 文件 | 对应缺陷 / 特性 |
|---|---|
| `lai_coverage_fresh.png` | 全新库上的 LAI 卡片：覆盖度 55%，未测维度标注「不计入」 |
| `login_decoupled.png` | 口令解耦后的登录页，开发模式快捷登录可用 |
| `parent_page.png` / `parent_summary*` | 家长端周报（修复合约漂移后的渲染） |
| `student_home.png` | 学生仪表盘（修复 `Promise.allSettled` 解构缺陷后的渲染） |
| `student_leaderboard.png` | 新接线的学习榜页面 |

截图用于留痕，**不作为自动化断言**；断言在脚本内以文本匹配方式给出。

## 4. 数字门禁（不在本目录）

文档中的资产数字由 `learnflow-backend/scripts/` 下的脚本复算，与本目录无关：

```bash
cd learnflow-backend
.venv/Scripts/python scripts/verify_counts.py                     # 机制/方法/技能树计数
.venv/Scripts/python scripts/verify_asset_numbers.py --doc-check  # 文档资产数字一致性（差异即退出码 1）
```
