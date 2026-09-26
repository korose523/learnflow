# M2 A4 双编码 Cohen κ —— Provisional 报告（2026-09-26）

> **状态：Provisional / 未达投稿门槛，A4 仍 UNCHECKED。**

> 本文件为内部工作报告，非投稿稿 §6 终稿。M2 稿 §6 自设红线（"A4 完成前不报告任何 κ 值"），故 κ 仅在此与工作稿中记录，待 A4 真正完成（coderB 收敛多值 + ≥4 系统 + κ≥0.41）后方可写入 §6 并勾销清单第 19 项。

## 1. 方法（透明、可审计）
- 双编码：coderA（E2 真实锚点） vs coderB，17 个实例（Ludilearn 6 + Level Up XP 11）。
- coderB 原 CSV 含 12 个 `target_construct`、6 个 `channel` 多值单元格（分隔符 `?·?` / ` · ` / ` / `，LUXP_3 末位带 `?` 不确定标记）。
- 因 κ 管道要求每格恰一个标签，采用**预注册裁定规则**把多值格收敛为单标签：
  - 首候选 = coderB 列出的第一个（视作主判定）→ 主估计；
  - 上界：若 coderA 标签出现在候选集 → 视为该格一致；
  - 下界：若候选集存在 ≠coderA 的标签 → 取该标签（最差情形）。
- 注：上述规则**不替代 coderB 人工收敛**；区间越宽，说明编码方案/训练越不充分。

## 2. κ 区间估计（17 项，两编码者）

| 字段 | 下界 | 主估(首候选) | 上界 | 判定(主估) |
|---|---|---|---|---|
| target_construct | 0.034 | 0.346 | 0.485 | 不足(<0.40) |
| direction | 0.577 | 0.577 | 0.577 | 可接受(0.41–0.60) |
| channel | 0.332 | 0.572 | 0.572 | 可接受(0.41–0.60) |

## 3. 逐字段解读
- **target_construct（名义）**：主估 0.346 = **不足(<0.40)**；区间 [0.034, 0.485] 极宽，说明 coderB 在该字段的构念判定与 coderA 严重发散，且编码方案本身模糊。这是 A4 当前最薄弱的一环。
- **direction（有序·加权 κ）**：0.577 = **可接受(0.41–0.60)**，但仅勉强过线；两编码者在 LUDI_6/LUXP_1/3/7/10 的 withdraw/neutral/approach 判定上分歧明显。
- **channel（名义）**：主估 0.572 = **可接受**，下界 0.332 仍不足；差异多来自 coderB 的 channel 多值候选（如 分数/进度、等级/经验信息）。

## 4. 根因分析
1. **coderB 多值单元格未收敛**：12+6 格列出多个候选，κ 只能在裁定规则下近似，真实 IRR 须由 coderB 把每格收敛为单一标签后重算。
2. **CODEBOOK 标签集不一致（关键根因）**：A4 方案 §3 的 `target_construct`/`channel` 允许取值为**英文**（reward/nudge/badge/notification…），但 coderA/coderB 实际都用**中文**（身份/自主、成就/表现…）。两套词汇不映射，Cohen κ 自然偏低。→ 须先把 CODEBOOK 收敛为**单一、闭集、中英对齐**的标签表，再令双方据此重编码。

## 5. LevelUpXP 源仓库纠错（重要更正）
- **此前结论"LevelUpXP 404 / 不可复现"系误检**：当时查的是已失效的 `danbetcher/moodle-levelup`。
- **真实源为 `FMCorz/moodle-block_xp`**（commit `65541fdc9c77511a906353f6660e195eeaa51893`，Release v20.0），M2 稿 §6 已据此引用。
- **11 个 LUXP 锚点文件在该 commit 下全部 HTTP 200 核验通过**（badge_manager / cheatguard / group_division / levels_info / course_level_up_notification_service / promo / rank / limit_spec / the_dictator / state / course_user_leaderboard）。
- 结论：coderB 的 LUXP_* 判定**具备可复现锚点**，其独立性与可核查性不受影响；此前"LevelUpXP 不可获取"的担忧撤销。

## 6. A4 完整性门槛（仍缺）
- A4 要求**≥4 个外部系统**双编码；当前仅 2 个（Ludilearn + Level Up XP）已编码，缺 ≥2 个（候选 Habitica / Khan Academy 待 clone 复核）。
- 故 A4 在"系统数"维度仍未闭环，即便 κ 达标也不能勾销清单第 19 项。

## 7. 下一步（coderB / 编码负责人）
1. 把 `a4_coderB.csv` 中 12 个 target_construct、6 个 channel 多值格**收敛为单一标签**。
2. 依**修正后的闭集 CODEBOOK（中英对齐）**重编码全部 17 项（尤其 target_construct）。
3. 补 ≥2 个可公开获取、非同源的外部系统并双编码。
4. 重跑 `external_coding_kappa.py --coder-a a4_coderA.csv --coder-b <收敛后 coderB>`；全部字段 κ≥0.41 后，方可写入 M2 §6 并勾销第 19 项。

## 8. 复算命令
```bash
python results/m2/external_coding_kappa.py \
  --coder-a results/m2/a4_coderA.csv \
  --coder-b results/m2/a4_coderB_resolved_first.csv   # 首候选裁定版（仅用于试算）
```

> 数据文件：`a4_coderA.csv` / `a4_coderB.csv`（原始）/ `a4_coderB_resolved_first.csv`（裁定版）/ 本报告。