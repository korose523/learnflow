# 变更日志

本文件按 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 风格维护，**按日期倒序**，
标注 `Added` / `Changed` / `Fixed`。

> **纪律**：以下每一条都来自 `git log --date=short --pretty='%h|%ad|%s'`，并附提交号可回查。
> **未编造任何条目**；提交信息未涉及的内容不写入。

- 版本与 Zenodo 记录的对应关系见 [`CITATION.cff`](CITATION.cff) 与 README「引用」一节。
- 仓库现有 tag：`v0.1.0`（`0cfbeba`，2026-09-11）、`v0.2.0`（`0bee572`，2026-09-13）、
  `audit-m2-20260911`（`8a32843`，封存审计时点）。

---

## 2026-09-29

### Fixed
- **M3**：修复 ④b 模型族 × 规模矩阵的可复现性缺陷，并消除支撑文档中与之矛盾的陈旧表述（P0）。`f52b825`

---

## 2026-09-28

### Added
- 第 4 篇支撑稿 **M4《信度结构化组合难度估计》**完整稿与英文投稿件
  （`docs/M4_信度结构化组合难度估计_完整稿.md`、`docs/M4_submission_EN.md`）。`313af0e`
- M4 后端估计器 `learnflow-backend/app/services/difficulty_m4.py`。
  ⚠️ **已实现、未集成**：仅 `tests/test_difficulty_m4.py`（30 项）引用，尚未接入任何运行时路由。`313af0e`

### Changed
- 并入 learnflow-main 快照（2026-09-28），同步更新四篇稿件与 M3 矩阵。`313af0e`

---

## 2026-09-27

### Added
- M3 矩阵补入 `F4_DeepSeek/S1` 单元格（deepseek-r1:1.5b，实测 1.8B），矩阵达 **8 个 EVALUATED 单元格**，门禁 PASS。`75be700` `08e4643`
- 从 `/api/show` 实测 deepseek-r1:1.5b / :32b 的模型身份（1.8B / 32.8B Q4_K_M），并记录 Qwen2-distill 警示。`3532783`
- M2 附录 A4：33 题**闭集**盲态双编码问卷 v2/v3，扩展至 4 个外部系统（含 Habitica、Anki），含逐系统拆解与自检 kappa。`13a5ad9` `c125f04`
- M2 附录 A4：coderB 闭集编码问卷（HTML + CSV 导出）与 coderA 闭集复核表。`b306346`

### Changed
- A4 通道重编码资产改为闭集归一化口径。`cf0c230`
- 批量落盘 M1 AIPW、M3 R09、M2 A4、M3 矩阵与 docs/backend 同步（201 文件，3.71 MB）。`f43e2a7`
- `scripts/audit_staged.py` 归位到 `scripts/`（此前误提交到仓库根 `_audit_stage.py`）。`341d2ce`

### Fixed
- 修正 ④b 矩阵状态被写为「7 格 EVALUATED」的陈旧表述，改为 8 格。`5448595`
- 停止 32b 模型运行（19GB 模型 vs 15.8GB RAM），并把 `MIN_KEYS` 完备性门槛泛化（矩阵仍为 8 格）。`d719987`
- coderB v2 重编码后计算权威 A4 Cohen kappa，全部字段达阈值。`3faefd7` `208b1d4`

---

## 2026-09-26

### Added
- A4 双编码方案追踪与 kappa 管线；投稿前模拟审稿回复与就绪评估。`22f0ed4`
- A4 闭集双语 CODEBOOK v2 与 coderB 重编码模板。`de5aefd`

### Changed
- 按模拟审稿意见收敛 M1/M3 框架表述：教育利害关系与范围界定、headline 结论与方法定位。`75eee28`

### Fixed
- 修正 LevelUpXP 仓库引用。`8609eb1`
- 补齐投稿前缺口：M1 item12 与诚实负结果框架、M2 Route A 与 §5.4 修正、M3 跨模型边界与 8 项外部效度条目。`9b39372`

---

## 2026-09-13

### Added
- O11 **符号校正 + 折半信度加权**融合，并据此重新生成 M1/M2/M3 完整稿。`462ebdf`
- ECDF–logit 融合模块与 O8 `fused6` 估计器。`4073bb0`

### Changed
- `results/` 只保留最终红线证据，归档 agent 探测临时产物。`0bee572`（tag `v0.2.0`）

