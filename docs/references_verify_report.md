# LearnFlow 参考文献 `[VERIFY]` 核验报告

> 生成时间：2026-09-22（续会话）
> 配套：`references.bib`（已回填 `note`）、`results/ref_verify/crossref_report.json`、`results/ref_verify/verify_refs.py`
> 范围：批量核验 `references.bib` 中全部 30 条标 `[VERIFY]` 条目的元数据（作者全名 / 卷期页码 / DOI 或标识符）
> 纪律：仅回填 web 可证实的真实元数据，**绝不虚构** DOI / 卷 / 页 / 作者；无标识符且无法证实者列「需作者补」

---

## 0. 汇总

| 指标 | 数量 |
|---|---|
| 标 `[VERIFY]` 条目总数 | 30 |
| `[已核验]`（四项一致 / 可证实） | 29 |
| `[部分核验]`（某项待作者确认） | ~~1（`dellanna2025` 作者名冲突）~~ → **0（已于 2026-09-23 闭环）** |
| 高风险条目（待办 §4 标注 3 条） | 3，全部澄清，非误填 |
| 触发页码仲裁 | 1（`neurips2017posetbandits`） |
| 预印本 / 非同行评议（引用须注明状态） | 10 |

> 注：待办原文记「M1 7 + M2 14 = 21 条」，实际 `references.bib` 中带 VERIFY 注释的条目为 **30 条**（其余为已核验但带 VERIFY 注释或分散标注者），本轮一并闭环。

---

## 1. 核验渠道与逐条结论

### 1.1 Crossref DOI 直查（9 条，全部 `[已核验]`）

| bib key | 载体 / 卷期页 / 年 | DOI | 作者（已补全名） |
|---|---|---|---|
| liu2025pykt | IEEE Trans. Knowl. Data Eng. 37(8):4512-4536, 2025 | 10.1109/TKDE.2025.3552759 | Liu Zitao, Guo Teng, Liang Qianru, Hou Mingliang, Zhan Bojun, Tang Jiliang, Luo Weiqi, Weng Jian |
| choudhary2025blockchain | Multimedia Tools Appl. 84(8):4003-4048, 2024 | 10.1007/s11042-024-20303-x | Choudhary Ankita, Chawla Meenu, Tiwari Namita |
| razzaq2026blockchain | IET Software 2026(1), 2026 | 10.1049/sfw2/5556408 | Razzaq Abdul, Numair Muhammad, Ahmed Salman, Junaid Waqas |
| jusic2025microcredential | EDULEARN Proc. 1:5382-5388, 2025 | 10.21125/edulearn.2025.1342 | Jušić Arvin, Fuks Svetlana, Kochovski Petar, Stankovski Vlado |
| lieberoth2015shallow | Games Cult. 10(3):229-248, 2015 | 10.1177/1555412014559978 | Lieberoth Andreas |
| falconcode2022 | SIGCSE TS 2023, pp.938-944 | 10.1145/3545945.3569822 | de Freitas Adrian, Coffman Joel, de Freitas Michelle, Wilson Justin, Weingart Troy |
| hamari2014doesgamification | HICSS 2014, pp.3025-3034 | 10.1109/HICSS.2014.377 | Hamari Juho, Koivisto Jonna, Sarsa Harri |
| rafferty2016pomdp | Cogn. Sci. 40(6):1290-1332, 2016 | 10.1111/cogs.12290 | Rafferty Anna N., Brunskill Emma, Griffiths Thomas L., Shafto Patrick |
| nafchi2025digitalfatigue | ACC Journal 31(2):59-69, 2025 | 10.2478/acc-2025-0010 | Nafchi Majid Ziaei |

### 1.2 Crossref 标题检索补 DOI（4 条，全部 `[已核验]`）

| bib key | 载体 / 卷期页 / 年 | DOI | 作者 |
|---|---|---|---|
| guadagnoli2004challengepoint | J. Mot. Behav. 36(2):212-224, 2004 | 10.3200/jmbr.36.2.212-224 | Guadagnoli Mark A., Lee Timothy D. |
| hodges2022extendedchallenge | J. Sports Sci. 40(7):754-768, 2022 | 10.1080/02640414.2021.2015917 | Hodges Nicola J, Lohse Keith R |
| feng2009assistments | User Model. User-Adapt. Interact. 19(3):243-266, 2009 | 10.1007/s11257-009-9063-7 | Feng Mingyu, Heffernan Neil, Koedinger Kenneth |
| zhang2021theoryintegration | J. Med. Internet Res. 23(4):e17127, 2021 | 10.2196/17127 | Zhang Chao, Lakens Daniël, IJsselsteijn Wijnand A. |

### 1.3 arXiv API（8 条）

