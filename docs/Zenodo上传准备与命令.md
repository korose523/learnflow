# Zenodo v0.2.0 上传 · 准备清单与命令

> 生成时间：2026-09-23（续会话 10 · E 任务准备）
> **命令与路径复核：2026-09-29**（复核内容：`.zenodo.json` 存在且版本为 0.2.0；`scripts/zenodo_upload.py` 的 dry-run 实际执行通过；git tag 现状、打包文件数、data/ 排除情况均按当日仓库实测）
> 关联：待办 §3-E；`.zenodo.json`（v0.2.0，已备）；`scripts/zenodo_upload.py`（就绪即传工具）
> 纪律：本会话**不代执行**外部发布动作（需 Zenodo token 与作者授权）；本文件把 E 从「⛔ 待上传」推进到「🟡 准备就绪·待 token」。

---

## 0. 当前状态（已核验）

- ✅ `.zenodo.json` 结构有效、可直接用于上传（v0.2.0；标题/描述已统一为难度路线；LAI 明确降为「附属模块·未验证」；license MIT；upload_type software；language eng；related_identifiers 指向 GitHub 仓库）。
- ✅ `scripts/zenodo_upload.py` 已写、脚本存在；**2026-09-29 实跑 dry-run 通过**（退出码 0，打印计划、未发起网络请求；无需 token）。
- ✅ 打包口径已确认：**`git archive v0.2.0` = 470 文件**（tag `v0.2.0` 指向提交 `6a4858b`），已自动排除 `data/`(13GB)、`.venv`、`node_modules`、`artifacts/state/`、`experiments.json` 等（尊重 `.gitignore` 与伦理边界）；`artifacts/` 刻意保留（可复现性印章）。
  - ⚠️ **tag 落后于 HEAD**：截至 2026-09-29，`git archive HEAD` = **797 文件**（HEAD = `f52b825`）。即「470」是 **v0.2.0 tag 快照**的文件数，若改用 HEAD 打包则为 797。上传前须二选一并记录所选 ref。
  - 复算命令：`git archive <ref> | tar -t | wc -l`（把 `<ref>` 换成 `v0.2.0` 或 `HEAD`）。
- ⚠️ **`data/` 必不在 tarball 内**：`.gitignore` 显式忽略 `data/` 与 `data_backup/`，且 `git ls-files data | wc -l` = **0**（四个公开数据集原始文件从未入库）。因此归档物**不含任何数据集原文**；若 Zenodo 记录需承载数据，redataset须另行处理（见下方 §1.1）。
- ⚠️ git tag 现状：**`v0.2.0` 已存在**（指向 `6a4858b`，落后于 HEAD `f52b825`）。若打算把当前 HEAD 作为发布快照，须**在 HEAD 上重新打 tag**（如 `v0.2.1`）或明确以 `v0.2.0` 的旧快照发布。

---

## 1. 上传前置依赖（外部，须作者提供）

| 依赖 | 用途 | 获取方式 |
|---|---|---|
| **ZENODO_TOKEN** | 生产环境 API 写权限 | zenodo.org → 右上角头像 → Applications → Personal access tokens；或 `settings/tokens` |
| **ZENODO_DEPOSITION_ID** | 对 v0.1.0 记录建 newversion（接续，不新建重复记录） | 从现有 v0.1.0 Zenodo 记录 URL 提取（`/deposit/depositions/<ID>` 的数字 ID） |
| **git tag（已存在 `v0.2.0`）** | 冻结发布快照，使 tarball 取自该 tag | 现存 tag：`v0.1.0`、`v0.2.0`（2026-09-29 实测）。`v0.2.0` → 提交 `6a4858b`；若要以当前 `HEAD`(`f52b825`) 发布，须新打 tag：`git tag v0.2.1 && git push --tags` |
| （备选）**GitHub × Zenodo 连接** | 走 GitHub 集成自动归档（路径 A） | Zenodo「GitHub」页授权连接 `korose523/learnflow` 仓库 |

> 沙盒预演可用 `ZENODO_SANDBOX_TOKEN` + `--sandbox`（sandbox.zenodo.org，需先在该处建 token 与测试 deposition）。

### 1.1 数据集不在归档内（须知悉）

`.gitignore` 忽略 `data/` 与 `data_backup/`，且这两个目录下**没有任何被 git 跟踪的文件**（`git ls-files data | wc -l` = 0），因此 `git archive` 生成的 tarball **不含四个公开数据集（assist09 / DBE-KT22 / XES3G5M / Junyi）的原始文件**。原因见 `.gitignore` 注释：它们非本项目产物、体积达 13 GB 级，且 Junyi 为 CC-BY-NC-SA-4.0（禁商用），不应随代码分发。

处理方式（二选一，由作者定夺）：

1. **代码归档与数据分离**：Zenodo 记录描述中写明数据集须按 `docs/Kaggle与DataShop凭据获取指南.md` 从上游获取，本记录只保证**代码 + 可复现性印章 + 派生结果**的可复现性；
2. **另行处理数据**：若确需一并归档，不得通过放开 `.gitignore` 实现，须单独打包并在 Zenodo 记录中以 additional file 形式附加，同时确认各数据集许可允许再分发。

---

## 2. 两条上传路径

### 路径 A（推荐 · GitHub 集成，最干净）
1. 打 tag 并发布 GitHub Release：若以当前 HEAD 发布，用新 tag（`git tag v0.2.1 && git push --tags`）；若沿用既有 `v0.2.0`（指向 `6a4858b`），则直接对该 tag 建 Release。
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
- 依赖：仅 Python 3 标准库（无 requests 依赖）。
- **可选参数全集**（与脚本 argparse 一致）：`--yes`、`--sandbox`、`--ref`（默认 `HEAD`）、`--tarball`、`--deposition-id`（默认值取环境变量 `ZENODO_DEPOSITION_ID`）。
- Windows 下若 `set` 命令不生效，改用 Git Bash：`export ZENODO_TOKEN=xxxxx`。

### 3.1 最小可用示例（2026-09-29 实跑通过）

在仓库根执行，不需要 token、不联网：

```bash
python scripts/zenodo_upload.py --ref v0.2.0
```

实测输出（退出码 0）：

```json
{
  "zenodo_api": "https://zenodo.org/api",
  "mode": "new deposition",
  "version": "0.2.0",
  "license": "MIT",
  "upload_type": "software",
  "tarball_bytes": 7948210,
  "will_publish": false
}
```

> 以上为 `--ref v0.2.0`（tag 快照）的实测结果。`tarball_bytes` 随所选 ref 变化，重跑请以实际输出为准；`mode` 在未设 `ZENODO_DEPOSITION_ID` 时为 `new deposition`。

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