---

## 2026-09-11

### Added
- 自陈测量基础设施（量表目录 / 作答 / 覆盖度）与 LAI 偏倚修复。`8a32843`（tag `audit-m2-20260911`）
- **首次公开发布**：补齐 MIT 许可与社区文件（README / CONTRIBUTING / CITATION.cff / .zenodo.json）。`0cfbeba`（tag `v0.1.0`）

### Fixed
- 修复数据诚信缺陷（随首次公开发布一并落盘）。`0cfbeba`

---

## 2026-09-10

### Added
- 干预奖励函数 + RL 在线决策闭环接线。`30cabbd`
- 实时分析层、研究同意标记、班级宠物，并修复 `learning_events` 建表。`8d6eba7`

### Changed
- UI 设计系统落地、三页信息架构升级、全局氛围背景；构建与类型检查通过。`7ce9ffb`
- 机制数统一 **53 → 54**（`LF-M01`–`LF-M54`），敏感性区间 51–56 → 52–57，指纹刷新。`57d9540`

### Fixed
- schema 自动迁移 + 种子统一 + SQLite 时区修复，打通研究管线。`79d7f36`
- design token 重复声明导致的构建失败。`bdac9d4`
- 冷启动死锁与审计假阳性。`30cabbd`

---

## 2026-09-06

### Added
- `SQLExperimentStore` + 建表脚本落地到项目真实数据库方言。`59c988b`
- dataclass 状态后端与 `mutate()` 原子读改写。`10a4db7`

### Changed
- 9 个内存态容器接入可落盘后端，消除 11 处就地修改的静默数据丢失。`a4c40ac`

### Fixed
- 补全泛型容器类型还原，消除切换后端时的 `AttributeError`。`14ecac1`

---

## 2026-09-05

### Fixed
- 修正 10 条 `impl_ref` 行号漂移，改为符号级引用。`616e1c1`
- 修复三处静默失效——错误数据此前与正常数据无法区分。`79f1673`
- 修复三处 P0 正确性缺陷，并把 LF-M52 合规引擎真正接入编排器。`60b1bcc`

---

## 2026-09-04

### Added
- 28 个孤儿机制经 step-13 评估钩子接入编排器（`LF-M01..M53` 落地 53/53）。`fa2f119`

### Changed
- 重写期刊论文拆分方案为「学术论文组合审计报告」。`061e2cf`
- 重写博士论文总纲为学位论文结构规格。`8be9643`
- 重写学术论文转化方案为开题报告学术版。`e819cd7`
- 重写机制治理方案为期刊论文稿件（分类学 / 仲裁形式化 / 可复现性 / 消融设计）。`feda25b`

### Fixed
- 定点修正文献测绘方向③的陈旧数字，改为治理前后对照口径。`85eafd4`

---

## 2026-09-03（仓库基线日）

### Added
- 为 LearnFlow 建立版本控制基线。`2c6972e`
- 机制注册表 `mechanism_registry.py`（`LF-M01..LF-M53`）+ 11 步流水线注册表驱动。`4c253f5`
- 学习方法统一注册表 + 数字诚信复算脚本（可复现性印章）。`41d2dd8`
- 落地 28 种学习方法，注册表扩至 `LF-L28`。`8072383`
- 三层漏斗干预仲裁器 `mechanism_arbitrator.py` + `Effect` 类型。`31f0d26`
- 实验框架 §3.4.2 改造：机制开关 + 功效分析预注册 + 落库后端。`d6e2c82`
- 机制落地审计矩阵 + `xp_leveling` 消融门控修复（53 机制可复算落地状态）。`0e748b7`
- 补全实验：类别级消融预设 + 真实样本量门槛 + 回放接埋点 + 预注册 YAML（DEFF=2.45 分层 Gatekeeping）。`3d4eee1`
- `learning_events` 埋点接入 `process_submission` + 决策快照。`0f66fb9`

### Changed
- `StateStore` 可插拔后端：内存态容器落库（宝箱 `BOX_STATES`、技能树 db 持久化接线），并批量迁移 9 个容器。`f75f364` `4984371`
- FOMO 引擎迁移：`generate_fomo_nudge` 改为产出 `Effect` 候选并经仲裁器下发（LF-M44）；LF-M52 命中时 Layer1 丢弃。`9846ae1`