| bib key | 状态 | 标识符 | 作者（已补全名） |
|---|---|---|---|
| raihan2025llmcsed | 预印本，未正式发表 | arXiv:2410.16349 (2024-10-21) | Nishat Raihan, Mohammed Latif Siddiq, Joanna C. S. Santos, Marcos Zampieri |
| kcgenkt2025 | **v4 预印本，未正式发表** | arXiv:2502.18632v4 (更新 2026-05-17) | Zhangqi Duan, Nigel Fernandez, Arun Balajiee Lekshmi Narayanan, Mohammad Hassany, Rafaella Sampaio de Alencar, Peter Brusilovsky, Bita Akram, Andrew Lan |
| kone2024banditpareto | journal_ref = AISTATS 2024 | arXiv:2311.03992v2 | Cyrille Kone, Emilie Kaufmann, Laura Richert |
| kone2025constrainedpareto | 预印本，未正式发表 | arXiv:2506.08127v1 (2025-06-09) | Cyrille Kone, Emilie Kaufmann, Laura Richert |
| kim2025morlportfolios | 预印本，未正式发表 | arXiv:2502.09724v2 (更新 2025-07-16) | Cheol Woo Kim, Jai Moondra, Shresth Verma, Madeleine Pollack, Lingkai Kong, Milind Tambe, Swati Gupta |
| ballon2025estimating | 预印本，未正式发表 | arXiv:2512.14220v1 (2025-12-16) | Marthe Ballon, Andres Algaba, Brecht Verbeken, Vincent Ginis |
| ~~li2025canllms~~ → `li2026canllms` | **已正式发表**（2026-09-27 复核推翻首轮判断） | **Findings of ACL 2026**, pp. 25414–25441, DOI 10.18653/v1/2026.findings-acl.1270（权威源 = ACL Anthology 2026.findings-acl.1270）；预印本 arXiv:2512.18880v2 仅作辅助 | Ming Li, Han Chen, Yunze Xiao, Jian Chen, Hong Jiao, Tianyi Zhou（**注：`author` 字段原写 Xiao, Yan / Chen, Jia / Jiao, Hao / Zhou, Tian 四位名字全错，已更正**） |
| parfenova2025textannotation | **已正式发表** NAACL 2025 Findings | arXiv:2512.00046v1；DOI 10.18653/v1/2025.findings-naacl.361 | Angelina Parfenova, Andreas Marfurt, Alexander Denzler, Juergen Pfeffer |

### 1.4 WebSearch 补无标识符条目（7 条，全部 `[已核验]`）

| bib key | 载体 / 卷期页 / 年 | DOI | 备注 |
|---|---|---|---|
| neurips2017posetbandits | NeurIPS 2017, pp.2129-2138 | — | 作者 Audiffren Julien, Ralaivola Liva；**页码仲裁见 §3** |
| sensors2026flowbalance | Sensors 2026, 26(1):38 | 10.3390/s26010038 | 作者 Rosas David Antonio, Padilla-Zea Natalia, Burgos Daniel |
| reymond2024bestarm | AAMAS '24, pp.1611-1620 | — | IFAAMAS/ACM |
| chang2015junyi | EDM 2015, pp.532-535 | — | ISBN 978-8-4606-9425-0；数据集 CC-BY-NC-SA-4.0（禁商用） |
| mazarakis2024whichone | Int. J. Hum.-Comput. Interact. 39(3):612-627, **2023** | 10.1080/10447318.2022.2041909 | 作者 Mazarakis Athanasios, Bräuer Paula；**bib 原记 year=2024 已更正为 2023** |
| hepp2018originstamp | it - Inf. Technol. 60(5-6):273-281, 2018 | 10.1515/itit-2018-0020 | 作者 Hepp Thomas, Schoenhals Alexander, Gondek Christopher, Gipp Bela |
| preprints2025dlktreview | Preprints.org 预印本 202510.1845, 2025-10 | 10.20944/preprints202510.1845.v1 | **非同行评议预印本** |

### 1.5 技术报告（1 条，`[已核验]`）

| bib key | 载体 | 标识符 | 备注 |
|---|---|---|---|
| baillifard2025engagement | EADTU《Envisioning Report for Empowering Universities》, 2025 | 无 DOI/ISBN（公开记录未见） | 作者 Baillifard Alexandra, Belardi Alessia, Martarelli Corinna S.；**非同行评议机构报告**，引用须注明来源等级；n=413，最优成功率≈80.7% |

---

## 2. 部分核验 / 待作者确认（1 条 → 已闭环）

