# Zenodo v0.2.0 上传 · 准备清单与命令

> 生成时间：2026-09-23（续会话 10 · E 任务准备）
> 关联：待办 §3-E；`.zenodo.json`（v0.2.0，已备）；`scripts/zenodo_upload.py`（就绪即传工具）
> 纪律：本会话**不代执行**外部发布动作（需 Zenodo token 与作者授权）；本文件把 E 从「⛔ 待上传」推进到「🟡 准备就绪·待 token」。

---

## 0. 当前状态（已核验）

- ✅ `.zenodo.json` 结构有效、可直接用于上传（v0.2.0；标题/描述已统一为难度路线；LAI 明确降为「附属模块·未验证」；license MIT；upload_type software；language eng；related_identifiers 指向 GitHub 仓库）。
- ✅ `scripts/zenodo_upload.py` 已写、已 `py_compile` 通过、dry-run 实跑正常（打印计划、不联网）。
- ✅ 打包口径已确认：`git archive HEAD` = **470 文件**，已自动排除 `data/`(13GB)、`.venv`、`node_modules`、`artifacts/state/`、`experiments.json` 等（尊重 `.gitignore` 与伦理边界）；`artifacts/` 刻意保留（可复现性印章）。
- ⚠️ git tag 现状：现有 `v0.1.0`（无 `v0.2.0`）→ 上传前应打 `v0.2.0` tag。

---

## 1. 上传前置依赖（外部，须作者提供）

| 依赖 | 用途 | 获取方式 |
|---|---|---|
| **ZENODO_TOKEN** | 生产环境 API 写权限 | zenodo.org → 右上角头像 → Applications → Personal access tokens；或 `settings/tokens` |
| **ZENODO_DEPOSITION_ID** | 对 v0.1.0 记录建 newversion（接续，不新建重复记录） | 从现有 v0.1.0 Zenodo 记录 URL 提取（`/deposit/depositions/<ID>` 的数字 ID） |
| （推荐）**git tag v0.2.0** | 冻结发布快照，使 tarball 取自该 tag | `git tag v0.2.0 && git push --tags` |
| （备选）**GitHub × Zenodo 连接** | 走 GitHub 集成自动归档（路径 A） | Zenodo「GitHub」页授权连接 `korose523/learnflow` 仓库 |

> 沙盒预演可用 `ZENODO_SANDBOX_TOKEN` + `--sandbox`（sandbox.zenodo.org，需先在该处建 token 与测试 deposition）。

---

## 2. 两条上传路径

### 路径 A（推荐 · GitHub 集成，最干净）
1. 打 tag 并发布 GitHub Release：`git tag v0.2.0 && git push --tags` → GitHub 建 Release。
2. Zenodo GitHub 集成侦测到新 Release → 自动建档案，读取仓库根 `.zenodo.json` 作元数据。
3. 在 Zenodo 记录页核对标题/描述（应为 v0.2.0 难度路线版本），发布并领取 DOI。
- 优点：tarball 由 Zenodo 从 Release 自动生成，无需手动上传；记录与 GitHub Release 绑定。

### 路径 B（手动 API · 用本脚本）
1. 设置 `ZENODO_TOKEN`（与可选 `ZENODO_DEPOSITION_ID`）。
2. dry-run 确认计划：`python scripts/zenodo_upload.py --ref v0.2.0`（或默认 HEAD）。
3. 实际发布：`python scripts/zenodo_upload.py --ref v0.2.0 --yes`（接 v0.1.0 则同时设 `ZENODO_DEPOSITION_ID`）。
- 安全：默认 dry-run；`--yes` 才发写请求；绝不删除 deposition。

---

## 3. 脚本用法（`scripts/zenodo_upload.py`）

```
# dry-run（无 token 亦可，仅打印计划）
python scripts/zenodo_upload.py --ref v0.2.0

# 实际发布（接续 v0.1.0 记录）
set ZENODO_TOKEN=xxxxx
set ZENODO_DEPOSITION_ID=yyyyy        # v0.1.0 记录的 deposition ID
python scripts/zenodo_upload.py --ref v0.2.0 --yes

# 沙盒预演
set ZENODO_SANDBOX_TOKEN=xxxxx
python scripts/zenodo_upload.py --ref v0.2.0 --sandbox --yes
```

- 元数据源：仓库根 `.zenodo.json`（v0.2.0）。
- 打包：`git archive --format=tar.gz`（尊重 `.gitignore`）。
- newversion 流程：先 `POST .../actions/newversion` 取 draft，再用 `.zenodo.json` `PUT` 覆盖旧元数据（v0.1.0 标题/描述），上传 tarball，最后 `publish`。
- 依赖：仅 Python 3 标准库（urllib，无 requests 依赖）。

---

## 4. 上传后动作（作者/本会话后续）

1. **更新 `CITATION.cff`**：`version: 0.2.0` + 新增 `doi:`（Zenodo 记录的 DOI，格式 `https://doi.org/10.5281/zenodo.<ID>`）。
2. **README 加 Zenodo badge**：`![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.<ID>.svg)`。
3. **文档记 DOI**：在 `references.bib` 或 docs 记 Zenodo DOI（artifact 引用）。
4. **核对 LAI 口径**：发布物描述已声明 LAI 为「未验证附属模块」，与三稿一致。

---

## 5. 本会话不代执行说明（阻塞）

- E 是**外部发布动作**，需作者提供 `ZENODO_TOKEN` 并对发布授权；本会话已把脚本与清单准备到「一键上传」状态，但**不擅自代执行**。
- 提供 token 后，本会话可代为跑路径 B 的 `--yes`（或你自行运行）；路径 A 须你在 GitHub/Zenodo 网页操作。

---

## 6. 待办更新

- 待办 §3-E：`⛔ 待上传` → `🟡 准备就绪（脚本+清单已备，待 ZENODO_TOKEN 与 deposition ID）`。
- 仍外部/人工：G 正式提交(10-20)、H 语言确认；实验类 A1/A2/A4/C 待外部算力。
