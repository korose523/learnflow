import re, os

BIB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "references.bib"))
with open(BIB, encoding="utf-8") as f:
    text = f.read()

# ---- parse entries with absolute offsets ----
entries = {}
pat = re.compile(r'@(\w+)\s*\{\s*([^,]+),', re.MULTILINE)
for m in pat.finditer(text):
    key = m.group(2).strip()
    start = m.start()
    depth = 1; i = m.end()
    while i < len(text) and depth > 0:
        c = text[i]
        if c == '{': depth += 1
        elif c == '}': depth -= 1
        i += 1
    end = i  # index just after closing brace
    entries[key] = (start, end)

def note_inner_span(body, body_abs_start):
    p = body.find('note')
    while p != -1:
        if body[p:p+4] == 'note':
            q = body.find('=', p)
            if q != -1:
                r = body.find('{', q)
                if r != -1:
                    depth = 0; i = r
                    while i < len(body):
                        if body[i] == '{': depth += 1
                        elif body[i] == '}':
                            depth -= 1
                            if depth == 0:
                                return (body_abs_start + r + 1, body_abs_start + i)
                        i += 1
        p = body.find('note', p+1)
    return None

# ---- new note contents (no raw braces; unicode accents used) ----
NEW_NOTES = {
"liu2025pykt":
"[已核验] IEEE Trans. Knowl. Data Eng. 37(8):4512-4536, 2025. DOI: 10.1109/TKDE.2025.3552759. CCF-A. 作者：Liu Zitao, Guo Teng, Liang Qianru, Hou Mingliang, Zhan Bojun, Tang Jiliang, Luo Weiqi, Weng Jian. 9 个数据集、21 个 DLKT 模型、开源 pyKT 工具包",
"choudhary2025blockchain":
"[已核验] Multimedia Tools Appl. 84(8):4003-4048, 2024. DOI: 10.1007/s11042-024-20303-x. 作者：Choudhary Ankita, Chawla Meenu, Tiwari Namita. PRISMA 系统综述. 关键数据：150 个模型中 124 个为原型/试点、26 个仅为提案",
"razzaq2026blockchain":
"[已核验] IET Software 2026(1), 2026. DOI: 10.1049/sfw2/5556408（前缀 sfw2 经 Crossref 核验有效，非异常）. 作者：Razzaq Abdul, Numair Muhammad, Ahmed Salman, Junaid Waqas. 64 项研究 (2017-2025). 应用类别：证书/文凭管理、微证书与学分转移、能力与评估追踪——注意：无「算法决策审计」类",
"jusic2025microcredential":
"[已核验] EDULEARN Proc. 1:5382-5388, 2025. DOI: 10.21125/edulearn.2025.1342. 作者：Jusic Arvin, Fuks Svetlana, Kochovski Petar, Stankovski Vlado. 综述 EBSI、ESSA、NOO Ultra、TRUSTCHAIN、FRI Academy. 结论：微证书/学分互认赛道已被制度化占据，LearnFlow 不应进入",
"lieberoth2015shallow":
"[已核验] Games Cult. 10(3):229-248, 2015. DOI: 10.1177/1555412014559978. N=90. framing 单独即可产生与完整游戏机制相当的兴趣/享受效果. 威胁：LearnFlow 60 个机制的效果可能大部分来自框架效应. 机会：N=90 短时实验室；真实生产系统上的长期复制/否证有明确价值",
"falconcode2022":
"[已核验] SIGCSE TS 2023, pp.938-944 (Proc. 54th ACM Tech. Symp. Comput. Sci. Educ. V.1). DOI: 10.1145/3545945.3569822. 作者：de Freitas Adrian, Coffman Joel, de Freitas Michelle, Wilson Justin, Weingart Troy. 数据规模：3,267 名学生 / 157 题 / 20 个知识组件",
"hamari2014doesgamification":
"[已核验] HICSS 2014, pp.3025-3034. DOI: 10.1109/HICSS.2014.377. 会议 2014-01-06 至 01-09, Waikoloa, HI, USA. Electronic ISBN 978-1-4799-2504-9. 核心结论：游戏化具正向效应，但效应高度依赖实施情境与使用者",
"rafferty2016pomdp":
"[已核验] Cogn. Sci. 40(6):1290-1332, 2016. DOI: 10.1111/cogs.12290. 作者：Rafferty Anna N., Brunskill Emma, Griffiths Thomas L., Shafto Patrick",
"nafchi2025digitalfatigue":
"[已核验] ACC Journal 31(2):59-69, 2025. DOI: 10.2478/acc-2025-0010. 作者：Nafchi Majid Ziaei",
"guadagnoli2004challengepoint":
"[已核验] J. Mot. Behav. 36(2):212-224, 2004. DOI: 10.3200/jmbr.36.2.212-224. 作者：Guadagnoli Mark A., Lee Timothy D.",
"hodges2022extendedchallenge":
"[已核验] J. Sports Sci. 40(7):754-768, 2022. DOI: 10.1080/02640414.2021.2015917. 作者：Hodges Nicola J, Lohse Keith R",
"feng2009assistments":
"[已核验] User Model. User-Adapt. Interact. 19(3):243-266, 2009. DOI: 10.1007/s11257-009-9063-7. 作者：Feng Mingyu, Heffernan Neil, Koedinger Kenneth",
"zhang2021theoryintegration":
"[已核验] J. Med. Internet Res. 23(4):e17127, 2021. DOI: 10.2196/17127. 作者：Zhang Chao, Lakens Daniel, IJsselsteijn Wijnand A. (PMCID: PMC8065564)",
"raihan2025llmcsed":
"[已核验] 预印本 arXiv:2410.16349 (2024-10-21). 作者：Nishat Raihan, Mohammed Latif Siddiq, Joanna C. S. Santos, Marcos Zampieri. 篇幅 7 页. SIGCSE TS 是 CS 教育第一顶会（未被 CCF 列表收录）. 尚未正式发表，引用须注明预印本状态",
"kcgenkt2025":
"[已核验] 预印本 arXiv:2502.18632v4 (更新 2026-05-17). 作者：Zhangqi Duan, Nigel Fernandez, Arun Balajiee Lekshmi Narayanan, Mohammad Hassany, Rafaella Sampaio de Alencar, Peter Brusilovsky, Bita Akram, Andrew Lan. 数据规模：CodeWorkout（246 学生 / 50 题 / 10,834 次首次提交）+ FalconCode（3,267 学生 / 157 题 / 28,617 次提交）；用 CodeBLEU 评估. v4 仍为预印本，未正式发表（journal_ref 空、doi 空）. 缺口：LLM 生成的 KC 只用于追踪，未反馈到难度选择",
"kone2024banditpareto":
"[已核验] arXiv:2311.03992v2；journal_ref = AISTATS 2024（PMLR 卷号与页码以正式 Proceedings 为准）. 作者：Cyrille Kone, Emilie Kaufmann, Laura Richert",
"kone2025constrainedpareto":
"[已核验] 预印本 arXiv:2506.08127v1 (2025-06-09). 作者：Cyrille Kone, Emilie Kaufmann, Laura Richert. 尚未正式发表（journal_ref 空、doi 空）",
"kim2025morlportfolios":
"[已核验] 预印本 arXiv:2502.09724v2 (更新 2025-07-16). 作者：Cheol Woo Kim, Jai Moondra, Shresth Verma, Madeleine Pollack, Lingkai Kong, Milind Tambe, Swati Gupta. 尚未正式发表",
"ballon2025estimating":
"[已核验] 预印本 arXiv:2512.14220v1 (2025-12-16). 作者：Marthe Ballon, Andres Algaba, Brecht Verbeken, Vincent Ginis. 尚未正式发表",
"li2025canllms":
"[已核验] 预印本 arXiv:2512.18880v2 (更新 2026-05-10). 作者：Ming Li, Han Chen, Yunze Xiao, Jian Chen, Hong Jiao, Tianyi Zhou. 尚未正式发表",
"parfenova2025textannotation":
"[已核验] NAACL 2025 Findings；arXiv:2512.00046v1；DOI: 10.18653/v1/2025.findings-naacl.361. 作者：Angelina Parfenova, Andreas Marfurt, Alexander Denzler, Juergen Pfeffer",
"neurips2017posetbandits":
"[已核验] NeurIPS 2017, pp.2129-2138 (Advances in Neural Information Processing Systems 30). 作者：Audiffren Julien, Ralaivola Liva. 算法名 UnchainedBandits，引入 decoy 概念. 注意：NeurIPS 审稿意见指出该设定对含环 social poset 处理不自然、Pareto 前沿可能为空——引用时须诚实呈现此局限. 注：ACM DL 元数据页标 2126-2135，与 NeurIPS 官方 Proceedings 2129-2138 不一致，采官方值",
"sensors2026flowbalance":
"[已核验] Sensors 2026, 26(1):38. DOI: 10.3390/s26010038. 作者：Rosas David Antonio, Padilla-Zea Natalia, Burgos Daniel. MDPI. 心流通道效度存疑的关键证据来源",
"reymond2024bestarm":
"[已核验] AAMAS '24, pp.1611-1620 (Proc. 23rd Int. Conf. Auton. Agents Multiagent Syst., IFAAMAS/ACM). 作者：Reymond Mathieu, Bargiacchi Eugenio, Roijers Diederik M., Nowe Ann",
"chang2015junyi":
"[已核验] EDM 2015, pp.532-535 (Proc. 8th Int. Conf. Educ. Data Mining). ISBN 978-8-4606-9425-0. 亦见 Educational Technology & Society 18(2), 128-141（M1 稿所引载体）. 数据集 CC-BY-NC-SA-4.0，禁商用. 会议论文集无卷期",
"dellanna2025":
"[部分核验] LUMAT-B: Int. J. Math. Sci. Technol. Educ. 31, 2025 (MAVI 31, Vaxjo; article 2841, University of Helsinki). 作者存疑：bib 记 Dell'Anna Silvia / 检索源记 Helena Dell'Anna；合作者 Domenico Brunetto, Ralucca Gera. 需作者确认姓名. 题名以正式出版为准",
"mazarakis2024whichone":
"[已核验] Int. J. Hum.-Comput. Interact. 39(3):612-627, 2023. DOI: 10.1080/10447318.2022.2041909. 作者：Mazarakis Athanasios, Brauer Paula. Kiel University. N=505，最多 190 道多选题. 核心发现：单个机制各有显著动机增益，但组合效应不等于各机制效应之和. 注：bib 原记 year=2024，实为期刊 2023 卷（online 2022）；已更正为 2023",
"preprints2025dlktreview":
"[已核验] Preprints.org 预印本（manuscript 202510.1845），2025-10；DOI: 10.20944/preprints202510.1845.v1. 未经同行评议. 核心数据：82.1% 的 KT 研究仅用 ASSIST 系列数据集；56.0% 未处理数据质量问题；仅 3.6% 使用定量序列稳定性指标；90.5% 仅报告 AUC. 注：同行评议状态=否（Preprints.org 为预印本平台）；应回溯其原始引用 [77][78][44][45][56][30] 定位一次文献，用一次文献替代预印本断言",
"hepp2018originstamp":
"[已核验] it - Inf. Technol. 60(5-6):273-281, 2018. DOI: 10.1515/itit-2018-0020. 作者：Hepp Thomas, Schoenhals Alexander, Gondek Christopher, Gipp Bela. 机制（已由 docs.originstamp.com 官方文档与 2018-11-26 白皮书 v2 独立核实）：本地 SHA-256 → 固定间隔批收集哈希 → 字典序排序 → 平衡 Merkle 树 → 根写入区块链",
"baillifard2025engagement":
"[已核验] EADTU《Envisioning Report for Empowering Universities》, 2025（techreport，非期刊论文）. 作者：Baillifard Alexandra, Belardi Alessia, Martarelli Corinna S. 无卷期；公开记录未见 DOI/ISBN（本库不填）. 非同行评议机构报告；引用处须注明来源等级. n=413，最优成功率约 80.7%",
}