- ~~**`dellanna2025`**（LUMAT-B: Int. J. Math. Sci. Technol. Educ. 31, 2025；MAVI 31, Växjö；article 2841, University of Helsinki）~~
  - ~~**作者名冲突**：`references.bib` 原记 `Dell'Anna, Silvia`；WebSearch 检索源记 `Helena Dell'Anna`。合作者 Domenico Brunetto, Ralucca Gera 一致。~~
  - ✅ **2026-09-23 闭环（无需再等作者确认，出版方双源已定案）**：条目已重命名为 `dellanna2026flowframing`，著录为 **Dell'Anna, H., Brunetto, D., & Gera, R. (2026). Integrating flow framework into learning and development systems. *LUMAT-B*, 11(2), Article 23.** https://journals.helsinki.fi/lumatb/article/view/2841
  - **定案依据**：出版方 OJS 文章页 + OAI-PMH `dc:creator` + 版权行三处一致为 **Helena Dell'Anna**（附 ORCID 0009-0009-0463-1567）；OJS 作者检索 `query=Dell'Anna` 仅返回本条。**Silvia 在任何权威源中均检索不到**（OpenAlex 作者检索亦无；arXiv `au:"Dell'Anna"` 95 条命中全为 Luca/Federico 等物理与医学方向作者，与教育方向无关），故按无源支持删除。
  - **连带更正三处**：① 出版年 **2026** 非 2025（Published 2026-05-06）；② 原「31」是 **MAVI 届次**（第 31 届 International Conference on Mathematical Views, Växjö 2025-09），**不是卷号**，真实卷期 **11(2)**，文章号 **23**；③ 该刊**未为该文注册 DOI**（Crossref 无该 ISSN 记录、OAI/文章页/DataCite 均无），以稳定 URL 代替，**不得虚构 DOI**。
  - **已同步**：M3 完整稿 `[10]` 条目与 §2.4 正文引用（2025 → 2026）。

---

## 3. 高风险条目澄清（待办 §4 标 3 条，均非误填）

1. **`razzaq2026blockchain` — DOI 前缀 `sfw2`**：`10.1049/sfw2/5556408` 经 Crossref 直查返回有效记录（IET Software 2026(1)），属 IET 正常 DOI 前缀，**非异常**。原 `[VERIFY]` 疑虑已消除。
2. **`baillifard2025engagement` — 非同行评议年度报告**：确认为 EADTU 机构技术报告（非期刊论文），公开记录未见 DOI/ISBN，本库不填；引用处须注明来源等级（已在 note 固化）。
3. **`kcgenkt2025` — 版本 v4**：arXiv:2502.18632**v4**（更新 2026-05-17），`journal_ref` 与 `doi` 均为空，**仍为预印本未正式发表**；note 已标注，避免被误写为期刊版本。

### 页码仲裁
- **`neurips2017posetbandits`**：ACM DL 元数据页误标 `2126-2135`；NeurIPS 官方 Proceedings（Advances in Neural Information Processing Systems 30）与 dblp / ML Anthology 一致为 **2129-2138**。采官方值，并在 note 注明差异。

---

## 4. 预印本 / 非同行评议清单（引用须注明状态）

| bib key | 类型 | 正式发表？ |
|---|---|---|
| raihan2025llmcsed | arXiv 预印本 | 否 |
| kcgenkt2025 | arXiv 预印本 (v4) | 否 |
| kone2025constrainedpareto | arXiv 预印本 | 否 |
| kim2025morlportfolios | arXiv 预印本 | 否 |
| ballon2025estimating | arXiv 预印本 | 否 |
| ~~li2025canllms~~ `li2026canllms` | ~~arXiv 预印本~~ **Findings of ACL 2026（会议版）** | ~~否~~ **是**（同行评议，2026-07 出版，DOI 10.18653/v1/2026.findings-acl.1270） |
| preprints2025dlktreview | Preprints.org 预印本 | 否（明确非同行评议） |
| baillifard2025engagement | EADTU 技术报告 | 否（非同行评议机构报告） |
| kone2024banditpareto | AISTATS 2024（journal_ref 已记录，PMLR 卷页以正式 Proceedings 为准） | 会议收录 |
| parfenova2025textannotation | NAACL 2025 Findings | **是**（DOI 已补） |

> 建议：投稿前对 8 条预印本/报告类，在正文引用处显式标注「preprint / tech report, non-peer-reviewed」；`preprints2025dlktreview` 的断言应回溯其引用的一次文献（[77][78][44][45][56][30]）以替代预印本表述。

---

## 5. 仍待外部 / 作者动作

| 项 | 责任 | 说明 |
|---|---|---|
| ~~`dellanna2025` 作者名确认~~ | ~~作者~~ | ✅ **已闭环（2026-09-23）**：出版方双源定案为 Helena Dell'Anna，条目已更正为 `dellanna2026flowframing`（2026, 11(2), Article 23，无 DOI 用 URL）。**无需作者动作** |
| 8 条预印本正式发表追踪 | 投稿前 | 若已正式发表，回填期刊卷页/DOI 并升级 `[已核验]` |
| `baillifard2025engagement` 引用标注 | 作者 | 正文注明非同行评议来源等级 |

> 其余 29 条元数据已闭环，可直接进入投稿参考文献终校。