# ---- collect splice operations on ORIGINAL text ----
ops = []  # (start, end, newtext)

# note inner replacements
for key, content in NEW_NOTES.items():
    if key not in entries:
        print("WARN key not found:", key); continue
    s, e = entries[key]
    body = text[s:e]
    span = note_inner_span(body, s)
    if span is None:
        print("WARN no note field for:", key); continue
    ops.append((span[0], span[1], content))

# ---- structured-field insertions (before the note line) ----
def insert_before_note(key, snippet):
    s, e = entries[key]
    body = text[s:e]
    p = body.find('note')
    # align to line start of 'note'
    line_start = body.rfind('\n', 0, p) + 1
    abs_pos = s + line_start
    ops.append((abs_pos, abs_pos, snippet))

insert_before_note("neurips2017posetbandits",
    "  author    = {Audiffren, Julien and Ralaivola, Liva},\n  pages     = {2129--2138},\n")
insert_before_note("sensors2026flowbalance",
    "  author    = {Rosas, David Antonio and Padilla-Zea, Natalia and Burgos, Daniel},\n  doi       = {10.3390/s26010038},\n")
insert_before_note("reymond2024bestarm",
    "  pages     = {1611--1620},\n")
insert_before_note("preprints2025dlktreview",
    "  doi       = {10.20944/preprints202510.1845.v1},\n")
insert_before_note("hepp2018originstamp",
    "  doi       = {10.1515/itit-2018-0020},\n")

# ---- mazarakis full rewrite (year was wrong + missing journal/vol/pages/doi) ----
MAZ = """@article{mazarakis2024whichone,
  author    = {Mazarakis, Athanasios and Br{\\"a}uer, Paula},
  title     = {Gamification is Working, but Which One Exactly? Results from an Experiment with Four Game Design Elements},
  journal   = {International Journal of Human-Computer Interaction},
  volume    = {39},
  number    = {3},
  pages     = {612--627},
  year      = {2023},
  doi       = {10.1080/10447318.2022.2041909},
  note      = {[已核验] Int. J. Hum.-Comput. Interact. 39(3):612-627, 2023. DOI: 10.1080/10447318.2022.2041909. 作者：Mazarakis Athanasios, Brauer Paula. Kiel University. N=505，最多 190 道多选题. 核心发现：单个机制各有显著动机增益，但组合效应不等于各机制效应之和. 注：bib 原记 year=2024，实为期刊 2023 卷（online 2022）；已更正为 2023}
}"""
s, e = entries["mazarakis2024whichone"]
ops.append((s, e, MAZ))

# ---- apply splices descending by start ----
ops.sort(key=lambda o: o[0], reverse=True)
new_text = text
for (a, b, c) in ops:
    new_text = new_text[:a] + c + new_text[b:]

# write back to original
with open(BIB, "w", encoding="utf-8") as f:
    f.write(new_text)

print("WROTE", BIB)
print("ops applied:", len(ops))
